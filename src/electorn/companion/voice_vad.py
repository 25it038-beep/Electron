"""Intelligent Speech & Voice Activity Detection (Adaptive VAD).

Distinguishes between breathing, background noise, micro-pauses (1-2s),
thinking pauses (2-4s), sentence continuation windows (4-6s), and definitive silence.
Dynamically tracks ambient noise floors so it remains accurate in varied room acoustics.
"""
from __future__ import annotations

import logging
import time
from collections import deque
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


class PauseType(str, Enum):
    MICRO_PAUSE = "MICRO_PAUSE"               # < 1.2s: Breathing or natural intra-sentence pause
    SHORT_PAUSE = "SHORT_PAUSE"               # 1.2s - 2.5s: Brief hesitation
    THINKING_PAUSE = "THINKING_PAUSE"         # 2.5s - 4.5s: Formulating next words
    CONTINUATION_WINDOW = "CONTINUATION"      # 4.5s - 7.0s: Waiting for incomplete clause
    DEFINITIVE_SILENCE = "DEFINITIVE_SILENCE" # > 7.0s: User finished speaking


class AudioFrameCategory(str, Enum):
    SILENCE = "SILENCE"
    NOISE = "NOISE"
    SPEECH = "SPEECH"


class AdaptiveVADConfig:
    def __init__(
        self,
        sample_rate: int = 16000,
        frame_duration_ms: int = 100,
        min_speech_energy: float = 120.0,
        snr_ratio: float = 1.8,
        short_pause_sec: float = 1.5,
        thinking_pause_sec: float = 3.0,
        continuation_window_sec: float = 5.0,
        extended_pause_sec: float = 8.0,
        max_utterance_sec: float = 60.0,
    ) -> None:
        self.sample_rate = sample_rate
        self.frame_duration_ms = frame_duration_ms
        self.frame_samples = int(sample_rate * (frame_duration_ms / 1000.0))
        self.min_speech_energy = min_speech_energy
        self.snr_ratio = snr_ratio
        self.short_pause_sec = short_pause_sec
        self.thinking_pause_sec = thinking_pause_sec
        self.continuation_window_sec = continuation_window_sec
        self.extended_pause_sec = extended_pause_sec
        self.max_utterance_sec = max_utterance_sec


class AdaptiveVAD:
    """Adaptive acoustic voice activity detector with dynamic background noise tracking."""

    def __init__(self, config: Optional[AdaptiveVADConfig] = None) -> None:
        self.config = config or AdaptiveVADConfig()
        self.noise_floor = 80.0
        self.speech_energy_threshold = self.config.min_speech_energy
        self.is_speech_active = False
        self.speech_start_time: Optional[float] = None
        self.last_speech_time: Optional[float] = None
        self.total_speech_frames = 0
        self.consecutive_speech_frames = 0
        self.consecutive_silence_frames = 0
        self._pre_speech_ring: deque[np.ndarray] = deque(maxlen=3)
        self._audio_buffer: List[np.ndarray] = []

    def reset(self) -> None:
        """Reset state for a new conversational turn."""
        self.is_speech_active = False
        self.speech_start_time = None
        self.last_speech_time = None
        self.total_speech_frames = 0
        self.consecutive_speech_frames = 0
        self.consecutive_silence_frames = 0
        self._pre_speech_ring.clear()
        self._audio_buffer.clear()

    def process_frame(self, frame: np.ndarray) -> Tuple[AudioFrameCategory, float]:
        """Process a single PCM int16 audio frame and return classification and RMS energy."""
        if len(frame) == 0:
            return AudioFrameCategory.SILENCE, 0.0

        # Compute RMS energy
        rms = float(np.sqrt(np.mean(frame.astype(float) ** 2)))
        now = time.time()

        # Dynamic speech threshold based on calibrated ambient noise floor
        effective_threshold = max(self.config.min_speech_energy, self.noise_floor * self.config.snr_ratio)
        self.speech_energy_threshold = effective_threshold

        if rms >= effective_threshold:
            category = AudioFrameCategory.SPEECH
            self.consecutive_speech_frames += 1
            self.consecutive_silence_frames = 0
            self.last_speech_time = now

            if not self.is_speech_active:
                if self.consecutive_speech_frames >= 2:
                    self.is_speech_active = True
                    self.speech_start_time = now
                    # Flush lookback frames into audio buffer so speech onset is never lost
                    self._audio_buffer.extend(list(self._pre_speech_ring))
                    self._pre_speech_ring.clear()
                else:
                    self._pre_speech_ring.append(frame.copy())
            self.total_speech_frames += 1

        elif rms >= self.noise_floor * 1.1:
            category = AudioFrameCategory.NOISE
            self.consecutive_silence_frames += 1
            self.consecutive_speech_frames = 0
            if not self.is_speech_active:
                self._pre_speech_ring.append(frame.copy())
        else:
            category = AudioFrameCategory.SILENCE
            self.consecutive_silence_frames += 1
            self.consecutive_speech_frames = 0
            # Adapt ambient noise floor during steady background silence
            if not self.is_speech_active:
                self.noise_floor = 0.95 * self.noise_floor + 0.05 * max(20.0, rms)
                self._pre_speech_ring.append(frame.copy())

        # Buffer frames when utterance is actively underway
        if self.is_speech_active:
            self._audio_buffer.append(frame.copy())

        return category, rms

    def get_current_pause_type(self) -> PauseType:
        """Classify the current pause duration since user last spoke."""
        if not self.is_speech_active or self.last_speech_time is None:
            return PauseType.DEFINITIVE_SILENCE

        silence_dur = time.time() - self.last_speech_time

        if silence_dur < self.config.short_pause_sec:
            return PauseType.MICRO_PAUSE
        elif silence_dur < self.config.thinking_pause_sec:
            return PauseType.SHORT_PAUSE
        elif silence_dur < self.config.continuation_window_sec:
            return PauseType.THINKING_PAUSE
        elif silence_dur < self.config.extended_pause_sec:
            return PauseType.CONTINUATION_WINDOW
        else:
            return PauseType.DEFINITIVE_SILENCE

    def get_silence_duration(self) -> float:
        """Return elapsed seconds since speech was last observed."""
        if self.last_speech_time is None:
            return 0.0
        return max(0.0, time.time() - self.last_speech_time)

    def get_utterance_duration(self) -> float:
        """Return total elapsed seconds since speech began."""
        if self.speech_start_time is None:
            return 0.0
        return max(0.0, time.time() - self.speech_start_time)

    def is_max_duration_exceeded(self) -> bool:
        """Check if speech has exceeded maximum allowable single utterance time."""
        return self.get_utterance_duration() >= self.config.max_utterance_sec

    def get_buffered_audio_int16(self) -> np.ndarray:
        """Return the collected audio buffer as a single 1D int16 numpy array."""
        if not self._audio_buffer:
            return np.array([], dtype=np.int16)
        return np.concatenate(self._audio_buffer)

    def get_buffered_audio_bytes(self) -> bytes:
        """Return raw PCM int16 audio bytes."""
        arr = self.get_buffered_audio_int16()
        return arr.tobytes()

    def has_buffered_speech(self) -> bool:
        """True if speech was detected and at least 200ms of audio was collected."""
        return self.is_speech_active and len(self._audio_buffer) >= 2
