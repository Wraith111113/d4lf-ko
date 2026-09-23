import html
from typing import TYPE_CHECKING, cast

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from src.app.dashboard.controls import ActivityLogControlsMixin
from src.app.dashboard.drag import ActivityProfileDragMixin, DragHandleButton
from src.app.dashboard.profiles import ActivityProfileRowsMixin
from src.desktop.activity import ANSIConsoleWidget
from src.desktop.widgets import CheckmarkCheckBox
from src.game_data import GameCatalog
from src.localization import tr
from src.loot.equipped_scan import EquippedResult
from src.profiles import ProfileDocumentError, ProfileDocumentStore
from src.settings import IS_HOTKEY_KEY, get_settings

if TYPE_CHECKING:
    from src.app.shell import UnifiedMainWindow

__all__ = ["ActivityLogWidget", "DragHandleButton"]


class ActivityLogWidget(ActivityProfileRowsMixin, ActivityProfileDragMixin, ActivityLogControlsMixin, QWidget):
    equipped_scan_update = pyqtSignal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.equipped_scan_update.connect(self._show_equipped_scan)
        self._main_window = cast("UnifiedMainWindow | None", parent)
        self._config = get_settings()
        self._config.register_change_listener(self._on_config_changed)
        self.setAcceptDrops(True)

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(15)

        # === CENTER CONTENT: PROFILES & HOTKEYS ===
        content_splitter = QSplitter(Qt.Orientation.Horizontal)
        content_splitter.setObjectName("dashboard-content-splitter")

        # -- LEFT: PROFILE LIST --
        profile_section = QVBoxLayout()
        profile_section.setSpacing(10)

        profile_hdr = QLabel(tr("ACTIVE PROFILES"))
        profile_hdr.setStyleSheet("font-weight: bold; color: #888; letter-spacing: 1px;")
        profile_section.addWidget(profile_hdr)

        # Inline help text instead of a tooltip for better discovery and clarity
        profile_help = QLabel(
            tr(
                "Toggle profiles to enable them. Drag <b>⠿</b> to set priority; "
                "the top profile determines affix highlighting."
            )
        )
        profile_help.setWordWrap(True)
        profile_help.setObjectName("profile-help")
        profile_section.addWidget(profile_help)

        # Visual drop indicator for drag-and-drop
        self.drop_indicator = QFrame()
        self.drop_indicator.setObjectName("drop-indicator")
        self.drop_indicator.setFixedHeight(2)
        self.drop_indicator.hide()

        self._checkboxes: dict[str, CheckmarkCheckBox] = {}
        self._rows: dict[str, QWidget] = {}

        self.profile_scroll = QScrollArea()
        self.profile_scroll.setWidgetResizable(True)
        self.profile_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.profile_container = QWidget()
        self.profile_layout = QVBoxLayout(self.profile_container)
        self.profile_layout.setSpacing(0)
        self.profile_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.profile_scroll.setWidget(self.profile_container)

        # Search bar for profiles
        self.profile_search_input = QLineEdit()
        self.profile_search_input.setPlaceholderText(f"🔍 {tr('Filter profiles...')}")
        self.profile_search_input.textChanged.connect(self._filter_profiles)

        # Bulk selection buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        self.enable_all_btn = QPushButton(tr("Enable All"))
        self.disable_all_btn = QPushButton(tr("Disable All"))
        self.enable_all_btn.clicked.connect(self._select_all)
        self.disable_all_btn.clicked.connect(self._deselect_all)
        btn_layout.addWidget(self.enable_all_btn)
        btn_layout.addWidget(self.disable_all_btn)
        btn_layout.addStretch()

        profile_section.addWidget(self.profile_search_input)
        profile_section.addWidget(self.profile_scroll)
        profile_section.addLayout(btn_layout)

        profile_container = QWidget()
        profile_container.setLayout(profile_section)
        content_splitter.addWidget(profile_container)

        # -- RIGHT: EQUIPMENT FIRST, SHORTCUTS ON DEMAND --
        detail_tabs = QTabWidget()
        detail_tabs.setObjectName("dashboard-detail-tabs")
        equipment_section = QVBoxLayout()
        equipment_section.setSpacing(10)
        equipment_hdr = QLabel(tr("EQUIPPED GEAR STATUS"))
        equipment_hdr.setObjectName("dashboard-section-heading")
        equipment_section.addWidget(equipment_hdr)
        self.scan_equipment_btn = QPushButton(tr("Scan Equipped Gear"))
        self.scan_equipment_btn.setObjectName("primary")
        self.scan_equipment_btn.clicked.connect(self._start_equipped_scan)
        equipment_section.addWidget(self.scan_equipment_btn)
        self.equipment_status = QLabel(
            tr("No equipped gear scan yet. Open the character screen and press Scan Equipped Gear.")
        )
        self.equipment_status.setObjectName("equipment-status")
        self.equipment_status.setWordWrap(True)
        self.equipment_status.setTextFormat(Qt.TextFormat.RichText)
        self.equipment_status.setAlignment(Qt.AlignmentFlag.AlignTop)
        equipment_scroll = QScrollArea()
        equipment_scroll.setWidgetResizable(True)
        equipment_scroll.setFrameShape(QFrame.Shape.NoFrame)
        equipment_scroll.setWidget(self.equipment_status)
        equipment_section.addWidget(equipment_scroll, stretch=1)
        equipment_page = QWidget()
        equipment_page.setLayout(equipment_section)
        detail_tabs.addTab(equipment_page, tr("EQUIPPED GEAR STATUS"))

        hotkey_section = QVBoxLayout()
        hotkey_hdr = QLabel(tr("KEYBOARD SHORTCUTS"))
        hotkey_hdr.setObjectName("dashboard-section-heading")
        hotkey_section.addWidget(hotkey_hdr)

        self.hotkey_grid = QGridLayout()
        self.hotkey_grid.setSpacing(10)
        self._setup_hotkey_grid()

        hotkey_section.addLayout(self.hotkey_grid)
        hotkey_section.addStretch()
        hotkey_page = QWidget()
        hotkey_page.setLayout(hotkey_section)
        detail_tabs.addTab(hotkey_page, tr("KEYBOARD SHORTCUTS"))
        content_splitter.addWidget(detail_tabs)
        content_splitter.setStretchFactor(0, 3)
        content_splitter.setStretchFactor(1, 2)
        content_splitter.setSizes([720, 480])

        # Use a splitter for the main dashboard content and the log viewer to allow drag-resizing
        self.splitter = QSplitter(Qt.Orientation.Vertical)
        self.splitter.setObjectName("dashboard-splitter")

        self.splitter.addWidget(content_splitter)

        # === BOTTOM: MINI LOG PREVIEW ===
        self.log_viewer = ANSIConsoleWidget()
        self.log_viewer.setReadOnly(True)
        self.log_viewer.setObjectName("log-viewer")
        self.splitter.addWidget(self.log_viewer)

        # Set initial distribution (top takes priority, log starts at 100px)
        self.splitter.setStretchFactor(0, 4)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.setSizes([500, 100])

        self.main_layout.addWidget(self.splitter, stretch=1)

        # Hidden button that appears when the log viewer is fully collapsed
        self.show_log_btn = QPushButton(tr("Show Activity Log"))
        self.show_log_btn.setObjectName("secondary")
        self.show_log_btn.setVisible(False)
        self.main_layout.addWidget(self.show_log_btn)

        # === ACTION BAR ===
        action_layout = QHBoxLayout()
        self.import_btn = QPushButton(tr("Import Profile"))
        self.import_btn.setObjectName("primary")
        self.settings_btn = QPushButton(tr("Settings"))

        self.minimize_to_tray_cb = CheckmarkCheckBox(tr("Minimize to Tray"))
        self.minimize_to_tray_cb.setObjectName("switch")

        for btn in [self.import_btn, self.settings_btn]:
            btn.setFixedHeight(34)
            btn.setFixedWidth(130)
            action_layout.addWidget(btn)

        action_layout.addStretch()
        action_layout.addWidget(self.minimize_to_tray_cb)

        self.main_layout.addLayout(action_layout)
        self._connect_signals()
        self.refresh_profiles()

    def _start_equipped_scan(self) -> None:
        if not self._config.general.profiles:
            self.equipment_status.setText(tr("Select an active profile first."))
            return
        handler = self._main_window.worker.script_handler if self._main_window and self._main_window.worker else None
        if handler is None:
            self.equipment_status.setText(tr("Game connection is not ready."))
            return
        name = self._config.general.profiles[0]
        path = self._config.user_dir / "profiles" / f"{name}.yaml"
        if not path.exists():
            path = path.with_suffix(".yml")
        try:
            profile = ProfileDocumentStore.default().load(path).profile
            self.scan_equipment_btn.setEnabled(False)
            self.equipment_status.setText(tr("Scanning equipped gear..."))
            handler.scan_equipped(profile, self.equipped_scan_update.emit)
        except (OSError, ProfileDocumentError, RuntimeError) as error:
            self.scan_equipment_btn.setEnabled(True)
            self.equipment_status.setText(str(error))

    def _show_equipped_scan(self, result: object) -> None:
        if result is None:
            self.scan_equipment_btn.setEnabled(True)
            return
        if isinstance(result, Exception):
            self.scan_equipment_btn.setEnabled(True)
            self.equipment_status.setText(str(result))
            return
        if not isinstance(result, list):
            return
        lines = []
        for entry in result:
            if not isinstance(entry, EquippedResult):
                continue
            state = {
                "complete": tr("Complete"),
                "incomplete": tr("Needs work"),
                "unread": tr("Not read"),
                "no_target": tr("No profile target"),
            }.get(entry.state, entry.state)
            missing = ", ".join(
                tr("Greater affixes needed")
                if name.startswith("greater affixes ")
                else GameCatalog().affix_dict.get(name, name.replace("_", " "))
                for name in entry.missing
            )
            color = {"complete": "#62e889", "incomplete": "#f0be65"}.get(entry.state, "#9aa4b2")
            label = tr("Weapon") if entry.label == "Mace" else entry.label
            lines.append(
                f"{entry.slot + 1}. <b>{html.escape(label)}</b>: <span style='color:{color}'>{html.escape(state)}</span>"
                + (f"<br><span style='color:#aeb5bf'>{html.escape(entry.item_name)}</span>" if entry.item_name else "")
                + (f"<br><span style='color:#aeb5bf'>{html.escape(missing)}</span>" if missing else "")
            )
        self.equipment_status.setText("<br><br>".join(lines))
        if len(result) >= 13:
            self.scan_equipment_btn.setEnabled(True)

    def _setup_hotkey_grid(self) -> None:
        """Build the hotkey grid dynamically from AdvancedOptionsModel metadata."""
        while self.hotkey_grid.count():
            item = self.hotkey_grid.takeAt(0)
            if item is None:
                continue
            if widget := item.widget():
                widget.deleteLater()
            elif layout := item.layout():
                while layout.count():
                    child = layout.takeAt(0)
                    if child is not None and (w := child.widget()):
                        w.deleteLater()

        opts = self._config.advanced_options
        schema = opts.model_json_schema()
        properties = schema.get("properties", {})

        hotkey_items = []
        # Filter for keys that control the app (Advanced section) and are tagged as hotkeys
        for key, field in opts.model_fields.items():
            meta = field.json_schema_extra or {}
            if meta.get(IS_HOTKEY_KEY) == "True":
                val = getattr(opts, key)
                prop_meta = properties.get(key, {})
                label = prop_meta.get("title") or key.replace("_", " ").title()
                hotkey_items.append((str(val), label))

        for row, (key_val, label) in enumerate(hotkey_items):
            item_layout = QHBoxLayout()
            item_layout.setContentsMargins(0, 0, 0, 0)
            badge = QLabel(key_val.upper())
            badge.setObjectName("key-badge")
            item_layout.addWidget(badge)
            item_layout.addWidget(QLabel(label))
            item_layout.addStretch()
            self.hotkey_grid.addLayout(item_layout, row, 0)
