import json
import logging
import pathlib
import threading
from typing import TYPE_CHECKING, ClassVar, Self, TypeGuard, cast

from src.game_data.item_type import ItemType
from src.settings import BASE_DIR, get_settings

if TYPE_CHECKING:
    from src.type_aliases import JsonObject, JsonValue

LOGGER = logging.getLogger(__name__)
GAME_CATALOG_LOCK = threading.RLock()


def _is_string_map(value: JsonValue) -> TypeGuard[dict[str, str]]:
    return isinstance(value, dict) and all(
        isinstance(key, str) and isinstance(item, str) for key, item in value.items()
    )


def _load_string_map(path: pathlib.Path) -> dict[str, str]:
    with path.open(encoding="utf-8") as file:
        data = cast("JsonValue", json.load(file))
    if not _is_string_map(data):
        msg = f"Expected a JSON object containing only string keys and values: {path}"
        raise ValueError(msg)
    return data


class GameCatalog:
    """Localized Diablo 4 reference data shared by the Item and Profiles capabilities."""

    affix_dict: dict[str, str] = {}
    charm_affix_dict: dict[str, str] = {}
    seal_affix_dict: dict[str, str] = {}
    english_affix_dict: dict[str, str] = {}
    english_charm_affix_dict: dict[str, str] = {}
    english_seal_affix_dict: dict[str, str] = {}
    affix_sigil_dict: dict[str, str] = {}
    affix_sigil_dict_all: dict[str, dict[str, str]] = {}
    sigil_name_aliases: dict[str, str] = {}
    aspect_list: list[str] = []
    aspect_name_aliases: dict[str, str] = {}
    aspect_display_names: dict[str, str] = {}
    aspect_unique_dict: JsonObject = {}
    unique_name_aliases: dict[str, str] = {}
    bad_tts_uniques: dict[str, str] = {}
    filter_after_keyword: list[str] = []
    filter_words: list[str] = []
    item_types_dict: dict[str, str] = {}
    set_list: list[str] = []
    set_name_aliases: dict[str, str] = {}
    tooltips: JsonObject = {}
    tribute_dict: dict[str, str] = {}
    tribute_name_aliases: dict[str, str] = {}

    _instance: ClassVar[Self | None] = None
    data_loaded = False

    def __new__(cls) -> Self:
        with GAME_CATALOG_LOCK:
            if cls._instance is None:
                instance = super().__new__(cls)
                instance.data_loaded = False
                cls._instance = instance
                try:
                    instance.load_data()
                except BaseException:
                    cls._instance = None
                    instance.data_loaded = False
                    raise
                instance.data_loaded = True
            return cls._instance

    def load_data(self) -> None:
        language_dir = pathlib.Path(BASE_DIR / f"assets/lang/{get_settings().general.language}")
        self.affix_dict = _load_string_map(language_dir / "affixes.json")
        self.seal_affix_dict = _load_string_map(language_dir / "seals_affixes.json")
        self.charm_affix_dict = _load_string_map(language_dir / "charms_affixes.json")
        english_dir = pathlib.Path(BASE_DIR / "assets/lang/enUS")
        self.english_affix_dict = _load_string_map(english_dir / "affixes.json")
        self.english_seal_affix_dict = _load_string_map(english_dir / "seals_affixes.json")
        self.english_charm_affix_dict = _load_string_map(english_dir / "charms_affixes.json")

        self.aspect_list = cast("list[str]", self._load_json(language_dir / "aspects.json"))
        corrections = cast("JsonObject", self._load_json(language_dir / "corrections.json"))
        self.filter_after_keyword = cast("list[str]", corrections["filter_after_keyword"])
        self.filter_words = cast("list[str]", corrections["filter_words"])
        self.bad_tts_uniques = cast("dict[str, str]", corrections["bad_tts_uniques"])

        self.item_types_dict = cast("dict[str, str]", self._load_json(language_dir / "item_types.json"))
        for item in self.item_types_dict:
            if item not in ItemType.__members__:
                LOGGER.warning("%s type not in item_type.py", item)

        self.affix_sigil_dict_all = cast("dict[str, dict[str, str]]", self._load_json(language_dir / "sigils.json"))
        self.affix_sigil_dict = {
            key: value
            for section in ("dungeons", "minor", "major", "positive")
            for key, value in self.affix_sigil_dict_all[section].items()
        }
        self.sigil_name_aliases = self.affix_sigil_dict_all.get("aliases", {})
        self.tribute_dict = _load_string_map(language_dir / "tributes.json")
        self.tooltips = cast("JsonObject", self._load_json(language_dir / "tooltips.json"))
        self.aspect_unique_dict = cast("JsonObject", self._load_json(language_dir / "uniques.json"))
        self.unique_name_aliases = self._unique_name_aliases(self.aspect_unique_dict)
        self.set_list = cast("list[str]", self._load_json(language_dir / "sets.json"))
        aliases = cast("dict[str, dict[str, str]]", self._load_optional_json(language_dir / "aliases.json", {}))
        self.aspect_name_aliases = aliases.get("aspects", {})
        display_candidates: dict[str, list[str]] = {}
        for localized_name, canonical_name in self.aspect_name_aliases.items():
            display_candidates.setdefault(canonical_name, []).append(localized_name.replace("_", " "))
        self.aspect_display_names = {
            canonical_name: min(names, key=lambda name: (len(name), name))
            for canonical_name, names in display_candidates.items()
        }
        self.aspect_display_names.update(aliases.get("aspect_labels", {}))
        self.set_name_aliases = aliases.get("sets", {})
        self.tribute_name_aliases = aliases.get("tributes", {})

    @staticmethod
    def _unique_name_aliases(unique_data: JsonObject) -> dict[str, str]:
        aliases = {}
        for canonical_name, value in unique_data.items():
            if not isinstance(value, dict):
                continue
            localized_name = value.get("localized_name")
            if isinstance(localized_name, str) and localized_name:
                aliases[localized_name] = canonical_name
        return aliases

    def item_type_label(self, item_type: ItemType) -> str:
        """Return the current localized display label for an item type."""
        return self.item_types_dict.get(item_type.name, item_type.value)

    def aspect_label(self, canonical_name: str) -> str:
        return self.aspect_display_names.get(canonical_name, canonical_name.replace("_", " "))

    def unique_label(self, canonical_name: str) -> str:
        value = self.aspect_unique_dict.get(canonical_name)
        if isinstance(value, dict):
            localized_name = value.get("localized_name")
            if isinstance(localized_name, str) and localized_name:
                return localized_name.replace("_", " ")
        return canonical_name.replace("_", " ")

    def item_type_names(self, item_type: ItemType) -> tuple[str, ...]:
        """Return accepted enum name, canonical value, and localized label for an item type."""
        return tuple(dict.fromkeys((item_type.name, item_type.value, self.item_type_label(item_type))))

    def item_type_from_text(self, value: str) -> ItemType | None:
        """Resolve an enum name, canonical value, or localized catalog label to an item type."""
        normalized = value.strip().casefold()
        if not normalized:
            return None

        for item_type in ItemType:
            if normalized in {item_type.name.casefold(), item_type.value.casefold()}:
                return item_type

        for item_type in ItemType:
            if normalized == self.item_type_label(item_type).strip().casefold():
                return item_type
        return None

    @staticmethod
    def _load_json(path: pathlib.Path) -> JsonValue:
        with path.open(encoding="utf-8") as file:
            return cast("JsonValue", json.load(file))

    @staticmethod
    def _load_optional_json(path: pathlib.Path, default: JsonValue) -> JsonValue:
        if not path.exists():
            return default
        return GameCatalog._load_json(path)
