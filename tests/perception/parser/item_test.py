from src import perception
from src.game_data import ItemRarity, ItemType
from src.item import AffixType, Aspect, Item
from src.perception import parse_item_text
from src.perception.parser.base import _create_base_item_from_tts
from src.perception.parser.details import _get_item_rarity


def test_captured_tts_cases_parse_without_item_description_modules(parser_cases) -> None:
    for input_item, expected_item in parser_cases:
        assert parse_item_text(input_item) == expected_item


LOOT_FILTER_TTS = ["SELECT ALL", "Checkbox Disabled", "Item Power Range", "Left mouse button"]


def test_loot_filter_controls_are_not_tts_item_start() -> None:
    assert perception.find_item_start(LOOT_FILTER_TTS) is None


def test_loot_filter_controls_do_not_raise_tts_parser_error() -> None:
    assert parse_item_text(LOOT_FILTER_TTS) is None


def test_captured_filters_screen_is_not_an_item() -> None:
    assert (
        parse_item_text([
            "FILTERS",
            *("Checkbox Disabled",) * 12,
            "Search",
            "&lt;CC&gt; Panoramix | 70 (300)",
            "Chest 7",
            "Chest 6",
            "Chest 5",
            "Chest 4",
            "Chest 3",
            "Consumables",
            "Chest 1",
            "Consumables",
            "Chest 3",
            "Chest 3",
            "Stash",
            "Left mouse button",
        ])
        is None
    )


def test_parser_returns_non_equipment_items_without_image_lookup() -> None:
    item_text = ["GREATER MATERIALS CACHE", "Legendary Cache"]

    assert parse_item_text(item_text) == Item(item_type=ItemType.Cache, original_name="GREATER MATERIALS CACHE")


def test_parser_returns_boss_keys_without_image_lookup() -> None:
    item_text = ["MALIGNANT HEART", "Legendary Boss Key"]

    assert parse_item_text(item_text) == Item(item_type=ItemType.LairBossKey, original_name="MALIGNANT HEART")


def test_korean_item_rarity_text_is_supported() -> None:
    assert _get_item_rarity("전설") == ItemRarity.Legendary
    assert _get_item_rarity("고유") == ItemRarity.Unique
    assert _get_item_rarity("신화") == ItemRarity.Mythic


def test_korean_ancestral_item_metadata_is_supported() -> None:
    item = _create_base_item_from_tts(["피바람", "선조 전설 양손 낫", "900 아이템 위력"])

    assert item is not None
    assert item.is_ancestral
    assert item.rarity == ItemRarity.Legendary
    assert item.item_type == ItemType.Scythe2H


def test_korean_unique_charm_resolves_to_canonical_unique_name() -> None:
    item_text = [
        "인검",
        "고유 부적",
        "아이템 위력 850",
        "행운의 적중: 최대 40% 확률로 주는 번개 피해 +3,020 [2,800 - 3,500]",
        "정수 생성량이 33% [30 - 40]% 증가합니다. 시전 시 보유한 정수 1당 뼈 기술 피해가 0.5%[x]씩, 최대 66%[x] [60 - 80]%까지 증가합니다.",
        "아아, 인검인가! 시안사이의 왕실 대장장이들이 강철에 호랑이 네 마리의 혼을 담았다고 하지!",
        "요구 레벨: 70. 고유 장착. 증오의 군주 아이템",
        "판매가: 8,031,176 금화",
        "마우스 오른쪽 버튼",
    ]

    item = parse_item_text(item_text)

    assert item is not None
    assert item.rarity == ItemRarity.Unique
    assert item.item_type == ItemType.Charm
    assert item.name == "in-geom"
    assert item.aspect is not None
    assert item.aspect.name == "in-geom"


def test_korean_insight_unique_tts_does_not_raise_when_aspect_line_is_missing() -> None:
    item_text = [
        "통찰",
        "선조 고유 양손 낫",
        "아이템 위력 900",
        "품질 25 ( +25)",
        "무기고 장비 구성",
        "랄티르탈솔",
        "4,429 초당 공격력",
        "적중당 공격력 [4,154 - 5,690]",
        "초당 공격 횟수 0.90 (느림)",
        "무기 공격력 +316 [207 - 345]",
        "모든 능력치 +395 +[300 - 360]",
        "정수 재생 +38 +[30]",
        "공격 속도 +52.5%",
        "극대화 확률 +36.7% [16.0 - 46.0]%",
        "극대화 피해 계수 x250% [200]%",
        "극대화 확률 +15.0%",
        "물리 피해 계수 x24%",
        "물리 피해 계수 x24%",
        "요구 레벨: 70. 계정 귀속 강령술사 전용. 고유 장착. 증오의 군주 아이템",
        "판매가: 547,885 금화",
    ]

    item = parse_item_text(item_text)

    assert item is not None
    assert item.name == "insight"
    assert item.aspect is not None
    assert item.aspect.name == "insight"


def test_equipped_korean_ring_starts_affixes_after_all_resistance() -> None:
    item_text = [
        "범람의 거대심장 가락지",
        "선조 전설 반지",
        "아이템 위력 900",
        "품질 25 ( +25)",
        "무기고 장비 구성",
        "모든 저항 216",
        "지능 +129 +[100 - 121]",
        "극대화 확률 +5.0% [3.5 - 5.0]%",
        "극대화 피해 계수 x44% [13 - 25]%",
        "자원 생성량 17.7% [11.0 - 15.0]%",
        "행운의 적중: 최대 15% 확률로 주 자원 +18 회복",
        "각인: 제압 중첩이 주 자원의 최대치를 7 [6 - 8], 재생량을 2 증가시킵니다.",
        "요구 레벨: 70. 계정 귀속. 증오의 군주 아이템",
        "판매가: 33,335 금화",
        "담금질: 1/4",
        "마우스 오른쪽 버튼",
    ]

    item = parse_item_text(item_text)

    assert item is not None
    assert item.item_type == ItemType.Ring
    assert item.aspect is not None
    assert item.aspect.name == "of_deluge"
    assert [affix.name for affix in item.affixes] == [
        "intelligence",
        "critical_strike_chance",
        "critical_strike_damage_multiplier",
        "resource_generation",
        "lucky_hit_up_to_a_chance_to_restore_primary_resource",
    ]


def test_legendary_horadric_seal_parses_item_power_charm_slots_as_inherent() -> None:
    item_text = [
        "SHIELDING HORADRIC SEAL OF ILL-TEMPERANCE",
        "Legendary Horadric Seal",
        "850 Item Power",
        "Unlocks 5 Charm Slots",
        "+11.6% Barrier Generation [8.0 - 12.0]% (+11.6%)",
        "Sescherons Fury:. +9% [8 - 11]% Fury Generation",
        "Berserkers Crucible:. Lucky Hit: Up to a 7% [7 - 9]% chance to Become Berserking",
        "Properties lost when equipped:",
        "Unlocks 1 Charm Slots",
        "18.0%[x] Critical Strike Damage",
        "Seal Power",
        "Seal Power",
        "Requires Level 50. Lord of Hatred Item",
        "Sell Value: 13,386,186 Gold",
        "Right mouse button",
    ]

    item = parse_item_text(item_text)

    assert item is not None
    assert [(affix.name, affix.text, affix.value, affix.type) for affix in item.inherent] == [
        ("charm_slot", "Unlocks 5 Charm Slots", 5.0, AffixType.inherent)
    ]
    assert [affix.name for affix in item.affixes] == [
        "barrier_generation",
        "sescherons_fury_fury_generation",
        "berserkers_crucible_lucky_hit_up_to_a_chance_to_become_berserking",
    ]


def test_unique_helm_with_armory_loadout_has_five_affixes_and_one_aspect() -> None:
    item_text = [
        "GODSLAYER CROWN",
        "Ancestral Unique Helm",
        "900 Item Power",
        "25 ( +25) Quality",
        "Armory Loadout",
        "2,004 Armor",
        "+128 Dexterity +[100 - 121]",
        "+1,754 Maximum Life [1,226 - 1,450]",
        "+35 Maximum Resource [15 - 20]",
        "+1,348 Armor [981 - 1,225]",
        "+3,000 Armor",
        "When you attempt to Incapacitate an enemy, you mark them and all surrounding enemies, pulling them in and dealing 7.5%[x] [7.5 - 10.0]% increased damage to them.",
        "CirMot (300/150) - Lethargic Shadow",
        "Cast 5 Skills then become exhausted for 3 seconds. (1 time). Gain 2 shadows, from the Rogues Dark Shroud Skill, reducing damage taken per shadow. . (Overflow: Gain Multiple Shadows)",
        "The Sahptev faithful believe in a thousand and one gods. If it takes me as many lifetimes, I will find and kill them all.. - Gaspar Stilbian, Veradani Outcast",
        "Requires Level 70. Account Bound. Unique Equipped. Vessel of Hatred Item",
        "Crafted",
        "Sell Value: 114,593 Gold",
        "Durability: 100/100. Tempers: 1/4",
        "Right mouse button",
    ]

    item = parse_item_text(item_text)

    assert item is not None
    assert [affix.text for affix in item.affixes] == [
        "+128 Dexterity +[100 - 121]",
        "+1,754 Maximum Life [1,226 - 1,450]",
        "+35 Maximum Resource [15 - 20]",
        "+1,348 Armor [981 - 1,225]",
        "+3,000 Armor",
    ]
    assert [(affix.name, affix.value, affix.min_value, affix.max_value, affix.type) for affix in item.affixes] == [
        ("dexterity", 128.0, 100.0, 121.0, AffixType.normal),
        ("maximum_life", 1754.0, 1226.0, 1450.0, AffixType.normal),
        ("maximum_resource", 35.0, 15.0, 20.0, AffixType.normal),
        ("armor", 1348.0, 981.0, 1225.0, AffixType.normal),
        ("armor", 3000.0, None, None, AffixType.greater),
    ]
    assert item.aspect == Aspect(
        name="godslayer_crown",
        min_value=7.5,
        max_value=10.0,
        text="When you attempt to Incapacitate an enemy, you mark them and all surrounding enemies, pulling them in and dealing 7.5%[x] [7.5 - 10.0]% increased damage to them.",
        value=7.5,
    )


def test_sigil_rarity_is_derived_from_tts_affixes() -> None:
    item_text = [
        "Nightmare Sigil",
        "Transform this dungeon into. aNightmare Dungeon",
        "Beast Graveyard in Nahantu",
        "DUNGEON AFFIXES",
        "Horadric Strongroom",
        "This place will always contain a Horadric Strongroom.",
        "Hellbound Elites",
        "Elite monsters have the Hellbound affix and deal 20% more damage.",
        "Account Bound. Vessel of Hatred Item",
        "Sell Value: 1 Gold",
        "Right mouse button",
    ]

    item = parse_item_text(item_text)

    assert item is not None
    assert item.item_type == ItemType.Sigil
    assert item.name == "beast_graveyard"
    assert [affix.name for affix in item.affixes] == ["horadric_strongroom", "hellbound_elites"]
    assert item.rarity == ItemRarity.Rare
