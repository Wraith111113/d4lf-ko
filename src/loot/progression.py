"""Compare locally imported build stages with one equipped-gear scan."""

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from src.game_data import ItemType, is_weapon
from src.loot.equipped_scan import EquippedResult, compare_equipped_item

if TYPE_CHECKING:
    from pathlib import Path

    from src.profiles import ItemFilterModel, ProfileModel

STAGES = ("starter", "midgame", "endgame", "push")
STAGE_LABELS = {"starter": "Starter", "midgame": "Midgame", "endgame": "Endgame", "push": "Push"}


@dataclass(frozen=True)
class GearTarget:
    key: str
    item_types: frozenset[ItemType]
    options: frozenset[str]
    uniques: frozenset[str]
    greater_counts: tuple[int, ...]
    minimum_matches: tuple[int, ...]
    count: int


@dataclass(frozen=True)
class TargetChange:
    key: str
    before: GearTarget | None
    after: GearTarget | None


def stage_paths(selected: Path) -> dict[str, Path]:
    """Find sibling variants saved by the same Maxroll import."""
    for stage in STAGES:
        suffix = f"_{stage}"
        if selected.stem.casefold().endswith(suffix):
            prefix = selected.stem[: -len(suffix)]
            paths: dict[str, Path] = {}
            for candidate_stage in STAGES:
                for extension in (".yaml", ".yml"):
                    candidate = selected.with_name(f"{prefix}_{candidate_stage}{extension}")
                    if candidate.is_file():
                        paths[candidate_stage] = candidate
                        break
            return paths
    return {}


def _target_key(name: str, item_types: list[ItemType]) -> str:
    if item_types and all(is_weapon(item_type) for item_type in item_types):
        return "weapon"
    if item_types and all(item_type == ItemType.Ring for item_type in item_types):
        return "ring"
    if len(item_types) == 1:
        return item_types[0].name
    return name


def gear_targets(profile: ProfileModel) -> dict[str, GearTarget]:
    grouped: dict[str, list[tuple[str, ItemFilterModel]]] = {}
    for entry in profile.affixes:
        for name, spec in entry.root.items():
            key = _target_key(name, spec.item_type)
            grouped.setdefault(key, []).append((name, spec))

    targets = {}
    for key, named_specs in grouped.items():
        count = 0
        for name, _ in named_specs:
            match = re.fullmatch(r".+\(x(\d+)\)", name)
            count += int(match.group(1)) if match else 1
        specs = [spec for _, spec in named_specs]
        targets[key] = GearTarget(
            key=key,
            item_types=frozenset(item_type for spec in specs for item_type in spec.item_type),
            options=frozenset(affix.name for spec in specs for pool in spec.affix_pool for affix in pool.count),
            uniques=frozenset(aspect.name for spec in specs for aspect in spec.unique_aspect),
            greater_counts=tuple(sorted(spec.min_greater_affix_count for spec in specs)),
            minimum_matches=tuple(sorted(pool.min_count for spec in specs for pool in spec.affix_pool)),
            count=count,
        )
    return targets


def target_changes(before: ProfileModel, after: ProfileModel) -> tuple[TargetChange, ...]:
    old, new = gear_targets(before), gear_targets(after)
    return tuple(
        TargetChange(key, old.get(key), new.get(key))
        for key in sorted(old.keys() | new.keys())
        if old.get(key) != new.get(key)
    )


def compare_scanned_gear(profile: ProfileModel, scan: list[EquippedResult]) -> tuple[EquippedResult, ...]:
    """Re-evaluate parsed items; an unread slot stays unknown at every stage."""
    used_targets: set[str] = set()
    evaluated = []
    for entry in scan:
        if entry.item is None:
            evaluated.append(EquippedResult(entry.slot, entry.label, "unread"))
            continue
        result = compare_equipped_item(entry.slot, entry.item, profile, used_targets)
        if result.state != "no_target":
            used_targets.add(result.label)
        evaluated.append(result)
    return tuple(evaluated)
