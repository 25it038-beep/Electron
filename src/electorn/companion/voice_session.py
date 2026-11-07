"""Natural Voice Conversation Engine with Adaptive VAD and Turn Management for Aria.

Supports uninterrupted human-like conversations, adaptive pause detection,
sentence continuation tracking, bilingual Tamil-English processing,
echo cancellation, and seamless user barge-in.
"""
from __future__ import annotations

import io
import logging
import threading
import time
import wave
from typing import Callable, Dict, List, Optional, Tuple

from electorn.voice import VoiceEngine, VOICE_DEPS_AVAILABLE
from electorn.companion.voice_vad import AdaptiveVAD, AdaptiveVADConfig, AudioFrameCategory, PauseType
from electorn.companion.sentence_completer import SentenceCompleter
from electorn.companion.conversational_turn import ConversationalTurnManager, TurnState

try:
    import numpy as np
    import sounddevice as sd
    import speech_recognition as sr
except Exception:
    pass

logger = logging.getLogger(__name__)


class CompanionVoiceSession:
    """Manages natural conversational turn-taking, adaptive VAD, and uninterrupted speech."""

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
        self._is_muted = False
        self._continuous_listening = False
        self._interrupted_event = threading.Event()
        self._speech_thread: Optional[threading.Thread] = None

        # Natural Conversation Subsystems
        self.vad_config = AdaptiveVADConfig(
            sample_rate=self.engine.sample_rate if hasattr(self.engine, "sample_rate") else 16000,
            frame_duration_ms=100,
            short_pause_sec=1.5,
            thinking_pause_sec=3.0,
            continuation_window_sec=5.0,
            extended_pause_sec=8.5,
            max_utterance_sec=60.0,
        )
        self.vad = AdaptiveVAD(self.vad_config)
        self.completer = SentenceCompleter()
        self.turn_manager = ConversationalTurnManager(
            completer=self.completer,
            on_state_change=self._on_turn_state_change,
        )
        self.on_state_change_cb: Optional[Callable[[TurnState, str], None]] = None
        self.on_partial_transcript_cb: Optional[Callable[[str], None]] = None

    def _on_turn_state_change(self, state: TurnState, details: str) -> None:
        """Propagate state change to external listener."""
        if self.on_state_change_cb:
            try:
                self.on_state_change_cb(state, details)
            except Exception:
                pass

    # =========================================================================
    # MUTE & CONTINUOUS LISTENING CONTROLS
    # =========================================================================

    def mute(self) -> None:
        """Immediately mute microphone and halt active speech."""
        self._is_muted = True
        self.interrupt_speech()

    def unmute(self) -> None:
        """Unmute microphone."""
        self._is_muted = False

    def toggle_mute(self) -> bool:
        """Toggle mute state. Returns new state."""
        self._is_muted = not self._is_muted
        if self._is_muted:
            self.interrupt_speech()
        return self._is_muted

    def is_muted(self) -> bool:
        """Check if voice session is currently muted."""
        return self._is_muted

    def enable_continuous_listening(self) -> None:
        """Enable continuous background listening mode."""
        self._continuous_listening = True

    def disable_continuous_listening(self) -> None:
        """Disable continuous listening mode."""
        self._continuous_listening = False

    def toggle_continuous_listening(self) -> bool:
        """Toggle continuous listening mode. Returns new state."""
        self._continuous_listening = not self._continuous_listening
        return self._continuous_listening

    def is_continuous_listening(self) -> bool:
        """Check if continuous listening is enabled."""
        return self._continuous_listening

    # =========================================================================
    # SPEECH PLAYBACK & BARGE-IN INTERRUPTION
    # =========================================================================

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
        if not text or not text.strip() or self._is_muted:
            return

        self.interrupt_speech()
        self._interrupted_event.clear()
        self._is_speaking = True
        self.turn_manager.mark_responding()

        if on_start_cb:
            on_start_cb()

        try:
            target_lang = language_override or self.language
            self.engine.speak(text, async_mode=False, language_override=target_lang)
        except Exception as e:
            logger.debug("Voice output error: %s", e)
        finally:
            self._is_speaking = False
            self.turn_manager.mark_ready_for_next_turn()
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
        if self._is_muted:
            return

        t = threading.Thread(
            target=self.speak,
            args=(text, on_start_cb, on_finish_cb, language_override),
            daemon=True,
        )
        self._speech_thread = t
        t.start()

    def wait_for_speech(self, timeout: float = 30.0, poll_interval: float = 0.05) -> bool:
        """Wait until active speech playback finishes or timeout is reached."""
        start = time.time()
        while self._is_speaking and (time.time() - start < timeout):
            time.sleep(poll_interval)
        return not self._is_speaking

    # =========================================================================
    # NATURAL ADAPTIVE LISTENING WITH THINKING PAUSE PRESERVATION
    # =========================================================================

    def listen_for_user(
        self,
        timeout_seconds: float = 5.0,
        status_cb: Optional[Callable[[str], None]] = None,
        language_override: Optional[str] = None,
    ) -> Optional[str]:
        """Listen to the microphone with adaptive pause detection and sentence completion tracking.

        Allows natural pauses (1-4s), breathing, and thinking without prematurely cutting the user off.
        Stitches multi-segment utterances together before returning complete instruction.
        """
        if self._is_muted or not self.engine.is_supported():
            return None

        # If Aria is speaking and barge-in is enabled, check for user speech
        if self._is_speaking:
            if not self.barge_in_enabled:
                self.wait_for_speech(timeout=30.0)
            else:
                # Small pause to allow barge-in to trigger naturally
                pass

        target_lang = language_override or self.language
        lang_label = "தமிழ் (Tamil)" if target_lang == "ta-IN" else "English"

        self.vad.reset()
        self.turn_manager.start_turn()

        if status_cb:
            status_cb(f"🎙️ Listening in {lang_label}... (Speak naturally)")

        chunk_duration_sec = 0.25  # 250ms chunks for responsive streaming VAD
        sample_rate = self.vad_config.sample_rate
        chunk_samples = int(chunk_duration_sec * sample_rate)

        start_time = time.time()
        last_transcribed_len = 0
        transcript_accumulated = ""

        try:
            while True:
                # 1. Check overall turn duration
                now = time.time()
                if not self.vad.is_speech_active and (now - start_time > timeout_seconds):
                    # No speech detected within initial listening timeout
                    return None

                if self.vad.is_max_duration_exceeded():
                    # Utterance hit 60s hard limit, transcribe whatever was spoken
                    break

                # 2. Record one audio chunk via sounddevice
                try:
                    chunk = sd.rec(
                        chunk_samples,
                        samplerate=sample_rate,
                        channels=1,
                        dtype="int16",
                    )
                    sd.wait()
                    audio_chunk = chunk.flatten()
                except Exception as rec_err:
                    logger.debug("Microphone chunk capture error: %s", rec_err)
                    time.sleep(0.1)
                    continue

                # 3. Handle Barge-In: If Aria is speaking and user speaks with high energy
                if self._is_speaking and self.barge_in_enabled:
                    rms = float(np.sqrt(np.mean(audio_chunk.astype(float) ** 2)))
                    if rms > max(250.0, self.vad.noise_floor * 2.5):
                        # Strong speech detected while Aria was speaking -> user interrupt!
                        self.interrupt_speech()
                        if status_cb:
                            status_cb("🛑 User interrupted Aria — listening to you now...")
                        self.vad.reset()
                        self.turn_manager.start_turn()
                        start_time = time.time()
                        continue
                    else:
                        # Echo gating: ignore speaker audio during playback
                        continue

                # 4. Feed audio chunk into Adaptive VAD
                category, energy = self.vad.process_frame(audio_chunk)

                if category == AudioFrameCategory.SPEECH:
                    if status_cb:
                        if transcript_accumulated:
                            status_cb(f"🎙️ Listening... '{transcript_accumulated}'")
                        else:
                            status_cb("🎙️ Listening... (Voice active)")

                # 5. When speech has been observed and a pause occurs
                if self.vad.has_buffered_speech():
                    silence_dur = self.vad.get_silence_duration()
                    pause_type = self.vad.get_current_pause_type()

                    # Transcribe current audio buffer periodically during pauses
                    current_buffer_len = len(self.vad._audio_buffer)
                    if silence_dur >= self.vad_config.short_pause_sec and current_buffer_len > last_transcribed_len:
                        if status_cb:
                            status_cb("⚡ Transcribing speech...")

                        raw_bytes = self.vad.get_buffered_audio_bytes()
                        chunk_text = self._transcribe_audio_bytes(raw_bytes, target_lang)

                        if chunk_text:
                            transcript_accumulated = chunk_text
                            self.turn_manager.accumulated_transcript = chunk_text
                            last_transcribed_len = current_buffer_len

                            if self.on_partial_transcript_cb:
                                self.on_partial_transcript_cb(chunk_text)

                    # 6. Evaluate sentence completeness against silence duration
                    if transcript_accumulated:
                        is_complete, reassurance = self.turn_manager.evaluate_pause(silence_dur)

                        if reassurance and status_cb:
                            status_cb(f"💭 Aria: '{reassurance}'")

                        if is_complete:
                            # Sentence is syntactically complete AND user paused long enough (>=1.5s)
                            break
                        else:
                            # Sentence is incomplete (e.g. ends with "and...", "create a...", etc.)
                            if silence_dur > self.vad_config.extended_pause_sec:
                                # User stopped completely even though incomplete clause; accept it
                                break
                            elif silence_dur >= self.vad_config.thinking_pause_sec and status_cb:
                                status_cb(f"💭 Thinking pause ({silence_dur:.1f}s)... waiting for you to continue...")

        except Exception as e:
            logger.debug("Natural voice loop exception: %s", e)

        # 7. Finalize turn
        final_text = self.turn_manager.finalize_turn()
        if not final_text and self.vad.has_buffered_speech():
            raw_bytes = self.vad.get_buffered_audio_bytes()
            final_text = self._transcribe_audio_bytes(raw_bytes, target_lang) or ""

        return final_text.strip() if final_text and final_text.strip() else None

    # =========================================================================
    # AUDIO BYTE BUFFER TRANSCRIPTION HELPER
    # =========================================================================

    def _transcribe_audio_bytes(self, audio_bytes: bytes, target_lang: str) -> Optional[str]:
        """Convert raw PCM 16-bit audio bytes to WAV and transcribe via SpeechRecognition."""
        if not audio_bytes or len(audio_bytes) < 3200:  # < 100ms
            return None

        wav_buf = io.BytesIO()
        with wave.open(wav_buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(self.vad_config.sample_rate)
            wf.writeframes(audio_bytes)
        wav_buf.seek(0)

        try:
            with sr.AudioFile(wav_buf) as source:
                audio = self.engine.recognizer.record(source)
                try:
                    text = self.engine.recognizer.recognize_google(audio, language=target_lang)
                    return text.strip() if text else None
                except sr.UnknownValueError:
                    # Bilingual fallback: if Tamil failed, try English
                    if target_lang == "ta-IN":
                        try:
                            text = self.engine.recognizer.recognize_google(audio, language="en-US")
                            return text.strip() if text else None
                        except Exception:
                            return None
                    return None
        except Exception as e:
            logger.debug("Transcription error on buffer: %s", e)
            return None
