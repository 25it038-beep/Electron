"""Voice processing package for Electorn AI: STT, Neural TTS, VAD, and Microphone management."""

from voice.microphone import MicrophoneManager
from voice.voice_activity import VoiceActivityDetector
from voice.speech_to_text import SpeechToTextEngine
from voice.text_to_speech import TextToSpeechEngine
from voice.wake_word import WakeWordDetector

__all__ = [
    "MicrophoneManager",
    "VoiceActivityDetector",
    "SpeechToTextEngine",
    "TextToSpeechEngine",
    "WakeWordDetector",
]
