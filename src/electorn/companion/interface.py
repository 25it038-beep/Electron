"""Interactive Rich terminal dashboard and live voice/screen runner for Companion Mode."""

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
    """Rich terminal user interface and interactive live voice/screen session for Companion Mode."""

    def __init__(self, supervisor: CompanionSupervisor) -> None:
        self.supervisor = supervisor
        self.messages: List[tuple[str, str]] = []
        self._running = False
        self.time_engine = TimeAwarenessEngine()

        # Wire up supervisor callbacks
        self.supervisor.on_message_cb = self._add_message

    def _add_message(self, speaker: str, content: str) -> None:
        """Append a dialogue entry to the active chat log and render to console if session is active."""
        self.messages.append((speaker, content))
        if len(self.messages) > 100:
            self.messages = self.messages[-100:]
        if self._running:
            if speaker == self.supervisor.config.personality.name:
                console.print(f"\n[bold magenta]💖 {speaker}:[/bold magenta] {content}\n")
            else:
                console.print(f"\n[bold cyan]👤 {speaker}:[/bold cyan] {content}\n")

    def build_dashboard(self) -> Panel:
        """Construct the Rich visual dashboard layout."""
        state = self.supervisor.state
        config = self.supervisor.config

        # Status indicators
        mic_status = "🔴 MUTED" if state.is_muted else ("🟢 LIVE LISTENING" if state.mic_active and not state.is_paused else "⚪ OFF")
        screen_status = "🟢 LIVE MONITORING" if config.screen.enabled and state.screen_active and not state.is_paused else "⚪ OFF"
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

        obs_text = state.active_window_title or "Inspecting desktop workspace..."
        if len(obs_text) > 60:
            obs_text = obs_text[:57] + "..."

        table_panel = Panel(
            status_table,
            title=f"💖 {config.personality.name} Live Companion • Active Window: {obs_text}",
            border_style=mode_style,
        )
        return table_panel

    def display_recent_conversation(self) -> None:
        """Render recent conversational exchanges."""
        if not self.messages:
            return

        for speaker, text in self.messages[-5:]:
            if speaker == self.supervisor.config.personality.name:
                console.print(f"[bold magenta]💖 {speaker}:[/bold magenta] {text}")
            else:
                console.print(f"[bold green]👤 {speaker}:[/bold green] {text}")

    def run_interactive_session(self) -> None:
        """Start the live companion interaction loop with hands-free voice and live screen access."""
        # Ensure live screen is enabled
        self.supervisor.config.screen.enabled = True
        self.supervisor.screen_observer.config.enabled = True
        self.supervisor.state.interactive_session_active = True
        self.supervisor.start()

        console.clear()
        console.print(Panel(
            f"[bold magenta]⚡ ELECTORN COMPANION MODE[/bold magenta] — Persistent Voice & Screen-Aware AI (Aria)\n"
            f"[dim]Addressing: [bold]{self.supervisor.config.personality.user_name}[/bold] | Live Screen: [bold green]ACTIVE[/bold green] | Live Voice: [bold green]ACTIVE[/bold green]\n"
            f"Voice: Speak naturally into your mic at any time. Press [bold]T[/bold] to type, [bold]M[/bold] to mute, [bold]Q[/bold] to quit.[/dim]",
            border_style="magenta",
        ))

        # Initial live screen capture
        try:
            img, report = self.supervisor.screen_observer.capture_screen()
            if img:
                analyzed = self.supervisor.vision_analyzer.analyze(img, report)
                self.supervisor.latest_report = analyzed
        except Exception:
            pass

        console.print(self.build_dashboard())
        self._running = True

        # Initial greeting aloud
        greeting = self.supervisor.personality.generate_greeting()
        self._add_message(self.supervisor.config.personality.name, greeting)

        if self.supervisor.config.voice_enabled and not self.supervisor.state.is_muted and self.supervisor.state.active_mode != CompanionMode.PRIVACY:
            self.supervisor.voice.speak_async(greeting)

        try:
            while self._running:
                # Check for keyboard hit on Windows without blocking
                user_typed = None
                if sys.platform == "win32":
                    try:
                        import msvcrt
                        if msvcrt.kbhit():
                            ch = msvcrt.getch()
                            if ch in (b'q', b'Q', b'\x1b'):
                                console.print(f"\n[yellow]Shutting down Companion session. Goodbye {self.supervisor.config.personality.user_name}![/yellow]")
                                break
                            elif ch in (b'm', b'M'):
                                is_mut = self.supervisor.voice.toggle_mute()
                                self.supervisor.state.is_muted = is_mut
                                status_txt = "MUTED" if is_mut else "UNMUTED"
                                console.print(f"\n[yellow]Microphone {status_txt}.[/yellow]\n")
                                continue
                            elif ch in (b'p', b'P'):
                                if self.supervisor.state.is_paused:
                                    self.supervisor.resume()
                                    console.print("\n[green]▶️ Companion resumed.[/green]\n")
                                else:
                                    self.supervisor.pause()
                                    console.print("\n[yellow]⏸️ Companion paused.[/yellow]\n")
                                continue
                            elif ch in (b't', b'T', b'\r'):
                                user_typed = Prompt.ask("\n[bold cyan]Type message or command[/bold cyan]").strip()
                    except Exception:
                        pass

                # If user typed a command
                if user_typed:
                    if not self._handle_text_input(user_typed):
                        break
                    continue

                # Live Voice Listening Turn
                if (
                    self.supervisor.config.voice_enabled
                    and not self.supervisor.state.is_muted
                    and self.supervisor.state.active_mode != CompanionMode.PRIVACY
                    and not self.supervisor.state.is_paused
                ):
                    def status_update(msg: str) -> None:
                        if "Transcribing" in msg:
                            console.print(f"[dim cyan]{msg}[/dim cyan]", end="\r")

                    # Live mic recording
                    voice_text = self.supervisor.voice.listen_for_user(
                        timeout_seconds=3.5,
                        status_cb=status_update,
                    )

                    if voice_text and voice_text.strip():
                        console.print(f"\n[bold cyan]👤 {self.supervisor.config.personality.user_name} (Voice)[/bold cyan] ❯ [white]{voice_text}[/white]")
                        self._add_message(self.supervisor.config.personality.user_name, voice_text)

                        # Check for exit command
                        if any(term in voice_text.lower() for term in ["exit", "quit", "goodbye", "bye bye", "stop companion"]):
                            console.print(f"\n[yellow]Goodbye {self.supervisor.config.personality.user_name}! Have a great rest of your day.[/yellow]")
                            break

                        console.print("[dim]Thinking...[/dim]")
                        reply = self.supervisor.process_user_input(voice_text)
                        console.print(f"[bold magenta]💖 {self.supervisor.config.personality.name}:[/bold magenta] {reply}\n")
                    else:
                        # User is quiet: evaluate autonomous conversation check-ins
                        self.supervisor.check_and_trigger_proactive()
                        time.sleep(0.1)
                else:
                    # In privacy or muted mode, fall back to typed prompt
                    typed = Prompt.ask("\n[bold cyan]Type message (or /help, /exit)[/bold cyan]").strip()
                    if typed:
                        if not self._handle_text_input(typed):
                            break

        finally:
            self.supervisor.state.interactive_session_active = False
            self.supervisor.stop()

    def _handle_text_input(self, user_input: str) -> bool:
        """Handle typed slash commands and text chats. Returns False to exit session."""
        lower = user_input.lower()
        if lower in ("/exit", "/quit", "exit", "quit", "q"):
            console.print(f"\n[yellow]Shutting down Companion session. Goodbye {self.supervisor.config.personality.user_name}![/yellow]")
            return False

        if lower in ("/pause", "pause"):
            self.supervisor.pause()
            console.print("[yellow]⏸️ Companion paused.[/yellow]\n")
            return True

        if lower in ("/resume", "resume"):
            self.supervisor.resume()
            console.print("[green]▶️ Companion resumed.[/green]\n")
            return True

        if lower in ("/mute", "mute"):
            self.supervisor.mute()
            console.print("[red]🔇 Microphone muted.[/red]\n")
            return True

        if lower in ("/unmute", "unmute"):
            self.supervisor.unmute()
            console.print("[green]🎙️ Microphone unmuted.[/green]\n")
            return True

        if lower in ("/focus", "focus"):
            self.supervisor.set_mode(CompanionMode.FOCUS)
            console.print("[blue]Switched to Focus Mode.[/blue]\n")
            return True

        if lower in ("/study", "study"):
            self.supervisor.set_mode(CompanionMode.STUDY)
            console.print("[green]Switched to Study Mode.[/green]\n")
            return True

        if lower in ("/night", "night"):
            self.supervisor.set_mode(CompanionMode.NIGHT)
            console.print("[purple]Switched to Night Mode.[/purple]\n")
            return True

        if lower in ("/companion", "companion"):
            self.supervisor.set_mode(CompanionMode.COMPANION)
            console.print("[magenta]Switched to Companion Mode.[/magenta]\n")
            return True

        if lower in ("/privacy", "privacy"):
            self.supervisor.set_mode(CompanionMode.PRIVACY)
            console.print("[red]Switched to Privacy Mode (Mic and screen disabled).[/red]\n")
            return True

        if lower in ("/snooze", "snooze"):
            self.supervisor.time_engine.snooze(self.supervisor.config.bedtime, minutes=30)
            console.print("[yellow]Bedtime reminder snoozed for 30 minutes.[/yellow]\n")
            return True

        if lower in ("/screen", "screen"):
            self.supervisor.config.screen.enabled = not self.supervisor.config.screen.enabled
            self.supervisor.screen_observer.config.enabled = self.supervisor.config.screen.enabled
            status = "ENABLED" if self.supervisor.config.screen.enabled else "DISABLED"
            console.print(f"[cyan]Screen observation {status}.[/cyan]\n")
            return True

        # Process message
        self._add_message(self.supervisor.config.personality.user_name, user_input)
        console.print("[dim]Thinking...[/dim]")
        reply = self.supervisor.process_user_input(user_input)
        console.print(f"[bold magenta]💖 {self.supervisor.config.personality.name}:[/bold magenta] {reply}\n")
        return True
