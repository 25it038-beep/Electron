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
from electorn.execution.environment import EnvironmentDetector
from electorn.orchestration.team import MultiAgentTeam
from electorn.runtime.model_selector import ModelSelector
from electorn.runtime.ollama_client import OllamaClient
from electorn.storage.config import Config, load_config, save_config
from electorn.workspace.file_manager import FileOperationResult


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


def print_banner() -> None:
    """Print the Electorn AI header banner."""
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
    """Explicit run command: electorn run '...'."""
    run_development_pipeline(
        prompt=prompt,
        workspace=workspace,
        model=model,
        auto_approve=auto_approve,
        mock=mock,
    )


def run_development_pipeline(
    prompt: str,
    workspace: Path,
    model: Optional[str] = None,
    auto_approve: bool = False,
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

    # Callbacks for Rich live status
    def on_step_start(agent_name: str, desc: str) -> None:
        console.print(f"⏳ [bold cyan][{agent_name}][/bold cyan] {desc}...")

    def on_step_complete(agent_name: str, artifacts: list[str]) -> None:
        art_str = f" [dim]({', '.join(artifacts[:3])}{'...' if len(artifacts) > 3 else ''})[/dim]" if artifacts else ""
        console.print(f"  ✔ [bold green][{agent_name}][/bold green] Completed{art_str}\n")

    def on_info(msg: str) -> None:
        console.print(f"  [yellow]{msg}[/yellow]")

    try:
        with console.status(f"[bold green]Electorn multi-agent team collaborating on {team.workspace_dir.name}...[/bold green]", spinner="dots"):
            state = team.develop(
                prompt=prompt,
                on_step_start=on_step_start,
                on_step_complete=on_step_complete,
                on_info=on_info,
            )

        console.print("\n✨ [bold green]Development Workflow Completed Successfully![/bold green]\n")

        # Summary Tree
        tree = Tree(f"📦 [bold cyan]{state.specification.project_name if state.specification else 'Project'}[/bold cyan]")
        for f in team.file_manager.list_files():
            tree.add(f"[green]{f}[/green]")
        console.print(tree)
        console.print("")

        if state.specification:
            spec = state.specification
            summary_table = Table(title="🚀 Application Quickstart", border_style="cyan")
            summary_table.add_column("Property", style="bold white")
            summary_table.add_column("Details", style="cyan")
            summary_table.add_row("Run Command", spec.run_command)
            summary_table.add_row("Test Command", spec.test_command)
            summary_table.add_row("Tech Stack", ", ".join(f"{k}: {v}" for k, v in spec.tech_stack.items()))
            if spec.dependencies:
                summary_table.add_row("Dependencies", ", ".join(spec.dependencies))
            console.print(summary_table)

        console.print(f"\n[dim]Session audit saved to: {team.workspace_dir}/.electorn/sessions/{team.session_id}.json[/dim]\n")

    except KeyboardInterrupt:
        console.print("\n[yellow]Operation aborted by user.[/yellow]")
        sys.exit(130)
    except Exception as err:
        console.print(f"\n[bold red]Pipeline failed with error:[/bold red] {err}")
        sys.exit(1)


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

    chat_banner = (
        f"🌌 [bold cyan]ELECTORN FUTURISTIC AI STUDIO[/bold cyan]\n"
        f"Active Neural Engine: [bold green]{profile.name}[/bold green] ({profile.description})\n"
        f"Active Persona: {current_icon} [bold yellow]{current_agent.name}[/bold yellow] — {current_desc}\n"
        f"Target Workspace: [bold white]{team.workspace_dir}[/bold white]\n\n"
        f"[dim]Commands: [bold]/agent <name>[/bold] (architect|backend|frontend|database|qa|devops) | "
        f"[bold]/files[/bold] | [bold]/read <file>[/bold] | [bold]/build <prompt>[/bold] | [bold]/clear[/bold] | [bold]/exit[/bold][/dim]"
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

            if user_input.lower().startswith("/build "):
                build_prompt = user_input[7:].strip()
                console.print(f"\n🚀 [bold green]Initiating Autonomous Multi-Agent Development Pipeline for:[/bold green] \"{build_prompt}\"\n")
                run_development_pipeline(prompt=build_prompt, workspace=team.workspace_dir, model=model, auto_approve=True)
                continue

            # Interactive AI Response
            conversation_history.append({"role": "user", "content": user_input})
            # Keep history compact for small model context budgets
            if len(conversation_history) > 8:
                conversation_history = conversation_history[-8:]

            # Inject active workspace awareness into prompt
            workspace_summary = team.file_manager.get_directory_tree_str()
            augmented_prompt = (
                f"[SYSTEM CONTEXT: You are {current_agent.name} ({current_agent.role}). "
                f"Workspace files: {', '.join(team.file_manager.list_files()[:10]) or 'empty'}]\n\n"
                f"User Question: {user_input}"
            )

            with console.status(f"[magenta]{current_icon} {current_agent.name} synthesizing solution...[/magenta]", spinner="dots"):
                response = current_agent.ask(augmented_prompt)

            # Display formatted markdown
            console.print(f"\n{current_icon} [bold yellow]{current_agent.name}[/bold yellow] ❯")
            console.print(Markdown(response.content))

            # Auto-detect if agent generated code files and ask user if they want to write them
            detected_files = BaseAgent.extract_files_from_text(response.content)
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

            conversation_history.append({"role": "assistant", "content": response.content})
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
