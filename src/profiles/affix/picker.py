from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from src.game_data import GameCatalog, ItemType
from src.localization import tr

ONE_HANDED_WEAPONS = {
    ItemType.Axe,
    ItemType.Dagger,
    ItemType.Flail,
    ItemType.Mace,
    ItemType.Scythe,
    ItemType.Sword,
    ItemType.Wand,
}
TWO_HANDED_WEAPONS = {
    ItemType.Axe2H,
    ItemType.Bow,
    ItemType.Crossbow2H,
    ItemType.Glaive,
    ItemType.Mace2H,
    ItemType.Polearm,
    ItemType.Quarterstaff,
    ItemType.Scythe2H,
    ItemType.Staff,
    ItemType.Sword2H,
}
OFF_HAND_ITEMS = {ItemType.Focus, ItemType.OffHandTotem, ItemType.Tome, ItemType.Shield}

AFFIXES_TABNAME = "Affixes"
AFFIX_VALUE_MODE = "Value"
AFFIX_PERCENT_MODE = "Min %"
UNIQUE_ASPECTS_TITLE = "Unique Aspects"


class ItemTypePicker(QDialog):
    def __init__(self, parent: QWidget | None, item_types: list[ItemType], selected_item_types: list[ItemType]) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr("Select Item Types"))
        self.resize(650, 500)
        self.checkboxes: dict[ItemType, QCheckBox] = {}

        selected_item_type_set = set(selected_item_types)
        layout = QVBoxLayout(self)
        self.category_tabs = QTabWidget(self)
        categories = (
            ("One-handed Weapons", ONE_HANDED_WEAPONS),
            ("Two-handed Weapons", TWO_HANDED_WEAPONS),
            ("Off-hand Items", OFF_HAND_ITEMS),
            ("Other Items", set(item_types) - ONE_HANDED_WEAPONS - TWO_HANDED_WEAPONS - OFF_HAND_ITEMS),
        )
        self.category_item_types: dict[str, list[ItemType]] = {}
        for title, category_types in categories:
            included = [item_type for item_type in item_types if item_type in category_types]
            if included:
                self.category_item_types[title] = included
                self.category_tabs.addTab(self._create_item_type_group(included, selected_item_type_set), tr(title))
        layout.addWidget(self.category_tabs)

        note_label = QLabel(tr("If no item types are selected, all item types will be evaluated for this filter."))
        note_label.setWordWrap(True)
        layout.addWidget(note_label)

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        clear_button = button_box.addButton(tr("Clear"), QDialogButtonBox.ButtonRole.ResetRole)
        if clear_button is not None:
            clear_button.clicked.connect(self.clear_selection)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _create_item_type_group(self, item_types: list[ItemType], selected_item_types: set[ItemType]) -> QWidget:
        group_box = QWidget()
        group_layout = QVBoxLayout(group_box)

        actions = QHBoxLayout()
        select_all = QPushButton(tr("Select Category"))
        select_all.clicked.connect(lambda: self._set_category_checked(item_types, checked=True))
        clear = QPushButton(tr("Clear Category"))
        clear.clicked.connect(lambda: self._set_category_checked(item_types, checked=False))
        actions.addWidget(select_all)
        actions.addWidget(clear)
        group_layout.addLayout(actions)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        for item_type in item_types:
            checkbox = QCheckBox(GameCatalog().item_type_label(item_type))
            checkbox.setChecked(item_type in selected_item_types)
            self.checkboxes[item_type] = checkbox
            content_layout.addWidget(checkbox)

        scroll_area.setWidget(content_widget)
        group_layout.addWidget(scroll_area)
        return group_box

    def _set_category_checked(self, item_types: list[ItemType], checked: bool) -> None:
        for item_type in item_types:
            self.checkboxes[item_type].setChecked(checked)

    def clear_selection(self) -> None:
        for checkbox in self.checkboxes.values():
            checkbox.setChecked(False)

    def get_selected_item_types(self) -> list[ItemType]:
        return [item_type for item_type, checkbox in self.checkboxes.items() if checkbox.isChecked()]
