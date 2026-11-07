"""Conversational Turn State Machine & Turn Management for Aria.

Maintains natural turn transitions, handles thinking pauses,
prevents premature command execution, and stitches multi-segment conversations.
"""
from __future__ import annotations

import logging
import time
from enum import Enum
from typing import Callable, Optional

from electorn.companion.sentence_completer import SentenceCompleter

logger = logging.getLogger(__name__)


class TurnState(str, Enum):
    IDLE = "IDLE"
    LISTENING = "LISTENING"
    TRANSCRIBING = "TRANSCRIBING"
    POSSIBLE_PAUSE = "POSSIBLE_PAUSE"
    WAITING_FOR_CONTINUATION = "WAITING_FOR_CONTINUATION"
    SPEECH_COMPLETE = "SPEECH_COMPLETE"
    UNDERSTANDING = "UNDERSTANDING"
    RESPONDING = "RESPONDING"
    LISTENING_AGAIN = "LISTENING_AGAIN"


class ConversationalTurnManager:
    """Manages the lifecycle of a conversational speech turn."""

    def __init__(
        self,
        completer: Optional[SentenceCompleter] = None,
        on_state_change: Optional[Callable[[TurnState, str], None]] = None,
        on_partial_transcript: Optional[Callable[[str], None]] = None,
    ) -> None:
        self.completer = completer or SentenceCompleter()
        self.state: TurnState = TurnState.IDLE
        self.accumulated_transcript: str = ""
        self.turn_start_time: float = 0.0
        self.last_speech_time: float = 0.0
        self.last_reassurance_time: float = 0.0
        self.reassurance_given: bool = False
        self.on_state_change = on_state_change
        self.on_partial_transcript = on_partial_transcript

    def start_turn(self) -> None:
        """Initialize state for a new incoming conversational turn."""
        self.accumulated_transcript = ""
        self.turn_start_time = time.time()
        self.last_speech_time = time.time()
        self.reassurance_given = False
        self.set_state(TurnState.LISTENING, "Listening for user speech...")

    def set_state(self, new_state: TurnState, details: str = "") -> None:
        """Transition to a new turn state and fire notification callback."""
        if self.state != new_state:
            old = self.state
            self.state = new_state
            logger.debug(f"Turn state transition: {old} -> {new_state} ({details})")
            if self.on_state_change:
                try:
                    self.on_state_change(new_state, details)
                except Exception as e:
                    logger.debug(f"Error in state change callback: {e}")

    def on_speech_chunk_transcribed(self, chunk_text: str) -> None:
        """Integrate a newly transcribed speech chunk into the current turn."""
        if not chunk_text or not chunk_text.strip():
            return

        self.last_speech_time = time.time()
        self.accumulated_transcript = self.completer.stitch_segments(self.accumulated_transcript, chunk_text)

        if self.on_partial_transcript:
            try:
                self.on_partial_transcript(self.accumulated_transcript)
            except Exception:
                pass

        self.set_state(TurnState.TRANSCRIBING, f"Transcribed: '{self.accumulated_transcript}'")

    def evaluate_pause(self, silence_seconds: float) -> Tuple[bool, Optional[str]]:
        """Evaluate silence duration against sentence completeness.

        Returns (is_turn_complete, optional_reassurance_prompt).
        """
        if not self.accumulated_transcript.strip():
            # No speech transcribed yet; still just listening
            return False, None

        is_complete, reason = self.completer.is_complete(self.accumulated_transcript)

        # 1. If sentence is grammatically incomplete:
        if not is_complete:
            # Short pause (1.0s - 2.5s)
            if silence_seconds < 2.5:
                self.set_state(TurnState.POSSIBLE_PAUSE, f"Brief pause in incomplete sentence ({reason})")
                return False, None

            # Thinking pause (2.5s - 5.5s)
            elif silence_seconds < 5.5:
                self.set_state(TurnState.WAITING_FOR_CONTINUATION, f"Waiting for user to finish clause ({reason})")
                return False, None

            # Extended pause (5.5s - 8.5s): provide optional gentle reassurance
            elif silence_seconds < 8.5:
                self.set_state(TurnState.WAITING_FOR_CONTINUATION, "Extended thinking pause detected")
                now = time.time()
                if not self.reassurance_given and (now - self.last_reassurance_time > 45.0):
                    self.reassurance_given = True
                    self.last_reassurance_time = now
                    return False, "Take your time. I'm listening."
                return False, None

            # Silence exceeded extended threshold (>8.5s): user has stopped, accept what was said
            else:
                self.set_state(TurnState.SPEECH_COMPLETE, f"Finalizing after extended silence ({silence_seconds:.1f}s)")
                return True, None

        # 2. If sentence is grammatically complete:
        else:
            # Normal conversational completion pause: require at least 1.5s of silence before acting
            if silence_seconds < 1.5:
                self.set_state(TurnState.POSSIBLE_PAUSE, "Sentence complete, confirming end of turn...")
                return False, None
            else:
                self.set_state(TurnState.SPEECH_COMPLETE, f"Sentence complete ({reason})")
                return True, None

    def finalize_turn(self) -> str:
        """Finalize and return the complete conversational instruction."""
        text = self.accumulated_transcript.strip()
        self.set_state(TurnState.UNDERSTANDING, f"Processing final instruction: '{text}'")
        return text

    def mark_responding(self) -> None:
        """Mark that Aria has begun speaking response."""
        self.set_state(TurnState.RESPONDING, "Aria is speaking response")

    def mark_ready_for_next_turn(self) -> None:
        """Mark that response finished and ready to listen again."""
        self.set_state(TurnState.LISTENING_AGAIN, "Ready for next conversational turn")
