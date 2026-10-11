"""Unit tests for Electorn AI Voice Engine."""

from unittest.mock import MagicMock, patch
import numpy as np
import pytest

from electorn.voice import VoiceEngine


def test_voice_is_supported():
    engine = VoiceEngine()
    # is_supported should return bool based on availability
    assert isinstance(engine.is_supported(), bool)


def test_sanitize_text_code_blocks():
    text = "Here is how to do it:\n```python\ndef hello():\n    print('world')\n```\nEnjoy!"
    clean = VoiceEngine._sanitize_text_for_speech(text)
    assert "```" not in clean
    assert "Here is the code implementation displayed on your screen." in clean


def test_sanitize_text_urls_and_markdown():
    text = "Check out **Electorn AI** at https://hs-ai-studio.onrender.com/ for #awesome updates!"
    clean = VoiceEngine._sanitize_text_for_speech(text)
    assert "https://" not in clean
    assert "**" not in clean
    assert "#" not in clean
    assert "link on screen" in clean


def test_sanitize_text_truncates_excessive_sentences():
    text = "First point. Second point. Third point. Fourth point. Fifth point. Sixth point."
    clean = VoiceEngine._sanitize_text_for_speech(text)
    assert "The full details are displayed on your screen." in clean


def test_speak_empty():
    engine = VoiceEngine()
    # Should safely return without invoking TTS or throwing errors
    engine.speak("")
    engine.speak("   \n\t  ")


@patch("sys.platform", "win32")
@patch("win32com.client.Dispatch")
def test_speak_windows_female_voice(mock_dispatch):
    mock_speaker = MagicMock()
    # Mock voices collection with male and female voice
    male_voice = MagicMock()
    male_voice.GetDescription.return_value = "Microsoft David Desktop - English (United States)"
    male_voice.GetAttribute.return_value = "Male"

    female_voice = MagicMock()
    female_voice.GetDescription.return_value = "Microsoft Zira Desktop - English (United States)"
    female_voice.GetAttribute.return_value = "Female"

    mock_voices = MagicMock()
    mock_voices.Count = 2
    mock_voices.Item.side_effect = lambda idx: [male_voice, female_voice][idx]
    mock_speaker.GetVoices.return_value = mock_voices
    mock_dispatch.return_value = mock_speaker

    engine = VoiceEngine(voice_gender="female")
    assert engine.voice_gender == "female"
    engine.speak("Hello developer", async_mode=False)

    mock_dispatch.assert_called_with("SAPI.SpVoice")
    assert mock_speaker.Voice == female_voice
    mock_speaker.Speak.assert_called_once()
    args, _ = mock_speaker.Speak.call_args
    assert "Hello developer" in args[0]


def test_set_gender():
    engine = VoiceEngine(voice_gender="female")
    assert engine.voice_gender == "female"
    engine.set_gender("male")
    assert engine.voice_gender == "male"
    engine.set_gender("female")
    assert engine.voice_gender == "female"



@patch("sounddevice.rec")
@patch("sounddevice.wait")
def test_listen_and_transcribe_silence(mock_wait, mock_rec):
    # Simulate silence (all zeros array)
    mock_rec.return_value = np.zeros((16000, 1), dtype=np.int16)

    engine = VoiceEngine()
    status_updates = []

    result = engine.listen_and_transcribe(
        record_seconds=1.0,
        status_cb=lambda msg: status_updates.append(msg),
    )

    assert result is None
    assert any("Listening" in s for s in status_updates)


@patch("sounddevice.rec")
@patch("sounddevice.wait")
@patch("speech_recognition.Recognizer.recognize_google")
def test_listen_and_transcribe_success(mock_recognize, mock_wait, mock_rec):
    # Simulate non-silent audio signal
    t = np.linspace(0, 1, 16000)
    signal = (np.sin(2 * np.pi * 440 * t) * 5000).astype(np.int16).reshape(-1, 1)
    mock_rec.return_value = signal
    mock_recognize.return_value = "build a fastapi app"

    engine = VoiceEngine()
    status_updates = []

    result = engine.listen_and_transcribe(
        record_seconds=1.0,
        status_cb=lambda msg: status_updates.append(msg),
    )

    assert result == "build a fastapi app"
    assert any("Transcribing" in s for s in status_updates)
