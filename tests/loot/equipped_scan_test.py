from types import SimpleNamespace

from src.game_data import ItemRarity, ItemType
from src.item import Affix, Item
from src.loot import equipped_scan
from src.loot.equipped_scan import compare_equipped_item
from src.perception import Publisher
from src.profiles import AffixFilterCountModel, AffixFilterModel, DynamicItemFilterModel, ItemFilterModel, ProfileModel


def test_equipped_comparison_uses_profile_threshold_and_reports_missing(mock_ini_loader) -> None:
    profile = ProfileModel(
        name="example",
        Affixes=[
            DynamicItemFilterModel(
                root={
                    "Ring": ItemFilterModel(
                        item_type=[ItemType.Ring],
                        affix_pool=[
                            AffixFilterCountModel(
                                count=[
                                    AffixFilterModel(name="critical_strike_chance"),
                                    AffixFilterModel(name="attack_speed"),
                                ],
                                min_count=2,
                            )
                        ],
                    )
                }
            )
        ],
    )
    ring = Item(
        item_type=ItemType.Ring, rarity=ItemRarity.Legendary, power=900, affixes=[Affix(name="critical_strike_chance")]
    )

    incomplete = compare_equipped_item(0, ring, profile)
    assert incomplete.state == "incomplete"
    assert incomplete.matched == ("critical_strike_chance",)
    assert incomplete.missing == ("attack_speed",)

    ring.affixes.append(Affix(name="attack_speed"))
    complete = compare_equipped_item(0, ring, profile)
    assert complete.state == "complete"
    assert complete.missing == ()


def test_scan_reads_new_tts_per_slot_and_marks_unread(monkeypatch, mock_ini_loader) -> None:
    profile = ProfileModel(name="example")
    monkeypatch.setattr(equipped_scan, "is_connected", lambda: True)
    monkeypatch.setattr(equipped_scan, "is_window_foreground", lambda _window: True)
    monkeypatch.setattr(equipped_scan, "move_window_to_foreground", lambda _window: None)
    monkeypatch.setattr(equipped_scan, "character_inventory", lambda: SimpleNamespace(open=lambda: True))
    monkeypatch.setattr(
        equipped_scan,
        "get_ui_coordinates",
        lambda: SimpleNamespace(pos=SimpleNamespace(possible_centers=[(1, 1), (2, 2)])),
    )
    monkeypatch.setattr(equipped_scan, "window_to_monitor", lambda point: point)
    monkeypatch.setattr(equipped_scan, "abs_window_to_monitor", lambda point: point)
    monkeypatch.setattr(equipped_scan.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(
        equipped_scan,
        "parse_item_text",
        lambda _lines: Item(item_type=ItemType.Ring, rarity=ItemRarity.Legendary, power=900),
    )

    def move(x: int, y: int, **_kwargs) -> None:
        if (x, y) in {(1, 1), (2, 2)}:
            Publisher().publish_item(["ring tooltip"])

    monkeypatch.setattr(equipped_scan, "move_pointer", move)
    snapshots = []
    equipped_scan.scan_equipped_items(profile, snapshots.append, timeout=0.01)

    assert len(snapshots) == 2
    assert snapshots[-1][0].state == "no_target"
    assert snapshots[-1][1].state == "unread"


def test_duplicate_ring_targets_are_assigned_to_different_slots(mock_ini_loader) -> None:
    profile = ProfileModel(
        name="example",
        Affixes=[
            DynamicItemFilterModel(root={"Ring": ItemFilterModel(item_type=[ItemType.Ring])}),
            DynamicItemFilterModel(root={"Ring2": ItemFilterModel(item_type=[ItemType.Ring])}),
        ],
    )
    ring = Item(item_type=ItemType.Ring, rarity=ItemRarity.Legendary, power=900)
    first = compare_equipped_item(0, ring, profile)
    second = compare_equipped_item(1, ring, profile, {first.label})
    assert {first.label, second.label} == {"Ring", "Ring2"}


def test_scan_does_not_accept_second_boots_payload(monkeypatch, mock_ini_loader) -> None:
    profile = ProfileModel(name="example")
    monkeypatch.setattr(equipped_scan, "is_connected", lambda: True)
    monkeypatch.setattr(equipped_scan, "is_window_foreground", lambda _window: True)
    monkeypatch.setattr(equipped_scan, "move_window_to_foreground", lambda _window: None)
    monkeypatch.setattr(equipped_scan, "character_inventory", lambda: SimpleNamespace(open=lambda: True))
    monkeypatch.setattr(
        equipped_scan,
        "get_ui_coordinates",
        lambda: SimpleNamespace(pos=SimpleNamespace(possible_centers=[(1, 1), (2, 2)])),
    )
    monkeypatch.setattr(equipped_scan, "window_to_monitor", lambda point: point)
    monkeypatch.setattr(equipped_scan, "abs_window_to_monitor", lambda point: point)
    monkeypatch.setattr(equipped_scan.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(
        equipped_scan,
        "parse_item_text",
        lambda lines: Item(item_type=ItemType.Boots, rarity=ItemRarity.Legendary, power=900, original_name=lines[0]),
    )

    def move(x: int, y: int, **_kwargs) -> None:
        if (x, y) in {(1, 1), (2, 2)}:
            Publisher().publish_item([f"boots tooltip {x}"])

    monkeypatch.setattr(equipped_scan, "move_pointer", move)
    snapshots = []
    equipped_scan.scan_equipped_items(profile, snapshots.append, timeout=0.01)

    assert snapshots[-1][0].item_name == "boots tooltip 1"
    assert snapshots[-1][0].state == "no_target"
    assert snapshots[-1][1].state == "unread"
