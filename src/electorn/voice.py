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
                try:
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
        # Remove inline backticks
        cleaned = re.sub(r"`([^`]+)`", r"\1", cleaned)
        # Remove markdown symbols
        cleaned = re.sub(r"[*_#~|>]", " ", cleaned)
        # Remove decorative emojis and symbols that can cause speech glitches
        cleaned = re.sub(r"[\U00010000-\U0010ffff]", "", cleaned)
        cleaned = re.sub(r"[\u2000-\u2bff]", "", cleaned)
        cleaned = re.sub(r"[\ufe00-\ufe0f\u200b-\u200f]", "", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()

        # Protect decimal numbers (e.g. 3.10, 15.5) and abbreviations from breaking mid-sentence
        protected = re.sub(r"(\d+)\.(\d+)", r"\1<DECIMAL_DOT>\2", cleaned)
        protected = re.sub(r"\b(e\.g|i\.e|vs|dr|mr|mrs|ms|prof|inc|ltd)\.", r"\1<ABBR_DOT>", protected, flags=re.IGNORECASE)

        # Split on sentence boundaries preserving closing punctuation
        parts = [
            s.replace("<DECIMAL_DOT>", ".").replace("<ABBR_DOT>", ".").strip()
            for s in re.split(r"(?<=[.!?।])\s+", protected)
            if s.strip()
        ]

        # Truncate only if truly excessive (> 4 full sentences)
        if len(parts) > 4:
            if cls.is_tamil_text(cleaned):
                cleaned = " ".join(parts[:4]) + " கூடுதல் தகவல்கள் உங்கள் திரையில் காட்டப்பட்டுள்ளன."
            else:
                cleaned = " ".join(parts[:4]) + " The full details are displayed on your screen."
        else:
            cleaned = " ".join(parts) if parts else cleaned

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


def should_ground_in_real_data(text: str) -> tuple[bool, str]:
    """Detect if a user query requires real-world live web data grounding instead of relying on outdated model training.

    Returns (should_ground, search_query).
    """
    import re
    raw = text.strip()
    if not raw:
        return False, ""
    lower = raw.lower()

    # 1. First check explicit web search intent
    is_search, search_q = detect_web_search_intent(raw)
    if is_search:
        return True, search_q

    # 2. Exclude local OS automation commands (mouse, keyboard, window control, app launching)
    automation_commands = [
        "click", "double click", "right click", "move cursor", "move mouse",
        "type ", "press enter", "press space", "press tab", "select all",
        "copy", "paste", "cut", "undo", "redo", "save",
        "open notepad", "open chrome", "open calc", "open terminal",
        "close notepad", "close browser", "close window", "minimize", "maximize",
        "switch window", "volume up", "volume down", "play music", "next song",
        "lock pc", "lock computer", "system info",
    ]
    if any(lower == cmd or lower.startswith(cmd + " ") or lower.startswith("press " + cmd) for cmd in automation_commands):
        return False, ""

    # Exclude basic conversational pleasantries and system commands
    meta_phrases = [
        "exit", "quit", "stop", "bye", "goodbye",
        "hello", "hi", "hey", "how are you", "who are you", "what can you do", "help",
        "switch to tamil", "switch to english", "change to tamil", "change to english",
        "தமிழுக்கு மாறு", "வணக்கம்", "நலமா", "வெளியேறு", "நிறுத்து",
    ]
    if any(lower == p or lower == p + "." for p in meta_phrases):
        return False, ""

    # 3. Informational question patterns (English)
    question_starts = [
        "who ", "who's ", "what ", "what's ", "when ", "when's ",
        "where ", "where's ", "why ", "how ", "how's ",
        "is ", "was ", "are ", "were ", "did ", "does ", "will ",
        "tell me about ", "tell me ", "explain ", "give me details on ",
        "information about ", "info on ",
    ]
    if any(lower.startswith(q) for q in question_starts) or lower.endswith("?"):
        return True, raw

    # Real-world temporal/entity keywords (English)
    entity_keywords = [
        "latest", "current", "recent", "today", "yesterday", "tomorrow", "now",
        "news", "weather", "price", "stock", "market", "ceo", "president",
        "prime minister", "minister", "election", "score", "winner", "released",
        "release date", "version", "update", "population", "gdp", "inflation",
        "2024", "2025", "2026",
    ]
    if any(re.search(r"\b" + re.escape(w) + r"\b", lower) for w in entity_keywords):
        return True, raw

    # 4. Tamil question & real-world patterns
    tamil_q_patterns = [
        r"யார்", r"என்ன", r"எங்கே", r"எப்போது", r"எப்படி",
        r"பற்றி\s+சொல்", r"விவரம்", r"செய்தி", r"வானிலை",
        r"விலை", r"நிலவரம்", r"தகவல்", r"இன்று", r"நேற்று",
        r"தற்போது", r"அரசியல்", r"அமைச்சர்", r"தலைவர்",
    ]
    if any(re.search(p, raw) for p in tamil_q_patterns):
        return True, raw

    return False, ""


def build_real_data_context(query: str, results: list, language: str = "en-US") -> str:
    """Build prompt context with live real-world date anchor and anti-cutoff directives."""
    from datetime import datetime
    now_str = datetime.now().strftime("%B %d, %Y")
    year_str = str(datetime.now().year)

    if language == "ta-IN":
        lines = [
            f"[நிகழ்நேர நேரடித் தரவுகள் — இன்றைய தேதி: {now_str}]",
            f"தற்போதைய ஆண்டு: {year_str}",
            "முக்கியக் குறிப்பு: உங்கள் பழைய பயிற்சித் தரவுகள் காலாவதியானவை (2023/2024 cutoff). நீங்கள் 2026-இல் இயங்குகிறீர்கள். "
            "கீழே உள்ள சரிபார்க்கப்பட்ட நேரடி இணையத் தேடல் முடிவுகளை மட்டுமே முதன்மையாகக் கொண்டு "
            "உண்மைத் தகவல்களை 2-3 வரிகளில் துல்லியமாகத் தமிழில் கூறவும். பழைய காலாவதியான நினைவுகளைத் தவிர்க்கவும்.",
            "",
            f"[இணைய தேடல் முடிவுகள்: '{query}']",
        ]
        for idx, r in enumerate(results, 1):
            lines.append(f"{idx}. {r.title} ({r.url})")
            lines.append(f"   விவரம்: {r.snippet}")
        lines.append("[நேரடித் தரவுகள் முடிவு]\n")
        return "\n".join(lines)
    else:
        lines = [
            f"[REAL-TIME LIVE DATA CONTEXT — CURRENT DATE: {now_str}]",
            f"Current Year: {year_str}",
            f"CRITICAL MODEL DATA CUTOFF OVERRIDE: Your internal pre-trained weights have an outdated cutoff (2023/2024). You are operating live in {year_str}. "
            f"NEVER assume outdated historical knowledge represents the current state. Always prioritize the verified real-time live web search results below over outdated pre-training memory.",
            "",
            f"[VERIFIED LIVE WEB SEARCH RESULTS FOR: '{query}']",
        ]
        for idx, r in enumerate(results, 1):
            lines.append(f"{idx}. {r.title} ({r.url})")
            lines.append(f"   Summary: {r.snippet}")
        lines.append("[END OF LIVE DATA CONTEXT]\n")
        return "\n".join(lines)


