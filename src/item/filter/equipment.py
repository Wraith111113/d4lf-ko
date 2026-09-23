import logging
from typing import TYPE_CHECKING

from src.game_data import GameCatalog
from src.item import ASPECT_UPGRADES_LABEL
from src.item.data.affix import AffixType
from src.item.models import FilterResult, MatchedFilter
from src.settings import AspectFilterType, UnfilteredUniquesType

if TYPE_CHECKING:
    from src.item.filter.matching import FilterContext
    from src.item.models import Item

LOGGER = logging.getLogger(__name__)


class FilterEquipmentMixin:
    def _check_affixes(self: FilterContext, item: Item) -> FilterResult:
        res = FilterResult(keep=False, matched=[])
        if not self.affix_filters:
            return FilterResult(keep=False, matched=[])
        non_tempered_affixes = [affix for affix in item.affixes if affix.type != AffixType.tempered]
        for profile_name, profile_filter in self.affix_filters.items():
            for filter_item in profile_filter:
                filter_name = next(iter(filter_item.root.keys()))
                filter_spec = filter_item.root[filter_name]
                if not self._match_item_type(filter_spec.item_type, item.item_type):  # check item type
                    LOGGER.debug(
                        "%s -- Profile miss %s.Affixes.%s: item type mismatch (item=%s, profile=%s)",
                        item.original_name,
                        profile_name,
                        filter_name,
                        item.item_type.value if item.item_type else None,
                        [item_type.value for item_type in filter_spec.item_type],
                    )
                    continue
                if filter_spec.rarities and item.rarity not in filter_spec.rarities:  # check item rarity
                    continue
                if not self._match_item_power(filter_spec.min_power, item.power):  # check item power
                    continue
                if not self._match_greater_affix_count(  # check greater affixes
                    filter_spec.min_greater_affix_count, non_tempered_affixes
                ):
                    LOGGER.info(
                        "%s -- Profile miss %s.Affixes.%s: greater affixes %d/%d",
                        item.original_name,
                        profile_name,
                        filter_name,
                        sum(affix.type == AffixType.greater for affix in non_tempered_affixes),
                        filter_spec.min_greater_affix_count,
                    )
                    continue
                if not self._check_unique_aspects_for_item(item, filter_spec.unique_aspect):
                    LOGGER.info(
                        "%s -- Profile miss %s.Affixes.%s: unique aspect mismatch (item=%s, expected=%s)",
                        item.original_name,
                        profile_name,
                        filter_name,
                        item.aspect.name if item.aspect else None,
                        [aspect.name for aspect in filter_spec.unique_aspect],
                    )
                    continue
                matched_affixes = []
                if filter_spec.affix_pool:
                    matched_affixes = self._match_affixes_count(
                        filter_spec.affix_pool, non_tempered_affixes, filter_spec.min_greater_affix_count
                    )
                    if not matched_affixes:
                        required_count = sum(group.min_count for group in filter_spec.affix_pool)
                        partial_matches = [
                            matched.name
                            for group in filter_spec.affix_pool
                            for _, matched in self._match_count_group(
                                group.model_copy(update={"min_count": 0}), non_tempered_affixes
                            )
                        ]
                        LOGGER.info(
                            "%s -- Profile miss %s.Affixes.%s: candidate matches %d/%d; "
                            "matched=%s; item=%s; required=%s; count or greater-affix requirements not met",
                            item.original_name,
                            profile_name,
                            filter_name,
                            len(partial_matches),
                            required_count,
                            partial_matches,
                            [affix.name for affix in non_tempered_affixes],
                            [affix.name for group in filter_spec.affix_pool for affix in group.count],
                        )
                        continue
                matched_inherents = []
                if filter_spec.inherent_pool:
                    matched_inherents = self._match_affixes_count(
                        filter_spec.inherent_pool, item.inherent, filter_spec.min_greater_affix_count
                    )
                    if not matched_inherents:
                        required_count = sum(group.min_count for group in filter_spec.inherent_pool)
                        LOGGER.info(
                            "%s -- Profile miss %s.Affixes.%s: inherent options matched 0/%d; item=%s; required=%s",
                            item.original_name,
                            profile_name,
                            filter_name,
                            required_count,
                            [affix.name for affix in item.inherent],
                            [affix.name for group in filter_spec.inherent_pool for affix in group.count],
                        )
                        continue
                all_matches = matched_affixes + matched_inherents
                affix_labels = GameCatalog().affix_dict
                match_details = [
                    f"{affix_labels.get(affix.name, affix.name)} (상급)"
                    if affix.type == AffixType.greater
                    else affix_labels.get(affix.name, affix.name)
                    for affix in all_matches
                ]
                LOGGER.info(f"{item.original_name} -- Matched {profile_name}.Affixes.{filter_name}: {match_details}")
                if filter_spec.unique_aspect:  # show the matched unique aspect
                    LOGGER.info(f"{item.original_name} -- Matched {profile_name}.Affixes.{filter_name}: Unique aspect")
                res.keep = True
                res.matched.append(
                    MatchedFilter(f"{profile_name}.{filter_name}", all_matches, bool(filter_spec.unique_aspect))
                )
        return res

    def _check_aspect_upgrades(self: FilterContext, item: Item) -> FilterResult:
        res = FilterResult(keep=False, matched=[])
        if item.codex_upgrade and self.aspect_upgrade_filters:
            for profile_name, profile_filter in self.aspect_upgrade_filters.items():
                if item.aspect and any(name == item.aspect.name for name in profile_filter):
                    LOGGER.info(f"{item.original_name} -- Matched build-specific aspects that updates codex")
                    res.keep = True
                    res.matched.append(MatchedFilter(f"{profile_name}.{ASPECT_UPGRADES_LABEL}", aspect_match=True))
            if res.keep:
                return res
        if self.evaluation_settings.keep_aspects == AspectFilterType.none or (
            self.evaluation_settings.keep_aspects == AspectFilterType.upgrade and not item.codex_upgrade
        ):
            return res
        LOGGER.info(f"{item.original_name} -- Matched Aspects that updates codex")
        res.keep = True
        res.matched.append(MatchedFilter(ASPECT_UPGRADES_LABEL, aspect_match=True))
        return res

    def _check_global_unique_filter(self: FilterContext, item: Item) -> FilterResult:
        res = FilterResult(keep=False, matched=[])
        if not self.global_unique_filters:
            keep = self.evaluation_settings.handle_uniques != UnfilteredUniquesType.junk
            return FilterResult(keep, [])
        for profile_name, profile_filter in self.global_unique_filters.items():
            for filter_item in profile_filter:
                if item.aspect is None:
                    continue
                if not self._match_item_power(filter_item.min_power, item.power):
                    continue
                if not self._match_greater_affix_count(filter_item.min_greater_affix_count, item.affixes):
                    continue
                if not self._match_item_roll_is_in_percent_range(filter_item.min_percent_of_aspect, item.aspect):
                    continue
                LOGGER.info(f"{item.original_name} -- Matched {profile_name}.GlobalUniques: {item.aspect.name}")
                res.keep = True
                matched_full_name = f"{profile_name}.{item.aspect.name}"
                if filter_item.profile_alias:
                    matched_full_name = f"{filter_item.profile_alias}.{item.aspect.name}"
                res.matched.append(MatchedFilter(matched_full_name, aspect_match=True))
        return res
