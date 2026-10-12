"""Text-to-Speech synthesis with Modern Neural Edge TTS and native SAPI fallback."""

from __future__ import annotations

import asyncio
import io
import re
import sys
import threading
from typing import Optional

try:
    import edge_tts
    import soundfile as sf
    import sounddevice as sd
    NEURAL_TTS_AVAILABLE = True
except Exception:
    NEURAL_TTS_AVAILABLE = False


class TextToSpeechEngine:
    """Provides natural neural speech output with interruptible playback and SAPI fallback."""

    NEURAL_VOICES = {
        "female": "en-US-AvaNeural",
        "male": "en-US-AndrewNeural",
    }

    def __init__(self, voice_gender: str = "female", speed: int = 1) -> None:
        self.voice_gender = voice_gender.lower()
        self.speed = speed
        self._lock = threading.Lock()
        self._interrupted = False
        self._is_speaking = False

    def is_speaking(self) -> bool:
        """Check if audio is currently playing."""
        return self._is_speaking

    def stop(self) -> None:
        """Interrupt active speech output immediately."""
        self._interrupted = True
        try:
            if NEURAL_TTS_AVAILABLE:
                sd.stop()
        except Exception:
            pass

    def speak(self, text: str, async_mode: bool = False) -> None:
        """Speak out text response via Neural Edge TTS or SAPI fallback."""
        if not text or not text.strip():
            return

        clean_text = self.sanitize_for_speech(text)
        if not clean_text:
            return

        self._interrupted = False

        def _worker() -> None:
            with self._lock:
                self._is_speaking = True
                success = False

                # 1. Attempt Modern Neural Voice (Edge TTS)
                if NEURAL_TTS_AVAILABLE and not self._interrupted:
                    try:
                        voice_name = self.NEURAL_VOICES.get(self.voice_gender, "en-US-AvaNeural")
                        audio_buffer = io.BytesIO()

                        async def _stream_tts() -> None:
                            communicate = edge_tts.Communicate(clean_text, voice_name)
                            async for chunk in communicate.stream():
                                if self._interrupted:
                                    break
                                if chunk["type"] == "audio":
                                    audio_buffer.write(chunk["data"])

                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        try:
                            loop.run_until_complete(_stream_tts())
                        finally:
                            loop.close()

                        audio_buffer.seek(0)
                        if not self._interrupted and audio_buffer.getbuffer().nbytes > 0:
                            data, fs = sf.read(audio_buffer)
                            sd.play(data, fs)
                            sd.wait()
                            success = True
                    except Exception:
                        success = False

                # 2. Fallback to Windows SAPI
                if not success and not self._interrupted and sys.platform == "win32":
                    try:
                        try:
                            import pythoncom
                            pythoncom.CoInitialize()
                        except Exception:
                            pass
                        import win32com.client
                        speaker = win32com.client.Dispatch("SAPI.SpVoice")
                        speaker.Rate = self.speed

                        # Select female/male SAPI voice
                        try:
                            voices = speaker.GetVoices()
                            for i in range(voices.Count):
                                v = voices.Item(i)
                                desc = v.GetDescription().lower()
                                if self.voice_gender == "female":
                                    if "zira" in desc or "female" in desc:
                                        speaker.Voice = v
                                        break
                                else:
                                    if "david" in desc or "male" in desc:
                                        speaker.Voice = v
                                        break
                        except Exception:
                            pass

                        speaker.Speak(clean_text)
                        try:
                            pythoncom.CoUninitialize()
                        except Exception:
                            pass
                        success = True
                    except Exception:
                        pass

                self._is_speaking = False

        if async_mode:
            t = threading.Thread(target=_worker, daemon=True)
            t.start()
        else:
            _worker()

    @staticmethod
    def sanitize_for_speech(text: str) -> str:
        """Strip raw code blocks, URLs, and markdown so speech sounds natural."""
        # Replace URLs
        cleaned = re.sub(r"https?://\S+", "link on screen", text)
        # Replace code blocks with courteous spoken notice
        cleaned = re.sub(r"```[\s\S]*?```", "Here is the code displayed on your screen.", cleaned)
        # Remove markdown symbols
        cleaned = re.sub(r"[*_#`>]", "", cleaned)
        # Truncate if response is excessively lengthy
        sentences = [s.strip() for s in cleaned.split(".") if s.strip()]
        if len(sentences) > 4:
            cleaned = ". ".join(sentences[:4]) + ". The full details are shown on your screen."
        return cleaned.strip()
