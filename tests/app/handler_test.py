import threading
import typing

if typing.TYPE_CHECKING:
    from pytest_mock import MockerFixture

from src.app.handler import ScriptHandler


def test_loot_interaction_stops_and_restarts_running_vision_mode(mocker: MockerFixture) -> None:
    handler = object.__new__(ScriptHandler)
    handler.loot_interaction_thread = threading.Thread()
    handler.did_stop_scripts = False
    handler.run_vision_mode = mocker.Mock()

    class VisionMode:
        def __init__(self) -> None:
            self.stopped = False

        def running(self) -> bool:
            return not self.stopped

        def stop(self) -> None:
            self.stopped = True

        def start(self) -> None:
            self.stopped = False

    handler.vision_mode = VisionMode()
    action = mocker.Mock()

    handler._wrapper_run_loot_interaction_method(action)

    action.assert_called_once_with()
    handler.run_vision_mode.assert_called_once_with()
    assert handler.loot_interaction_thread is None


def test_loot_interaction_logs_failure_and_restores_vision_mode(mocker: MockerFixture, caplog) -> None:
    handler = object.__new__(ScriptHandler)
    handler.loot_interaction_thread = threading.Thread()
    handler.did_stop_scripts = False
    handler.run_vision_mode = mocker.Mock()

    class VisionMode:
        def running(self) -> bool:
            return False

        def stop(self) -> None:
            pass

    handler.vision_mode = VisionMode()

    def failing_action() -> None:
        failure_message = "filter failure"
        raise RuntimeError(failure_message)

    handler._wrapper_run_loot_interaction_method(failing_action)

    assert "Loot interaction failed while running failing_action" in caplog.text
    assert handler.loot_interaction_thread is None


def test_filter_hotkey_is_registered_without_foreground_gate(mocker: MockerFixture) -> None:
    handler = object.__new__(ScriptHandler)
    handler._config = mocker.Mock()
    handler._config.advanced_options = mocker.Mock(
        run_vision_mode="f9",
        exit_key="f12",
        toggle_paragon_overlay="f10",
        info_overlay="f6",
        vision_mode_only=False,
        run_filter="f11",
        run_stash_filter="alt+f11",
        run_filter_drop="ctrl+f11",
        run_filter_force_refresh="shift+f11",
        force_refresh_only="ctrl+shift+f11",
        move_to_inv="f7",
        move_to_chest="f8",
    )
    handler._config.char.inventory = "i"
    handler._hotkey_handles = []
    handler._register_hotkey = mocker.Mock()
    handler.setup_key_binds()
    registered = {
        call.args[0]: call.kwargs.get("check_focus", True) for call in handler._register_hotkey.call_args_list
    }
    assert registered["f11"] is False
    assert registered["ctrl+f11"] is False
    assert registered["shift+f11"] is False
    assert registered["alt+f11"] is False
