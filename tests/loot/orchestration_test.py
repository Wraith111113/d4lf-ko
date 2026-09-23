from typing import Never

from src.loot import orchestration as _orchestration
from src.settings import ItemRefreshType


def test_loot_filter_processes_stash_tabs_before_inventory(monkeypatch) -> None:
    calls = []

    class Settings:
        class General:
            check_chest_tabs = [2, 4]

        general = General()

    class Stash:
        def is_open(self) -> bool:
            return True

        def switch_to_tab(self, tab) -> bool:
            calls.append(("tab", tab))
            return True

    class Inventory:
        def open(self) -> Never:
            raise AssertionError

    monkeypatch.setattr(_orchestration, "get_settings", lambda: Settings())
    monkeypatch.setattr(_orchestration, "stash_inventory", lambda: Stash())
    monkeypatch.setattr(_orchestration, "character_inventory", lambda: Inventory())
    monkeypatch.setattr(_orchestration, "move_pointer", lambda *pos: calls.append(("pointer", pos)))
    monkeypatch.setattr(_orchestration, "abs_window_to_monitor", lambda pos: pos)
    monkeypatch.setattr(_orchestration, "check_items", lambda *args, **kwargs: calls.append(("check", args, kwargs)))
    _orchestration.run_loot_filter(ItemRefreshType.no_refresh)
    assert [call[0:2] for call in calls if call[0] == "tab"] == [("tab", 2), ("tab", 4)]
    assert [call[0] for call in calls].count("check") == 3


def test_loot_filter_skips_failed_stash_tab_switch(monkeypatch) -> None:
    calls = []

    class Settings:
        class General:
            check_chest_tabs = [0, 1]

        general = General()

    class Stash:
        def is_open(self) -> bool:
            return True

        def switch_to_tab(self, tab) -> bool:
            calls.append(("tab", tab))
            return tab == 1

    class Inventory:
        def open(self):
            raise AssertionError

    monkeypatch.setattr(_orchestration, "get_settings", lambda: Settings())
    monkeypatch.setattr(_orchestration, "stash_inventory", lambda: Stash())
    monkeypatch.setattr(_orchestration, "character_inventory", lambda: Inventory())
    monkeypatch.setattr(_orchestration, "move_pointer", lambda *_pos: None)
    monkeypatch.setattr(_orchestration, "abs_window_to_monitor", lambda pos: pos)
    monkeypatch.setattr(_orchestration, "check_items", lambda *args, **_kwargs: calls.append(("check", args)))
    _orchestration.run_loot_filter(ItemRefreshType.no_refresh)
    assert [call[0:2] for call in calls if call[0] == "tab"] == [("tab", 0), ("tab", 1)]
    assert [call[0] for call in calls].count("check") == 2


def test_inventory_target_does_not_filter_stash_even_when_open(monkeypatch) -> None:
    calls = []

    class Settings:
        class General:
            check_chest_tabs = [0]

        general = General()

    class Stash:
        def is_open(self) -> bool:
            return True

    class Inventory:
        def open(self) -> bool:
            calls.append(("open_inventory",))
            return True

    inventory = Inventory()
    monkeypatch.setattr(_orchestration, "get_settings", lambda: Settings())
    monkeypatch.setattr(_orchestration, "stash_inventory", lambda: Stash())
    monkeypatch.setattr(_orchestration, "character_inventory", lambda: inventory)
    monkeypatch.setattr(_orchestration, "move_pointer", lambda *_pos: None)
    monkeypatch.setattr(_orchestration, "abs_window_to_monitor", lambda pos: pos)
    monkeypatch.setattr(_orchestration, "check_items", lambda inventory, *_args, **_kwargs: calls.append(inventory))

    _orchestration.run_loot_filter(ItemRefreshType.no_refresh, target="inventory")

    assert calls[0] == ("open_inventory",)
    assert len(calls) == 2
    assert calls[1] is inventory


def test_stash_target_does_not_fall_back_to_inventory(monkeypatch) -> None:
    class Settings:
        class General:
            check_chest_tabs = [0]

        general = General()

    class Stash:
        def is_open(self) -> bool:
            return False

    class Inventory:
        def open(self):
            message = "Stash-only filtering must not open inventory"
            raise AssertionError(message)

    monkeypatch.setattr(_orchestration, "get_settings", lambda: Settings())
    monkeypatch.setattr(_orchestration, "stash_inventory", lambda: Stash())
    monkeypatch.setattr(_orchestration, "character_inventory", lambda: Inventory())
    _orchestration.run_loot_filter(ItemRefreshType.no_refresh, target="stash")
