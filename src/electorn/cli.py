"""Electorn AI - Command Line Interface.

One CLI. A Complete AI Development Team.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional
import typer
from rich.console import Console
from rich.panel import Panel
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
    title.append(f"v{__version__} | Powered by Ollama Local AI Engine", style="dim cyan")
    console.print(Panel(title, border_style="cyan", padding=(1, 2)))


@app.callback(invoke_without_command=True)
def default_callback(ctx: typer.Context) -> None:
    """Callback triggered when electorn is invoked with no command."""
    if ctx.invoked_subcommand is None:
        print_banner()
        console.print(
            "Usage: [bold cyan]electorn \"Build a complete job recommendation platform\"[/bold cyan]\n"
            "   or: [bold cyan]electorn run \"<prompt>\"[/bold cyan]\n\n"
            "Available commands: [bold]run[/bold], [bold]models[/bold], [bold]doctor[/bold], [bold]init[/bold]\n"
            "Run [bold]electorn --help[/bold] to see all available commands and flags.\n"
        )


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
    client = OllamaClient(base_url=cfg.runtime.ollama_base_url, mock_mode=mock)

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

    try:
        team = MultiAgentTeam(
            workspace_dir=workspace,
            config=cfg,
            model_name=model,
            auto_approve=auto_approve,
            mock_mode=mock,
        )
    except Exception as err:
        console.print(f"[bold red]Initialization Error:[/bold red] {err}")
        sys.exit(1)

    profile = team.model_profile
    console.print(
        f"🤖 [bold green]Active AI Engine:[/bold green] [bold cyan]{profile.name}[/bold cyan] "
        f"({profile.description}) | [dim]Sequential RAM Optimization: Enabled[/dim]\n"
    )
    console.print(f"🎯 [bold white]Prompt:[/bold white] \"{prompt}\"")
    console.print(f"📁 [bold white]Target Workspace:[/bold white] {team.workspace_dir}\n")

    # Callbacks for Rich live status
    def on_step_start(agent_name: str, desc: str) -> None:
        console.print(f"⏳ [bold cyan][{agent_name}][/bold cyan] {desc}...")

    def on_step_complete(agent_name: str, artifacts: list[str]) -> None:
        art_str = f" [dim]({', '.join(artifacts[:3])}{'...' if len(artifacts) > 3 else ''})[/dim]" if artifacts else ""
        console.print(f"  ✔ [bold green][{agent_name}][/bold green] Completed{art_str}\n")

    def on_info(msg: str) -> None:
        console.print(f"  [yellow]{msg}[/yellow]")

    try:
        with console.status("[bold green]Electorn multi-agent team collaborating...[/bold green]", spinner="dots"):
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


def main() -> None:
    """Main CLI entrypoint."""
    app()


if __name__ == "__main__":
    main()
