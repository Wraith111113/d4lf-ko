from src.game_data import GameCatalog, ItemRarity, ItemType
from src.item import Item
from src.perception.parser.details import (
    _get_affix_from_text,
    _get_affix_starting_location_from_tts_section,
    _get_aspect_from_name,
    _get_item_rarity,
    _get_item_type,
    _get_set_from_text,
)


def test_parser_details_maps_rarity_and_item_type_labels() -> None:
    assert _get_item_rarity("legendary") is ItemRarity.Legendary
    assert _get_item_type("sword") is ItemType.Sword


def test_parser_details_accepts_item_type_enum_names_and_catalog_labels(monkeypatch) -> None:
    catalog = GameCatalog()
    monkeypatch.setattr(catalog, "item_types_dict", {**catalog.item_types_dict, "Incense": "Encens"})

    assert _get_item_type("Incense") is ItemType.Incense
    assert _get_item_type("incense") is ItemType.Incense
    assert _get_item_type("Encens") is ItemType.Incense


def test_parser_details_resolves_localized_aspect_and_set_aliases(monkeypatch) -> None:
    catalog = GameCatalog()
    monkeypatch.setattr(catalog, "aspect_name_aliases", {"시험의_위상": "aspect_of_testing"})
    monkeypatch.setattr(catalog, "set_name_aliases", {"시험의_무장": "arms_of_testing"})
    monkeypatch.setattr(catalog, "set_list", ["arms_of_testing"])

    aspect = _get_aspect_from_name("시험의 위상", "Legendary Gloves")

    assert aspect is not None
    assert aspect.name == "aspect_of_testing"
    assert _get_set_from_text("시험의 무장") == "arms_of_testing"


def test_parser_details_resolves_localized_aspect_prefix_in_item_name(monkeypatch) -> None:
    catalog = GameCatalog()
    monkeypatch.setattr(catalog, "aspect_name_aliases", {"라트마의_선택받은_자의": "of_rathmas_chosen"})
    monkeypatch.setattr(catalog, "aspect_list", [])

    aspect = _get_aspect_from_name(
        "각인: 피 기술의 공격 속도가 증가합니다.", "라트마의_선택받은_자의_태초의_팔목_장갑"
    )

    assert aspect is not None
    assert aspect.name == "of_rathmas_chosen"


def test_parser_details_matches_localized_affix_values_to_internal_keys(monkeypatch) -> None:
    catalog = GameCatalog()
    monkeypatch.setattr(
        catalog,
        "affix_dict",
        {
            "armor": "방어도",
            "intelligence": "지능",
            "maximum_life": "최대 생명력",
            "critical_strike_damage_multiplier": "극대화 피해 계수 x",
        },
    )

    assert _get_affix_from_text("지능 +190 +[150 - 180]").name == "intelligence"
    assert _get_affix_from_text("최대 생명력 +2,703 [1,831 - 2,200]").name == "maximum_life"
    assert _get_affix_from_text("극대화 피해 계수 x24% [13 - 25]%").name == "critical_strike_damage_multiplier"


def test_korean_jewelry_affixes_start_after_all_resistance_line() -> None:
    lines = [
        "범람의 거대심장 가락지",
        "선조 전설 반지",
        "아이템 위력 900",
        "품질 25 ( +25)",
        "무기고 장비 구성",
        "모든 저항 216",
        "지능 +129 [100 - 121]",
    ]
    item = Item(item_type=ItemType.Ring)

    assert _get_affix_starting_location_from_tts_section(lines, item) == 6
