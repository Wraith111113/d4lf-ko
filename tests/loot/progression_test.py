from src.game_data import ItemRarity, ItemType
from src.item import Affix, Item
from src.loot.equipped_scan import EquippedResult
from src.loot.progression import compare_scanned_gear, stage_paths, target_changes
from src.profiles import AffixFilterCountModel, AffixFilterModel, DynamicItemFilterModel, ItemFilterModel, ProfileModel


def _profile(name: str, targets: dict[str, ItemFilterModel]) -> ProfileModel:
    return ProfileModel(name=name, Affixes=[DynamicItemFilterModel(root={key: rule}) for key, rule in targets.items()])


def test_stage_paths_find_only_sibling_variants(tmp_path) -> None:
    names = ("starter", "midgame", "endgame", "push")
    for stage in names:
        (tmp_path / f"blood_wave_{stage}.yaml").touch()
    (tmp_path / "other_push.yaml").touch()

    paths = stage_paths(tmp_path / "blood_wave_midgame.yaml")

    assert list(paths) == list(names)
    assert all(path.stem.startswith("blood_wave_") for path in paths.values())


def test_stage_changes_group_ring_slots_and_report_unique_swap(mock_ini_loader) -> None:
    first = _profile(
        "first",
        {
            "Ring(x2)": ItemFilterModel(
                item_type=[ItemType.Ring],
                affix_pool=[AffixFilterCountModel(count=[AffixFilterModel(name="attack_speed")], min_count=1)],
            )
        },
    )
    second = _profile(
        "second",
        {
            "Ring": ItemFilterModel(
                item_type=[ItemType.Ring],
                affix_pool=[AffixFilterCountModel(count=[AffixFilterModel(name="attack_speed")], min_count=1)],
            ),
            "Ring2": ItemFilterModel(
                item_type=[ItemType.Ring],
                affix_pool=[
                    AffixFilterCountModel(count=[AffixFilterModel(name="critical_strike_chance")], min_count=1)
                ],
            ),
        },
    )

    changes = target_changes(first, second)

    assert len(changes) == 1
    assert changes[0].key == "ring"
    assert changes[0].before.count == 2
    assert changes[0].after.count == 2
    assert changes[0].after.options - changes[0].before.options == {"critical_strike_chance"}


def test_one_scan_can_be_compared_against_different_stages(mock_ini_loader) -> None:
    starter = _profile(
        "starter",
        {
            "Ring": ItemFilterModel(
                item_type=[ItemType.Ring],
                affix_pool=[AffixFilterCountModel(count=[AffixFilterModel(name="attack_speed")], min_count=1)],
            )
        },
    )
    endgame = _profile(
        "endgame",
        {
            "Ring": ItemFilterModel(
                item_type=[ItemType.Ring],
                affix_pool=[
                    AffixFilterCountModel(count=[AffixFilterModel(name="critical_strike_chance")], min_count=1)
                ],
            )
        },
    )
    ring = Item(item_type=ItemType.Ring, rarity=ItemRarity.Legendary, power=900, affixes=[Affix(name="attack_speed")])
    scan = [EquippedResult(0, "Ring", "complete", item=ring), EquippedResult(1, "Slot 2", "unread")]

    first = compare_scanned_gear(starter, scan)
    second = compare_scanned_gear(endgame, scan)

    assert [entry.state for entry in first] == ["complete", "unread"]
    assert [entry.state for entry in second] == ["incomplete", "unread"]
    assert second[0].item is ring
