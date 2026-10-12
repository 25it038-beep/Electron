"""Electorn AI — Voice-Controlled Autonomous Automation Engine.

Launcher supporting GUI mode (PyQt6), Continuous Voice Loop, and CLI direct execution.
"""

from __future__ import annotations

import argparse
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("ElectornAI")


def run_gui() -> None:
    """Launch the full PyQt6 Obsidian Dark Cinematic Desktop GUI."""
    try:
        from PyQt6.QtWidgets import QApplication
        from ui.main_window import MainWindow

        app = QApplication(sys.argv)
        app.setApplicationName("Electorn AI")
        window = MainWindow()
        window.show()
        sys.exit(app.exec())
    except ImportError as e:
        logger.error(f"Failed to launch GUI: {e}")
        logger.info("Falling back to CLI mode...")
        run_cli()


def run_cli(command: str | None = None) -> None:
    """Launch direct CLI mode."""
    from agent.task_manager import TaskManager
    from agent.planner import TaskPlanner
    from agent.executor import TaskExecutor
    from providers.local_llm import OllamaLocalProvider
    from voice.text_to_speech import TextToSpeechEngine

    tts = TextToSpeechEngine()
    ollama = OllamaLocalProvider(auto_start=True)
    planner = TaskPlanner(llm_provider=ollama)
    executor = TaskExecutor()
    manager = TaskManager(planner=planner, executor=executor, tts=tts)

    if command:
        logger.info(f"Executing command: {command}")
        plan = manager.submit_command(command, async_exec=False)
        print(f"Task completed with status: {plan.status}")
        return

    print("=" * 60)
    print("⚡ ELECTORN AI — Autonomous Voice & OS Engine (CLI Mode)")
    print("Type a command or 'exit' to quit.")
    print("=" * 60)

    while True:
        try:
            cmd = input("\nElectorn > ").strip()
            if not cmd:
                continue
            if cmd.lower() in ("exit", "quit", "q"):
                break
            manager.submit_command(cmd, async_exec=False)
        except (KeyboardInterrupt, EOFError):
            break


def main() -> None:
    parser = argparse.ArgumentParser(description="Electorn AI Voice Automation Engine")
    parser.add_argument("--cli", action="store_true", help="Launch in CLI interactive mode")
    parser.add_argument("--exec", type=str, help="Execute a single command directly and exit")
    args = parser.parse_args()

    if args.exec:
        run_cli(command=args.exec)
    elif args.cli:
        run_cli()
    else:
        run_gui()


if __name__ == "__main__":
    main()
