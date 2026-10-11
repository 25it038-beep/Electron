"""Voice mode for Electorn AI: Speech-To-Text (hearing) & Text-To-Speech (speaking)."""

from __future__ import annotations

import io
import os
import sys
import threading
import time
import wave
from typing import Callable, Optional

try:
    import numpy as np
    import sounddevice as sd
    import speech_recognition as sr
    VOICE_DEPS_AVAILABLE = True
except Exception:
    VOICE_DEPS_AVAILABLE = False


class VoiceEngine:
    """Provides bidirectional voice interaction for Electorn AI."""

    def __init__(
        self,
        sample_rate: int = 16000,
        speech_speed: int = 1,
        voice_gender: str = "female",
    ):
        self.sample_rate = sample_rate
        self.speech_speed = speech_speed
        self.voice_gender = voice_gender.lower()
        self.recognizer = sr.Recognizer() if VOICE_DEPS_AVAILABLE else None
        self._tts_lock = threading.Lock()
        self._is_speaking = False

    def is_supported(self) -> bool:
        """Check if microphone capture and speech recognition are available."""
        return VOICE_DEPS_AVAILABLE

    def set_gender(self, gender: str) -> None:
        """Switch voice gender ('female' or 'male')."""
        if gender.lower() in ("female", "male"):
            self.voice_gender = gender.lower()

    def speak(self, text: str, async_mode: bool = False) -> None:
        """Speak out text response via native Windows SAPI TTS or cross-platform fallback."""
        if not text or not text.strip():
            return

        # Strip code blocks or backticks from spoken text to sound natural
        clean_text = self._sanitize_text_for_speech(text)
        if not clean_text:
            return

        def _tts_worker() -> None:
            with self._tts_lock:
                self._is_speaking = True
                try:
                    if sys.platform == "win32":
                        try:
                            import pythoncom
                            pythoncom.CoInitialize()
                        except Exception:
                            pass
                        import win32com.client
                        speaker = win32com.client.Dispatch("SAPI.SpVoice")
                        speaker.Rate = self.speech_speed  # Speed rate (-10 to 10)

                        # Configure voice based on preferred gender (default: female)
                        try:
                            voices = speaker.GetVoices()
                            selected_voice = None
                            for i in range(voices.Count):
                                v = voices.Item(i)
                                desc = v.GetDescription().lower()
                                try:
                                    g = v.GetAttribute("Gender").lower()
                                except Exception:
                                    g = ""

                                if self.voice_gender == "female":
                                    if g == "female" or any(n in desc for n in ["zira", "female", "hazel", "eva", "susan", "helen"]):
                                        selected_voice = v
                                        break
                                else:
                                    if g == "male" or any(n in desc for n in ["david", "male", "mark", "george"]):
                                        selected_voice = v
                                        break

                            if selected_voice is not None:
                                speaker.Voice = selected_voice
                        except Exception:
                            pass

                        speaker.Speak(clean_text)
                        try:
                            pythoncom.CoUninitialize()
                        except Exception:
                            pass
                    else:
                        import subprocess
                        import shutil
                        if shutil.which("say"):
                            # macOS voice selection
                            voice_opt = ["-v", "Samantha"] if self.voice_gender == "female" else ["-v", "Alex"]
                            subprocess.run(["say"] + voice_opt + [clean_text], check=False)
                        elif shutil.which("espeak"):
                            # Linux espeak female variant
                            voice_opt = ["-v", "en+f3"] if self.voice_gender == "female" else ["-v", "en+m3"]
                            subprocess.run(["espeak"] + voice_opt + [clean_text], check=False)
                except Exception:
                    pass
                finally:
                    self._is_speaking = False

        if async_mode:
            t = threading.Thread(target=_tts_worker, daemon=True)
            t.start()
        else:
            _tts_worker()

    def listen_and_transcribe(
        self,
        record_seconds: float = 5.0,
        status_cb: Optional[Callable[[str], None]] = None,
    ) -> Optional[str]:
        """Capture microphone audio and transcribe into text via SpeechRecognition."""
        if not VOICE_DEPS_AVAILABLE:
            raise RuntimeError("Voice dependencies (sounddevice, speech_recognition, numpy) not installed.")

        if status_cb:
            status_cb("🎙️ Listening... (Speak now)")

        try:
            # Record audio from default microphone using sounddevice
            recording = sd.rec(
                int(record_seconds * self.sample_rate),
                samplerate=self.sample_rate,
                channels=1,
                dtype="int16",
            )
            sd.wait()

            # Check if volume/energy exceeds silence threshold
            audio_data = recording.flatten()
            rms = np.sqrt(np.mean(audio_data.astype(float) ** 2))
            if rms < 100:  # Silence threshold
                return None

            if status_cb:
                status_cb("⚡ Transcribing audio...")

            # Convert numpy int16 array to WAV buffer in memory
            wav_buffer = io.BytesIO()
            with wave.open(wav_buffer, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)  # 16-bit
                wf.setframerate(self.sample_rate)
                wf.writeframes(recording.tobytes())
            wav_buffer.seek(0)

            # Transcribe via SpeechRecognition Google speech engine
            with sr.AudioFile(wav_buffer) as source:
                audio = self.recognizer.record(source)
                text = self.recognizer.recognize_google(audio)
                return text.strip() if text else None

        except sr.UnknownValueError:
            return None
        except sr.RequestError as req_err:
            if status_cb:
                status_cb(f"Speech service error: {req_err}")
            return None
        except Exception as err:
            if status_cb:
                status_cb(f"Mic capture error: {err}")
            return None

    @staticmethod
    def _sanitize_text_for_speech(text: str) -> str:
        """Remove long code blocks and special markup so speech sounds conversational."""
        import re
        # Remove URLs
        cleaned = re.sub(r"https?://\S+", "link on screen", text)
        # Remove triple backtick blocks
        cleaned = re.sub(r"```[\s\S]*?```", "Here is the code implementation displayed on your screen.", cleaned)
        # Remove markdown symbols
        cleaned = re.sub(r"[*_#`>]", "", cleaned)
        # Limit spoken length if response is an essay
        sentences = [s.strip() for s in cleaned.split(".") if s.strip()]
        if len(sentences) > 4:
            cleaned = ". ".join(sentences[:4]) + ". The full details are displayed on your screen."
        return cleaned.strip()
