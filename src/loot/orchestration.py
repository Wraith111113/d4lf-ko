"""Loot interaction orchestration shared by the application handler."""

import logging
import time
from typing import Literal

from src.automation import character_inventory, move_pointer, stash_inventory
from src.loot.filter import check_items
from src.perception import abs_window_to_monitor, capture, screenshot
from src.settings import ItemRefreshType, get_settings

LOGGER = logging.getLogger(__name__)


def run_loot_filter(
    force_refresh: ItemRefreshType = ItemRefreshType.no_refresh,
    no_match_action: str = "junk",
    target: Literal["inventory", "stash", "both"] = "both",
) -> None:
    LOGGER.info("Running loot filter")
    move_pointer(*abs_window_to_monitor((0, 0)))
    inv = character_inventory()
    stash = stash_inventory()

    stash_open = stash.is_open()
    if target == "stash" and not stash_open:
        LOGGER.error("Stash-only filter requested but the stash is not open")
        return

    if target in {"stash", "both"} and stash_open:
        selected_tabs = get_settings().general.check_chest_tabs
        LOGGER.info("Stash detected; filtering configured tabs: %s", [tab + 1 for tab in selected_tabs])
        if not selected_tabs:
            LOGGER.warning("Stash is open but no stash tabs are selected in settings")
        for tab in selected_tabs:
            if not stash.switch_to_tab(tab):
                LOGGER.warning("Skipping invalid or unavailable stash tab: %s", tab + 1)
                continue
            time.sleep(0.3)
            LOGGER.info("Filtering stash tab %s", tab + 1)
            check_items(stash, force_refresh, stash_is_open=True, no_match_action="junk")
        move_pointer(*abs_window_to_monitor((0, 0)))
        if target == "both":
            move_pointer(*abs_window_to_monitor((0, 0)))
            time.sleep(0.3)
            LOGGER.info("Filtering character inventory after stash tabs")
            check_items(inv, force_refresh, stash_is_open=True, no_match_action="junk")
        else:
            LOGGER.info("Stash-only filter done")
            return
    else:
        LOGGER.info("Stash not detected; filtering character inventory")
        if not inv.open():
            screenshot("inventory_not_open", img=capture())
            LOGGER.error("Inventory did not open up")
            return
        check_items(inv, force_refresh, no_match_action=no_match_action)
    move_pointer(*abs_window_to_monitor((0, 0)))
    LOGGER.info("Loot filter done")
