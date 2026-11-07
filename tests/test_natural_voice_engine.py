"""Comprehensive Test Suite for ARIA Natural Voice Conversation Engine.

Validates all 13 required real-world voice interaction situations:
1. User speaks without pausing.
2. User pauses for two seconds (short pause).
3. User pauses for five seconds (thinking pause).
4. User pauses while thinking on incomplete sentence ('Aria, open my browser and...').
5. User speaks a long paragraph.
6. User changes/continues sentence midway ('I want you to create an application that...' + '...can manage my files').
7. User interrupts Aria while Aria is speaking (natural barge-in).
8. Background noise occurs (ambient noise rejection).
9. Aria's voice is playing (echo cancellation / self-suppression).
10. User speaks in Tamil (Tamil continuation markers).
11. User mixes Tamil and English (code-switching).
12. Microphone temporary glitch / recovery.
13. User gives a multi-step instruction.
"""
from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch
import numpy as np

from electorn.companion.voice_vad import AdaptiveVAD, AdaptiveVADConfig, AudioFrameCategory, PauseType
from electorn.companion.sentence_completer import SentenceCompleter
from electorn.companion.conversational_turn import ConversationalTurnManager, TurnState
from electorn.companion.voice_session import CompanionVoiceSession
from electorn.companion.supervisor import CompanionSupervisor
from electorn.companion.schema import CompanionConfig


class TestAdaptiveVAD(unittest.TestCase):
    def setUp(self):
        self.config = AdaptiveVADConfig(
            sample_rate=16000,
            frame_duration_ms=100,
            min_speech_energy=100.0,
            snr_ratio=1.5,
            short_pause_sec=1.5,
            thinking_pause_sec=3.0,
            continuation_window_sec=5.0,
            extended_pause_sec=8.0,
        )
        self.vad = AdaptiveVAD(self.config)

    def test_situation_08_background_noise_rejection(self):
        """Situation 8: Background noise occurs below speech threshold."""
        # Low amplitude random noise: RMS ~ 40
        low_noise = np.random.normal(0, 40, 1600).astype(np.int16)
        cat, rms = self.vad.process_frame(low_noise)
        self.assertIn(cat, (AudioFrameCategory.SILENCE, AudioFrameCategory.NOISE))
        self.assertFalse(self.vad.is_speech_active)

    def test_situation_01_user_speaks_without_pausing(self):
        """Situation 1: User speaks continuous audio frames."""
        # High amplitude speech frame: RMS ~ 500
        speech_frame = np.random.normal(0, 500, 1600).astype(np.int16)
        # Process consecutive frames to trigger speech state
        self.vad.process_frame(speech_frame)
        cat, rms = self.vad.process_frame(speech_frame)
        self.assertEqual(cat, AudioFrameCategory.SPEECH)
        self.assertTrue(self.vad.is_speech_active)
        self.assertTrue(self.vad.has_buffered_speech())

    def test_pause_classification_types(self):
        """Test pause duration classification."""
        speech_frame = np.random.normal(0, 500, 1600).astype(np.int16)
        self.vad.process_frame(speech_frame)
        self.vad.process_frame(speech_frame)

        # Right after speech: micro-pause (<1.2s)
        self.assertEqual(self.vad.get_current_pause_type(), PauseType.MICRO_PAUSE)


class TestSentenceCompleter(unittest.TestCase):
    def setUp(self):
        self.completer = SentenceCompleter()

    def test_situation_04_user_pauses_while_thinking_incomplete(self):
        """Situation 4: User says 'Aria, open my browser and...' - must be detected as incomplete!"""
        is_comp, reason = self.completer.is_complete("Aria, open my browser and...")
        self.assertFalse(is_comp)

        is_comp, reason = self.completer.is_complete("Aria, open my browser and")
        self.assertFalse(is_comp)
        self.assertIn("conjunction", reason)

    def test_situation_06_stitch_sentence_segments(self):
        """Situation 6: User speaks in two segments with pause midway."""
        part1 = "I want you to create an application that"
        part2 = "can manage all my files automatically."

        is_comp1, _ = self.completer.is_complete(part1)
        self.assertFalse(is_comp1, "First segment must be identified as incomplete")

        stitched = self.completer.stitch_segments(part1, part2)
        self.assertEqual(stitched, "I want you to create an application that can manage all my files automatically.")

        is_comp2, _ = self.completer.is_complete(stitched)
        self.assertTrue(is_comp2, "Combined sentence must be complete")

    def test_stitch_deduplicates_boundary_words(self):
        """Ensure repeated trailing words during pause are cleanly deduplicated."""
        part1 = "Aria open my browser and"
        part2 = "and search for the latest NVIDIA models"
        stitched = self.completer.stitch_segments(part1, part2)
        self.assertEqual(stitched, "Aria open my browser and search for the latest NVIDIA models")

    def test_situation_10_tamil_continuation_markers(self):
        """Situation 10: User speaks in Tamil with trailing continuation markers."""
        # "அப்புறம்" (appuram / and then)
        is_comp, reason = self.completer.is_complete("எனக்கு ஒரு பைதான் ப்ராஜெக்ட் ஓபன் பண்ணிட்டு அப்புறம்")
        self.assertFalse(is_comp)
        self.assertIn("tamil", reason)

        # "ஆனா" (aana / but)
        is_comp2, reason2 = self.completer.is_complete("நான் ட்ரை பண்ணேன் ஆனா")
        self.assertFalse(is_comp2)

    def test_situation_11_tanglish_continuation_markers(self):
        """Situation 11: User speaks mixed Tamil and English (Tanglish)."""
        is_comp, reason = self.completer.is_complete("Open VS Code and create python file apram")
        self.assertFalse(is_comp)
        self.assertIn("tamil", reason)

    def test_situation_05_long_paragraph_completion(self):
        """Situation 5: Complete long sentence/paragraph."""
        long_para = (
            "Aria please conduct a full diagnostic on my laptop hardware, check whether the NVIDIA GPU is overheating, "
            "verify my Wi-Fi connection latency, inspect the free disk space on my C drive, and organize my desktop files."
        )
        is_comp, reason = self.completer.is_complete(long_para)
        self.assertTrue(is_comp)
        self.assertEqual(reason, "complete_sentence")

    def test_situation_13_multi_step_instruction(self):
        """Situation 13: Multi-step instruction."""
        multi_step = "Open Chrome, search for latest machine learning news, and prepare a summary document."
        is_comp, reason = self.completer.is_complete(multi_step)
        self.assertTrue(is_comp)


class TestConversationalTurnManager(unittest.TestCase):
    def setUp(self):
        self.completer = SentenceCompleter()
        self.turn = ConversationalTurnManager(completer=self.completer)

    def test_situation_02_short_pause_does_not_terminate(self):
        """Situation 2: User pauses for 2 seconds on incomplete sentence - must NOT terminate turn."""
        self.turn.start_turn()
        self.turn.on_speech_chunk_transcribed("Aria, open my browser and")

        is_done, reassurance = self.turn.evaluate_pause(silence_seconds=2.0)
        self.assertFalse(is_done)
        self.assertEqual(self.turn.state, TurnState.POSSIBLE_PAUSE)

    def test_situation_03_thinking_pause_does_not_terminate(self):
        """Situation 3: User pauses for 4 seconds to think on incomplete sentence."""
        self.turn.start_turn()
        self.turn.on_speech_chunk_transcribed("I need you to create a script that")

        is_done, reassurance = self.turn.evaluate_pause(silence_seconds=4.0)
        self.assertFalse(is_done)
        self.assertEqual(self.turn.state, TurnState.WAITING_FOR_CONTINUATION)

    def test_completed_sentence_pauses_and_finalizes(self):
        """Completed sentence finalizes once silence exceeds completion threshold (1.5s)."""
        self.turn.start_turn()
        self.turn.on_speech_chunk_transcribed("Check my battery status.")

        # At 0.8s silence: still confirming
        is_done, _ = self.turn.evaluate_pause(silence_seconds=0.8)
        self.assertFalse(is_done)

        # At 1.8s silence: finalized!
        is_done, _ = self.turn.evaluate_pause(silence_seconds=1.8)
        self.assertTrue(is_done)
        self.assertEqual(self.turn.state, TurnState.SPEECH_COMPLETE)


class TestCompanionVoiceSession(unittest.TestCase):
    def setUp(self):
        self.session = CompanionVoiceSession()

    def test_situation_07_user_barge_in_interrupts_aria(self):
        """Situation 7: If Aria is speaking and user interrupts, speech stops immediately."""
        self.session._is_speaking = True
        self.session.interrupt_speech()
        self.assertFalse(self.session.is_speaking())
        self.assertTrue(self.session._interrupted_event.is_set())

    def test_situation_09_echo_suppression_and_mute(self):
        """Situation 9: Self-voice suppression & mute control."""
        self.session.mute()
        self.assertTrue(self.session.is_muted())
        # While muted, listen_for_user immediately returns None without capturing
        result = self.session.listen_for_user(timeout_seconds=0.1)
        self.assertIsNone(result)

        self.session.unmute()
        self.assertFalse(self.session.is_muted())

    def test_continuous_listening_toggle(self):
        """Continuous listening state management."""
        self.assertFalse(self.session.is_continuous_listening())
        self.session.enable_continuous_listening()
        self.assertTrue(self.session.is_continuous_listening())
        self.session.disable_continuous_listening()
        self.assertFalse(self.session.is_continuous_listening())

    def test_situation_12_microphone_glitch_recovery(self):
        """Situation 12: Microphone temporarily glitches / throws exception."""
        with patch("sounddevice.rec", side_effect=Exception("Mic device busy")):
            # listen_for_user must not crash, should handle exception gracefully and return None
            res = self.session.listen_for_user(timeout_seconds=0.2)
            self.assertIsNone(res)


class TestCompanionSupervisorNaturalVoice(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        config = CompanionConfig()
        config.personality.user_name = "Harshan"
        config.voice_enabled = False
        mock_llm = MagicMock()
        mock_llm.ask.return_value = "Understood."
        cls.supervisor = CompanionSupervisor(config=config, llm_provider=mock_llm)

    def test_continuous_listening_voice_command(self):
        """Voice command enables and disables continuous mode."""
        reply = self.supervisor.process_user_input("enable continuous listening")
        self.assertIn("Harshan", reply)
        self.assertTrue(self.supervisor.voice.is_continuous_listening())

        reply2 = self.supervisor.process_user_input("disable continuous listening")
        self.assertIn("Harshan", reply2)
        self.assertFalse(self.supervisor.voice.is_continuous_listening())


if __name__ == "__main__":
    unittest.main()
