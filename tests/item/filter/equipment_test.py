import logging

from src.game_data import ItemRarity, ItemType
from src.item import Affix, Item
from src.profiles import AffixFilterCountModel, AffixFilterModel, ItemFilterModel, ProfileModel

from .conftest import _create_mocked_filter


def test_ring_partial_matches_are_reported_without_accepting_item(mocker, caplog) -> None:
    names = ["critical_strike_chance", "critical_strike_damage_multiplier", "attack_speed"]
    profile = ProfileModel(
        name="ring_test",
        affixes=[
            {
                "Ring": ItemFilterModel(
                    item_type=[ItemType.Ring],
                    affix_pool=[
                        AffixFilterCountModel(
                            count=[AffixFilterModel(name=name) for name in names], min_count=3, max_count=3
                        )
                    ],
                )
            }
        ],
    )
    test_filter = _create_mocked_filter(mocker)
    test_filter.affix_filters = {profile.name: profile.affixes}
    item = Item(
        item_type=ItemType.Ring,
        rarity=ItemRarity.Legendary,
        power=900,
        affixes=[Affix(name=name, value=5) for name in names[:2]],
    )
    with caplog.at_level(logging.INFO):
        assert not test_filter._check_affixes(item).keep
    assert "candidate matches 2/3" in caplog.text
    assert "critical_strike_damage_multiplier" in caplog.text
    item.affixes.append(Affix(name="attack_speed", value=5))
    assert test_filter._check_affixes(item).keep


def test_gloves_can_match_two_saved_options_without_a_greater_requirement(mocker, caplog) -> None:
    profile = ProfileModel(
        name="glove_test",
        affixes=[
            {
                "Gloves": ItemFilterModel(
                    item_type=[ItemType.Gloves],
                    min_greater_affix_count=1,
                    affix_pool=[
                        AffixFilterCountModel(
                            count=[
                                AffixFilterModel(name=name)
                                for name in (
                                    "critical_strike_damage_multiplier",
                                    "vulnerable_damage_multiplier",
                                    "physical_damage_multiplier",
                                    "critical_strike_chance",
                                )
                            ],
                            min_count=2,
                        )
                    ],
                )
            }
        ],
    )
    test_filter = _create_mocked_filter(mocker)
    test_filter.affix_filters = {profile.name: profile.affixes}
    item = Item(
        item_type=ItemType.Gloves,
        rarity=ItemRarity.Legendary,
        power=900,
        affixes=[
            Affix(name="attack_speed", value=11.5),
            Affix(name="vulnerable_damage_multiplier", value=40),
            Affix(name="critical_strike_damage_multiplier", value=61),
        ],
    )
    with caplog.at_level(logging.INFO):
        assert not test_filter._check_affixes(item).keep
    assert "greater affixes 0/1" in caplog.text

    profile.affixes[0].root["Gloves"].min_greater_affix_count = 0
    assert test_filter._check_affixes(item).keep
