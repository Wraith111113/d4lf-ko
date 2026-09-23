# ruff:file-ignore[invalid-function-name]
from typing import TYPE_CHECKING, cast

from PyQt6.QtCore import QSettings
from PyQt6.QtWidgets import QApplication, QCheckBox

from src.app.dashboard import profiles as dashboard_profiles
from src.app.dashboard.drag import ActivityProfileDragMixin
from src.app.dashboard.profiles import ActivityProfileRowsMixin
from src.game_data import ItemType
from src.localization import tr
from src.profiles import (
    AffixFilterCountModel,
    AffixFilterModel,
    DynamicItemFilterModel,
    ItemFilterModel,
    ProfileDocumentStore,
    ProfileModel,
)

if TYPE_CHECKING:
    from PyQt6.QtWidgets import QLabel, QPushButton

    from src.app.dashboard.core import ActivityLogWidget


class _VisibilityFake:
    def __init__(self) -> None:
        self.visible = False

    def isVisible(self) -> bool:
        return self.visible

    def setVisible(self, visible: bool) -> None:
        self.visible = visible


class _ButtonFake:
    def __init__(self) -> None:
        self.label = "▶"

    def setText(self, label: str) -> None:
        self.label = label


def test_toggle_row_updates_visibility_and_button_label() -> None:
    mixin = cast("ActivityLogWidget", ActivityProfileRowsMixin())
    label = _VisibilityFake()
    button = _ButtonFake()

    ActivityProfileRowsMixin._toggle_row(mixin, cast("QLabel", label), cast("QPushButton", button))

    assert label.isVisible()
    assert button.label == "▼"

    ActivityProfileRowsMixin._toggle_row(mixin, cast("QLabel", label), cast("QPushButton", button))

    assert not label.isVisible()
    assert button.label == "▶"


def test_filter_profiles_matches_case_insensitively() -> None:
    mixin = cast("ActivityLogWidget", ActivityProfileDragMixin())
    matching = _VisibilityFake()
    other = _VisibilityFake()
    mixin.__dict__["_rows"] = {"Alpha": matching, "Beta": other}
    mixin.__dict__["_update_zebra_striping"] = lambda: None

    mixin._filter_profiles("ALP")

    assert matching.isVisible()
    assert not other.isVisible()


def test_quick_filter_exclusion_is_labeled_and_reversible(tmp_path, monkeypatch, mock_ini_loader) -> None:
    app = QApplication.instance() or QApplication([])
    store = ProfileDocumentStore(profiles_dir=tmp_path, full_dump=False)
    profile = ProfileModel(
        name="test",
        Affixes=[
            DynamicItemFilterModel(
                root={
                    "Gloves": ItemFilterModel(
                        item_type=[ItemType.Gloves],
                        affix_pool=[
                            AffixFilterCountModel(
                                count=[AffixFilterModel(name="attack_speed"), AffixFilterModel(name="maximum_life")],
                                min_count=2,
                            )
                        ],
                    )
                }
            )
        ],
    )
    path = store.save_new(file_name="test", profile=profile, source="test").path
    monkeypatch.setattr(ProfileDocumentStore, "default", lambda: store)
    monkeypatch.setattr(
        dashboard_profiles,
        "QSettings",
        lambda *_args: QSettings(str(tmp_path / "quick.ini"), QSettings.Format.IniFormat),
    )
    mixin = cast("ActivityLogWidget", ActivityProfileRowsMixin())
    panel = mixin._create_quick_filters(path)
    checkbox = panel.findChildren(QCheckBox)[0]
    assert checkbox.isChecked()
    assert checkbox.text().startswith(f"{tr('Find')}:")

    checkbox.setChecked(False)
    saved = store.load(path).profile.affixes[0].root["Gloves"].affix_pool[0]
    assert saved.min_count == 1
    assert len(saved.count) == 1
    reopened = mixin._create_quick_filters(path)
    excluded = next(box for box in reopened.findChildren(QCheckBox) if not box.isChecked())
    assert excluded.text().startswith(f"{tr('Excluded')}:")

    excluded.setChecked(True)
    restored = store.load(path).profile.affixes[0].root["Gloves"].affix_pool[0]
    assert len(restored.count) == 2
    assert app is not None
