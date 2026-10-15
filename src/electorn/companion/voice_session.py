"""Continuous voice session engine with barge-in interruption support."""

from __future__ import annotations

import io
import logging
import threading
import time
from typing import Callable, Optional

from electorn.voice import VoiceEngine, VOICE_DEPS_AVAILABLE

try:
    import numpy as np
    import sounddevice as sd
except Exception:
    pass

logger = logging.getLogger(__name__)


class CompanionVoiceSession:
    """Manages persistent voice listening, continuous turn-taking, and instant speech interruption."""

    def __init__(
        self,
        voice_engine: Optional[VoiceEngine] = None,
        language: str = "en-US",
        voice_gender: str = "female",
        speech_speed: float = 1.0,
        barge_in_enabled: bool = True,
    ) -> None:
        self.engine = voice_engine or VoiceEngine(
            language=language,
            voice_gender=voice_gender,
            speech_speed=int(speech_speed),
        )
        self.language = language
        self.voice_gender = voice_gender
        self.barge_in_enabled = barge_in_enabled
        self.is_running = False
        self._is_speaking = False
        self._interrupted_event = threading.Event()
        self._speech_thread: Optional[threading.Thread] = None

    def interrupt_speech(self) -> None:
        """Instantly stop companion speech playback when the user interrupts."""
        if self._is_speaking:
            self._interrupted_event.set()
            try:
                if VOICE_DEPS_AVAILABLE:
                    sd.stop()
            except Exception as e:
                logger.debug("Failed to stop sounddevice audio: %s", e)
            self._is_speaking = False

    def is_speaking(self) -> bool:
        """Check if companion is actively talking."""
        return self._is_speaking

    def speak(
        self,
        text: str,
        on_start_cb: Optional[Callable[[], None]] = None,
        on_finish_cb: Optional[Callable[[], None]] = None,
        language_override: Optional[str] = None,
    ) -> None:
        """Speak out text with barge-in support."""
        if not text or not text.strip():
            return

        self.interrupt_speech()
        self._interrupted_event.clear()
        self._is_speaking = True

        if on_start_cb:
            on_start_cb()

        try:
            target_lang = language_override or self.language
            # Synthesize & play through engine
            self.engine.speak(text, async_mode=False, language_override=target_lang)
        except Exception as e:
            logger.debug("Voice output error: %s", e)
        finally:
            self._is_speaking = False
            if on_finish_cb:
                on_finish_cb()

    def speak_async(
        self,
        text: str,
        on_start_cb: Optional[Callable[[], None]] = None,
        on_finish_cb: Optional[Callable[[], None]] = None,
        language_override: Optional[str] = None,
    ) -> None:
        """Non-blocking speech invocation."""
        t = threading.Thread(
            target=self.speak,
            args=(text, on_start_cb, on_finish_cb, language_override),
            daemon=True,
        )
        self._speech_thread = t
        t.start()

    def listen_for_user(
        self,
        timeout_seconds: float = 5.0,
        status_cb: Optional[Callable[[str], None]] = None,
        language_override: Optional[str] = None,
    ) -> Optional[str]:
        """Listen to the microphone and return transcribed text."""
        if not self.engine.is_supported():
            return None

        # Check for interrupt during user speech
        if self._is_speaking and self.barge_in_enabled:
            self.interrupt_speech()

        target_lang = language_override or self.language
        return self.engine.listen_and_transcribe(
            record_seconds=timeout_seconds,
            status_cb=status_cb,
            language_override=target_lang,
        )
