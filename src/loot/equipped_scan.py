"""Read equipped slots through D4LF's existing mouse and TTS pipeline."""

import logging
import operator
import queue
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

from src.automation import (
    WindowSpec,
    character_inventory,
    is_window_foreground,
    move_pointer,
    move_window_to_foreground,
)
from src.game_data import GameCatalog, ItemType, is_armor, is_jewelry, is_weapon
from src.item.data.affix import AffixType
from src.item.filter.matching import FilterMatchingMixin
from src.perception import Publisher, abs_window_to_monitor, is_connected, parse_item_text, window_to_monitor
from src.settings import get_settings, get_ui_coordinates

if TYPE_CHECKING:
    from collections.abc import Callable

    from src.item import Item
    from src.profiles import ItemFilterModel, ProfileModel

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class EquippedResult:
    slot: int
    label: str
    state: str
    matched: tuple[str, ...] = ()
    missing: tuple[str, ...] = ()
    item_name: str = ""
    item: Item | None = None


def _max_equipped_count(item_type: ItemType) -> int:
    if item_type == ItemType.Ring or is_weapon(item_type):
        return 2
    return 1


def _targets(profile: ProfileModel, item: Item) -> list[tuple[str, ItemFilterModel]]:
    return [
        (name, spec)
        for entry in profile.affixes
        for name, spec in entry.root.items()
        if not spec.item_type or item.item_type in spec.item_type
    ]


def compare_equipped_item(
    slot: int, item: Item, profile: ProfileModel, used_targets: set[str] | None = None
) -> EquippedResult:
    label = GameCatalog().item_type_label(item.item_type) if item.item_type else (item.original_name or "Unknown")
    targets = _targets(profile, item)
    if not targets:
        return EquippedResult(slot, label, "no_target", item_name=item.original_name or "", item=item)
    if len(targets) > 1 and used_targets:
        available = [(name, spec) for name, spec in targets if name not in used_targets]
        if available:
            targets = available

    matcher = FilterMatchingMixin()
    candidates: list[tuple[int, bool, EquippedResult]] = []
    for name, spec in targets:
        found: list[str] = []
        missing: list[str] = []
        for pool in spec.affix_pool:
            pairs = matcher._match_count_group(
                pool.model_copy(update={"min_count": 0}), [a for a in item.affixes if a.type != AffixType.tempered]
            )
            matched_ids = {id(expected) for expected, _ in pairs}
            found.extend(expected.name for expected, _ in pairs)
            if len(pairs) < pool.min_count:
                missing.extend(expected.name for expected in pool.count if id(expected) not in matched_ids)
        for pool in spec.inherent_pool:
            pairs = matcher._match_count_group(pool.model_copy(update={"min_count": 0}), item.inherent)
            matched_ids = {id(expected) for expected, _ in pairs}
            found.extend(expected.name for expected, _ in pairs)
            if len(pairs) < pool.min_count:
                missing.extend(expected.name for expected in pool.count if id(expected) not in matched_ids)
        aspect_ok = matcher._check_unique_aspects_for_item(item, spec.unique_aspect)
        if not aspect_ok and spec.unique_aspect:
            missing.extend(aspect.name for aspect in spec.unique_aspect)
        non_tempered = [a for a in item.affixes if a.type != AffixType.tempered]
        complete = (
            aspect_ok
            and matcher._match_item_power(spec.min_power, item.power)
            and (not spec.rarities or item.rarity in spec.rarities)
            and matcher._match_greater_affix_count(spec.min_greater_affix_count, non_tempered)
            and (
                not spec.affix_pool
                or bool(matcher._match_affixes_count(spec.affix_pool, non_tempered, spec.min_greater_affix_count))
            )
            and (not spec.inherent_pool or bool(matcher._match_affixes_count(spec.inherent_pool, item.inherent)))
        )
        if spec.min_power and (item.power is None or item.power < spec.min_power):
            missing.append(f"power {spec.min_power}")
        if not matcher._match_greater_affix_count(spec.min_greater_affix_count, non_tempered):
            missing.append(f"greater affixes {spec.min_greater_affix_count}")
        complete = complete and not missing
        state = "complete" if complete else "incomplete"
        candidates.append((
            len(found),
            complete,
            EquippedResult(slot, name, state, tuple(found), tuple(missing), item.original_name or "", item),
        ))
    return max(candidates, key=operator.itemgetter(1, 0))[2]


def scan_equipped_items(
    profile: ProfileModel, publish: Callable[[list[EquippedResult]], None], *, timeout: float = 2.0
) -> None:
    if not is_connected():
        msg = "TTS is not connected"
        raise RuntimeError(msg)

    window = WindowSpec(get_settings().advanced_options.process_name)
    move_window_to_foreground(window)
    time.sleep(0.2)
    if not is_window_foreground(window):
        msg = "Diablo IV could not be brought to the foreground"
        raise RuntimeError(msg)
    inventory = character_inventory()
    if not inventory.open():
        msg = "Character inventory did not open"
        raise RuntimeError(msg)

    received: queue.Queue[list[str]] = queue.Queue()

    def on_item(lines: list[str]) -> None:
        received.put(lines.copy())

    results: list[EquippedResult] = []
    used_targets: set[str] = set()
    seen_payloads: set[tuple[str, ...]] = set()
    seen_item_types: dict[ItemType, int] = {}
    publisher = Publisher()
    publisher.subscribe_item(on_item)
    try:
        centers = get_ui_coordinates().pos.possible_centers[:13]
        for index, center in enumerate(centers):
            LOGGER.info("Scanning equipped slot %s at %s", index + 1, center)
            move_pointer(*abs_window_to_monitor((0, 0)), randomize=0)
            time.sleep(0.12)
            while not received.empty():
                received.get_nowait()
            move_pointer(*window_to_monitor(center), randomize=0)
            deadline = time.monotonic() + timeout
            item = None
            while time.monotonic() < deadline:
                try:
                    lines = received.get(timeout=min(0.2, max(0.01, deadline - time.monotonic())))
                except queue.Empty:
                    continue
                if tuple(lines) in seen_payloads:
                    LOGGER.info("Equipped slot %s: repeated TTS payload ignored", index + 1)
                    continue
                try:
                    candidate = parse_item_text(lines)
                except Exception:
                    LOGGER.debug("Could not parse equipped slot %s", index + 1, exc_info=True)
                    continue
                if (
                    candidate
                    and candidate.item_type
                    and (
                        is_armor(candidate.item_type)
                        or is_jewelry(candidate.item_type)
                        or is_weapon(candidate.item_type)
                    )
                ):
                    item_type = candidate.item_type
                    if seen_item_types.get(item_type, 0) >= _max_equipped_count(item_type):
                        LOGGER.info(
                            "Equipped slot %s: unexpected additional %s (%s); leaving unread",
                            index + 1,
                            item_type.value,
                            candidate.original_name,
                        )
                        continue
                    item = candidate
                    seen_payloads.add(tuple(lines))
                    seen_item_types[item_type] = seen_item_types.get(item_type, 0) + 1
                    break
            if item is not None:
                result = compare_equipped_item(index, item, profile, used_targets)
                if result.state != "no_target":
                    used_targets.add(result.label)
            else:
                result = EquippedResult(index, f"Slot {index + 1}", "unread")
            LOGGER.info(
                "Equipped slot %s: %s (%s), state=%s, matched=%s, missing=%s",
                index + 1,
                result.item_name or result.label,
                item.item_type.value if item and item.item_type else "unknown",
                result.state,
                result.matched,
                result.missing,
            )
            results.append(result)
            publish(results.copy())
    finally:
        publisher.unsubscribe_item(on_item)
        move_pointer(*abs_window_to_monitor((0, 0)), randomize=0)
