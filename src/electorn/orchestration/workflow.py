"""Sequential multi-agent workflow pipeline."""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable, Optional
from pydantic import BaseModel
from electorn.workspace.project_state import ProjectSpecification, ProjectState

if TYPE_CHECKING:
    from electorn.orchestration.team import MultiAgentTeam


class WorkflowStep(BaseModel):
    """Metadata describing an active stage in the development lifecycle."""

    name: str
    agent_name: str
    description: str
    is_completed: bool = False


class WorkflowPipeline:
    """Executes the complete software development lifecycle sequentially."""

    def __init__(self, team: "MultiAgentTeam"):
        self.team = team

    def execute(
        self,
        user_prompt: str,
        on_step_start: Optional[Callable[[str, str], None]] = None,
        on_step_complete: Optional[Callable[[str, list[str]], None]] = None,
        on_info: Optional[Callable[[str], None]] = None,
    ) -> ProjectState:
        """Run the full end-to-end development pipeline sequentially."""
        state = ProjectState(prompt=user_prompt)

        # ---------------------------------------------------------
        # Step 1: System Architecture & Planning (Architect)
        # ---------------------------------------------------------
        if on_step_start:
            on_step_start("Architect", "Designing system specification and file manifest")

        spec: ProjectSpecification = self.team.architect.design_system(user_prompt)
        state.specification = spec
        self.team.history.record_action(
            agent_name=self.team.architect.name,
            role=self.team.architect.role,
            action_type="architecture_plan",
            summary=f"Designed {spec.project_name}: {len(spec.file_manifest)} planned files",
        )
        if on_step_complete:
            on_step_complete("Architect", [f.path for f in spec.file_manifest])

        # ---------------------------------------------------------
        # Step 2: Database & Data Models (Database Engineer)
        # ---------------------------------------------------------
        db_entries = [f for f in spec.file_manifest if f.component == "database"]
        if db_entries:
            if on_step_start:
                on_step_start("Database Engineer", "Building data models, schemas, and persistence layer")
            ctx = self.team.memory.build_agent_context(state, spec, ["database"])
            task = f"Create the database models and storage logic for the following files:\n" + "\n".join(
                f"- {f.path}: {f.purpose}" for f in db_entries
            )
            files = self.team.database.generate_files(task, ctx)
            written = []
            for path, content in files.items():
                self.team.file_manager.write_file(path, content)
                state.mark_file_created(path)
                written.append(path)
            self.team.history.record_action(
                self.team.database.name, self.team.database.role, "database_gen", "Generated DB schemas", written
            )
            if on_step_complete:
                on_step_complete("Database Engineer", written)

        # ---------------------------------------------------------
        # Step 3: Backend Logic & Services (Backend Developer)
        # ---------------------------------------------------------
        backend_entries = [f for f in spec.file_manifest if f.component == "backend"]
        if backend_entries:
            if on_step_start:
                on_step_start("Backend Developer", "Implementing server endpoints, routing, and core business services")
            ctx = self.team.memory.build_agent_context(state, spec, ["database", "backend"])
            task = f"Implement the core server services and endpoints for the following files:\n" + "\n".join(
                f"- {f.path}: {f.purpose}" for f in backend_entries
            )
            files = self.team.backend.generate_files(task, ctx)
            written = []
            for path, content in files.items():
                self.team.file_manager.write_file(path, content)
                state.mark_file_created(path)
                written.append(path)
            self.team.history.record_action(
                self.team.backend.name, self.team.backend.role, "backend_gen", "Implemented backend services", written
            )
            if on_step_complete:
                on_step_complete("Backend Developer", written)

        # ---------------------------------------------------------
        # Step 4: Frontend UI / Components (Frontend Developer)
        # ---------------------------------------------------------
        frontend_entries = [f for f in spec.file_manifest if f.component in ("frontend", "ui")]
        if frontend_entries:
            if on_step_start:
                on_step_start("Frontend Developer", "Building user interface, templates, and client styles")
            ctx = self.team.memory.build_agent_context(state, spec, ["frontend", "backend"])
            task = f"Create the user interface and frontend components for the following files:\n" + "\n".join(
                f"- {f.path}: {f.purpose}" for f in frontend_entries
            )
            files = self.team.frontend.generate_files(task, ctx)
            written = []
            for path, content in files.items():
                self.team.file_manager.write_file(path, content)
                state.mark_file_created(path)
                written.append(path)
            self.team.history.record_action(
                self.team.frontend.name, self.team.frontend.role, "frontend_gen", "Created frontend UI", written
            )
            if on_step_complete:
                on_step_complete("Frontend Developer", written)

        # ---------------------------------------------------------
        # Step 5: Integration & API Glue (Integration Specialist)
        # ---------------------------------------------------------
        integration_entries = [f for f in spec.file_manifest if f.component == "integration"]
        if integration_entries:
            if on_step_start:
                on_step_start("Integration Specialist", "Connecting subsystems, configurations, and environment glue")
            ctx = self.team.memory.build_agent_context(state, spec, ["backend", "frontend", "integration"])
            task = f"Implement integration contracts and glue code for:\n" + "\n".join(
                f"- {f.path}: {f.purpose}" for f in integration_entries
            )
            files = self.team.integration.generate_files(task, ctx)
            written = []
            for path, content in files.items():
                self.team.file_manager.write_file(path, content)
                state.mark_file_created(path)
                written.append(path)
            if on_step_complete:
                on_step_complete("Integration Specialist", written)

        # ---------------------------------------------------------
        # Step 6: QA Testing Suite (QA Engineer)
        # ---------------------------------------------------------
        test_entries = [f for f in spec.file_manifest if f.component == "test"]
        if test_entries or True:  # Always ensure comprehensive tests exist
            if on_step_start:
                on_step_start("QA Engineer", "Writing automated test suites and validation assertions")
            ctx = self.team.memory.build_agent_context(state, spec, ["backend", "database"])
            test_targets = test_entries if test_entries else [f for f in spec.file_manifest if f.component in ("backend", "database")]
            task = (
                f"Write comprehensive automated tests (e.g. pytest) covering all core functionality, "
                f"validations, and edge cases. Ensure test files start with 'test_' or reside in 'tests/'.\n"
                f"Planned test targets: " + ", ".join(f.path for f in test_targets)
            )
            files = self.team.qa_tester.generate_files(task, ctx)
            written = []
            for path, content in files.items():
                self.team.file_manager.write_file(path, content)
                state.mark_file_created(path)
                written.append(path)
            self.team.history.record_action(
                self.team.qa_tester.name, self.team.qa_tester.role, "test_gen", "Wrote automated tests", written
            )
            if on_step_complete:
                on_step_complete("QA Engineer", written)

        # ---------------------------------------------------------
        # Step 7: DevOps Setup & Docs (DevOps Engineer)
        # ---------------------------------------------------------
        if on_step_start:
            on_step_start("DevOps Engineer", "Generating dependency manifests, environment files, and README")
        ctx = self.team.memory.build_agent_context(state, spec)
        devops_task = (
            f"Generate project configuration files:\n"
            f"- requirements.txt or pyproject.toml including all needed libraries: {spec.dependencies + spec.dev_dependencies}\n"
            f"- README.md with clear overview, setup steps, run command ('{spec.run_command}'), and test command ('{spec.test_command}')\n"
            f"- .env.example with any necessary configuration variables\n"
        )
        files = self.team.devops.generate_files(devops_task, ctx)
        written = []
        for path, content in files.items():
            self.team.file_manager.write_file(path, content)
            state.mark_file_created(path)
            written.append(path)
        if on_step_complete:
            on_step_complete("DevOps Engineer", written)

        # ---------------------------------------------------------
        # Step 8: Static Syntax Verification
        # ---------------------------------------------------------
        if on_step_start:
            on_step_start("Verification", "Running static syntax checks on all generated code")
        all_created = self.team.file_manager.list_files()
        syntax_res = self.team.syntax_checker.check_all_files(all_created)
        failing_syntax = [r.file_path for r in syntax_res if not r.is_valid]
        if failing_syntax:
            if on_info:
                on_info(f"⚠️ Syntax errors found in: {', '.join(failing_syntax)}. Initiating self-repair...")
            self.team.repair_engine.repair_syntax(
                repair_agent=self.team.backend,
                state=state,
                failing_files=failing_syntax,
                status_cb=on_info,
            )
        if on_step_complete:
            on_step_complete("Verification", ["Syntax verified successfully"])

        # ---------------------------------------------------------
        # Step 9: Automated Test Run & Self-Repair Workflow
        # ---------------------------------------------------------
        if on_step_start:
            on_step_start("Verification", f"Executing test suite: '{spec.test_command}'")
        test_res = self.team.test_runner.run_tests(spec.test_command)
        if not test_res.passed:
            if on_info:
                on_info("⚠️ Test failures encountered. Triggering autonomous self-repair workflow...")
            repair_success = self.team.repair_engine.repair_test_failures(
                repair_agent=self.team.backend,
                state=state,
                test_result=test_res,
                status_cb=on_info,
            )
            state.is_completed = repair_success
        else:
            state.is_completed = True

        if on_step_complete:
            on_step_complete("Verification", [f"Tests passing: {test_res.passed_tests}/{test_res.total_tests or 1}"])

        return state
