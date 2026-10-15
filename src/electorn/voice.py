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
    """Provides bidirectional voice interaction for Electorn AI using recent neural voice models (English & Tamil)."""

    SUPPORTED_LANGUAGES = {
        "en": "en-US",
        "en-us": "en-US",
        "english": "en-US",
        "ta": "ta-IN",
        "ta-in": "ta-IN",
        "tamil": "ta-IN",
    }

    # Recent neural models (Edge TTS)
    NEURAL_MODELS = {
        "en-US": {
            "female": "en-US-AvaNeural",      # High-fidelity natural female English neural voice
            "male": "en-US-AndrewNeural",     # High-fidelity natural male English neural voice
        },
        "ta-IN": {
            "female": "ta-IN-PallaviNeural",  # High-fidelity natural female Tamil neural voice
            "male": "ta-IN-ValluvarNeural",   # High-fidelity natural male Tamil neural voice
        },
    }

    def __init__(
        self,
        sample_rate: int = 16000,
        speech_speed: int = 1,
        voice_gender: str = "female",
        language: str = "en-US",
    ):
        self.sample_rate = sample_rate
        self.speech_speed = speech_speed
        self.voice_gender = voice_gender.lower()
        self.language = self._normalize_language(language)
        self.recognizer = sr.Recognizer() if VOICE_DEPS_AVAILABLE else None
        self._tts_lock = threading.Lock()
        self._is_speaking = False

    @classmethod
    def _normalize_language(cls, lang: str) -> str:
        """Normalize language code to standard locale (e.g. 'ta' -> 'ta-IN', 'en' -> 'en-US')."""
        if not lang:
            return "en-US"
        key = lang.strip().lower()
        return cls.SUPPORTED_LANGUAGES.get(key, lang)

    @staticmethod
    def is_tamil_text(text: str) -> bool:
        """Check if text contains Tamil Unicode characters (U+0B80 to U+0BFF)."""
        import re
        return bool(re.search(r"[\u0B80-\u0BFF]", text))

    def set_language(self, language: str) -> str:
        """Change the active speech and synthesis language (e.g. 'ta-IN' or 'en-US')."""
        self.language = self._normalize_language(language)
        return self.language

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

    def get_active_model_name(self, for_text: Optional[str] = None) -> str:
        """Return the name of the active voice model based on language and text."""
        target_lang = self.language
        if for_text and self.is_tamil_text(for_text):
            target_lang = "ta-IN"

        if NEURAL_VOICE_AVAILABLE:
            lang_dict = self.NEURAL_MODELS.get(target_lang, self.NEURAL_MODELS["en-US"])
            return lang_dict.get(self.voice_gender, "en-US-AvaNeural")

        if sys.platform == "win32":
            if target_lang == "ta-IN":
                return "Microsoft Valluvar (Tamil)" if self.voice_gender == "male" else "Microsoft Pallavi (Tamil)"
            return "Microsoft Zira (SAPI)" if self.voice_gender == "female" else "Microsoft David (SAPI)"
        return "System TTS"

    def speak(self, text: str, async_mode: bool = False, language_override: Optional[str] = None) -> None:
        """Speak out text response via modern neural voice or native SAPI/OS fallback."""
        if not text or not text.strip():
            return

        # Strip code blocks or backticks from spoken text to sound natural
        clean_text = self._sanitize_text_for_speech(text)
        if not clean_text:
            return

        # Determine target language: override > auto-detect Tamil in text > configured language
        if language_override:
            target_lang = self._normalize_language(language_override)
        elif self.is_tamil_text(clean_text):
            target_lang = "ta-IN"
        else:
            target_lang = self.language

        def _tts_worker() -> None:
            with self._tts_lock:
                self._is_speaking = True
                success = False

                # 1. Try Recent Neural Voice Model (Edge TTS)
                if NEURAL_VOICE_AVAILABLE:
                    try:
                        lang_models = self.NEURAL_MODELS.get(target_lang, self.NEURAL_MODELS["en-US"])
                        voice_model = lang_models.get(self.voice_gender, "en-US-AvaNeural")
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

                        # Configure voice based on preferred gender and language
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

                                if target_lang == "ta-IN":
                                    if "tamil" in desc or "valluvar" in desc or "pallavi" in desc:
                                        selected_voice = v
                                        break

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
        language_override: Optional[str] = None,
    ) -> Optional[str]:
        """Capture microphone audio and transcribe into text via SpeechRecognition (supports Tamil and English)."""
        if not VOICE_DEPS_AVAILABLE:
            raise RuntimeError("Voice dependencies (sounddevice, speech_recognition, numpy) not installed.")

        if status_cb:
            lang_label = "தமிழ் (Tamil)" if (language_override or self.language) == "ta-IN" else "English"
            status_cb(f"🎙️ Listening in {lang_label}... (Speak now)")

        try:
            target_lang = self._normalize_language(language_override) if language_override else self.language

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
                try:
                    text = self.recognizer.recognize_google(audio, language=target_lang)
                except sr.UnknownValueError:
                    # Bilingual fallback: if primary is Tamil and didn't match, attempt English recognition
                    if target_lang == "ta-IN":
                        try:
                            text = self.recognizer.recognize_google(audio, language="en-US")
                        except Exception:
                            return None
                    else:
                        return None

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

    @classmethod
    def _sanitize_text_for_speech(cls, text: str) -> str:
        """Remove long code blocks and special markup so speech sounds conversational in English or Tamil."""
        import re
        # Remove URLs
        cleaned = re.sub(r"https?://\S+", "link on screen", text)
        # Remove triple backtick blocks
        cleaned = re.sub(r"```[\s\S]*?```", "Here is the code implementation displayed on your screen.", cleaned)
        # Remove markdown symbols
        cleaned = re.sub(r"[*_#`>]", "", cleaned)
        # Limit spoken length if response is an essay
        sentences = [s.strip() for s in re.split(r"[.!?।]+", cleaned) if s.strip()]
        if len(sentences) > 4:
            if cls.is_tamil_text(cleaned):
                cleaned = ". ".join(sentences[:4]) + ". கூடுதல் தகவல்கள் உங்கள் திரையில் காட்டப்பட்டுள்ளன."
            else:
                cleaned = ". ".join(sentences[:4]) + ". The full details are displayed on your screen."
        return cleaned.strip()


def detect_web_search_intent(text: str) -> tuple[bool, str]:
    """Detect if a spoken voice query is requesting a live web search (English or Tamil).

    Returns (is_search, clean_search_query).
    """
    import re
    raw = text.strip()
    if not raw:
        return False, ""
    lower = raw.lower()

    # 1. Tamil search patterns
    # இணையத்தில்/கூகுளில்/வலையில் தேடு <topic>
    m = re.match(r"^(?:இணையத்தில்|கூகுளில்|வலையில்)\s+(?:தேடு|தேடுக)\s+(.+)$", raw)
    if m:
        return True, m.group(1).strip()

    # <topic> பற்றி (இணையத்தில்)? தேடு
    m = re.match(r"^(.+?)\s+பற்றி(?:\s+இணையத்தில்|\s+கூகுளில்)?\s+(?:தேடு|தேடுக)$", raw)
    if m:
        return True, m.group(1).strip()

    # தேடு <topic>
    m = re.match(r"^(?:தேடு|தேடுக)\s+(.+)$", raw)
    if m:
        return True, m.group(1).strip()

    # வலைத் தேடல் / வலை தேடல் <topic>
    m = re.match(r"^(?:வலைத்\s*தேடல்|வலை\s*தேடல்)\s+(.+)$", raw)
    if m:
        return True, m.group(1).strip()

    # இன்றைய செய்தி / வானிலை / நிலவரம்
    if any(k in raw for k in ["இன்றைய செய்தி", "இன்றைய வானிலை", "நடப்பு நிகழ்வுகள்", "தற்போதைய நிலவரம்"]):
        return True, raw

    # 2. English search patterns
    # Explicit search prefixes: "search web for X", "web search X", "search for X", "google X"
    prefixes = [
        r"^(?:search\s+(?:the\s+)?web\s+for|search\s+for|web\s+search(?:\s+for)?|search\s+google\s+for|google|search\s+online\s+for|look\s+up|search\s+internet\s+for)\s+(.+?)(?:\s+(?:on\s+the\s+web|online|on\s+google|on\s+internet))?$",
        r"^(?:find|browse\s+for)\s+(.+?)\s+(?:online|on\s+the\s+web|on\s+google)$",
    ]
    for p in prefixes:
        m = re.match(p, lower)
        if m:
            start, end = m.span(1)
            q = raw[start:end].strip()
            if q:
                return True, q

    # Informational questions about latest / real-time events
    info_patterns = [
        r"^(?:what(?:'s|\s+is)\s+the\s+latest\s+(?:news|update|score|status|price|version)\s+(?:about|on|of)?)\s+(.+)$",
        r"^(?:current\s+(?:weather|temperature|stock\s+price|news)\s+(?:in|for|of)?)\s+(.+)$",
        r"^(?:who\s+won\s+the)\s+(.+)$",
    ]
    for p in info_patterns:
        m = re.match(p, lower)
        if m:
            return True, raw

    return False, ""

