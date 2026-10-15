"""Interactive Rich terminal dashboard and session runner for Companion Mode."""

from __future__ import annotations

import sys
import threading
import time
from typing import List, Optional

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich.text import Text

from electorn.companion.schema import CompanionLifecycleState, CompanionMode, CompanionState
from electorn.companion.supervisor import CompanionSupervisor
from electorn.companion.time_engine import TimeAwarenessEngine

console = Console(legacy_windows=False)


class CompanionInterface:
    """Rich terminal user interface and interactive conversation loop for Companion Mode."""

    def __init__(self, supervisor: CompanionSupervisor) -> None:
        self.supervisor = supervisor
        self.messages: List[tuple[str, str]] = []
        self._running = False
        self.time_engine = TimeAwarenessEngine()

        # Wire up supervisor callbacks
        self.supervisor.on_message_cb = self._add_message

    def _add_message(self, speaker: str, content: str) -> None:
        """Append a dialogue entry to the active chat log."""
        self.messages.append((speaker, content))
        if len(self.messages) > 100:
            self.messages = self.messages[-100:]

    def build_dashboard(self) -> Panel:
        """Construct the Rich visual dashboard layout."""
        state = self.supervisor.state
        config = self.supervisor.config

        # Status indicators
        mic_status = "🔴 MUTED" if state.is_muted else ("🟢 ACTIVE" if state.mic_active and not state.is_paused else "⚪ OFF")
        screen_status = "🟢 ACTIVE" if config.screen.enabled and state.screen_active and not state.is_paused else "⚪ OFF"
        barge_in = "🟢 ON" if config.barge_in_enabled else "⚪ OFF"
        paused_status = "⏸️ PAUSED" if state.is_paused else f"▶️ {state.current_lifecycle.value}"

        # Active Mode formatting
        mode_colors = {
            CompanionMode.COMPANION: "magenta",
            CompanionMode.FOCUS: "blue",
            CompanionMode.STUDY: "green",
            CompanionMode.NIGHT: "purple",
            CompanionMode.PASSIVE: "yellow",
            CompanionMode.PRIVACY: "red",
            CompanionMode.WORK_ASSISTANT: "cyan",
        }
        mode_style = mode_colors.get(state.active_mode, "white")

        current_time_str = self.time_engine.get_formatted_time()
        bedtime_str = config.bedtime.bedtime

        status_table = Table.grid(padding=(0, 2))
        status_table.add_column("Key", style="dim")
        status_table.add_column("Val", style="bold")
        status_table.add_column("Key2", style="dim")
        status_table.add_column("Val2", style="bold")

        status_table.add_row(
            "Companion:", f"[bold magenta]{config.personality.name}[/bold magenta]",
            "Mode:", f"[{mode_style}]{state.active_mode.value.upper()}[/{mode_style}]",
        )
        status_table.add_row(
            "Addressing:", f"[bold cyan]{config.personality.user_name}[/bold cyan]",
            "Status:", f"[bold]{paused_status}[/bold]",
        )
        status_table.add_row(
            "System Clock:", f"[bold white]{current_time_str}[/bold white]",
            "Target Bedtime:", f"[yellow]{bedtime_str}[/yellow]",
        )
        status_table.add_row(
            "Voice Engine:", mic_status,
            "Screen Vision:", screen_status,
        )
        status_table.add_row(
            "Barge-In:", barge_in,
            "Activity:", f"[cyan]{state.current_activity.value.upper()}[/cyan]",
        )

        obs_text = state.active_window_title or "No active window inspected yet"
        if len(obs_text) > 60:
            obs_text = obs_text[:57] + "..."

        table_panel = Panel(
            status_table,
            title=f"💖 {config.personality.name} Companion Dashboard • Window: {obs_text}",
            border_style=mode_style,
        )
        return table_panel

    def display_recent_conversation(self) -> None:
        """Render recent conversational exchanges."""
        if not self.messages:
            return

        for speaker, text in self.messages[-6:]:
            if speaker == self.supervisor.config.personality.name:
                console.print(f"[bold magenta]💖 {speaker}:[/bold magenta] {text}")
            else:
                console.print(f"[bold green]👤 {speaker}:[/bold green] {text}")

    def run_interactive_session(self) -> None:
        """Start the live companion interaction loop."""
        self.supervisor.start()
        self._running = True

        console.clear()
        console.print(Panel(
            f"[bold magenta]⚡ ELECTORN COMPANION MODE[/bold magenta] — Persistent Voice & Screen-Aware AI (Aria)\n"
            f"[dim]Addressing: [bold]{self.supervisor.config.personality.user_name}[/bold] | Modes: [bold]/companion[/bold], [bold]/focus[/bold], [bold]/study[/bold], [bold]/night[/bold], [bold]/privacy[/bold]\n"
            f"Commands: [bold]/screen[/bold], [bold]/mute[/bold], [bold]/unmute[/bold], [bold]/snooze[/bold], [bold]/pause[/bold], [bold]/resume[/bold], [bold]/exit[/bold][/dim]",
            border_style="magenta",
        ))

        try:
            while self._running:
                console.print(self.build_dashboard())
                self.display_recent_conversation()

                user_input = Prompt.ask("\n[bold cyan]Speak or type (or /help)[/bold cyan]").strip()
                if not user_input:
                    continue

                lower = user_input.lower()
                if lower in ("/exit", "/quit", "exit", "quit", "q"):
                    console.print(f"\n[yellow]Shutting down Companion session. Goodbye {self.supervisor.config.personality.user_name}![/yellow]")
                    break

                if lower in ("/pause", "pause"):
                    self.supervisor.pause()
                    console.print("[yellow]⏸️ Companion paused.[/yellow]\n")
                    continue

                if lower in ("/resume", "resume"):
                    self.supervisor.resume()
                    console.print("[green]▶️ Companion resumed.[/green]\n")
                    continue

                if lower in ("/mute", "mute"):
                    self.supervisor.mute()
                    console.print("[red]🔇 Microphone muted.[/red]\n")
                    continue

                if lower in ("/unmute", "unmute"):
                    self.supervisor.unmute()
                    console.print("[green]🎙️ Microphone unmuted.[/green]\n")
                    continue

                if lower in ("/focus", "focus"):
                    self.supervisor.set_mode(CompanionMode.FOCUS)
                    console.print("[blue]Switched to Focus Mode.[/blue]\n")
                    continue

                if lower in ("/study", "study"):
                    self.supervisor.set_mode(CompanionMode.STUDY)
                    console.print("[green]Switched to Study Mode.[/green]\n")
                    continue

                if lower in ("/night", "night"):
                    self.supervisor.set_mode(CompanionMode.NIGHT)
                    console.print("[purple]Switched to Night Mode.[/purple]\n")
                    continue

                if lower in ("/companion", "companion"):
                    self.supervisor.set_mode(CompanionMode.COMPANION)
                    console.print("[magenta]Switched to Companion Mode.[/magenta]\n")
                    continue

                if lower in ("/privacy", "privacy"):
                    self.supervisor.set_mode(CompanionMode.PRIVACY)
                    console.print("[red]Switched to Privacy Mode (Mic and screen disabled).[/red]\n")
                    continue

                if lower in ("/snooze", "snooze"):
                    self.supervisor.time_engine.snooze(self.supervisor.config.bedtime, minutes=30)
                    console.print("[yellow]Bedtime reminder snoozed for 30 minutes.[/yellow]\n")
                    continue

                if lower in ("/screen", "screen"):
                    self.supervisor.config.screen.enabled = not self.supervisor.config.screen.enabled
                    self.supervisor.screen_observer.config.enabled = self.supervisor.config.screen.enabled
                    status = "ENABLED" if self.supervisor.config.screen.enabled else "DISABLED"
                    console.print(f"[cyan]Screen observation {status}.[/cyan]\n")
                    continue

                # Process message
                self._add_message(self.supervisor.config.personality.user_name, user_input)
                console.print("[dim]Thinking...[/dim]")
                reply = self.supervisor.process_user_input(user_input)
                console.print(f"[bold magenta]💖 {self.supervisor.config.personality.name}:[/bold magenta] {reply}\n")

        finally:
            self.supervisor.stop()
