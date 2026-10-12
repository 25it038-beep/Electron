"""Microphone device discovery and audio stream acquisition."""

from __future__ import annotations

import io
import wave
from typing import Any, Optional

try:
    import numpy as np
    import sounddevice as sd
    AUDIO_AVAILABLE = True
except Exception:
    AUDIO_AVAILABLE = False


class MicrophoneManager:
    """Manages audio capture devices and records PCM audio in memory."""

    def __init__(self, sample_rate: int = 16000, device_index: Optional[int] = None) -> None:
        self.sample_rate = sample_rate
        self.device_index = device_index

    def list_microphones(self) -> list[dict[str, Any]]:
        """List all available input audio devices."""
        if not AUDIO_AVAILABLE:
            return []
        devices = []
        try:
            device_list = sd.query_devices()
            for idx, d in enumerate(device_list):
                if d.get("max_input_channels", 0) > 0:
                    devices.append({
                        "index": idx,
                        "name": d["name"],
                        "channels": d["max_input_channels"],
                        "default_sample_rate": d.get("default_samplerate", 16000),
                    })
        except Exception:
            pass
        return devices

    def record_chunk(self, duration_sec: float = 4.0) -> tuple[Optional[bytes], float]:
        """Record a chunk of microphone audio. Returns (wav_bytes, rms_energy)."""
        if not AUDIO_AVAILABLE:
            return None, 0.0

        try:
            frames_to_record = int(duration_sec * self.sample_rate)
            rec = sd.rec(
                frames_to_record,
                samplerate=self.sample_rate,
                channels=1,
                dtype="int16",
                device=self.device_index,
            )
            sd.wait()

            audio_data = rec.flatten()
            rms = float(np.sqrt(np.mean(audio_data.astype(float) ** 2)))

            # Convert numpy array to standard WAV buffer in memory
            buf = io.BytesIO()
            with wave.open(buf, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)  # 16-bit
                wf.setframerate(self.sample_rate)
                wf.writeframes(rec.tobytes())
            buf.seek(0)

            return buf.read(), rms
        except Exception:
            return None, 0.0
