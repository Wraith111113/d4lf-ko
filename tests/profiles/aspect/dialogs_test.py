import importlib
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication

from src.game_data import GameCatalog
from src.profiles.aspect.dialogs import AddAspectUpgrade


def test_dialogs_module_is_importable() -> None:
    module = importlib.import_module("src.profiles.aspect.dialogs")
    assert hasattr(module, "AddAspectUpgrade")


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def test_aspect_dialog_displays_localized_name_but_returns_canonical_id(qapp, monkeypatch) -> None:
    catalog = GameCatalog()
    monkeypatch.setattr(catalog, "aspect_list", ["accelerating"])
    monkeypatch.setattr(catalog, "aspect_display_names", {"accelerating": "가속하는"})

    dialog = AddAspectUpgrade([])

    assert dialog.name_input.currentText() == "가속하는"
    assert dialog.get_value() == "accelerating"
