import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication, QComboBox, QLabel, QWidget

from src import localization


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def test_widget_tree_localizes_combo_text_without_changing_data(qapp, monkeypatch) -> None:
    monkeypatch.setattr(localization, "is_korean", lambda: True)
    root = QWidget()
    combo = QComboBox(root)
    combo.addItem("favorite", "favorite")
    combo.addItem("junk", "junk")
    label = QLabel("Profile Alias:", root)

    localization.localize_widget_tree(root)

    assert combo.itemText(0) == "즐겨찾기"
    assert combo.itemData(0) == "favorite"
    assert combo.itemText(1) == "폐품"
    assert combo.itemData(1) == "junk"
    assert label.text() == "프로필 별칭:"
