"""Audio playback utility for Electorn AI intro and theme music."""

from __future__ import annotations

import os
import sys
import threading
import time
from pathlib import Path


def get_intro_audio_path() -> Path:
    """Resolve the path to the bundled intro audio file."""
    # First priority: bundled asset inside electorn package
    pkg_asset = Path(__file__).parent / "assets" / "intro.mp3"
    if pkg_asset.is_file():
        return pkg_asset

    # Second priority: user downloads fallback
    user_download = Path.home() / "Downloads" / "atc_around_the_world.mp3"
    if user_download.is_file():
        return user_download

    return pkg_asset


def play_intro_audio(duration: float = 6.0, async_mode: bool = True) -> None:
    """Play intro music (ATC - Around the World) safely on Windows using native MCI.
    
    Plays asynchronously in the background so it never freezes the CLI or startup flow.
    Automatically fades/stops after `duration` seconds.
    """
    audio_path = get_intro_audio_path()
    if not audio_path.is_file():
        return

    def _play_worker() -> None:
        try:
            if sys.platform == "win32":
                import ctypes
                mci = ctypes.windll.winmm.mciSendStringW
                alias = f"electorn_intro_{int(time.time() * 1000)}"
                abs_path = str(audio_path.resolve())
                
                # Open audio using Windows Media Control Interface (MCI)
                open_cmd = f'open "{abs_path}" type mpegvideo alias {alias}'
                res = mci(open_cmd, None, 0, None)
                if res == 0:
                    mci(f"play {alias}", None, 0, None)
                    # Play for requested duration
                    time.sleep(duration)
                    mci(f"stop {alias}", None, 0, None)
                    mci(f"close {alias}", None, 0, None)
            else:
                # Linux/macOS fallback using available command line players if present
                import shutil
                import subprocess
                for player in ["afplay", "mpg123", "mpv", "ffplay", "cvlc"]:
                    if shutil.which(player):
                        proc = subprocess.Popen([player, str(audio_path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        time.sleep(duration)
                        proc.terminate()
                        break
        except Exception:
            # Silent fallback: never crash CLI if audio devices are unavailable
            pass

    if async_mode:
        t = threading.Thread(target=_play_worker, daemon=True)
        t.start()
    else:
        _play_worker()
