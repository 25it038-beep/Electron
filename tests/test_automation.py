"""Unit tests for Full OS Automation & Selenium Browser Automation."""

from unittest.mock import MagicMock, patch
import pytest

from electorn.automation import AutomationEngine


def test_selenium_is_available():
    engine = AutomationEngine()
    assert engine.is_selenium_available() is True


def test_get_system_specs_and_health():
    engine = AutomationEngine()
    health = engine.get_system_health()
    assert "os" in health
    assert "cpu_percent" in health

    specs = engine.get_system_specs()
    assert "OS:" in specs
    assert "CPU Usage:" in specs


@patch("pyautogui.hotkey")
def test_minimize_and_window_controls(mock_hotkey):
    engine = AutomationEngine()
    msg = engine.minimize_all_windows()
    assert "Minimized" in msg
    mock_hotkey.assert_called_with("win", "d")

    msg2 = engine.maximize_window()
    assert "Maximized" in msg2
    mock_hotkey.assert_called_with("win", "up")


@patch("pyautogui.press")
def test_volume_and_media_controls(mock_press):
    engine = AutomationEngine()
    msg_vol = engine.control_volume("up")
    assert "volume up" in msg_vol.lower()

    msg_med = engine.control_media("playpause")
    assert "media playback" in msg_med.lower()


@patch("electorn.automation.AutomationEngine.open_path", return_value="Opened folder")
def test_open_special_folder(mock_open):
    engine = AutomationEngine()
    res = engine.open_special_folder("downloads")
    assert "Opened folder" in res


def test_create_directory_and_file(tmp_path):
    engine = AutomationEngine()
    test_dir = tmp_path / "subfolder"
    dir_res = engine.create_directory(str(test_dir))
    assert test_dir.exists()
    assert "Created directory" in dir_res

    test_file = test_dir / "sample.txt"
    file_res = engine.create_file(str(test_file), "Hello Electorn")
    assert test_file.exists()
    assert test_file.read_text(encoding="utf-8") == "Hello Electorn"
    assert "Created file" in file_res


@patch("pyperclip.paste", return_value="Sample clipboard text")
@patch("pyperclip.copy")
def test_clipboard_operations(mock_copy, mock_paste):
    engine = AutomationEngine()
    assert "Sample clipboard text" in engine.get_clipboard()
    res = engine.set_clipboard("New text")
    assert "Copied" in res
    mock_copy.assert_called_with("New text")


def test_execute_intent_minimize_windows():
    engine = AutomationEngine()
    with patch.object(engine, "minimize_all_windows", return_value="Minimized"):
        res = engine.execute_intent("minimize windows")
        assert res is not None
        assert res["action"] == "minimize_windows"
        assert res["success"] is True


def test_execute_intent_volume():
    engine = AutomationEngine()
    with patch.object(engine, "control_volume", return_value="Turned volume up"):
        res = engine.execute_intent("volume up")
        assert res is not None
        assert res["action"] == "volume"
        assert res["success"] is True


def test_execute_intent_open_folder():
    engine = AutomationEngine()
    with patch.object(engine, "open_special_folder", return_value="Opened Downloads"):
        res = engine.execute_intent("open downloads")
        assert res is not None
        assert res["action"] == "open_folder"
        assert res["success"] is True


def test_execute_intent_search_web():
    engine = AutomationEngine()
    with patch.object(engine, "search_web", return_value="Searched Google for FastAPI"):
        res = engine.execute_intent("search for FastAPI on google")
        assert res is not None
        assert res["action"] == "search_web"
        assert res["success"] is True
        assert "FastAPI" in res["spoken_response"]


def test_execute_intent_open_url():
    engine = AutomationEngine()
    with patch.object(engine, "open_url", return_value="Navigated to https://github.com"):
        res = engine.execute_intent("open github")
        assert res is not None
        assert res["action"] == "open_url"
        assert res["success"] is True
        assert "Github" in res["spoken_response"]


def test_execute_intent_launch_and_close_app():
    engine = AutomationEngine()
    with patch.object(engine, "launch_application", return_value="Opened Notepad"):
        res = engine.execute_intent("open notepad")
        assert res is not None
        assert res["action"] == "launch_app"
        assert res["success"] is True

    with patch.object(engine, "close_application", return_value="Closed Notepad"):
        res_close = engine.execute_intent("close notepad")
        assert res_close is not None
        assert res_close["action"] == "close_app"
        assert res_close["success"] is True


def test_execute_intent_non_automation():
    engine = AutomationEngine()
    res = engine.execute_intent("Can you explain how machine learning models work?")
    assert res is None
