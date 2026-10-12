"""Voice mode for Electorn AI: Speech-To-Text (hearing) & Modern Neural Text-To-Speech (speaking)."""

from __future__ import annotations

import asyncio
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

try:
    import edge_tts
    import soundfile as sf
    NEURAL_VOICE_AVAILABLE = True
except Exception:
    NEURAL_VOICE_AVAILABLE = False


class VoiceEngine:
    """Provides bidirectional voice interaction for Electorn AI using recent neural voice models."""

    # Recent neural models (Edge TTS)
    NEURAL_MODELS = {
        "female": "en-US-AvaNeural",      # High-fidelity natural female neural voice
        "male": "en-US-AndrewNeural",     # High-fidelity natural male neural voice
    }

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

    def is_neural_supported(self) -> bool:
        """Check if Edge TTS neural voice is available."""
        return NEURAL_VOICE_AVAILABLE

    def set_gender(self, gender: str) -> None:
        """Switch voice gender ('female' or 'male')."""
        if gender.lower() in ("female", "male"):
            self.voice_gender = gender.lower()

    def get_active_model_name(self) -> str:
        """Return the name of the active voice model."""
        if NEURAL_VOICE_AVAILABLE:
            return self.NEURAL_MODELS.get(self.voice_gender, "en-US-AvaNeural")
        if sys.platform == "win32":
            return "Microsoft Zira (SAPI)" if self.voice_gender == "female" else "Microsoft David (SAPI)"
        return "System TTS"

    def speak(self, text: str, async_mode: bool = False) -> None:
        """Speak out text response via modern neural voice or native SAPI/OS fallback."""
        if not text or not text.strip():
            return

        # Strip code blocks or backticks from spoken text to sound natural
        clean_text = self._sanitize_text_for_speech(text)
        if not clean_text:
            return

        def _tts_worker() -> None:
            with self._tts_lock:
                self._is_speaking = True
                success = False

                # 1. Try Recent Neural Voice Model (Edge TTS)
                if NEURAL_VOICE_AVAILABLE:
                    try:
                        voice_model = self.NEURAL_MODELS.get(self.voice_gender, "en-US-AvaNeural")
                        # Run edge-tts stream asynchronously
                        audio_buffer = io.BytesIO()

                        async def _stream_tts() -> None:
                            communicate = edge_tts.Communicate(clean_text, voice_model)
                            async for chunk in communicate.stream():
                                if chunk["type"] == "audio":
                                    audio_buffer.write(chunk["data"])

                        # Run event loop for edge-tts
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        try:
                            loop.run_until_complete(_stream_tts())
                        finally:
                            loop.close()

                        audio_buffer.seek(0)
                        if audio_buffer.getbuffer().nbytes > 0:
                            data, fs = sf.read(audio_buffer)
                            sd.play(data, fs)
                            sd.wait()
                            success = True
                    except Exception:
                        success = False

                # 2. Fallback to Native Windows SAPI if neural failed or unavailable
                if not success and sys.platform == "win32":
                    try:
                        try:
                            import pythoncom
                            pythoncom.CoInitialize()
                        except Exception:
                            pass
                        import win32com.client
                        speaker = win32com.client.Dispatch("SAPI.SpVoice")
                        speaker.Rate = self.speech_speed

                        # Configure voice based on preferred gender
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
                        success = True
                    except Exception:
                        success = False

                # 3. Fallback for macOS / Linux
                if not success:
                    try:
                        import subprocess
                        import shutil
                        if shutil.which("say"):
                            voice_opt = ["-v", "Samantha"] if self.voice_gender == "female" else ["-v", "Alex"]
                            subprocess.run(["say"] + voice_opt + [clean_text], check=False)
                        elif shutil.which("espeak"):
                            voice_opt = ["-v", "en+f3"] if self.voice_gender == "female" else ["-v", "en+m3"]
                            subprocess.run(["espeak"] + voice_opt + [clean_text], check=False)
                    except Exception:
                        pass

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
