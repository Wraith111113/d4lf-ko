"""Dashboard presentation for locally saved build stages and equipped gear."""

import html
import logging
from typing import TYPE_CHECKING

from src.game_data import GameCatalog, ItemType
from src.localization import tr
from src.loot.equipped_scan import EquippedResult
from src.loot.progression import STAGE_LABELS, STAGES, compare_scanned_gear, stage_paths, target_changes
from src.profiles import ProfileDocumentError, ProfileDocumentStore

if TYPE_CHECKING:
    from src.app.dashboard.core import ActivityLogWidget
    from src.profiles import ProfileModel

LOGGER = logging.getLogger(__name__)


def _label(key: str) -> str:
    if key == "weapon":
        return tr("Weapon")
    if key == "ring":
        return GameCatalog().item_type_label(ItemType.Ring)
    if key in ItemType.__members__:
        return GameCatalog().item_type_label(ItemType[key])
    return key.replace("_", " ")


def _names(values: frozenset[str], *, unique: bool = False, aspect: bool = False) -> str:
    catalog = GameCatalog()
    labels = (
        (
            catalog.unique_label(value)
            if unique
            else catalog.aspect_label(value)
            if aspect
            else catalog.affix_dict.get(value, value.replace("_", " "))
        )
        for value in sorted(values)
    )
    return ", ".join(html.escape(value) for value in labels)


def _counts(values: tuple[int, ...]) -> str:
    return ", ".join(str(value) for value in values) if values else "0"


def _change_lines(before: ProfileModel, after: ProfileModel) -> list[str]:
    lines = []
    for change in target_changes(before, after):
        old, new = change.before, change.after
        details = []
        if old is None or new is None:
            details.append(tr("Target added") if new else tr("Target removed"))
        if old and new:
            if old.item_types != new.item_types:
                old_types = ", ".join(GameCatalog().item_type_label(t) for t in sorted(old.item_types, key=str))
                new_types = ", ".join(GameCatalog().item_type_label(t) for t in sorted(new.item_types, key=str))
                details.append(f"{tr('Item type')}: {html.escape(old_types)} → {html.escape(new_types)}")
            if old.count != new.count:
                details.append(f"{tr('Targets')}: {old.count} → {new.count}")
            if old.greater_counts != new.greater_counts:
                details.append(
                    f"{tr('Greater affixes')}: {_counts(old.greater_counts)} → {_counts(new.greater_counts)}"
                )
            if old.minimum_matches != new.minimum_matches:
                details.append(
                    f"{tr('Matching options')}: {_counts(old.minimum_matches)} → {_counts(new.minimum_matches)}"
                )
        old_uniques = old.uniques if old else frozenset()
        new_uniques = new.uniques if new else frozenset()
        if added := new_uniques - old_uniques:
            details.append(f"{tr('Unique target added')}: {_names(added, unique=True)}")
        if removed := old_uniques - new_uniques:
            details.append(f"{tr('Unique target removed')}: {_names(removed, unique=True)}")
        old_options = old.options if old else frozenset()
        new_options = new.options if new else frozenset()
        if added := new_options - old_options:
            details.append(f"{tr('Option candidates added')}: {_names(added)}")
        if removed := old_options - new_options:
            details.append(f"{tr('Option candidates removed')}: {_names(removed)}")
        if details:
            lines.append(f"<b>{html.escape(_label(change.key))}</b> · " + " · ".join(details))
    added_aspects = set(after.aspect_upgrades) - set(before.aspect_upgrades)
    removed_aspects = set(before.aspect_upgrades) - set(after.aspect_upgrades)
    if added_aspects or removed_aspects:
        parts = []
        if added_aspects:
            parts.append("+" + _names(frozenset(added_aspects), aspect=True))
        if removed_aspects:
            parts.append("−" + _names(frozenset(removed_aspects), aspect=True))
        lines.append(f"<b>{tr('Aspect upgrades')}</b> · " + " · ".join(parts))
    return lines


class EquipmentProgressionMixin:
    def _refresh_equipment_profiles(self: ActivityLogWidget) -> None:
        selected = self.equipment_profile_choice.currentData()
        self.equipment_profile_choice.blockSignals(True)  # ruff:ignore[boolean-positional-value-in-call]
        self.equipment_profile_choice.clear()
        for name in self._rows:
            self.equipment_profile_choice.addItem(name.replace("_", " "), name)
        preferred = (
            selected
            if selected in self._rows
            else next((name for name in self._config.general.profiles if name in self._rows), None)
        )
        if preferred:
            self.equipment_profile_choice.setCurrentIndex(self.equipment_profile_choice.findData(preferred))
        self.equipment_profile_choice.blockSignals(False)  # ruff:ignore[boolean-positional-value-in-call]
        self._equipment_profile_changed()

    def _equipment_profile_changed(self: ActivityLogWidget) -> None:
        name = self.equipment_profile_choice.currentData()
        self._selected_profile = None
        self._stage_profiles = {}
        self._selected_stage = None
        self._profile_load_error = ""
        self.equipment_stage_choice.blockSignals(True)  # ruff:ignore[boolean-positional-value-in-call]
        self.equipment_stage_choice.clear()
        if name:
            folder = self._config.user_dir / "profiles"
            path = folder / f"{name}.yaml"
            if not path.is_file():
                path = folder / f"{name}.yml"
            try:
                store = ProfileDocumentStore.default()
                self._selected_profile = store.load(path).profile
                paths = stage_paths(path)
                for stage, stage_path in paths.items():
                    try:
                        self._stage_profiles[stage] = store.load(stage_path).profile
                    except OSError, ProfileDocumentError:
                        LOGGER.warning("Could not load stage profile %s", stage_path, exc_info=True)
                self._selected_stage = next((stage for stage, stage_path in paths.items() if stage_path == path), None)
                for stage in STAGES:
                    if stage in self._stage_profiles:
                        self.equipment_stage_choice.addItem(tr(STAGE_LABELS[stage]), stage)
                if self._selected_stage:
                    current_index = STAGES.index(self._selected_stage)
                    target = next(
                        (stage for stage in STAGES[current_index + 1 :] if stage in self._stage_profiles),
                        self._selected_stage,
                    )
                    self.equipment_stage_choice.setCurrentIndex(self.equipment_stage_choice.findData(target))
            except (OSError, ProfileDocumentError) as error:
                LOGGER.warning("Could not load selected profile %s: %s", path, error)
                self._profile_load_error = str(error)
        self.equipment_stage_choice.setEnabled(self.equipment_stage_choice.count() > 1)
        self.equipment_stage_choice.blockSignals(False)  # ruff:ignore[boolean-positional-value-in-call]
        self._render_equipment()

    def _start_equipped_scan(self: ActivityLogWidget) -> None:
        profile = self._selected_profile
        if profile is None:
            self.equipment_status.setText(tr("Select a profile first."))
            return
        handler = self._main_window.worker.script_handler if self._main_window and self._main_window.worker else None
        if handler is None:
            self.equipment_status.setText(tr("Game connection is not ready."))
            return
        try:
            self._scan_results = []
            self.scan_equipment_btn.setEnabled(False)
            self.equipment_status.setText(tr("Scanning equipped gear..."))
            handler.scan_equipped(profile, self.equipped_scan_update.emit)
        except RuntimeError as error:
            self.scan_equipment_btn.setEnabled(True)
            self.equipment_status.setText(str(error))

    def _show_equipped_scan(self: ActivityLogWidget, result: object) -> None:
        if result is None:
            self.scan_equipment_btn.setEnabled(True)
            return
        if isinstance(result, Exception):
            self.scan_equipment_btn.setEnabled(True)
            self._scan_results = []
            self.equipment_status.setText(str(result))
            return
        if not isinstance(result, list) or not all(isinstance(entry, EquippedResult) for entry in result):
            return
        self._scan_results = result
        self._render_equipment()
        if len(result) >= 13:
            self.scan_equipment_btn.setEnabled(True)

    def _render_equipment(self: ActivityLogWidget) -> None:
        if self._profile_load_error:
            self.progression_status.setText(html.escape(self._profile_load_error))
            self.equipment_status.clear()
            return
        stage = self.equipment_stage_choice.currentData()
        if stage and stage in self._stage_profiles:
            target = self._stage_profiles[stage]
            previous = next(
                (name for name in reversed(STAGES[: STAGES.index(stage)]) if name in self._stage_profiles), None
            )
            if previous:
                changes = _change_lines(self._stage_profiles[previous], target)
                title = f"{tr(STAGE_LABELS[previous])} → {tr(STAGE_LABELS[stage])}"
                details = "<br><br>".join(changes) if changes else tr("No equipment target changes.")
                self.progression_status.setText(f"<b>{html.escape(title)}</b><br><br>{details}")
            else:
                self.progression_status.setText(f"<b>{tr(STAGE_LABELS[stage])}</b> · {tr('Saved profile targets')}")
        else:
            self.progression_status.setText(tr("No saved stage variants for this profile."))

        if not self._scan_results:
            self.equipment_status.setText(
                tr("No equipped gear scan yet. Open the character screen and press Scan Equipped Gear.")
            )
            return

        stages = self._stage_profiles or {"selected": self._selected_profile}
        summary = []
        for stage_name, profile in stages.items():
            if profile is None:
                continue
            results = compare_scanned_gear(profile, self._scan_results)
            complete = sum(entry.state == "complete" for entry in results)
            assessed = sum(entry.state in {"complete", "incomplete"} for entry in results)
            unread = sum(entry.state == "unread" for entry in results)
            outside = sum(entry.state == "no_target" for entry in results)
            label = tr(STAGE_LABELS[stage_name]) if stage_name in STAGE_LABELS else tr("Selected profile")
            summary.append(f"<b>{html.escape(label)}</b> {complete}/{assessed} {tr('matched scanned targets')}")
            if unread:
                summary[-1] += f" · {unread} {tr('unread slots')}"
            if outside:
                summary[-1] += f" · {outside} {tr('outside profile target')}"

        target_profile = self._stage_profiles.get(stage) if stage else self._selected_profile
        if target_profile is None:
            return
        rows = []
        for entry in compare_scanned_gear(target_profile, self._scan_results):
            state = {
                "complete": tr("Complete"),
                "incomplete": tr("Needs work"),
                "unread": tr("Not read"),
                "no_target": tr("No profile target"),
            }.get(entry.state, entry.state)
            color = {"complete": "#62e889", "incomplete": "#f0be65"}.get(entry.state, "#9aa4b2")
            item_type = entry.item.item_type if entry.item else None
            label = GameCatalog().item_type_label(item_type) if item_type else _label(entry.label)
            row = f"{entry.slot + 1}. <b>{html.escape(label)}</b> · <span style='color:{color}'>{html.escape(state)}</span>"
            if entry.item_name:
                row += f"<br>{html.escape(entry.item_name)}"
            if entry.missing:
                names = [
                    tr("Greater affixes needed")
                    if value.startswith("greater affixes ")
                    else GameCatalog().affix_dict.get(value, GameCatalog().unique_label(value))
                    for value in entry.missing
                ]
                row += f"<br><span style='color:#aeb5bf'>{tr('Possible missing options')}: {html.escape(', '.join(names))}</span>"
            elif entry.state == "incomplete":
                row += f"<br><span style='color:#aeb5bf'>{tr('Other profile condition not met')}</span>"
            rows.append(row)
        self.equipment_status.setText("<br><br>".join(summary + rows))
