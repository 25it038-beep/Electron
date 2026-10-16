"""Unit and integration tests for Electorn Companion 3D Animated Avatar and Video Call system."""

import base64
import json
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from electorn.cli import app as root_app
from electorn.companion.cli import companion_app
from electorn.companion.schema import (
    AvatarExpression,
    AvatarStyle,
    CompanionConfig,
    CompanionMode,
    VideoCallConfig,
)
from electorn.companion.supervisor import CompanionSupervisor
from electorn.companion.video_server import VideoCallServer, detect_expression_from_text, find_available_port

runner = CliRunner()


@pytest.fixture
def mock_supervisor():
    """Create a test companion supervisor with mocked LLM and storage."""
    cfg = CompanionConfig()
    cfg.personality.user_name = "Harshan"
    cfg.personality.name = "Aria"
    cfg.video_call.avatar_style = AvatarStyle.REALISTIC

    mock_llm = MagicMock()
    mock_llm.ask.return_value = "Hello Harshan! I am your companion."

    supervisor = CompanionSupervisor(config=cfg, llm_provider=mock_llm)
    return supervisor


def test_video_call_config_and_avatar_enums():
    """Verify VideoCallConfig, AvatarStyle, and AvatarExpression schemas."""
    config = VideoCallConfig(avatar_style=AvatarStyle.ANIME, port=9000, camera_enabled=True)
    assert config.avatar_style == AvatarStyle.ANIME
    assert config.port == 9000
    assert config.camera_enabled is True

    # Test all 5 styles
    for style in [AvatarStyle.REALISTIC, AvatarStyle.ANIME, AvatarStyle.HOLOGRAM, AvatarStyle.MINIMALIST, AvatarStyle.CANVAS_2D]:
        assert isinstance(style.value, str)

    # Test expressions
    for expr in [AvatarExpression.IDLE, AvatarExpression.LISTENING, AvatarExpression.THINKING,
                 AvatarExpression.SPEAKING, AvatarExpression.HAPPY, AvatarExpression.CONFUSED,
                 AvatarExpression.EMPATHETIC, AvatarExpression.ERROR]:
        assert isinstance(expr.value, str)


def test_detect_expression_from_text():
    """Verify facial expression heuristics based on text sentiment."""
    assert detect_expression_from_text("Why is this error happening?") == AvatarExpression.CONFUSED
    assert detect_expression_from_text("This is awesome and wonderful!") == AvatarExpression.HAPPY
    assert detect_expression_from_text("I am so tired and worried.") == AvatarExpression.EMPATHETIC
    assert detect_expression_from_text("Here is your terminal output.") == AvatarExpression.SPEAKING


def test_find_available_port():
    """Verify port finder returns a valid integer port."""
    port = find_available_port(host="127.0.0.1", start_port=8900)
    assert isinstance(port, int)
    assert port >= 8900


def test_video_call_server_html_and_status(mock_supervisor):
    """Verify VideoCallServer serves HTML interface and status endpoint."""
    server = VideoCallServer(supervisor=mock_supervisor)
    client = TestClient(server.app)

    # GET / (HTML Interface)
    resp = client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "Harshan" in resp.text
    assert "Aria" in resp.text
    assert "avatar-canvas" in resp.text
    assert "THREE.Scene" in resp.text

    # GET /api/status
    resp_status = client.get("/api/status")
    assert resp_status.status_code == 200
    data = resp_status.json()
    assert data["name"] == "Aria"
    assert data["user_name"] == "Harshan"
    assert data["avatar_style"] == "realistic"


def test_video_call_server_chat_endpoint(mock_supervisor):
    """Verify POST /api/chat triggers supervisor and returns reply with facial expression."""
    server = VideoCallServer(supervisor=mock_supervisor)
    client = TestClient(server.app)

    resp = client.post("/api/chat", json={"text": "Hey Aria, what are you working on?"})
    assert resp.status_code == 200
    data = resp.json()
    assert "reply" in data
    assert "expression" in data
    assert data["user_name"] == "Harshan"
    assert data["speaker"] == "Aria"


def test_video_call_server_camera_analyze(mock_supervisor):
    """Verify POST /api/camera-analyze parses webcam frame and provides natural feedback."""
    server = VideoCallServer(supervisor=mock_supervisor)
    client = TestClient(server.app)

    # Create dummy 1x1 base64 png
    dummy_b64 = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="

    resp = client.post("/api/camera-analyze", json={"image_base64": dummy_b64, "prompt": "Check my screen"})
    assert resp.status_code == 200
    data = resp.json()
    assert "reply" in data
    assert "Harshan" in data["reply"]


def test_cli_companion_call_help():
    """Verify electorn companion call --help shows video-call flags."""
    res = runner.invoke(companion_app, ["call", "--help"])
    assert res.exit_code == 0
    assert "--style" in res.output
    assert "--port" in res.output
    assert "--no-browser" in res.output


def test_cli_root_call_help():
    """Verify electorn call --help shows video-call flags at the top level."""
    res = runner.invoke(root_app, ["call", "--help"])
    assert res.exit_code == 0
    assert "--style" in res.output
    assert "--port" in res.output
    assert "--no-browser" in res.output
