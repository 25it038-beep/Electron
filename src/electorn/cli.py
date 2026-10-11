"""Electorn AI - Command Line Interface.

One CLI. A Complete AI Development Team.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional
import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich.text import Text
from rich.tree import Tree

from typer.core import TyperGroup
from electorn import __version__
from electorn.agents.base import BaseAgent
from electorn.analysis.codebase_analyzer import CodebaseAnalyzer, CodebaseSummary
from electorn.execution.environment import EnvironmentDetector
from electorn.orchestration.team import MultiAgentTeam
from electorn.runtime.model_selector import ModelProfile, ModelSelector
from electorn.runtime.ollama_client import OllamaClient, OllamaModelInfo
from electorn.runtime.web_search import SearchResult, WebSearchEngine
from electorn.storage.config import Config, load_config, save_config
from electorn.storage.project_memory import ProjectMemory
from electorn.verification.quality_report import ExecutedCheck, QualityReport
from electorn.workspace.checkpoints import CheckpointManager
from electorn.workspace.file_manager import FileOperationResult
from electorn.workspace.project_state import ProjectState


# Force UTF-8 on Windows terminals to support emojis and rich unicode formatting
if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


class DefaultGroup(TyperGroup):
    """Custom TyperGroup that routes bare prompts directly to the 'run' command."""

    def resolve_command(self, ctx, args):
        if args and args[0] not in self.commands and not args[0].startswith("-"):
            args = ["run"] + args
        return super().resolve_command(ctx, args)


app = typer.Typer(
    cls=DefaultGroup,
    name="electorn",
    help="Electorn AI - One CLI. A Complete AI Development Team powered by Ollama.",
    add_completion=False,
    invoke_without_command=True,
)
console = Console(legacy_windows=False)


from electorn.audio import play_intro_audio

# Audio intro flag to only play once per session
_INTRO_PLAYED = False


def print_banner() -> None:
    """Print the Electorn AI header banner and play theme intro."""
    global _INTRO_PLAYED
    if not _INTRO_PLAYED:
        _INTRO_PLAYED = True
        play_intro_audio(duration=6.0, async_mode=True)

    title = Text()
    title.append("⚡ ELECTORN AI", style="bold cyan")
    title.append(" — ", style="dim")
    title.append("One CLI. A Complete AI Development Team.\n", style="bold white")
    title.append(f"v{__version__} | Powered by Ollama Local AI Engine\n", style="dim cyan")
    title.append("Part of HS AI Solutions: https://hs-ai-studio.onrender.com/", style="dim magenta")
    console.print(Panel(title, border_style="cyan", padding=(1, 2)))


@app.callback(invoke_without_command=True)
def default_callback(ctx: typer.Context) -> None:
    """Callback triggered when electorn is invoked with no command."""
    if ctx.invoked_subcommand is None:
        print_banner()

        # Non-interactive / headless environment check (e.g., CI or pipe)
        if not sys.stdin.is_atty() if hasattr(sys.stdin, "is_atty") else False:
            console.print(
                "Usage: [bold cyan]electorn \"Build a complete job recommendation platform\"[/bold cyan]\n"
                "   or: [bold cyan]electorn chat[/bold cyan]\n"
                "   or: [bold cyan]electorn run \"<prompt>\"[/bold cyan]\n\n"
                "Available commands: [bold]run[/bold], [bold]chat[/bold], [bold]models[/bold], [bold]doctor[/bold], [bold]init[/bold], [bold]studio[/bold]\n"
                "Run [bold]electorn --help[/bold] to see all available commands and flags.\n"
            )
            return

        console.print("[bold cyan]Choose your development mode:[/bold cyan]\n")
        console.print("  [bold green]1.[/bold green] 🚀 [bold white]Autonomous App Creator[/bold white] — Build a full application, generate files, run tests & self-repair")
        console.print("  [bold magenta]2.[/bold magenta] 💬 [bold white]Futuristic AI Chat Studio[/bold white] — Interactive multi-agent terminal with code streaming, memory & file inspector")
        console.print("  [bold yellow]3.[/bold yellow] 🩺 [bold white]System Doctor[/bold white] — Audit developer runtimes, Ollama engine & models")
        console.print("  [bold blue]4.[/bold blue] 🌐 [bold white]HS AI Solutions Studio[/bold white] — Explore the product suite (Pendulum, Lumina, Ledger, HS CODE)")
        console.print("  [bold red]0.[/bold red] ❌ [bold white]Exit[/bold white]\n")

        choice = Prompt.ask(
            "[bold cyan]Select an option[/bold cyan]",
            choices=["1", "2", "3", "4", "0"],
            default="1",
        )

        if choice == "1":
            user_prompt = Prompt.ask("\n[bold green]Enter your application description or goal[/bold green]")
            if user_prompt.strip():
                run_development_pipeline(prompt=user_prompt.strip(), workspace=Path("."))
        elif choice == "2":
            chat_command()
        elif choice == "3":
            doctor_command()
        elif choice == "4":
            studio_command()
        else:
            console.print("\n[yellow]Exiting Electorn AI. Goodbye![/yellow]")


@app.command(name="run", help="Build a full application from a prompt description.")
def run_command(
    prompt: str = typer.Argument(
        ...,
        help="Description of application or feature to develop",
    ),
    workspace: Path = typer.Option(
        Path("."),
        "--workspace",
        "-w",
        help="Target workspace directory for generated code",
    ),
    model: Optional[str] = typer.Option(
        None,
        "--model",
        "-m",
        help="Ollama model name",
    ),
    auto_approve: bool = typer.Option(
        True,
        "--yes",
        "-y",
        help="Auto-approve routine development operations",
    ),
    preview: bool = typer.Option(
        False,
        "--preview",
        "-p",
        help="Launch background dev server and detect active localhost port upon completion",
    ),
    mock: bool = typer.Option(
        False,
        "--mock",
        hidden=True,
        help="Mock mode for automated test suites",
    ),
) -> None:
    """Explicit run command: electorn run '...'."""
    run_development_pipeline(
        prompt=prompt,
        workspace=workspace,
        model=model,
        auto_approve=auto_approve,
        preview=preview,
        mock=mock,
    )


def run_development_pipeline(
    prompt: str,
    workspace: Path,
    model: Optional[str] = None,
    auto_approve: bool = True,
    preview: bool = False,
    mock: bool = False,
) -> None:
    """Core development pipeline execution loop with Rich terminal UI."""
    print_banner()

    cfg = load_config(workspace)
    client = OllamaClient(
        base_url=cfg.runtime.ollama_base_url,
        timeout=cfg.runtime.timeout_seconds,
        mock_mode=mock,
    )

    # Pre-flight check
    if not mock and not client.is_available():
        console.print(
            Panel(
                f"[bold red]❌ Cannot connect to Ollama at {client.base_url}[/bold red]\n\n"
                "Please make sure the Ollama service is running on your machine:\n"
                "  1. Start Ollama: [bold green]ollama serve[/bold green]\n"
                "  2. Pull a model: [bold green]ollama pull llama3.2[/bold green] (or qwen2.5-coder:7b)\n"
                "  3. Retry your electorn command.",
                border_style="red",
            )
        )
        sys.exit(1)

    # Live File Operation Callback
    def on_file_op(op: FileOperationResult) -> None:
        if op.action == "created":
            console.print(f"    📄 [bold green][FILE CREATED][/bold green] [cyan]{op.path}[/cyan] ({op.bytes_written} bytes)")
        elif op.action == "modified":
            diff_hint = f" [dim](+ modified content)[/dim]" if op.diff else ""
            console.print(f"    ✏️  [bold yellow][FILE EDITING][/bold yellow] [cyan]{op.path}[/cyan]{diff_hint}")
        elif op.action == "deleted":
            console.print(f"    🗑️  [bold red][FILE DELETED][/bold red] [cyan]{op.path}[/cyan]")

    try:
        team = MultiAgentTeam(
            workspace_dir=workspace,
            config=cfg,
            model_name=model,
            auto_approve=auto_approve,
            mock_mode=mock,
            on_file_op=on_file_op,
        )
    except Exception as err:
        console.print(f"[bold red]Initialization Error:[/bold red] {err}")
        sys.exit(1)

    profile = team.model_profile

    # Workspace & Agent Status Panel
    status_content = (
        f"[bold white]🎯 Prompt:[/bold white] \"{prompt}\"\n"
        f"[bold white]📁 Live Workspace:[/bold white] [bold green]{team.workspace_dir}[/bold green]\n"
        f"[bold white]🤖 Active AI Engine:[/bold white] [bold cyan]{profile.name}[/bold cyan] ({profile.description})\n"
        f"[bold white]⚡ Sequential Execution:[/bold white] [green]Active[/green] (Memory-Optimized 2-4GB RAM)\n"
        f"[bold white]🏢 Solution Studio:[/bold white] [dim]https://hs-ai-studio.onrender.com/[/dim]"
    )
    console.print(
        Panel(
            status_content,
            title="[bold cyan]⚡ ELECTORN LIVE WORKSPACE STATUS[/bold cyan]",
            border_style="cyan",
            padding=(1, 2),
        )
    )
    console.print("")

    try:
        build_res = team.build_application(
            prompt=prompt,
            install_deps=True,
            launch_preview=preview,
        )

        console.print("\n✨ [bold green]Autonomous Application Build Finished![/bold green]\n")

        # Summary Tree
        tree = Tree(f"📦 [bold cyan]{build_res.project_name}[/bold cyan]")
        for f in team.file_manager.list_files():
            tree.add(f"[green]{f}[/green]")
        console.print(tree)
        console.print("")

        summary_table = Table(title="🚀 Application Quickstart", border_style="cyan")
        summary_table.add_column("Property", style="bold white")
        summary_table.add_column("Details", style="cyan")
        summary_table.add_row("Run Command", build_res.start_command or "python -m uvicorn ...")
        summary_table.add_row("Test Command", build_res.test_command or "pytest")
        summary_table.add_row("Dependencies", build_res.dependencies_message)
        summary_table.add_row("Status", build_res.final_status)
        if build_res.preview_url:
            summary_table.add_row("Preview URL", build_res.preview_url)
        console.print(summary_table)

        console.print(f"\n[dim]Session audit saved to: {team.workspace_dir}/.electorn/sessions/{team.session_id}.json[/dim]\n")

    except KeyboardInterrupt:
        console.print("\n[yellow]Operation aborted by user.[/yellow]")
        sys.exit(130)
    except Exception as err:
        console.print(f"\n[bold red]Pipeline failed with error:[/bold red] {err}")
        sys.exit(1)


@app.command(name="preview", help="Launch background dev server for the workspace application.")
def preview_command(
    workspace: Path = typer.Option(
        Path("."),
        "--workspace",
        "-w",
        help="Workspace directory",
    ),
    cmd: Optional[str] = typer.Option(
        None,
        "--command",
        "-c",
        help="Custom server command (auto-detected if omitted)",
    ),
) -> None:
    """Launch application preview server and report active port."""
    print_banner()
    cfg = load_config(workspace)
    team = MultiAgentTeam(workspace_dir=workspace, config=cfg, auto_approve=True)

    server_cmd = cmd
    if not server_cmd:
        # Check project memory or package.json/main.py
        mem_cmds = team.project_memory.data.build_commands
        if "run" in mem_cmds and mem_cmds["run"]:
            server_cmd = mem_cmds["run"]
        elif (team.workspace_dir / "package.json").exists():
            server_cmd = "npm run dev"
        elif (team.workspace_dir / "main.py").exists():
            server_cmd = "python main.py"
        elif (team.workspace_dir / "app.py").exists():
            server_cmd = "python app.py"
        else:
            server_cmd = "python -m http.server 8000"

    console.print(f"🚀 [bold green]Starting background dev server:[/bold green] [cyan]{server_cmd}[/cyan]...")
    proc_info = team.powershell.start_background_server(server_cmd, name=team.workspace_dir.name)
    if proc_info.port:
        console.print(f"✨ [bold green]Server live at:[/bold green] [underline cyan]http://localhost:{proc_info.port}[/underline cyan] (PID: {proc_info.pid})")
    else:
        console.print(f"✨ [bold green]Server process running[/bold green] (PID: {proc_info.pid})")
    console.print(f"[dim]To terminate background processes, run: [bold]electorn stop[/bold][/dim]\n")


@app.command(name="stop", help="Stop background servers started by Electorn in this workspace.")
def stop_command(
    workspace: Path = typer.Option(
        Path("."),
        "--workspace",
        "-w",
        help="Workspace directory",
    ),
) -> None:
    """Stop all background servers started in workspace."""
    print_banner()
    cfg = load_config(workspace)
    team = MultiAgentTeam(workspace_dir=workspace, config=cfg, auto_approve=True)

    stopped = team.powershell.stop_all_processes()
    if stopped:
        console.print(f"✔ [bold green]Stopped {len(stopped)} background process(es):[/bold green] {', '.join(map(str, stopped))}\n")
    else:
        console.print("[dim]No active background Electorn processes found in this workspace.[/dim]\n")



@app.command(name="models", help="List installed Ollama models and check compatibility.")
def models_command(
    url: str = typer.Option(
        "http://localhost:11434",
        "--url",
        "-u",
        help="Ollama base URL",
    ),
) -> None:
    """List locally installed Ollama models with parameter sizes and tiers."""
    print_banner()
    client = OllamaClient(base_url=url)

    if not client.is_available():
        console.print(f"[bold red]❌ Cannot connect to Ollama at {url}[/bold red]")
        sys.exit(1)

    selector = ModelSelector(client)
    models = client.list_models()

    if not models:
        console.print("[yellow]No models found in Ollama. Pull one with: [bold]ollama pull llama3.2[/bold][/yellow]")
        return

    table = Table(title="Installed Ollama Models", border_style="cyan")
    table.add_column("Model Name", style="bold cyan")
    table.add_column("Tier", style="white")
    table.add_column("Params", style="yellow")
    table.add_column("Size", style="green")
    table.add_column("Coding Tuned", style="magenta")

    best = selector.select_best_model()

    for m in models:
        prof = selector.profile_model(m)
        is_best_mark = " ⭐ [bold green](Recommended)[/bold green]" if prof.name == best.name else ""
        table.add_row(
            f"{m.name}{is_best_mark}",
            prof.tier.capitalize(),
            f"~{prof.parameter_approx:g}B",
            f"{m.size_bytes / (1024**3):.2f} GB",
            "Yes" if prof.is_code_specialized else "General",
        )

    console.print(table)
    console.print("")


@app.command(name="doctor", help="Inspect local development environment, Ollama, and runtimes.")
def doctor_command() -> None:
    """Run full environment diagnostic check."""
    print_banner()
    detector = EnvironmentDetector()
    env = detector.detect()
    client = OllamaClient()
    ollama_ok = client.is_available()

    table = Table(title="System & Developer Environment Audit", border_style="cyan")
    table.add_column("Component", style="bold white")
    table.add_column("Status", style="bold")
    table.add_column("Details", style="dim")

    table.add_row("Operating System", "[green]✔ OK[/green]", f"{env.os_system} {env.os_release} ({env.architecture})")
    table.add_row("Python", "[green]✔ OK[/green]", env.python_version)
    table.add_row(
        "Ollama Engine",
        "[green]✔ Connected[/green]" if ollama_ok else "[red]✖ Offline[/red]",
        client.base_url if ollama_ok else "Run 'ollama serve' to start",
    )
    table.add_row(
        "Git",
        "[green]✔ Available[/green]" if env.has_git else "[yellow]✖ Missing[/yellow]",
        "Version control",
    )
    table.add_row(
        "Node.js",
        f"[green]✔ {env.node_version}[/green]" if env.has_node else "[dim]Not installed[/dim]",
        "Frontend JavaScript runtime",
    )
    table.add_row(
        "PowerShell Engine",
        f"[green]✔ Available ({env.powershell_version or 'Windows PowerShell'})[/green]" if env.has_powershell else "[yellow]✖ Missing[/yellow]",
        "Windows automation & script execution engine",
    )
    table.add_row(
        "Docker",
        "[green]✔ Available[/green]" if env.has_docker else "[dim]Not installed[/dim]",
        "Container runtime",
    )

    console.print(table)
    console.print("")


@app.command(name="init", help="Create a project-level .electorn.yaml configuration.")
def init_command(
    workspace: Path = typer.Option(
        Path("."),
        "--workspace",
        "-w",
        help="Directory to initialize",
    ),
) -> None:
    """Generate default .electorn.yaml file."""
    config_file = workspace / ".electorn.yaml"
    if config_file.exists():
        console.print(f"[yellow]Configuration already exists at {config_file}[/yellow]")
        return

    cfg = Config()
    save_config(cfg, config_file)
    console.print(f"[green]✔ Created Electorn configuration at:[/green] [bold]{config_file}[/bold]")


@app.command(name="studio", help="Explore the HS AI Solutions ecosystem & live products.")
def studio_command() -> None:
    """Display HS AI Solutions product portfolio and live links."""
    print_banner()

    table = Table(title="🌐 HS AI Solutions Ecosystem (https://hs-ai-studio.onrender.com/)", border_style="cyan")
    table.add_column("Product", style="bold cyan")
    table.add_column("Category", style="yellow")
    table.add_column("Description", style="white")
    table.add_column("Live URL / Status", style="green")

    table.add_row(
        "⚡ Electorn AI",
        "Autonomous Dev Team",
        "One CLI. A Complete AI Development Team powered by Ollama.",
        "Local CLI (Active)",
    )
    table.add_row(
        "🛡️ Pendulum",
        "AI Browser & Privacy",
        "Automated private desktop browser with stealth web workflows.",
        "https://hs-ai-studio.onrender.com/products/pendulum",
    )
    table.add_row(
        "🎨 Lumina",
        "AI Creation",
        "Intelligent AI presentation planner, slide architecture & designer.",
        "https://lumina-pghe.onrender.com/",
    )
    table.add_row(
        "🤖 HSBot",
        "Multi-Model Workspace",
        "Multi-model AI assistant bringing multiple models into one chat.",
        "https://hs-chatbot-3.onrender.com/",
    )
    table.add_row(
        "📜 Ledger",
        "AI Digital Identity",
        "Connects credentials, projects, and skills into career intelligence.",
        "https://ledger-2-er3t.onrender.com/",
    )
    table.add_row(
        "⛨ Phishing Defence",
        "AI Threat Operations",
        "Analyzes suspicious URLs, emails, and links before you interact.",
        "https://forensic-ai-1-mma4.onrender.com/",
    )
    table.add_row(
        "💻 HS CODE",
        "Desktop AI Companion",
        "Lightweight native Windows desktop AI coding companion.",
        "https://hs-ai-studio.onrender.com/products/hs-code",
    )
    table.add_row(
        "🎓 Academia AI",
        "Learning Operating System",
        "Turns syllabi and notes into roadmaps, live tutors, and quizzes.",
        "https://acdemia01-2.onrender.com/",
    )

    console.print(table)
    console.print(
        "\n✨ [bold cyan]HS AI Solutions Studio:[/bold cyan] [underline magenta]https://hs-ai-studio.onrender.com/[/underline magenta]\n"
        "Built by [bold white]Harshan Seliyan[/bold white] | [dim]harshanseliyan28@gmail.com[/dim]\n"
    )


@app.command(name="build", help="Build a complete application from a natural language prompt.")
def build_command(
    prompt: str = typer.Argument(
        ...,
        help="Description of application or feature to develop",
    ),
    workspace: Path = typer.Option(
        Path("."),
        "--workspace",
        "-w",
        help="Target workspace directory for generated code",
    ),
    model: Optional[str] = typer.Option(
        None,
        "--model",
        "-m",
        help="Target AI model name",
    ),
    auto_approve: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Auto-approve file creation and executions",
    ),
    mock: bool = typer.Option(
        False,
        "--mock",
        hidden=True,
        help="Mock mode for automated test suites",
    ),
) -> None:
    """Build application from natural language prompt."""
    run_development_pipeline(
        prompt=prompt,
        workspace=workspace,
        model=model,
        auto_approve=auto_approve,
        mock=mock,
    )


@app.command(name="analyze", help="Inspect and analyze existing project structure, dependencies, and security.")
def analyze_command(
    path: Path = typer.Argument(
        Path("."),
        help="Target project directory to analyze",
    ),
) -> None:
    """Multi-file codebase intelligence and security analysis."""
    print_banner()
    analyzer = CodebaseAnalyzer(path)
    summary = analyzer.analyze()

    table = Table(title=f"📊 Codebase Intelligence: {summary.root_dir}", border_style="cyan")
    table.add_column("Metric", style="bold white")
    table.add_column("Details", style="cyan")

    table.add_row("Total Files", str(summary.total_files))
    table.add_row("Total Lines of Code", f"~{summary.total_lines:,}")
    table.add_row("Primary Tech Stack", ", ".join(summary.primary_tech_stack) or "General")
    table.add_row("Languages", ", ".join(f"{k} ({v})" for k, v in summary.languages.items()) or "None detected")
    table.add_row("Entry Points", ", ".join(summary.entry_points[:4]) or "None detected")
    table.add_row("Configuration Files", ", ".join(summary.configuration_files[:4]) or "None")
    table.add_row("Routes / Endpoints", str(len(summary.route_endpoints)))
    table.add_row("Database Models", str(len(summary.database_models)))
    table.add_row("Test Files", str(len(summary.test_files)))

    console.print(table)
    console.print("")

    if summary.security_findings:
        sec_table = Table(title="⚠️ Security Exposures Detected", border_style="red")
        sec_table.add_column("File", style="yellow")
        sec_table.add_column("Line", style="dim")
        sec_table.add_column("Rule", style="bold red")
        sec_table.add_column("Preview", style="white")
        for finding in summary.security_findings:
            sec_table.add_row(finding.file_path, str(finding.line_number), finding.rule, finding.snippet_preview)
        console.print(sec_table)
        console.print("")
    else:
        console.print("[bold green]✔ Security Hygiene: No exposed API keys or credentials detected.[/bold green]\n")


@app.command(name="explain", help="Explain architecture, entry points, and workflows of a project or file.")
def explain_command(
    path: Path = typer.Argument(
        Path("."),
        help="Target directory or file to explain",
    ),
) -> None:
    """Analyze and explain project architecture."""
    print_banner()
    if path.is_file():
        text = path.read_text(encoding="utf-8", errors="replace")
        console.print(Panel(text[:2000], title=f"📄 {path.name}", border_style="cyan"))
        console.print(f"[bold cyan]File Summary:[/bold cyan] {len(text.splitlines())} lines | {len(text)} bytes\n")
        return

    analyzer = CodebaseAnalyzer(path)
    summary = analyzer.analyze()
    console.print(f"🏛️ [bold cyan]Architecture Overview for {path.resolve().name}:[/bold cyan]")
    console.print(f"• [bold white]Tech Stack:[/bold white] {', '.join(summary.primary_tech_stack) or 'Multi-language'}")
    console.print(f"• [bold white]Entry Points:[/bold white] {', '.join(summary.entry_points) or 'Not detected'}")
    console.print(f"• [bold white]Key Routes:[/bold white] {', '.join(summary.route_endpoints[:5]) or 'No routes found'}")
    console.print(f"• [bold white]Data Models:[/bold white] {', '.join(summary.database_models[:5]) or 'No ORM models found'}")
    console.print(f"• [bold white]Test Coverage:[/bold white] {len(summary.test_files)} test files discovered\n")


@app.command(name="fix", help="Detect syntax errors and test failures, and autonomously repair them.")
def fix_command(
    workspace: Path = typer.Option(
        Path("."),
        "--workspace",
        "-w",
        help="Workspace directory to repair",
    ),
) -> None:
    """Autonomous self-repair of syntax errors and failing tests."""
    print_banner()
    cfg = load_config(workspace)
    team = MultiAgentTeam(workspace_dir=workspace, config=cfg, auto_approve=True)

    console.print(f"🔍 [bold cyan]Auditing workspace for errors:[/bold cyan] {team.workspace_dir}\n")
    # 1. Syntax check
    files = team.file_manager.list_files()
    syntax_results = team.syntax_checker.check_all_files(files)
    bad_syntax = [r.file_path for r in syntax_results if not r.is_valid]

    if bad_syntax:
        console.print(f"⚠️ [yellow]Found {len(bad_syntax)} syntax errors in: {', '.join(bad_syntax)}[/yellow]")
        console.print("🔧 Initiating self-repair on syntax...")
        team.repair_engine.repair_syntax(
            repair_agent=team.backend,
            state=ProjectState(prompt="repair"),
            failing_files=bad_syntax,
            status_cb=lambda msg: console.print(f"  {msg}"),
        )
    else:
        console.print("✔ [green]All workspace files passed syntax verification.[/green]")

    # 2. Test runner
    console.print("\n🧪 [bold cyan]Running automated test discovery...[/bold cyan]")
    test_res = team.test_runner.run_tests("pytest")
    if not test_res.passed:
        console.print("⚠️ [yellow]Tests failed. Running test repair loop...[/yellow]")
        success = team.repair_engine.repair_test_failures(
            repair_agent=team.backend,
            state=ProjectState(prompt="repair"),
            test_result=test_res,
            status_cb=lambda msg: console.print(f"  {msg}"),
        )
        if success:
            console.print("✨ [bold green]Self-repair succeeded! All tests passing.[/bold green]\n")
        else:
            console.print("❌ [bold red]Self-repair could not resolve all test failures. Check diff or rollback.[/bold red]\n")
    else:
        console.print("✔ [bold green]All automated tests passed successfully![/bold green]\n")


@app.command(name="test", help="Run comprehensive quality verification checks and test suites.")
def test_command(
    workspace: Path = typer.Option(
        Path("."),
        "--workspace",
        "-w",
        help="Workspace directory to verify",
    ),
    cmd: Optional[str] = typer.Option(
        None,
        "--command",
        "-c",
        help="Custom test command (defaults to pytest)",
    ),
) -> None:
    """Run full quality verification suite and generate honest quality report."""
    print_banner()
    cfg = load_config(workspace)
    team = MultiAgentTeam(workspace_dir=workspace, config=cfg, auto_approve=True)

    report = QualityReport(project_name=team.workspace_dir.name)

    # 1. Syntax check
    files = team.file_manager.list_files()
    syntax_results = team.syntax_checker.check_all_files(files)
    for r in syntax_results:
        if not r.is_valid:
            report.syntax_errors.append(f"{r.file_path}: {r.error_message}")

    # 2. Test run
    test_cmd = cmd or "pytest"
    test_res = team.test_runner.run_tests(test_cmd)
    report.executed_checks.append(
        ExecutedCheck(
            name="Automated Test Suite",
            command_or_action=test_cmd,
            exit_code=0 if test_res.passed else 1,
            output_snippet=test_res.raw_output.strip()[-100:] if test_res.raw_output else "No output",
            passed=test_res.passed,
        )
    )
    report.tests_passed = test_res.passed_tests
    report.tests_failed = test_res.failed_tests

    # 3. Security scan
    analyzer = CodebaseAnalyzer(workspace)
    summary = analyzer.analyze()
    for s in summary.security_findings:
        report.security_warnings.append(f"{s.file_path}:{s.line_number} - {s.rule}")

    console.print(report.format_terminal_table())
    console.print(f"\nFinal Quality Status: [bold]{report.final_status}[/bold]\n")


@app.command(name="refactor", help="Refactor codebase components for clean architecture and best practices.")
def refactor_command(
    file_path: str = typer.Argument(
        ...,
        help="Relative path of file to refactor",
    ),
    instruction: str = typer.Option(
        "Refactor to improve code quality, type annotations, and modular design",
        "--instruction",
        "-i",
        help="Refactoring instructions",
    ),
    workspace: Path = typer.Option(
        Path("."),
        "--workspace",
        "-w",
        help="Workspace directory",
    ),
) -> None:
    """Targeted refactoring assistant."""
    print_banner()
    cfg = load_config(workspace)
    team = MultiAgentTeam(workspace_dir=workspace, config=cfg, auto_approve=True)

    # Pre-refactor checkpoint
    cid = team.checkpoints.create_checkpoint(f"Pre-refactor snapshot of {file_path}")
    console.print(f"💾 Created pre-refactor checkpoint: [dim]{cid}[/dim]")

    try:
        content = team.file_manager.read_file(file_path)
    except Exception as e:
        console.print(f"[bold red]Cannot read target file:[/bold red] {e}")
        return

    prompt = f"""
Refactor the file '{file_path}' according to this instruction:
{instruction}

Current content:
```
{content}
```

Return ONLY the complete refactored source code.
Format as:
FILE: {file_path}
```
// Refactored code
```
"""
    with console.status("[cyan]Refactoring component...[/cyan]", spinner="dots"):
        resp = team.backend.ask(prompt)
        extracted = BaseAgent.extract_files_from_text(resp.content)

    if file_path in extracted:
        team.file_manager.write_file(file_path, extracted[file_path])
        console.print(f"✔ [bold green]Refactored and updated:[/bold green] {file_path}")
    else:
        code_blocks = BaseAgent.extract_code_blocks(resp.content)
        if code_blocks:
            team.file_manager.write_file(file_path, code_blocks[0][1])
            console.print(f"✔ [bold green]Refactored and updated:[/bold green] {file_path}")
        else:
            console.print("[yellow]Could not extract clean refactored code block.[/yellow]")
    console.print("")


@app.command(name="docs", help="Generate or update architecture documentation and README.")
def docs_command(
    workspace: Path = typer.Option(
        Path("."),
        "--workspace",
        "-w",
        help="Target workspace directory",
    ),
) -> None:
    """Autonomous documentation generator."""
    print_banner()
    cfg = load_config(workspace)
    team = MultiAgentTeam(workspace_dir=workspace, config=cfg, auto_approve=True)

    analyzer = CodebaseAnalyzer(workspace)
    summary = analyzer.analyze()

    prompt = f"""
Generate comprehensive, production-ready README.md documentation for this project:
- Root directory: {summary.root_dir}
- Total files: {summary.total_files}
- Tech Stack: {', '.join(summary.primary_tech_stack)}
- Entry Points: {', '.join(summary.entry_points)}
- Endpoints: {', '.join(summary.route_endpoints[:10])}
- Models: {', '.join(summary.database_models[:10])}

Include:
1. Project title & high-level architecture overview
2. Tech stack & prerequisites
3. Installation & setup steps
4. Execution & API endpoints overview
5. Testing guidelines

Format output strictly as:
FILE: README.md
```markdown
# Content
```
"""
    with console.status("[cyan]Generating project documentation...[/cyan]", spinner="dots"):
        resp = team.devops.ask(prompt)
        files = BaseAgent.extract_files_from_text(resp.content)

    if "README.md" in files:
        team.file_manager.write_file("README.md", files["README.md"])
        console.print("✔ [bold green]Saved README.md documentation successfully![/bold green]\n")
    else:
        console.print("[yellow]Could not extract formatted documentation.[/yellow]\n")


@app.command(name="diff", help="Show differences between current workspace and recorded checkpoints.")
def diff_command(
    checkpoint: Optional[str] = typer.Option(
        None,
        "--checkpoint",
        "-c",
        help="Specific checkpoint ID (defaults to latest)",
    ),
    workspace: Path = typer.Option(
        Path("."),
        "--workspace",
        "-w",
        help="Target workspace directory",
    ),
) -> None:
    """Show unified diff from latest or specified checkpoint."""
    print_banner()
    cfg = load_config(workspace)
    team = MultiAgentTeam(workspace_dir=workspace, config=cfg, auto_approve=True)

    diff_str = team.checkpoints.diff(checkpoint)
    console.print(Panel(diff_str, title="🔍 Unified Checkpoint Diff", border_style="cyan"))
    console.print("")


@app.command(name="checkpoint", help="Create a recoverable snapshot of the current workspace.")
def checkpoint_command(
    message: str = typer.Argument(
        "Manual snapshot",
        help="Description message for this checkpoint",
    ),
    workspace: Path = typer.Option(
        Path("."),
        "--workspace",
        "-w",
        help="Target workspace directory",
    ),
) -> None:
    """Create safe checkpoint snapshot."""
    print_banner()
    cfg = load_config(workspace)
    team = MultiAgentTeam(workspace_dir=workspace, config=cfg, auto_approve=True)

    cid = team.checkpoints.create_checkpoint(message)
    console.print(f"✔ [bold green]Created snapshot checkpoint:[/bold green] [bold cyan]{cid}[/bold cyan]")
    console.print(f"  [dim]Message: '{message}' in {team.workspace_dir}/.electorn/checkpoints/{cid}[/dim]\n")


@app.command(name="rollback", help="Restore workspace to a previous checkpoint snapshot.")
def rollback_command(
    checkpoint: Optional[str] = typer.Argument(
        None,
        help="Checkpoint ID to restore (defaults to latest)",
    ),
    workspace: Path = typer.Option(
        Path("."),
        "--workspace",
        "-w",
        help="Target workspace directory",
    ),
) -> None:
    """Restore workspace files from checkpoint."""
    print_banner()
    cfg = load_config(workspace)
    team = MultiAgentTeam(workspace_dir=workspace, config=cfg, auto_approve=True)

    success = team.checkpoints.rollback(checkpoint)
    if success:
        console.print(f"✔ [bold green]Successfully rolled back workspace to checkpoint: {checkpoint or 'latest'}[/bold green]\n")
    else:
        console.print(f"❌ [bold red]Rollback failed. Checkpoint '{checkpoint}' not found or no checkpoints exist.[/bold red]\n")


@app.command(name="status", help="Display workspace status, engineering memory, and active checkpoints.")
def status_command(
    workspace: Path = typer.Option(
        Path("."),
        "--workspace",
        "-w",
        help="Target workspace directory",
    ),
) -> None:
    """Show workspace status, engineering memory, and checkpoints."""
    print_banner()
    cfg = load_config(workspace)
    team = MultiAgentTeam(workspace_dir=workspace, config=cfg, auto_approve=True)

    checkpoints = team.checkpoints.list_checkpoints()
    mem = team.project_memory.data

    table = Table(title=f"📌 Workspace Status: {team.workspace_dir.name}", border_style="cyan")
    table.add_column("Property", style="bold white")
    table.add_column("Details", style="cyan")

    table.add_row("Operating Mode", cfg.runtime.mode.upper())
    table.add_row("Active AI Model", team.model_profile.name)
    table.add_row("Files in Workspace", str(len(team.file_manager.list_files())))
    table.add_row("Recorded Checkpoints", str(len(checkpoints)))
    if checkpoints:
        table.add_row("Latest Checkpoint", f"{checkpoints[0].id} ({checkpoints[0].iso_time})")
    table.add_row("Project Purpose", mem.project_purpose or "(Not set)")
    table.add_row("Tech Stack", ", ".join(f"{k}: {v}" for k, v in mem.tech_stack.items()) or "(Empty)")
    table.add_row("Decisions Recorded", str(len(mem.architectural_decisions)))
    table.add_row("Completed Tasks", str(len(mem.completed_tasks)))

    console.print(table)
    console.print("")


@app.command(name="mode", help="Inspect or switch operating mode: 'local', 'cloud', or 'auto'.")
def mode_command(
    mode_name: Optional[str] = typer.Argument(
        None,
        help="Target operating mode ('local', 'cloud', 'auto')",
    ),
    workspace: Path = typer.Option(
        Path("."),
        "--workspace",
        "-w",
        help="Workspace directory",
    ),
) -> None:
    """Inspect or configure operating mode."""
    print_banner()
    cfg = load_config(workspace)

    if not mode_name:
        console.print(f"Active Operating Mode: [bold cyan]{cfg.runtime.mode.upper()}[/bold cyan]")
        console.print("[dim]Options: [bold]electorn mode local[/bold] | [bold]electorn mode cloud[/bold] | [bold]electorn mode auto[/bold][/dim]\n")
        return

    clean_mode = mode_name.lower().strip()
    if clean_mode not in ("local", "cloud", "auto"):
        console.print(f"[bold red]Invalid mode '{mode_name}'.[/bold red] Choose from: local, cloud, auto.\n")
        return

    cfg.runtime.mode = clean_mode
    config_file = workspace / ".electorn.yaml"
    save_config(cfg, config_file)
    console.print(f"✔ [bold green]Operating mode set to:[/bold green] [bold cyan]{clean_mode.upper()}[/bold cyan]")
    console.print(f"  [dim]Saved to {config_file}[/dim]\n")


@app.command(name="config", help="View or modify Electorn configuration.")
def config_command(
    workspace: Path = typer.Option(
        Path("."),
        "--workspace",
        "-w",
        help="Target workspace directory",
    ),
) -> None:
    """Display project configuration."""
    print_banner()
    cfg = load_config(workspace)

    table = Table(title="⚙️ Electorn Configuration", border_style="cyan")
    table.add_column("Setting", style="bold white")
    table.add_column("Value", style="cyan")

    table.add_row("Operating Mode", cfg.runtime.mode)
    table.add_row("Ollama Base URL", cfg.runtime.ollama_base_url)
    table.add_row("Target Model", cfg.runtime.model or "Auto-selected")
    table.add_row("Fallback Model", cfg.runtime.fallback_model or "None")
    table.add_row("Timeout Seconds", str(cfg.runtime.timeout_seconds))
    table.add_row("Context Tokens", str(cfg.runtime.context_tokens))
    table.add_row("Max Repair Attempts", str(cfg.orchestration.max_repair_attempts))
    table.add_row("Sequential Execution", str(cfg.orchestration.sequential_execution))

    console.print(table)
    console.print("")


@app.command(name="version", help="Show Electorn version and runtime info.")
def version_command() -> None:
    """Print Electorn version."""
    console.print(f"[bold cyan]Electorn AI[/bold cyan] [bold green]v{__version__}[/bold green] — Autonomous AI Development Team")
    console.print(f"Powered by HS AI Solutions: [underline]https://hs-ai-studio.onrender.com/[/underline]\n")


@app.command(name="chat", help="Launch futuristic multi-agent interactive chat studio.")
def chat_command(
    workspace: Path = typer.Option(
        Path("."),
        "--workspace",
        "-w",
        help="Workspace directory to interact with",
    ),
    model: Optional[str] = typer.Option(
        None,
        "--model",
        "-m",
        help="Target Ollama model name",
    ),
) -> None:
    """Futuristic conversational terminal with specialized AI agents, file inspection & code streaming."""
    # Unwrap OptionInfo if invoked directly from default_callback
    if hasattr(workspace, "default"):
        workspace = getattr(workspace, "default", Path("."))
    if hasattr(model, "default"):
        model = getattr(model, "default", None)
    if not isinstance(workspace, Path):
        workspace = Path(str(workspace) if workspace else ".")

    print_banner()

    cfg = load_config(workspace)
    client = OllamaClient(
        base_url=cfg.runtime.ollama_base_url,
        timeout=cfg.runtime.timeout_seconds,
    )

    if not client.is_available():
        console.print(f"[bold red]❌ Cannot connect to Ollama at {client.base_url}[/bold red]")
        sys.exit(1)

    team = MultiAgentTeam(
        workspace_dir=workspace,
        config=cfg,
        model_name=model,
        auto_approve=True,
    )
    profile = team.model_profile
    selector = ModelSelector(client)
    web_searcher = WebSearchEngine()

    # Agent registry for dynamic switching
    agent_map = {
        "architect": (team.architect, "🧠", "System Architecture & File Blueprints"),
        "backend": (team.backend, "⚙️", "Server, API & Business Logic"),
        "frontend": (team.frontend, "🎨", "UI, Client Templates & Styling"),
        "database": (team.database, "🗄️", "Data Models & SQL Persistence"),
        "qa": (team.qa_tester, "🧪", "Automated Tests & Quality Assurance"),
        "devops": (team.devops, "📦", "Environments, Docker & Deployment"),
    }
    current_agent_key = "architect"
    current_agent, current_icon, current_desc = agent_map[current_agent_key]

    def display_help() -> None:
        table = Table(title="⚡ Electorn Studio Commands & Futuristic Shortcuts", border_style="cyan")
        table.add_column("Command", style="bold yellow")
        table.add_column("Description", style="white")
        table.add_row("/search <query>", "🌐 Run autonomous live web search without API keys")
        table.add_row("/web <prompt>", "🌐 Search web & synthesize answer with live citations")
        table.add_row("/agent <name>", "🔄 Switch active persona (architect, backend, frontend, database, qa, devops)")
        table.add_row("/model [name]", "⚡ Inspect installed Ollama models or switch active model")
        table.add_row("/files", "📁 Inspect workspace file hierarchy tree")
        table.add_row("/read <file>", "📄 View workspace file contents")
        table.add_row("/build <prompt>", "🚀 Trigger full autonomous multi-agent development pipeline")
        table.add_row("/clear", "🧹 Clear conversation memory buffer")
        table.add_row("/help", "❓ Show this command reference table")
        table.add_row("/exit", "🚪 Exit studio session")
        console.print(table)
        console.print("")

    chat_banner = (
        f"🌌 [bold cyan]ELECTORN FUTURISTIC AI STUDIO[/bold cyan]\n"
        f"Active Neural Engine: [bold green]{profile.name}[/bold green] ({profile.description})\n"
        f"Active Persona: {current_icon} [bold yellow]{current_agent.name}[/bold yellow] — {current_desc}\n"
        f"Target Workspace: [bold white]{team.workspace_dir}[/bold white]\n\n"
        f"[dim]Commands: [bold]/search <query>[/bold] | [bold]/web <query>[/bold] | [bold]/agent <name>[/bold] | "
        f"[bold]/model [name][/bold] | [bold]/files[/bold] | [bold]/build <prompt>[/bold] | [bold]/help[/bold] | [bold]/exit[/bold][/dim]"
    )
    console.print(Panel(chat_banner, border_style="magenta", padding=(1, 2)))
    console.print("")

    conversation_history: list[dict[str, str]] = []

    while True:
        try:
            user_input = Prompt.ask(f"[bold cyan]You[/bold cyan] ❯").strip()
            if not user_input:
                continue

            # Slash commands
            if user_input.lower() in ("/exit", "/quit", "exit", "quit"):
                console.print("\n[yellow]Shutting down Electorn Studio. Until next time! 🚀[/yellow]")
                break

            if user_input.lower() in ("/help", "help", "?"):
                display_help()
                continue

            if user_input.lower() == "/clear":
                conversation_history.clear()
                console.print("[dim]Conversation buffer cleared.[/dim]\n")
                continue

            if user_input.lower() == "/files":
                files = team.file_manager.list_files()
                tree = Tree(f"📁 [bold cyan]{team.workspace_dir.name}[/bold cyan] ({len(files)} files)")
                for f in files:
                    tree.add(f"[green]{f}[/green]")
                console.print(tree)
                console.print("")
                continue

            if user_input.lower().startswith("/read "):
                target_file = user_input[6:].strip()
                try:
                    content = team.file_manager.read_file(target_file)
                    console.print(Panel(content, title=f"📄 {target_file}", border_style="green"))
                except Exception as e:
                    console.print(f"[bold red]Error reading file:[/bold red] {e}")
                console.print("")
                continue

            if user_input.lower().startswith("/agent "):
                target_key = user_input[7:].strip().lower()
                if target_key in agent_map:
                    current_agent_key = target_key
                    current_agent, current_icon, current_desc = agent_map[current_agent_key]
                    console.print(f"\n🔄 [bold green]Switched persona to:[/bold green] {current_icon} [bold yellow]{current_agent.name}[/bold yellow] ({current_desc})\n")
                else:
                    console.print(f"[yellow]Unknown agent. Choose from: {', '.join(agent_map.keys())}[/yellow]\n")
                continue

            if user_input.lower().startswith("/model"):
                parts = user_input.split(maxsplit=1)
                if len(parts) == 1:
                    models = client.list_models()
                    console.print(f"\n[cyan]Active Neural Engine:[/cyan] [bold green]{team.model_profile.name}[/bold green]")
                    console.print("[dim]Installed models in Ollama:[/dim]")
                    for m in models:
                        marker = " ⭐ [bold green](Active)[/bold green]" if m.name == team.model_profile.name else ""
                        console.print(f"  • {m.name}{marker}")
                    console.print("[dim]Switch model with: [bold]/model <model_name>[/bold] (e.g. /model llama3.2:1b)[/dim]\n")
                else:
                    new_model = parts[1].strip()
                    new_profile = selector.profile_model(OllamaModelInfo(name=new_model, size_bytes=0))
                    team.model_profile = new_profile
                    for a_tuple in agent_map.values():
                        a_tuple[0].model = new_model
                        a_tuple[0].model_profile = new_profile
                    console.print(f"\n⚡ [bold green]Switched active neural engine to:[/bold green] [bold cyan]{new_model}[/bold cyan] ({new_profile.description})\n")
                continue

            # Live autonomous web search
            if user_input.lower().startswith("/search "):
                search_query = user_input[8:].strip()
                with console.status(f"[cyan]🌐 Searching the web for: \"{search_query}\"...[/cyan]", spinner="dots"):
                    results = web_searcher.search(search_query)
                if not results:
                    console.print(f"[yellow]No web search results found for \"{search_query}\".[/yellow]\n")
                else:
                    console.print(web_searcher.format_table(search_query, results))
                    console.print("")
                continue

            web_context_prompt = ""
            effective_query = user_input

            # Web-augmented prompt (/web <query>)
            if user_input.lower().startswith("/web "):
                effective_query = user_input[5:].strip()
                with console.status(f"[cyan]🌐 Retrieving live web sources for: \"{effective_query}\"...[/cyan]", spinner="dots"):
                    results = web_searcher.search(effective_query, max_results=4)
                if results:
                    console.print(web_searcher.format_table(effective_query, results))
                    web_context_prompt = web_searcher.format_context_prompt(effective_query, results)
                else:
                    console.print(f"[dim]No external web results returned; consulting internal knowledge.[/dim]")

            if user_input.lower().startswith("/build "):
                build_prompt = user_input[7:].strip()
                console.print(f"\n🚀 [bold green]Initiating Autonomous Multi-Agent Development Pipeline for:[/bold green] \"{build_prompt}\"\n")
                run_development_pipeline(prompt=build_prompt, workspace=team.workspace_dir, model=model, auto_approve=True)
                continue

            # Append user question to history
            conversation_history.append({"role": "user", "content": effective_query})
            if len(conversation_history) > 8:
                conversation_history = conversation_history[-8:]

            # Workspace + Agent Context
            workspace_files = team.file_manager.list_files()[:10]
            ws_context = f"Workspace files: {', '.join(workspace_files) if workspace_files else 'empty'}"
            augmented_prompt = (
                f"You are {current_agent.name} ({current_agent.role}) in Electorn AI Studio.\n"
                f"Target Workspace: {team.workspace_dir} ({ws_context})\n"
                f"{web_context_prompt}\n"
                f"Guidelines: Answer the user directly, helpfully, and conversationally. "
                f"If the user greets you or asks a question, answer with natural explanation first. "
                f"Only generate file code blocks when specifically asked to design, write, or build code.\n\n"
                f"User Question: {effective_query}"
            )

            # LIVE STREAMING RESPONSE
            console.print(f"\n{current_icon} [bold yellow]{current_agent.name}[/bold yellow] ❯ ", end="")
            streamed_chunks: list[str] = []

            try:
                # Direct streaming yields tokens as they are generated by Ollama
                for chunk in current_agent.stream_ask(augmented_prompt, conversation_history[:-1]):
                    console.print(chunk, end="", highlight=False)
                    streamed_chunks.append(chunk)
                    if hasattr(sys.stdout, "flush"):
                        sys.stdout.flush()
            except Exception as stream_err:
                console.print(f"\n[dim yellow]Streaming paused ({stream_err}), executing direct generation...[/dim yellow]")
                try:
                    direct_resp = current_agent.ask(augmented_prompt)
                    console.print(direct_resp.content)
                    streamed_chunks = [direct_resp.content]
                except Exception as direct_err:
                    console.print(f"\n[bold red]Model generation error:[/bold red] {direct_err}")
                    continue

            full_text = "".join(streamed_chunks).strip()
            console.print("\n")

            if full_text:
                conversation_history.append({"role": "assistant", "content": full_text})

                # Auto-detect if agent generated code files and prompt user to write them
                detected_files = BaseAgent.extract_files_from_text(full_text)
                if detected_files:
                    console.print("")
                    for f_path, f_code in detected_files.items():
                        save_choice = Prompt.ask(
                            f"  💾 Detected code for [bold cyan]{f_path}[/bold cyan]. Save directly to workspace?",
                            choices=["y", "n"],
                            default="y",
                        )
                        if save_choice.lower() == "y":
                            op = team.file_manager.write_file(f_path, f_code)
                            console.print(f"  ✔ [bold green]Saved[/bold green] {op.path} ({op.bytes_written} bytes)")
                    console.print("")

        except KeyboardInterrupt:
            console.print("\n[yellow]Chat session closed.[/yellow]")
            break
        except Exception as err:
            console.print(f"[bold red]Chat Error:[/bold red] {err}\n")



def main() -> None:
    """Main CLI entrypoint."""
    app()


if __name__ == "__main__":
    main()
