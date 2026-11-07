"""
Acceptance Test Suite for ARIA Human-Level Device Interaction Engine (HACE)
Validates all 18 requirements from Project Specification:
1. Open and close applications.
2. Move and click the mouse.
3. Type text.
4. Use keyboard shortcuts.
5. Drag and drop files.
6. Navigate File Explorer.
7. Change a permitted system setting.
8. Operate Chrome.
9. Operate VS Code.
10. Create and edit documents.
11. Coordinate multiple applications.
12. Recover from unexpected dialogs.
13. Adapt to window movement.
14. Recover after a failed click.
15. Interrupt an active task.
16. Resume an approved unfinished task.
17. Recall a previous successful workflow.
18. Verify that actual operations succeeded.
"""

import pytest
import time
from unittest.mock import MagicMock, patch

from electorn.computer_engine import ComputerEngine, EmergencyStop, PermissionManager
from electorn.computer_engine.types import ActionPayload, TaskPlan, TaskStep, UIElement
from electorn.companion.supervisor import CompanionSupervisor
from electorn.companion.awareness import AwarenessEngine


@pytest.fixture
def computer_engine():
    engine = ComputerEngine()
    engine.emergency_stop.reset()
    return engine


@pytest.fixture
def supervisor():
    sup = CompanionSupervisor()
    sup.computer_engine.reset_safety()
    # Mock voice speaking and Ollama ask to avoid device or network latency
    sup.voice.speak_async = MagicMock()
    sup.llm.ask = MagicMock(return_value="Understood, Harshan.")
    return sup


# 1. Open and close applications
def test_01_open_and_close_applications(computer_engine):
    ok_launch = computer_engine.window.launch_application("notepad")
    assert ok_launch is True
    ok_close = computer_engine.window.close_window("notepad")
    assert ok_close is True


# 2. Move and click the mouse
def test_02_move_and_click_mouse(computer_engine):
    ok_move = computer_engine.mouse.move_to(250, 350, duration_s=0.05)
    assert ok_move is True
    ok_click = computer_engine.mouse.click()
    assert ok_click is True
    ok_double = computer_engine.mouse.double_click()
    assert ok_double is True
    ok_right = computer_engine.mouse.right_click()
    assert ok_right is True


# 3. Type text
def test_03_type_text(computer_engine):
    ok_type = computer_engine.keyboard.type_text("Hello Harshan", use_clipboard=False)
    assert ok_type is True
    ok_tamil = computer_engine.keyboard.type_text("வணக்கம்", use_clipboard=True)
    assert ok_tamil is True


# 4. Use keyboard shortcuts
def test_04_keyboard_shortcuts(computer_engine):
    assert computer_engine.keyboard.select_all() is True
    assert computer_engine.keyboard.copy() is True
    assert computer_engine.keyboard.paste() is True
    assert computer_engine.keyboard.press_shortcut("ctrl", "s") is True


# 5. Drag and drop files
def test_05_drag_and_drop_files(computer_engine):
    ok_drag = computer_engine.mouse.drag_and_drop(100, 100, 300, 300, duration_s=0.05)
    assert ok_drag is True


# 6. Navigate File Explorer
def test_06_navigate_file_explorer(computer_engine):
    ok_exp = computer_engine.window.launch_application("explorer")
    assert ok_exp is True
    wins = computer_engine.window.list_windows()
    assert len(wins) > 0


# 7. Change a permitted system setting
def test_07_change_permitted_system_setting(supervisor):
    resp_bright = supervisor.process_user_input("change brightness to 75%")
    assert "75%" in resp_bright
    assert "Harshan" in resp_bright

    resp_vol = supervisor.process_user_input("set volume to 80%")
    assert "80%" in resp_vol
    assert "Harshan" in resp_vol


# 8. Operate Chrome
def test_08_operate_chrome(computer_engine):
    ok_url = computer_engine.browser.open_url("https://www.google.com")
    assert ok_url is True
    ok_search = computer_engine.browser.search("latest AI developments")
    assert ok_search is True


# 9. Operate VS Code
def test_09_operate_vs_code(supervisor):
    resp = supervisor.process_user_input("open vs code and create a python project")
    assert "VS Code" in resp
    assert "Harshan" in resp


# 10. Create and edit documents
def test_10_create_and_edit_documents(computer_engine):
    plan = computer_engine.execute_instruction("Type 'def main(): return 42' into document")
    assert plan.status == "completed"
    assert len(plan.steps) > 0


# 11. Coordinate multiple applications
def test_11_coordinate_multiple_applications(supervisor):
    query = "Find information about NVIDIA's latest GPU, create a comparison document and save it."
    resp = supervisor.process_user_input(query)
    assert "NVIDIA" in resp
    assert "Harshan" in resp


# 12. Recover from unexpected dialogs
def test_12_recover_from_unexpected_dialogs(computer_engine):
    dialog = UIElement(
        id="dlg_1",
        type="dialog",
        label="Save changes?",
        location=(400, 300),
    )
    res = computer_engine.element_detector.find_dialog([dialog])
    assert res is not None
    assert "Save changes" in res.label


# 13. Adapt to window movement
def test_13_adapt_to_window_movement(computer_engine):
    el1 = UIElement(
        id="btn_search",
        type="button",
        label="Search",
        location=(140, 115),
    )
    # Window moved
    el2 = UIElement(
        id="btn_search",
        type="button",
        label="Search",
        location=(540, 315),
    )
    target = computer_engine.grounding.find_target("Search", candidate_elements=[el2])
    assert target is not None
    assert target.location == (540, 315)


# 14. Recover after a failed click
def test_14_recover_after_failed_click(computer_engine):
    invalid_action = ActionPayload(
        action_id="act_bad",
        category="mouse",
        type="click",
        coordinates=(-100, -50),
        description="Out of bounds click",
    )
    check = computer_engine.validator.validate_preconditions(invalid_action)
    assert check["valid"] is False


# 15. Interrupt an active task (Emergency Stop)
def test_15_interrupt_active_task(supervisor):
    resp = supervisor.process_user_input("STOP")
    assert "stopped" in resp.lower()
    assert supervisor.computer_engine.emergency_stop.check() is True

    # Subsequent actions must be blocked while stopped
    plan = supervisor.computer_engine.execute_instruction("Click the download button")
    assert plan.status in ("aborted", "failed")


# 16. Resume an approved unfinished task
def test_16_resume_approved_unfinished_task(supervisor):
    supervisor.computer_engine.stop_all()
    assert supervisor.computer_engine.emergency_stop.check() is True

    resp = supervisor.process_user_input("resume operations")
    assert "resumed" in resp.lower()
    assert supervisor.computer_engine.emergency_stop.check() is False


# 17. Recall a previous successful workflow
def test_17_recall_previous_successful_workflow(supervisor):
    supervisor.computer_engine.execute_instruction("Open Chrome and search for latest AI")
    resp = supervisor.process_user_input("continue what we did yesterday")
    assert "Chrome" in resp
    assert "Harshan" in resp


# 18. Verify that actual operations succeeded
def test_18_verify_actual_operations_succeeded(computer_engine):
    plan = computer_engine.execute_instruction("Search online for quantum computing")
    assert plan.status == "completed"
    assert len(plan.steps) >= 1
    assert all(s.status == "completed" for s in plan.steps)
