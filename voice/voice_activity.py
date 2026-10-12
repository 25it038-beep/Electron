"""Voice Activity Detection (VAD) and noise thresholding."""

from __future__ import annotations

import io
import wave
from typing import Optional

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except Exception:
    NUMPY_AVAILABLE = False


class VoiceActivityDetector:
    """Calculates RMS audio energy to distinguish silence from active human speech."""

    def __init__(self, silence_threshold_rms: float = 120.0) -> None:
        self.silence_threshold = silence_threshold_rms

    def is_speech(self, wav_bytes: bytes) -> bool:
        """Check if audio buffer contains energy exceeding silence threshold."""
        if not wav_bytes or not NUMPY_AVAILABLE:
            return False

        try:
            buf = io.BytesIO(wav_bytes)
            with wave.open(buf, "rb") as wf:
                raw_frames = wf.readframes(wf.getnframes())
            data = np.frombuffer(raw_frames, dtype=np.int16)
            if len(data) == 0:
                return False
            rms = float(np.sqrt(np.mean(data.astype(float) ** 2)))
            return rms >= self.silence_threshold
        except Exception:
            return False
