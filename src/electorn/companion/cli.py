"""CLI command group for Electorn Companion Mode."""

from __future__ import annotations

from pathlib import Path
from typing import Optional
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from electorn.companion.activity_classifier import ActivityClassifier
from electorn.companion.interface import CompanionInterface
from electorn.companion.memory import MemoryEngine
from electorn.companion.schema import (
    AffectionIntensity,
    CompanionConfig,
    CompanionMode,
    HumorLevel,
    MemoryCategory,
)
from electorn.companion.screen_observer import ScreenObservationEngine
from electorn.companion.startup import StartupManager
from electorn.companion.storage import CompanionStorage
from electorn.companion.supervisor import CompanionSupervisor
from electorn.companion.time_engine import TimeAwarenessEngine
from electorn.companion.vision_analyzer import VisionAnalyzer

companion_app = typer.Typer(
    name="companion",
    help="💖 Electorn Companion Mode — Persistent, Voice-Enabled, Screen-Aware AI Companion (Harshan).",
    invoke_without_command=True,
)
screen_subapp = typer.Typer(name="screen", help="Manage screen observation and privacy exclusions.")
startup_subapp = typer.Typer(name="startup", help="Manage automatic Windows login startup.")
bedtime_subapp = typer.Typer(name="bedtime", help="Manage bedtime schedules and sleep reminders.")
quiet_hours_subapp = typer.Typer(name="quiet-hours", help="Manage quiet hours.")
voice_subapp = typer.Typer(name="voice", help="Voice engine controls and status.")
proactive_subapp = typer.Typer(name="proactive", help="Proactive speech controls and limits.")
focus_subapp = typer.Typer(name="focus", help="Focus mode controls.")
activity_subapp = typer.Typer(name="activity", help="Activity tracking and summaries.")

companion_app.add_typer(screen_subapp)
companion_app.add_typer(startup_subapp)
companion_app.add_typer(bedtime_subapp)
companion_app.add_typer(quiet_hours_subapp)
companion_app.add_typer(voice_subapp)
companion_app.add_typer(proactive_subapp)
companion_app.add_typer(focus_subapp)
companion_app.add_typer(activity_subapp)

console = Console(legacy_windows=False)


@companion_app.callback(invoke_without_command=True)
def companion_default_callback(
    ctx: typer.Context,
    mode: Optional[str] = typer.Option(None, "--mode", "-m", help="companion, focus, study, night, passive, privacy"),
    screen: Optional[bool] = typer.Option(None, "--screen/--no-screen", help="Enable/disable screen observation"),
    voice: Optional[bool] = typer.Option(None, "--voice/--no-voice", help="Enable/disable voice speech"),
    status: bool = typer.Option(False, "--status", help="Show companion status and exit"),
) -> None:
    """Launch the unified all-in-one Electorn AI Companion (Voice, Screen, Autonomous Conversation)."""
    if ctx.invoked_subcommand is None:
        if status:
            status_cmd()
            return
        start_cmd(mode=mode, screen=screen, voice=voice)


# =============================================================================
# START / STOP / PAUSE / RESUME / STATUS
# =============================================================================

@companion_app.command(name="start", help="Start the persistent companion voice and screen session.")
@companion_app.command(name="run", help="Start the persistent companion voice and screen session.")
def start_cmd(
    mode: Optional[str] = typer.Option(None, "--mode", "-m", help="companion, focus, study, night, passive, privacy"),
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
            console.print(f"[red]Invalid mode '{mode}'. Choose from: companion, focus, study, night, passive, privacy[/red]")
            raise typer.Exit(1)

    if screen is not None:
        config.screen.enabled = screen
    if voice is not None:
        config.voice_enabled = voice

    storage.save_config(config)

    supervisor = CompanionSupervisor(config=config)
    ui = CompanionInterface(supervisor=supervisor)
    ui.run_interactive_session()


@companion_app.command(name="stop", help="Stop any active background companion instance.")
def stop_cmd() -> None:
    """Stop active companion instances."""
    storage = CompanionStorage()
    cfg = storage.load_config()
    mgr = StartupManager(cfg.storage_directory)
    mgr.release_instance_lock()
    console.print("[green]✔ Companion session stopped and lock released.[/green]")


@companion_app.command(name="pause", help="Pause companion speech and proactive remarks.")
def pause_cmd() -> None:
    """Pause companion."""
    storage = CompanionStorage()
    config = storage.load_config()
    storage.log_activity("cli_pause", {})
    console.print("[yellow]⏸️ Companion paused.[/yellow]")


@companion_app.command(name="resume", help="Resume companion operations.")
def resume_cmd() -> None:
    """Resume companion."""
    storage = CompanionStorage()
    storage.log_activity("cli_resume", {})
    console.print("[green]▶️ Companion resumed.[/green]")


@companion_app.command(name="status", help="Show companion configuration, active mode, and health status.")
def status_cmd() -> None:
    """Display comprehensive status table."""
    storage = CompanionStorage()
    config = storage.load_config()
    memory = MemoryEngine(config.storage_directory)
    time_engine = TimeAwarenessEngine()
    startup_mgr = StartupManager(config.storage_directory)

    table = Table(title="💖 Electorn Companion Status", border_style="magenta")
    table.add_column("Property", style="bold cyan")
    table.add_column("Value", style="white")

    table.add_row("Name", config.personality.name)
    table.add_row("User", config.personality.user_name)
    table.add_row("Preferred Address", config.personality.preferred_address)
    table.add_row("Operating Mode", config.mode.value.upper())
    table.add_row("System Clock", time_engine.get_formatted_time())
    table.add_row("Bedtime", f"{config.bedtime.bedtime} (Reminders: {'ON' if config.bedtime.enabled else 'OFF'})")
    table.add_row("Quiet Hours", f"{config.bedtime.quiet_hours_start} to {config.bedtime.quiet_hours_end}")
    table.add_row("Windows Startup", "Enabled" if startup_mgr.is_startup_enabled() else "Disabled")
    table.add_row("Voice Output", "Enabled" if config.voice_enabled else "Disabled")
    table.add_row("Barge-In Interrupt", "Enabled" if config.barge_in_enabled else "Disabled")
    table.add_row("Proactive Conversations", "Enabled" if config.proactive.enabled else "Disabled")
    table.add_row("Screen Observation", "Enabled" if config.screen.enabled else "Disabled (Opt-in required)")
    table.add_row("Screen Interval", f"{config.screen.interval_seconds} seconds")
    table.add_row("Vision Model", config.screen.vision_model)
    table.add_row("Stored Memories", str(len(memory.load_all())))

    console.print(table)


# =============================================================================
# OPERATING MODE COMMAND
# =============================================================================

@companion_app.command(name="mode", help="Switch companion operating mode.")
def mode_cmd(
    new_mode: str = typer.Argument(..., help="Mode: companion, focus, study, night, passive, privacy")
) -> None:
    """Switch operating mode."""
    storage = CompanionStorage()
    config = storage.load_config()
    try:
        mode_enum = CompanionMode(new_mode.lower())
    except ValueError:
        console.print(f"[red]Invalid mode '{new_mode}'. Valid choices: companion, focus, study, night, passive, privacy[/red]")
        raise typer.Exit(1)

    config.mode = mode_enum
    storage.save_config(config)
    console.print(f"[bold green]✔ Switched mode to: {mode_enum.value.upper()}[/bold green]")


@companion_app.command(name="privacy", help="Immediately engage Privacy Mode (disable mic and screen).")
def privacy_cmd() -> None:
    """Engage Privacy Mode."""
    storage = CompanionStorage()
    config = storage.load_config()
    config.mode = CompanionMode.PRIVACY
    config.screen.enabled = False
    storage.save_config(config)
    console.print("[bold red]✔ Privacy Mode engaged. Microphone and screen observation completely disabled.[/bold red]")


# =============================================================================
# WINDOWS STARTUP SUBCOMMANDS
# =============================================================================

@startup_subapp.command(name="enable", help="Enable automatic startup on Windows login.")
def startup_enable_cmd() -> None:
    storage = CompanionStorage()
    cfg = storage.load_config()
    mgr = StartupManager(cfg.storage_directory)
    ok, msg = mgr.enable_startup()
    if ok:
        cfg.startup.enabled = True
        storage.save_config(cfg)
        console.print(f"[bold green]✔ {msg}[/bold green]")
    else:
        console.print(f"[bold red]❌ {msg}[/bold red]")


@startup_subapp.command(name="disable", help="Disable automatic startup on Windows login.")
def startup_disable_cmd() -> None:
    storage = CompanionStorage()
    cfg = storage.load_config()
    mgr = StartupManager(cfg.storage_directory)
    ok, msg = mgr.disable_startup()
    if ok:
        cfg.startup.enabled = False
        storage.save_config(cfg)
        console.print(f"[bold green]✔ {msg}[/bold green]")
    else:
        console.print(f"[bold red]❌ {msg}[/bold red]")


@startup_subapp.command(name="status", help="Check Windows startup registration status.")
def startup_status_cmd() -> None:
    storage = CompanionStorage()
    cfg = storage.load_config()
    mgr = StartupManager(cfg.storage_directory)
    is_on = mgr.is_startup_enabled()
    status_str = "[bold green]ENABLED[/bold green]" if is_on else "[yellow]DISABLED[/yellow]"
    console.print(f"Windows Automatic Login Startup: {status_str}")


# =============================================================================
# BEDTIME & QUIET HOURS SUBCOMMANDS
# =============================================================================

@bedtime_subapp.command(name="set", help="Set bedtime target (e.g. 23:30 or 11:30 PM).")
def bedtime_set_cmd(time_str: str = typer.Argument(..., help="Time in HH:MM format (24-hour)")) -> None:
    storage = CompanionStorage()
    cfg = storage.load_config()
    cfg.bedtime.bedtime = time_str.strip()
    storage.save_config(cfg)
    console.print(f"[bold green]✔ Bedtime updated to: {cfg.bedtime.bedtime}[/bold green]")


@quiet_hours_subapp.command(name="set", help="Set quiet hours interval (e.g. 23:00 07:00).")
def quiet_hours_set_cmd(
    start: str = typer.Argument(..., help="Start time in HH:MM (e.g. 23:00)"),
    end: str = typer.Argument(..., help="End time in HH:MM (e.g. 07:00)"),
) -> None:
    storage = CompanionStorage()
    cfg = storage.load_config()
    cfg.bedtime.quiet_hours_start = start.strip()
    cfg.bedtime.quiet_hours_end = end.strip()
    storage.save_config(cfg)
    console.print(f"[bold green]✔ Quiet hours updated: {start} to {end}[/bold green]")


# =============================================================================
# VOICE & PROACTIVE TOGGLES
# =============================================================================

@voice_subapp.command(name="on", help="Enable voice output.")
def voice_on_cmd() -> None:
    storage = CompanionStorage()
    cfg = storage.load_config()
    cfg.voice_enabled = True
    storage.save_config(cfg)
    console.print("[bold green]✔ Companion voice enabled.[/bold green]")


@voice_subapp.command(name="off", help="Disable voice output.")
def voice_off_cmd() -> None:
    storage = CompanionStorage()
    cfg = storage.load_config()
    cfg.voice_enabled = False
    storage.save_config(cfg)
    console.print("[yellow]✔ Companion voice disabled.[/yellow]")


@voice_subapp.command(name="status", help="Show voice engine configuration.")
def voice_status_cmd() -> None:
    storage = CompanionStorage()
    cfg = storage.load_config()
    console.print(f"Voice Enabled: {cfg.voice_enabled} | Language: {cfg.personality.language} | Barge-in: {cfg.barge_in_enabled}")


@proactive_subapp.command(name="on", help="Enable proactive conversations.")
def proactive_on_cmd() -> None:
    storage = CompanionStorage()
    cfg = storage.load_config()
    cfg.proactive.enabled = True
    storage.save_config(cfg)
    console.print("[bold green]✔ Proactive conversations enabled.[/bold green]")


@proactive_subapp.command(name="off", help="Disable proactive conversations.")
def proactive_off_cmd() -> None:
    storage = CompanionStorage()
    cfg = storage.load_config()
    cfg.proactive.enabled = False
    storage.save_config(cfg)
    console.print("[yellow]✔ Proactive conversations disabled.[/yellow]")


@proactive_subapp.command(name="status", help="Show proactive speech configuration.")
def proactive_status_cmd() -> None:
    storage = CompanionStorage()
    cfg = storage.load_config()
    console.print(f"Proactive Enabled: {cfg.proactive.enabled} | Max/Hour: {cfg.proactive.max_per_hour} | Min Interval: {cfg.proactive.min_interval_seconds}s")


@focus_subapp.command(name="on", help="Enable focus mode.")
def focus_on_cmd() -> None:
    mode_cmd("focus")


@focus_subapp.command(name="off", help="Disable focus mode (return to companion mode).")
def focus_off_cmd() -> None:
    mode_cmd("companion")


# =============================================================================
# SCREEN SUBCOMMANDS
# =============================================================================

@screen_subapp.command(name="enable", help="Enable screen observation.")
def screen_enable_cmd() -> None:
    storage = CompanionStorage()
    cfg = storage.load_config()
    cfg.screen.enabled = True
    storage.save_config(cfg)
    console.print("[bold green]✔ Screen observation ENABLED.[/bold green]")


@screen_subapp.command(name="disable", help="Disable screen observation.")
def screen_disable_cmd() -> None:
    storage = CompanionStorage()
    cfg = storage.load_config()
    cfg.screen.enabled = False
    storage.save_config(cfg)
    console.print("[yellow]✔ Screen observation DISABLED.[/yellow]")


@screen_subapp.command(name="status", help="Show screen observation status.")
def screen_status_cmd() -> None:
    storage = CompanionStorage()
    cfg = storage.load_config()
    status = "ENABLED" if cfg.screen.enabled else "DISABLED"
    console.print(f"Screen Observation: {status} (Interval: {cfg.screen.interval_seconds}s, Vision Model: {cfg.screen.vision_model})")


@screen_subapp.command(name="exclusions", help="List excluded sensitive applications.")
def screen_exclusions_cmd() -> None:
    storage = CompanionStorage()
    cfg = storage.load_config()
    console.print("[bold cyan]Excluded Applications:[/bold cyan]")
    for app in cfg.screen.excluded_apps:
        console.print(f"  - {app}")


@screen_subapp.command(name="live", help="Real-time live screen monitoring and sharing feed.")
@screen_subapp.command(name="watch", help="Real-time live screen monitoring and sharing feed.")
def screen_live_cmd(
    interval: int = typer.Option(3, "--interval", "-i", help="Monitoring capture interval in seconds"),
    count: int = typer.Option(0, "--count", "-c", help="Number of frames to observe (0 = continuous)"),
) -> None:
    """Stream live real-time screen monitoring and visual activity feed."""
    import time
    storage = CompanionStorage()
    cfg = storage.load_config()
    cfg.screen.enabled = True
    observer = ScreenObservationEngine(config=cfg.screen)
    analyzer = VisionAnalyzer(config=cfg.screen)

    console.print(Panel(
        f"[bold magenta]🖥️ ELECTORN REAL-TIME SCREEN SHARING & MONITORING[/bold magenta]\n"
        f"[dim]Observing foreground windows, process activity, OCR text, and code errors every {interval}s.\n"
        f"Press [bold]Ctrl+C[/bold] to exit monitoring.[/dim]",
        border_style="magenta",
    ))

    frames = 0
    try:
        while True:
            img, report = observer.capture_screen()
            analyzed = analyzer.analyze(img, report) if img else report

            table = Table(title=f"Live Screen Frame #{frames + 1} • {time.strftime('%H:%M:%S')}", border_style="cyan")
            table.add_column("Property", style="bold cyan")
            table.add_column("Value", style="white")

            table.add_row("Active Window", analyzed.window_title)
            table.add_row("Process Name", analyzed.process_name)
            table.add_row("App Category", analyzed.app_category)
            table.add_row("Activity Category", f"[bold green]{analyzed.activity_category.value.upper()}[/bold green]")
            table.add_row("Sustained Duration", f"{int(analyzed.sustained_duration_seconds)}s ({int(analyzed.sustained_duration_seconds / 60)} min)")
            table.add_row("Visual Change Ratio", f"{analyzed.change_ratio * 100:.1f}%")
            table.add_row("Privacy Filter", "[red]EXCLUDED/FILTERED[/red]" if analyzed.is_excluded else "[green]PERMITTED[/green]")
            table.add_row("Visual Summary", analyzed.visible_summary or "Inspecting visual workspace...")

            if analyzed.visible_error:
                table.add_row("Detected Error", f"[bold red]{analyzed.visible_error}[/bold red]")

            console.print(table)
            frames += 1
            if count > 0 and frames >= count:
                break
            time.sleep(interval)
    except KeyboardInterrupt:
        console.print("\n[yellow]Screen monitoring stopped.[/yellow]")


@screen_subapp.command(name="snapshot", help="Capture and analyze instant screen snapshot.")
def screen_snapshot_cmd(
    save: bool = typer.Option(True, "--save/--no-save", help="Save captured snapshot image to disk"),
) -> None:
    """Capture instant screen snapshot and run comprehensive visual error and activity analysis."""
    import time
    storage = CompanionStorage()
    cfg = storage.load_config()
    cfg.screen.enabled = True
    observer = ScreenObservationEngine(config=cfg.screen)
    analyzer = VisionAnalyzer(config=cfg.screen)

    img, report = observer.capture_screen()
    analyzed = analyzer.analyze(img, report) if img else report

    save_path_str = "Not saved"
    if save and img:
        snap_dir = cfg.storage_directory / "screenshots"
        snap_dir.mkdir(parents=True, exist_ok=True)
        filename = f"snapshot_{int(time.time())}.png"
        full_path = snap_dir / filename
        img.save(full_path)
        save_path_str = str(full_path)

    table = Table(title="📸 Instant Screen Snapshot & Analysis", border_style="magenta")
    table.add_column("Field", style="bold cyan")
    table.add_column("Observation Details", style="white")

    table.add_row("Active Window", analyzed.window_title)
    table.add_row("Process Name", analyzed.process_name)
    table.add_row("Application Category", analyzed.app_category)
    table.add_row("Activity Classification", analyzed.activity_category.value.upper())
    table.add_row("Visual Change Ratio", f"{analyzed.change_ratio * 100:.1f}%")
    table.add_row("Snapshot Path", save_path_str)
    table.add_row("Summary / OCR", analyzed.visible_summary or "Workspace inspected.")

    if analyzed.visible_error:
        table.add_row("Detected Error", f"[bold red]{analyzed.visible_error}[/bold red]")

    console.print(table)


# =============================================================================
# ACTIVITY & MEMORY SUBCOMMANDS
# =============================================================================

@activity_subapp.command(name="summary", help="Show summary of observed activity.")
def activity_summary_cmd() -> None:
    storage = CompanionStorage()
    records = storage.load_recent_activity(limit=20)
    console.print(f"[bold cyan]Recent Observations & Activities ({len(records)} entries):[/bold cyan]")
    for r in records[:10]:
        console.print(f"- [dim]{r.get('type')}[/dim]: {str(r.get('details', {}))[:80]}")


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


@companion_app.command(name="config", help="View current companion configuration.")
def config_cmd() -> None:
    storage = CompanionStorage()
    cfg = storage.load_config()
    console.print(cfg.model_dump_json(indent=2))


@companion_app.command(name="reset", help="Reset companion settings to fresh factory defaults.")
def reset_cmd() -> None:
    confirm = typer.confirm("Reset companion configuration to defaults?")
    if confirm:
        storage = CompanionStorage()
        storage.reset_config()
        console.print("[green]✔ Companion configuration reset to factory defaults.[/green]")
