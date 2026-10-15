"""CLI command group for Electorn Companion Mode."""

from __future__ import annotations

from pathlib import Path
from typing import Optional
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from electorn.companion.interface import CompanionInterface
from electorn.companion.memory import MemoryEngine
from electorn.companion.schema import (
    AffectionIntensity,
    CompanionConfig,
    CompanionMode,
    HumorLevel,
    MemoryCategory,
)
from electorn.companion.storage import CompanionStorage
from electorn.companion.supervisor import CompanionSupervisor

companion_app = typer.Typer(
    name="companion",
    help="💖 Electorn Companion Mode — Persistent, Voice-Enabled, Screen-Aware AI Girlfriend (Aria).",
    invoke_without_command=True,
)
console = Console(legacy_windows=False)


@companion_app.callback(invoke_without_command=True)
def companion_default_callback(ctx: typer.Context) -> None:
    """Launch interactive session if invoked without subcommands."""
    if ctx.invoked_subcommand is None:
        start_cmd()


@companion_app.command(name="start", help="Start the persistent companion voice and screen session.")
def start_cmd(
    mode: Optional[str] = typer.Option(None, "--mode", "-m", help="Mode: passive, companion, focus, work_assistant, privacy"),
    screen: Optional[bool] = typer.Option(None, "--screen", help="Enable/disable screen observation"),
    voice: Optional[bool] = typer.Option(None, "--voice", help="Enable/disable voice speech"),
) -> None:
    """Launch the interactive companion terminal dashboard and voice session."""
    storage = CompanionStorage()
    config = storage.load_config()

    if mode:
        try:
            config.mode = CompanionMode(mode.lower())
        except ValueError:
            console.print(f"[red]Invalid mode '{mode}'. Choose from: passive, companion, focus, work_assistant, privacy[/red]")
            raise typer.Exit(1)

    if screen is not None:
        config.screen.enabled = screen
    if voice is not None:
        config.voice_enabled = voice

    storage.save_config(config)

    supervisor = CompanionSupervisor(config=config)
    ui = CompanionInterface(supervisor=supervisor)
    ui.run_interactive_session()


@companion_app.command(name="status", help="Show companion configuration, active mode, and health status.")
def status_cmd() -> None:
    """Display comprehensive status table."""
    storage = CompanionStorage()
    config = storage.load_config()
    memory = MemoryEngine(config.storage_directory)

    table = Table(title="💖 Electorn Companion Status", border_style="magenta")
    table.add_column("Property", style="bold cyan")
    table.add_column("Value", style="white")

    table.add_row("Name", config.personality.name)
    table.add_row("User Address", f"{config.personality.preferred_address} ({config.personality.user_name})")
    table.add_row("Operating Mode", config.mode.value.upper())
    table.add_row("Affection Level", config.personality.affection_intensity.value)
    table.add_row("Humor Level", config.personality.humor_level.value)
    table.add_row("Language", f"{config.personality.language} (Tamil code-switch: {config.personality.code_switch_tamil})")
    table.add_row("Voice Output", "Enabled" if config.voice_enabled else "Disabled")
    table.add_row("Barge-In Interrupt", "Enabled" if config.barge_in_enabled else "Disabled")
    table.add_row("Screen Observation", "Enabled" if config.screen.enabled else "Disabled (Opt-in required)")
    table.add_row("Screen Interval", f"{config.screen.interval_seconds} seconds")
    table.add_row("Vision Model", config.screen.vision_model)
    table.add_row("Quiet Hours", f"{config.personality.quiet_hours_start} to {config.personality.quiet_hours_end}")
    table.add_row("Stored Memories", str(len(memory.load_all())))

    console.print(table)


@companion_app.command(name="mode", help="Switch companion operating mode.")
def mode_cmd(
    new_mode: str = typer.Argument(..., help="Mode: passive, companion, focus, work_assistant, privacy")
) -> None:
    """Switch operating mode."""
    storage = CompanionStorage()
    config = storage.load_config()
    try:
        mode_enum = CompanionMode(new_mode.lower())
    except ValueError:
        console.print(f"[red]Invalid mode '{new_mode}'. Valid choices: passive, companion, focus, work_assistant, privacy[/red]")
        raise typer.Exit(1)

    config.mode = mode_enum
    storage.save_config(config)
    console.print(f"[bold green]✔ Switched mode to: {mode_enum.value.upper()}[/bold green]")


@companion_app.command(name="personality", help="Configure companion persona, address title, and affection.")
def personality_cmd(
    name: Optional[str] = typer.Option(None, "--name", help="Companion name (e.g. Aria)"),
    address: Optional[str] = typer.Option(None, "--address", help="Preferred address (e.g. Darling, Babe, Dear)"),
    user_name: Optional[str] = typer.Option(None, "--user", help="User name (e.g. Harshan)"),
    affection: Optional[str] = typer.Option(None, "--affection", help="low, medium, high"),
    humor: Optional[str] = typer.Option(None, "--humor", help="low, medium, high"),
    tamil: Optional[bool] = typer.Option(None, "--tamil", help="Enable/disable Tamil code-switching"),
) -> None:
    """Update companion persona settings."""
    storage = CompanionStorage()
    config = storage.load_config()

    if name:
        config.personality.name = name
    if address:
        config.personality.preferred_address = address
    if user_name:
        config.personality.user_name = user_name
    if affection:
        try:
            config.personality.affection_intensity = AffectionIntensity(affection.lower())
        except ValueError:
            console.print("[red]Invalid affection level. Use: low, medium, high[/red]")
    if humor:
        try:
            config.personality.humor_level = HumorLevel(humor.lower())
        except ValueError:
            console.print("[red]Invalid humor level. Use: low, medium, high[/red]")
    if tamil is not None:
        config.personality.code_switch_tamil = tamil

    storage.save_config(config)
    console.print("[bold green]✔ Companion personality settings updated successfully.[/bold green]")


@companion_app.command(name="screen", help="Configure screen observation privacy and capture settings.")
def screen_cmd(
    enable: Optional[bool] = typer.Option(None, "--enable/--disable", help="Toggle screen observation"),
    interval: Optional[int] = typer.Option(None, "--interval", help="Seconds between screen captures (min: 5)"),
) -> None:
    """Update screen observation configuration."""
    storage = CompanionStorage()
    config = storage.load_config()

    if enable is not None:
        config.screen.enabled = enable
    if interval is not None:
        config.screen.interval_seconds = max(5, interval)

    storage.save_config(config)
    status_str = "ENABLED" if config.screen.enabled else "DISABLED"
    console.print(f"[bold green]✔ Screen observation is now: {status_str} (Interval: {config.screen.interval_seconds}s)[/bold green]")


@companion_app.command(name="voice", help="Configure voice speech, gender, and barge-in.")
def voice_cmd(
    enable: Optional[bool] = typer.Option(None, "--enable/--disable", help="Toggle voice speech"),
    gender: Optional[str] = typer.Option(None, "--gender", help="female or male"),
    barge_in: Optional[bool] = typer.Option(None, "--barge-in/--no-barge-in", help="Toggle barge-in speech interruption"),
    speed: Optional[float] = typer.Option(None, "--speed", help="Speaking speed factor (e.g. 1.0)"),
) -> None:
    """Update voice parameters."""
    storage = CompanionStorage()
    config = storage.load_config()

    if enable is not None:
        config.voice_enabled = enable
    if gender and gender.lower() in ("female", "male"):
        config.personality.voice_gender = gender.lower()
    if barge_in is not None:
        config.barge_in_enabled = barge_in
    if speed is not None:
        config.personality.speaking_speed = max(0.5, min(2.0, speed))

    storage.save_config(config)
    console.print("[bold green]✔ Companion voice configuration updated.[/bold green]")


@companion_app.command(name="memory", help="Inspect and manage persistent companion memories.")
def memory_cmd(
    action: str = typer.Argument("list", help="list, add, search, clear, delete"),
    key: Optional[str] = typer.Option(None, "--key", "-k", help="Memory key"),
    value: Optional[str] = typer.Option(None, "--val", "-v", help="Memory value"),
    query: Optional[str] = typer.Option(None, "--query", "-q", help="Search query"),
    memory_id: Optional[str] = typer.Option(None, "--id", help="Memory record ID for deletion"),
) -> None:
    """Manage companion memory storage."""
    storage = CompanionStorage()
    config = storage.load_config()
    memory = MemoryEngine(config.storage_directory)

    act = action.lower()
    if act == "list":
        items = memory.load_all()
        if not items:
            console.print("[yellow]No memories saved yet.[/yellow]")
            return
        table = Table(title="Companion Memories", border_style="cyan")
        table.add_column("ID", style="dim")
        table.add_column("Category", style="cyan")
        table.add_column("Key", style="bold")
        table.add_column("Value", style="white")
        for item in items:
            table.add_row(item.memory_id, item.category.value, item.key, item.value)
        console.print(table)

    elif act == "add":
        if not key or not value:
            console.print("[red]Please provide both --key and --val to add a memory.[/red]")
            return
        item = memory.add_memory(category=MemoryCategory.USER_PREFERENCE, key=key, value=value)
        console.print(f"[bold green]✔ Added memory: [{item.memory_id}] {key} -> {value}[/bold green]")

    elif act == "search":
        if not query:
            console.print("[red]Please provide --query to search memories.[/red]")
            return
        results = memory.search_memories(query)
        console.print(f"Found {len(results)} matches for '{query}':")
        for r in results:
            console.print(f"- [dim]{r.memory_id}[/dim] [bold]{r.key}[/bold]: {r.value}")

    elif act == "delete":
        if not memory_id:
            console.print("[red]Please provide --id to delete a memory.[/red]")
            return
        if memory.delete_memory(memory_id):
            console.print(f"[green]✔ Memory {memory_id} deleted.[/green]")
        else:
            console.print(f"[red]Memory {memory_id} not found.[/red]")

    elif act == "clear":
        confirm = typer.confirm("Are you sure you want to delete all stored memories?")
        if confirm:
            memory.clear_memories()
            console.print("[yellow]✔ All companion memories cleared.[/yellow]")


@companion_app.command(name="activity", help="Show recent companion observations and activity.")
def activity_cmd(limit: int = typer.Option(15, "--limit", "-n", help="Number of records to show")) -> None:
    """Display audit log entries."""
    storage = CompanionStorage()
    records = storage.load_recent_activity(limit=limit)
    if not records:
        console.print("[yellow]No recent companion activity logged.[/yellow]")
        return

    table = Table(title="Recent Companion Activity", border_style="magenta")
    table.add_column("Time", style="dim")
    table.add_column("Activity Type", style="cyan")
    table.add_column("Details", style="white")

    for rec in records:
        import datetime
        dt = datetime.datetime.fromtimestamp(rec.get("timestamp", 0)).strftime("%H:%M:%S")
        act_type = rec.get("type", "unknown")
        details = str(rec.get("details", {}))[:70]
        table.add_row(dt, act_type, details)

    console.print(table)


@companion_app.command(name="reset", help="Reset companion settings to fresh factory defaults.")
def reset_cmd() -> None:
    """Reset configuration to default values."""
    confirm = typer.confirm("Reset companion configuration to defaults?")
    if confirm:
        storage = CompanionStorage()
        storage.reset_config()
        console.print("[green]✔ Companion configuration reset to factory defaults.[/green]")
