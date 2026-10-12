"""Speech-to-Text transcription with interchangeable engines and modes."""

from __future__ import annotations

import io
from typing import Callable, Optional

try:
    import speech_recognition as sr
    SR_AVAILABLE = True
except Exception:
    SR_AVAILABLE = False

from voice.microphone import MicrophoneManager
from voice.voice_activity import VoiceActivityDetector


class SpeechToTextEngine:
    """Handles audio transcription in both push-to-talk and continuous listening modes."""

    def __init__(
        self,
        mic_manager: Optional[MicrophoneManager] = None,
        vad: Optional[VoiceActivityDetector] = None,
        language: str = "en-US",
    ) -> None:
        self.mic = mic_manager or MicrophoneManager()
        self.vad = vad or VoiceActivityDetector()
        self.language = language
        self.recognizer = sr.Recognizer() if SR_AVAILABLE else None

    def is_available(self) -> bool:
        """Check if STT dependencies are installed."""
        return SR_AVAILABLE

    def transcribe_wav_bytes(self, wav_bytes: bytes) -> Optional[str]:
        """Transcribe in-memory WAV audio bytes to text."""
        if not self.is_available() or not wav_bytes:
            return None

        # Check VAD first to skip processing silence
        if not self.vad.is_speech(wav_bytes):
            return None

        try:
            buf = io.BytesIO(wav_bytes)
            with sr.AudioFile(buf) as source:
                audio = self.recognizer.record(source)
                text = self.recognizer.recognize_google(audio, language=self.language)
                return text.strip() if text else None
        except sr.UnknownValueError:
            return None
        except sr.RequestError:
            return None
        except Exception:
            return None

    def listen_and_transcribe(
        self,
        duration_sec: float = 4.0,
        status_cb: Optional[Callable[[str], None]] = None,
    ) -> Optional[str]:
        """Record from mic and transcribe. Returns text string or None if silence."""
        if status_cb:
            status_cb("Listening...")

        wav_bytes, energy = self.mic.record_chunk(duration_sec=duration_sec)
        if not wav_bytes:
            return None

        if status_cb and energy > self.vad.silence_threshold:
            status_cb("Transcribing...")

        return self.transcribe_wav_bytes(wav_bytes)
