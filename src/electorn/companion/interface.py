"""Interactive Rich terminal dashboard and session runner for Companion Mode."""

from __future__ import annotations

import sys
import threading
import time
from typing import List, Optional

from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich.text import Text

from electorn.companion.schema import CompanionMode, CompanionState
from electorn.companion.supervisor import CompanionSupervisor

console = Console(legacy_windows=False)


class CompanionInterface:
    """Rich terminal user interface and interactive conversation loop for Companion Mode."""

    def __init__(self, supervisor: CompanionSupervisor) -> None:
        self.supervisor = supervisor
        self.messages: List[tuple[str, str]] = []
        self._running = False

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
        mic_status = "🟢 ACTIVE" if state.mic_active and not state.is_paused else "⚪ MUTED"
        screen_status = "🟢 ACTIVE" if config.screen.enabled and state.screen_active and not state.is_paused else "⚪ OFF"
        barge_in = "🟢 ON" if config.barge_in_enabled else "⚪ OFF"
        paused_status = "⏸️ PAUSED" if state.is_paused else "▶️ RUNNING"

        # Active Mode formatting
        mode_colors = {
            CompanionMode.PASSIVE: "yellow",
            CompanionMode.COMPANION: "magenta",
            CompanionMode.FOCUS: "blue",
            CompanionMode.WORK_ASSISTANT: "cyan",
            CompanionMode.PRIVACY: "red",
        }
        mode_style = mode_colors.get(state.active_mode, "white")

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
            "Addressing:", f"[cyan]{config.personality.preferred_address}[/cyan]",
            "Status:", f"[bold]{paused_status}[/bold]",
        )
        status_table.add_row(
            "Voice Engine:", mic_status,
            "Screen Vision:", screen_status,
        )
        status_table.add_row(
            "Barge-In:", barge_in,
            "Proactive Today:", f"{state.proactive_messages_today}/{config.personality.proactive_daily_limit}",
        )

        obs_text = state.active_window_title or "No active window inspected yet"
        if len(obs_text) > 65:
            obs_text = obs_text[:62] + "..."

        content = Text()
        content.append(f"💖 {config.personality.name} Companion Dashboard\n", style="bold magenta")
        content.append(f"Window: [dim]{obs_text}[/dim]\n\n")

        table_panel = Panel(status_table, title="Session Controls", border_style=mode_style)
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
            "[bold magenta]⚡ ELECTORN COMPANION MODE[/bold magenta] — Voice-Enabled Screen-Aware AI Girlfriend (Aria)\n"
            "[dim]Commands: [bold]/focus[/bold], [bold]/companion[/bold], [bold]/privacy[/bold], [bold]/work[/bold], "
            "[bold]/screen[/bold], [bold]/pause[/bold], [bold]/resume[/bold], [bold]/exit[/bold][/dim]",
            border_style="magenta",
        ))

        # Initial greeting
        greeting = self.supervisor.personality.generate_greeting()
        self._add_message(self.supervisor.config.personality.name, greeting)
        console.print(f"\n[bold magenta]💖 {self.supervisor.config.personality.name}:[/bold magenta] {greeting}\n")

        if self.supervisor.config.voice_enabled and self.supervisor.state.active_mode != CompanionMode.PRIVACY:
            self.supervisor.voice.speak_async(greeting)

        try:
            while self._running:
                console.print(self.build_dashboard())
                self.display_recent_conversation()

                user_input = Prompt.ask("\n[bold cyan]Speak or type (or /help)[/bold cyan]").strip()
                if not user_input:
                    continue

                # Hotkeys & Slash command shortcuts
                lower = user_input.lower()
                if lower in ("/exit", "/quit", "exit", "quit", "q"):
                    console.print("\n[yellow]Shutting down Companion session. Goodbye darling![/yellow]")
                    break

                if lower in ("/pause", "pause"):
                    self.supervisor.pause()
                    console.print("[yellow]⏸️ Companion paused.[/yellow]\n")
                    continue

                if lower in ("/resume", "resume"):
                    self.supervisor.resume()
                    console.print("[green]▶️ Companion resumed.[/green]\n")
                    continue

                if lower in ("/focus", "focus"):
                    self.supervisor.set_mode(CompanionMode.FOCUS)
                    console.print("[blue]Switched to Focus Mode.[/blue]\n")
                    continue

                if lower in ("/companion", "companion"):
                    self.supervisor.set_mode(CompanionMode.COMPANION)
                    console.print("[magenta]Switched to Companion Mode.[/magenta]\n")
                    continue

                if lower in ("/privacy", "privacy"):
                    self.supervisor.set_mode(CompanionMode.PRIVACY)
                    console.print("[red]Switched to Privacy Mode (Mic and screen disabled).[/red]\n")
                    continue

                if lower in ("/work", "work"):
                    self.supervisor.set_mode(CompanionMode.WORK_ASSISTANT)
                    console.print("[cyan]Switched to Work Assistant Mode.[/cyan]\n")
                    continue

                if lower in ("/screen", "screen"):
                    self.supervisor.config.screen.enabled = not self.supervisor.config.screen.enabled
                    self.supervisor.screen_observer.config.enabled = self.supervisor.config.screen.enabled
                    status = "ENABLED" if self.supervisor.config.screen.enabled else "DISABLED"
                    console.print(f"[cyan]Screen observation {status}.[/cyan]\n")
                    continue

                # Process user message
                self._add_message(self.supervisor.config.personality.user_name, user_input)
                console.print(f"[dim]Processing...[/dim]")
                reply = self.supervisor.process_user_input(user_input)
                console.print(f"[bold magenta]💖 {self.supervisor.config.personality.name}:[/bold magenta] {reply}\n")

        finally:
            self.supervisor.stop()
