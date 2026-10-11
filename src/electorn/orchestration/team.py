"""Coordinates the multi-agent AI development team."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Callable, Optional
from electorn.agents.architect import ArchitectAgent
from electorn.agents.backend import BackendAgent
from electorn.agents.database import DatabaseAgent
from electorn.agents.devops import DevOpsAgent
from electorn.agents.frontend import FrontendAgent
from electorn.agents.integration import IntegrationAgent
from electorn.agents.qa_tester import QATesterAgent
from electorn.agents.ui_ux import UIUXAgent
from electorn.execution.powershell import PowerShellExecutionEngine
from electorn.execution.runner import CommandRunner
from electorn.orchestration.application_builder import ApplicationBuilder
from electorn.orchestration.memory_manager import MemoryManager
from electorn.orchestration.workflow import WorkflowPipeline
from electorn.runtime.model_selector import ModelProfile, ModelSelector
from electorn.runtime.ollama_client import OllamaClient
from electorn.storage.config import Config
from electorn.storage.history import SessionHistory
from electorn.storage.project_memory import ProjectMemory
from electorn.verification.self_repair import SelfRepairEngine
from electorn.verification.syntax_checker import SyntaxChecker
from electorn.verification.test_runner import TestRunner
from electorn.workspace.checkpoints import CheckpointManager
from electorn.workspace.file_manager import FileManager, FileOperationResult
from electorn.workspace.permissions import PermissionManager
from electorn.orchestration.planner import TaskPlanner


class MultiAgentTeam:
    """Orchestrates the entire team of specialized AI agents for autonomous development."""

    def __init__(
        self,
        workspace_dir: Path | str = ".",
        config: Optional[Config] = None,
        model_name: Optional[str] = None,
        auto_approve: bool = False,
        mock_mode: bool = False,
        on_file_op: Optional[Callable[[FileOperationResult], None]] = None,
    ):
        self.workspace_dir = Path(workspace_dir).resolve()
        self.config = config or Config()
        self.auto_approve = auto_approve
        self.mock_mode = mock_mode
        self.on_file_op = on_file_op

        # Core runtime
        self.client = OllamaClient(
            base_url=self.config.runtime.ollama_base_url,
            timeout=self.config.runtime.timeout_seconds,
            mock_mode=self.mock_mode,
        )
        self.selector = ModelSelector(self.client)
        self.model_profile: ModelProfile = self.selector.select_best_model(
            preferred_model=model_name or self.config.runtime.model
        )

        # Permissions and File Management
        self.permissions = PermissionManager(auto_approve=self.auto_approve)
        self.file_manager = FileManager(
            workspace_root=self.workspace_dir,
            permissions=self.permissions,
            ignore_patterns=self.config.workspace.ignore_patterns,
            on_file_op=self.on_file_op,
        )

        # Execution and Verification Tools
        self.powershell = PowerShellExecutionEngine(
            workspace_dir=self.workspace_dir,
            permissions=self.permissions,
        )
        self.runner = CommandRunner(
            workspace_dir=self.workspace_dir,
            permissions=self.permissions,
        )
        self.syntax_checker = SyntaxChecker(self.file_manager)
        self.test_runner = TestRunner(self.file_manager, self.runner)
        self.repair_engine = SelfRepairEngine(
            file_manager=self.file_manager,
            syntax_checker=self.syntax_checker,
            test_runner=self.test_runner,
            max_attempts=self.config.orchestration.max_repair_attempts,
        )

        # Memory, Checkpoint, and Task Planner
        self.memory = MemoryManager(self.file_manager)
        self.checkpoints = CheckpointManager(self.workspace_dir, ignore_patterns=self.config.workspace.ignore_patterns)
        self.project_memory = ProjectMemory(self.workspace_dir)
        self.planner = TaskPlanner()

        # Session Audit Tracking
        self.session_id = f"electorn-{uuid.uuid4().hex[:8]}"
        self.history = SessionHistory(
            session_id=self.session_id,
            prompt="",
            model_used=self.model_profile.name,
            workspace_dir=str(self.workspace_dir),
        )

        # Specialized Agent Initialization
        self.architect = ArchitectAgent(self.client, self.model_profile)
        self.ui_ux = UIUXAgent(self.client, self.model_profile)
        self.database = DatabaseAgent(self.client, self.model_profile)
        self.backend = BackendAgent(self.client, self.model_profile)
        self.frontend = FrontendAgent(self.client, self.model_profile)
        self.integration = IntegrationAgent(self.client, self.model_profile)
        self.qa_tester = QATesterAgent(self.client, self.model_profile)
        self.devops = DevOpsAgent(self.client, self.model_profile)

        # Workflow Pipeline & Dedicated Builder
        self.pipeline = WorkflowPipeline(self)
        self.builder = ApplicationBuilder(self)

    def build_application(self, prompt: str, install_deps: bool = True, launch_preview: bool = False):
        """Execute autonomous application building engine."""
        return self.builder.build(prompt, install_dependencies=install_deps, launch_preview=launch_preview)

    def develop(self, prompt: str, **callbacks):
        """Execute the full development lifecycle for the user prompt."""
        self.history.prompt = prompt
        try:
            state = self.pipeline.execute(prompt, **callbacks)
            self.history.status = "completed" if state.is_completed else "partial"
            self.history.save(self.workspace_dir)
            return state
        except Exception as err:
            self.history.status = "failed"
            self.history.save(self.workspace_dir)
            raise err
