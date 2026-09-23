import logging
import time

import cv2
import numpy as np

from src.automation.inventory import InventoryBase
from src.automation.mouse import Mouse
from src.perception import SearchArgs, capture, crop, window_to_monitor
from src.settings import get_settings, get_ui_coordinates

LOGGER = logging.getLogger(__name__)


class Stash(InventoryBase):
    def __init__(self) -> None:
        super().__init__(5, 10, is_stash=True)
        self.menu_name = "Stash"
        self.is_open_search_args = SearchArgs(
            ref=["stash_menu_icon", "stash_menu_icon_medium"], threshold=0.8, roi="stash_menu_icon", use_grayscale=True
        )
        self.curr_tab = 0

    @staticmethod
    def _looks_like_stash_header(img: np.ndarray) -> bool:
        """Detect the localized stash header without relying on the English STASH text template."""
        roi = get_ui_coordinates().roi.stash_menu_icon
        header = crop(img, tuple(int(value) for value in roi))
        if header.size == 0:
            return False
        hsv = cv2.cvtColor(header, cv2.COLOR_BGR2HSV)
        brightness = float(np.mean(hsv[:, :, 2]))
        saturation = float(np.mean(hsv[:, :, 1]))
        brightness_variation = float(np.std(hsv[:, :, 2]))
        neutral_bright_ratio = float(np.mean((hsv[:, :, 2] > 70) & (hsv[:, :, 1] < 100)))
        return brightness >= 45 and saturation < 160 and brightness_variation >= 15 and neutral_bright_ratio >= 0.4

    def is_open(self, img: np.ndarray | None = None) -> bool:
        if super().is_open(img):
            return True
        current = capture() if img is None else img
        detected = self._looks_like_stash_header(current)
        if detected:
            LOGGER.debug("Detected localized stash header using visual fallback")
        return detected

    @staticmethod
    def switch_to_tab(tab_idx: int) -> bool:
        number_tabs = get_settings().general.max_stash_tabs
        LOGGER.info(f"Switch Stash Tab to: {tab_idx}")
        if not 0 <= tab_idx < number_tabs:
            LOGGER.warning("Stash tab index out of range: %s (available: 1-%s)", tab_idx + 1, number_tabs)
            return False
        x, y, w, h = get_ui_coordinates().roi.tab_slots
        section_length = w // number_tabs
        centers = [(x + (i + 0.5) * section_length, y + h // 2) for i in range(number_tabs)]
        Mouse.move(*window_to_monitor(centers[tab_idx]), randomize=2)
        Mouse.click("left")
        time.sleep(0.2)
        return True
