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


def test_sanitize_text_preserves_decimals_and_abbreviations():
    text = "Hello Harshan, Python 3.10 is installed. Let us check the status. System load is 15.5%. All tests pass."
    clean = VoiceEngine._sanitize_text_for_speech(text)
    assert "Python 3.10" in clean
    assert "15.5%" in clean
    assert "All tests pass." in clean
    assert "The full details are displayed" not in clean


def test_sanitize_text_removes_glitchy_emojis():
    text = "💖 Aria: ⚡ ELECTORN is ready! ▶️ Running smoothly."
    clean = VoiceEngine._sanitize_text_for_speech(text)
    assert "💖" not in clean
    assert "⚡" not in clean
    assert "▶" not in clean
    assert "ELECTORN is ready!" in clean


def test_speak_empty():
    engine = VoiceEngine()
    # Should safely return without invoking TTS or throwing errors
    engine.speak("")
    engine.speak("   \n\t  ")


@patch("electorn.voice.NEURAL_VOICE_AVAILABLE", True)
@patch("sounddevice.wait")
@patch("sounddevice.play")
@patch("soundfile.read")
@patch("edge_tts.Communicate")
def test_speak_neural_voice(mock_comm_cls, mock_sf_read, mock_sd_play, mock_sd_wait):
    mock_comm = MagicMock()
    async def _dummy_stream():
        yield {"type": "audio", "data": b"dummy_audio_bytes"}
    mock_comm.stream.return_value = _dummy_stream()
    mock_comm_cls.return_value = mock_comm

    mock_sf_read.return_value = (np.zeros((100,)), 24000)

    engine = VoiceEngine(voice_gender="female")
    engine.speak("Hello developer", async_mode=False)

    mock_comm_cls.assert_called_once()
    args, _ = mock_comm_cls.call_args
    assert "Hello developer" in args[0]
    assert args[1] == "en-US-AvaNeural"
    mock_sd_play.assert_called_once()


@patch("electorn.voice.NEURAL_VOICE_AVAILABLE", False)
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


def test_voice_tamil_language_support():
    """Verify Tamil language normalization, text detection, and model retrieval."""
    engine = VoiceEngine(language="ta")
    assert engine.language == "ta-IN"

    engine.set_language("tamil")
    assert engine.language == "ta-IN"

    assert VoiceEngine.is_tamil_text("வணக்கம்") is True
    assert VoiceEngine.is_tamil_text("Hello world") is False

    model_name = engine.get_active_model_name()
    assert "Pallavi" in model_name or "Valluvar" in model_name

    engine.set_gender("male")
    assert "Valluvar" in engine.get_active_model_name()


def test_sanitize_text_tamil():
    """Verify Tamil text sanitization and Tamil detail truncation message."""
    text = "முதல் வாக்கியம். இரண்டாவது வாக்கியம். மூன்றாவது வாக்கியம். நான்காவது வாக்கியம். ஐந்தாவது வாக்கியம்."
    clean = VoiceEngine._sanitize_text_for_speech(text)
    assert "கூடுதல் தகவல்கள் உங்கள் திரையில் காட்டப்பட்டுள்ளன." in clean


@patch("electorn.voice.NEURAL_VOICE_AVAILABLE", True)
@patch("sounddevice.wait")
@patch("sounddevice.play")
@patch("soundfile.read")
@patch("edge_tts.Communicate")
def test_speak_tamil_neural_voice(mock_comm_cls, mock_sf_read, mock_sd_play, mock_sd_wait):
    """Verify edge_tts Communicate uses ta-IN-PallaviNeural when speaking Tamil text."""
    mock_comm = MagicMock()
    async def _dummy_stream():
        yield {"type": "audio", "data": b"dummy_audio_bytes"}
    mock_comm.stream.return_value = _dummy_stream()
    mock_comm_cls.return_value = mock_comm

    mock_sf_read.return_value = (np.zeros((100,)), 24000)

    engine = VoiceEngine(voice_gender="female", language="en-US")
    # Even if default language is English, speaking Tamil text should auto-select ta-IN-PallaviNeural
    engine.speak("வணக்கம் நண்பரே", async_mode=False)

    mock_comm_cls.assert_called_once()
    args, _ = mock_comm_cls.call_args
    assert "வணக்கம் நண்பரே" in args[0]
    assert args[1] == "ta-IN-PallaviNeural"
    mock_sd_play.assert_called_once()


@patch("sounddevice.rec")
@patch("sounddevice.wait")
@patch("speech_recognition.Recognizer.recognize_google")
def test_listen_and_transcribe_tamil_language(mock_recognize, mock_wait, mock_rec):
    """Verify speech recognizer uses ta-IN language code when configured for Tamil."""
    signal = np.ones((16000, 1), dtype=np.int16) * 5000
    mock_rec.return_value = signal
    mock_recognize.return_value = "வணக்கம்"

    engine = VoiceEngine(language="ta")
    status_updates = []
    result = engine.listen_and_transcribe(
        record_seconds=1.0,
        status_cb=lambda msg: status_updates.append(msg),
    )

    assert result == "வணக்கம்"
    mock_recognize.assert_called_once()
    _, kwargs = mock_recognize.call_args
    assert kwargs.get("language") == "ta-IN"
    assert any("தமிழ்" in s for s in status_updates)


def test_detect_web_search_intent_english():
    """Verify English web search intent detection across patterns."""
    from electorn.voice import detect_web_search_intent

    is_search, q = detect_web_search_intent("search web for latest AI news")
    assert is_search is True
    assert q == "latest AI news"

    is_search, q = detect_web_search_intent("google quantum computing algorithms")
    assert is_search is True
    assert q == "quantum computing algorithms"

    is_search, q = detect_web_search_intent("look up Nvidia stock price online")
    assert is_search is True
    assert "Nvidia stock price" in q

    is_search, q = detect_web_search_intent("what is the latest news about NASA")
    assert is_search is True
    assert "NASA" in q

    # OS automation intents should NOT be flagged as web search
    is_search, _ = detect_web_search_intent("click")
    assert is_search is False
    is_search, _ = detect_web_search_intent("open notepad")
    assert is_search is False
    is_search, _ = detect_web_search_intent("type hello world")
    assert is_search is False


def test_detect_web_search_intent_tamil():
    """Verify Tamil web search intent detection across patterns."""
    from electorn.voice import detect_web_search_intent

    is_search, q = detect_web_search_intent("இணையத்தில் தேடு செயற்கை நுண்ணறிவு")
    assert is_search is True
    assert q == "செயற்கை நுண்ணறிவு"

    is_search, q = detect_web_search_intent("சென்னை வானிலை பற்றி தேடு")
    assert is_search is True
    assert q == "சென்னை வானிலை"

    is_search, q = detect_web_search_intent("தேடு தமிழ்நாடு செய்திகள்")
    assert is_search is True
    assert q == "தமிழ்நாடு செய்திகள்"

    is_search, q = detect_web_search_intent("இன்றைய செய்தி")
    assert is_search is True

    # Non-search Tamil query
    is_search, _ = detect_web_search_intent("வணக்கம் நலமா")
    assert is_search is False


def test_should_ground_in_real_data_english():
    """Verify factual and informational questions are routed to real-world live grounding."""
    from electorn.voice import should_ground_in_real_data

    # Real-world factual questions should trigger grounding
    ground, q = should_ground_in_real_data("who is the prime minister of UK")
    assert ground is True
    assert "prime minister" in q

    ground, q = should_ground_in_real_data("what is the latest stock price of Apple")
    assert ground is True

    ground, q = should_ground_in_real_data("how is bitcoin trading today")
    assert ground is True

    ground, q = should_ground_in_real_data("tell me about the 2026 economic forecast")
    assert ground is True

    # OS actions should NOT trigger grounding
    ground, _ = should_ground_in_real_data("click")
    assert ground is False
    ground, _ = should_ground_in_real_data("open notepad")
    assert ground is False
    ground, _ = should_ground_in_real_data("type hello")
    assert ground is False

    # Meta/pleasantries should NOT trigger grounding
    ground, _ = should_ground_in_real_data("hello")
    assert ground is False
    ground, _ = should_ground_in_real_data("how are you")
    assert ground is False
    ground, _ = should_ground_in_real_data("switch to tamil")
    assert ground is False


def test_should_ground_in_real_data_tamil():
    """Verify Tamil informational questions trigger real-world live grounding."""
    from electorn.voice import should_ground_in_real_data

    ground, q = should_ground_in_real_data("சென்னை வானிலை நிலவரம் என்ன")
    assert ground is True

    ground, q = should_ground_in_real_data("இன்றைய தங்கம் விலை என்ன")
    assert ground is True

    ground, q = should_ground_in_real_data("நரேந்திர மோடி பற்றி சொல்")
    assert ground is True

    # Greeting should not ground
    ground, _ = should_ground_in_real_data("வணக்கம்")
    assert ground is False


def test_build_real_data_context():
    """Verify build_real_data_context embeds date, year, and anti-cutoff directives."""
    from electorn.voice import build_real_data_context
    from electorn.runtime.web_search import SearchResult

    results = [
        SearchResult(title="Live News 2026", url="https://news.org", snippet="Current events verified.")
    ]

    en_ctx = build_real_data_context("latest tech news", results, language="en-US")
    assert "REAL-TIME LIVE DATA CONTEXT" in en_ctx
    assert "CRITICAL MODEL DATA CUTOFF OVERRIDE" in en_ctx
    assert "2026" in en_ctx
    assert "Live News 2026" in en_ctx

    ta_ctx = build_real_data_context("செய்திகள்", results, language="ta-IN")
    assert "நிகழ்நேர நேரடித் தரவுகள்" in ta_ctx
    assert "2026" in ta_ctx
    assert "Live News 2026" in ta_ctx



