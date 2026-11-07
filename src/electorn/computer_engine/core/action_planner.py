"""
Action Planner: Translates high-level natural language instructions into ordered TaskPlans.
"""

import time
import re
import urllib.parse
from typing import Optional, List
from electorn.computer_engine.types import (
    TaskPlan,
    TaskStep,
    ActionPayload,
    ComputerState,
)


class ActionPlanner:
    def plan_instruction(
        self,
        instruction: str,
        current_state: Optional[ComputerState] = None,
    ) -> TaskPlan:
        clean = instruction.strip()
        lower = clean.lower()
        task_id = f"task_{int(time.time() * 1000)}"

        steps: List[TaskStep] = []
        target_app = "Desktop"

        # 1. Browser Search Workflows
        if any(k in lower for k in ["chrome", "edge", "browser", "search for", "search online"]):
            target_app = "Google Chrome"
            match = re.search(r"search(?:\s+for|\s+online)?\s+([^.]+)", clean, re.IGNORECASE)
            query = match.group(1).strip() if match else "latest technology"

            steps.append(
                TaskStep(
                    step_id="step_launch_browser",
                    order=1,
                    description=f"Launch web browser and search for '{query}'",
                    action=ActionPayload(
                        action_id="act_browser_1",
                        category="browser",
                        type="open_url",
                        url=f"https://www.google.com/search?q={urllib.parse.quote(query)}",
                        description=f"Open Google search for '{query}'",
                        risk_level="safe",
                    ),
                    expected_outcome="Browser window is loaded with search results",
                )
            )

        # 2. VS Code & Python Project Workflows
        elif any(k in lower for k in ["vs code", "vscode", "python project", "open code"]):
            target_app = "Visual Studio Code"
            steps.append(
                TaskStep(
                    step_id="step_launch_vscode",
                    order=1,
                    description="Launch Visual Studio Code",
                    action=ActionPayload(
                        action_id="act_vscode_1",
                        category="window",
                        type="launch_app",
                        target="code",
                        description="Launch VS Code",
                        risk_level="safe",
                    ),
                    expected_outcome="VS Code window is active",
                )
            )
            steps.append(
                TaskStep(
                    step_id="step_create_file",
                    order=2,
                    description="Open new file in editor",
                    action=ActionPayload(
                        action_id="act_vscode_2",
                        category="keyboard",
                        type="shortcut",
                        keys=["ctrl", "n"],
                        description="Press Ctrl+N for new file",
                        risk_level="safe",
                    ),
                    expected_outcome="New editor tab opened",
                )
            )

        # 3. Excel & Spreadsheet Workflows
        elif any(k in lower for k in ["excel", "spreadsheet", "table"]):
            target_app = "Microsoft Excel"
            steps.append(
                TaskStep(
                    step_id="step_launch_excel",
                    order=1,
                    description="Launch Microsoft Excel or spreadsheet",
                    action=ActionPayload(
                        action_id="act_excel_1",
                        category="window",
                        type="launch_app",
                        target="excel",
                        description="Launch Microsoft Excel",
                        risk_level="safe",
                    ),
                    expected_outcome="Excel window is active",
                )
            )

        # 4. Terminal & Shell Command Workflows
        elif any(k in lower for k in ["terminal", "powershell", "run command", "open cmd"]):
            target_app = "PowerShell Terminal"
            steps.append(
                TaskStep(
                    step_id="step_launch_terminal",
                    order=1,
                    description="Launch PowerShell terminal",
                    action=ActionPayload(
                        action_id="act_term_1",
                        category="window",
                        type="launch_app",
                        target="powershell",
                        description="Open PowerShell",
                        risk_level="safe",
                    ),
                    expected_outcome="Terminal is open and focused",
                )
            )

        # 5. Direct Click / Type Commands
        elif lower.startswith("click") or "click " in lower:
            target = re.sub(r".*click\s+", "", clean, flags=re.IGNORECASE).strip()
            steps.append(
                TaskStep(
                    step_id="step_click_1",
                    order=1,
                    description=f"Click target '{target}'",
                    action=ActionPayload(
                        action_id="act_click_1",
                        category="mouse",
                        type="click",
                        target=target,
                        description=f"Locate and click '{target}'",
                        risk_level="safe",
                    ),
                    expected_outcome=f"Target '{target}' clicked",
                )
            )
        elif lower.startswith("type") or "type " in lower:
            quote_match = re.search(r"type\s+['\"](.*?)['\"]", clean, re.IGNORECASE)
            if quote_match:
                text = quote_match.group(1)
            else:
                text = re.sub(r"^type\s+", "", clean, flags=re.IGNORECASE).strip().strip("'\"")

            steps.append(
                TaskStep(
                    step_id="step_type_1",
                    order=1,
                    description=f"Type text '{text}'",
                    action=ActionPayload(
                        action_id="act_type_1",
                        category="keyboard",
                        type="type_text",
                        text=text,
                        description="Type text into focused element",
                        risk_level="safe",
                    ),
                    expected_outcome="Text entered into field",
                )
            )

        # Fallback single step
        if not steps:
            steps.append(
                TaskStep(
                    step_id="step_custom_1",
                    order=1,
                    description=clean,
                    action=ActionPayload(
                        action_id="act_custom_1",
                        category="system",
                        type="custom_command",
                        description=clean,
                        risk_level="safe",
                    ),
                    expected_outcome="Operation completed",
                )
            )

        return TaskPlan(
            task_id=task_id,
            original_instruction=clean,
            goal=clean,
            target_application=target_app,
            steps=steps,
            current_step_index=0,
            status="planned",
            start_time=time.time(),
        )
