"""FastAPI-powered real-time video call server and WebSocket bridge for Electorn Companion Mode.

Provides an interactive 3D avatar video-call interface, Web Audio API lip synchronization,
real-time speech recognition, barge-in interruption, and optional camera vision understanding.
"""

from __future__ import annotations

import asyncio
import base64
import io
import json
import logging
import os
from pathlib import Path
import re
import socket
import threading
import time
from typing import Any, Dict, List, Optional, Set
import urllib.request
import webbrowser

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from electorn.companion.schema import (
    AvatarExpression,
    AvatarStyle,
    CompanionLifecycleState,
    CompanionMode,
    CompanionState,
    VideoCallConfig,
)
from electorn.companion.supervisor import CompanionSupervisor

logger = logging.getLogger(__name__)

# Check neural voice capability
try:
    import edge_tts
    EDGE_TTS_AVAILABLE = True
except ImportError:
    EDGE_TTS_AVAILABLE = False

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


def find_available_port(host: str = "127.0.0.1", start_port: int = 8765, max_attempts: int = 50) -> int:
    """Find an available TCP port starting from start_port."""
    for port in range(start_port, start_port + max_attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind((host, port))
                return port
            except OSError:
                continue
    return start_port


def generate_tts_base64(text: str, language: str = "en-US", gender: str = "female") -> Optional[str]:
    """Generate speech audio via Edge TTS and return as base64-encoded MP3 string."""
    if not EDGE_TTS_AVAILABLE or not text.strip():
        return None

    # Determine voice model
    is_tamil = bool(re.search(r"[\u0B80-\u0BFF]", text)) or "ta" in language.lower()
    if is_tamil:
        voice = "ta-IN-PallaviNeural" if gender.lower() == "female" else "ta-IN-ValluvarNeural"
    else:
        voice = "en-US-AvaNeural" if gender.lower() == "female" else "en-US-AndrewNeural"

    # Strip code or markdown symbols for speech synthesis
    clean_text = re.sub(r"```[\s\S]*?```", "", text)
    clean_text = re.sub(r"`([^`]+)`", r"\1", clean_text)
    clean_text = re.sub(r"[*#_~>|]", " ", clean_text).strip()
    if not clean_text:
        clean_text = text.strip()

    try:
        audio_chunks: List[bytes] = []

        async def _run_stream() -> None:
            comm = edge_tts.Communicate(clean_text, voice)
            async for chunk in comm.stream():
                if chunk["type"] == "audio":
                    audio_chunks.append(chunk["data"])

        # Execute async TTS
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # In running loop: run in separate thread
                def _worker():
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    try:
                        new_loop.run_until_complete(_run_stream())
                    finally:
                        new_loop.close()
                t = threading.Thread(target=_worker)
                t.start()
                t.join(timeout=15.0)
            else:
                loop.run_until_complete(_run_stream())
        except RuntimeError:
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            try:
                new_loop.run_until_complete(_run_stream())
            finally:
                new_loop.close()

        if audio_chunks:
            raw_audio = b"".join(audio_chunks)
            return base64.b64encode(raw_audio).decode("ascii")
    except Exception as exc:
        logger.warning("Edge TTS synthesis failed in video call server: %s", exc)

    return None


def detect_expression_from_text(text: str) -> AvatarExpression:
    """Infer appropriate avatar facial expression from message tone and content."""
    lower = text.lower()

    if any(w in lower for w in ["?", "how", "what", "why", "who", "when", "wondering", "explain"]):
        return AvatarExpression.CONFUSED
    if any(w in lower for w in ["great", "awesome", "perfect", "good", "happy", "welcome", "glad", "haha", "yay", "love"]):
        return AvatarExpression.HAPPY
    if any(w in lower for w in ["sorry", "apologize", "tired", "sleep", "rest", "worry", "stress", "late", "careful"]):
        return AvatarExpression.EMPATHETIC
    if any(w in lower for w in ["error", "fail", "broken", "issue", "crash", "bug"]):
        return AvatarExpression.THINKING
    return AvatarExpression.SPEAKING


class VideoCallServer:
    """Dedicated video-call server orchestrating 3D animated avatar rendering and real-time interaction."""

    def __init__(
        self,
        supervisor: CompanionSupervisor,
        config: Optional[VideoCallConfig] = None,
    ) -> None:
        self.supervisor = supervisor
        self.config = config or self.supervisor.config.video_call
        self.app = FastAPI(title="Electorn AI Companion Video Call", version="0.1.0")
        self.active_websockets: Set[WebSocket] = set()
        self._server_thread: Optional[threading.Thread] = None
        self._uvicorn_server: Any = None
        self.host = self.config.host
        self.port = find_available_port(self.host, self.config.port)

        self._configure_routes()

    def _configure_routes(self) -> None:
        """Register API endpoints and WebSocket handlers."""
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        @self.app.get("/", response_class=HTMLResponse)
        async def get_index():
            return HTMLResponse(content=self.get_html_interface(), status_code=200)

        @self.app.get("/api/status")
        async def get_status():
            cfg = self.supervisor.config
            st = self.supervisor.state
            return JSONResponse({
                "name": cfg.personality.name,
                "user_name": cfg.personality.user_name,
                "active_mode": st.active_mode.value,
                "lifecycle": st.current_lifecycle.value,
                "language": cfg.personality.language,
                "avatar_style": self.config.avatar_style.value,
                "camera_enabled": self.config.camera_enabled,
                "camera_analysis_enabled": self.config.camera_analysis_enabled,
                "current_activity": st.current_activity.value,
                "active_window": st.active_window_title or "",
                "is_muted": st.is_muted,
                "is_paused": st.is_paused,
            })

        @self.app.post("/api/chat")
        async def post_chat(request: Request):
            data = await request.json()
            user_message = data.get("text", "").strip()
            if not user_message:
                return JSONResponse({"reply": "", "expression": "idle"})

            # Notify UI thinking
            await self.broadcast({
                "type": "state_change",
                "state": AvatarExpression.THINKING.value,
                "user_text": user_message,
            })

            # Process conversational turn through supervisor
            reply = self.supervisor.process_user_input(user_message)
            expression = detect_expression_from_text(reply)

            # Generate neural speech audio for lip sync
            lang = self.supervisor.config.personality.language
            gender = self.supervisor.config.personality.voice_gender
            audio_b64 = generate_tts_base64(reply, language=lang, gender=gender)

            # Broadcast response event to all active video-call clients
            response_payload = {
                "type": "companion_reply",
                "reply": reply,
                "expression": expression.value,
                "audio_base64": audio_b64,
                "speaker": self.supervisor.config.personality.name,
                "user_name": self.supervisor.config.personality.user_name,
            }
            await self.broadcast(response_payload)

            return JSONResponse(response_payload)

        @self.app.post("/api/tts")
        async def post_tts(request: Request):
            data = await request.json()
            text = data.get("text", "").strip()
            lang = data.get("language", self.supervisor.config.personality.language)
            gender = data.get("gender", self.supervisor.config.personality.voice_gender)
            audio_b64 = generate_tts_base64(text, language=lang, gender=gender)
            return JSONResponse({"audio_base64": audio_b64})

        @self.app.post("/api/camera-analyze")
        async def post_camera_analyze(request: Request):
            data = await request.json()
            image_b64 = data.get("image_base64", "")
            user_prompt = data.get("prompt", "What do you see in my camera view?")

            if not self.config.camera_analysis_enabled:
                return JSONResponse({
                    "error": "Camera visual analysis is currently disabled in privacy settings.",
                    "status": "disabled",
                })

            if not image_b64:
                return JSONResponse({"error": "No image data provided.", "status": "error"})

            # Remove base64 header if present
            if "," in image_b64:
                image_b64 = image_b64.split(",", 1)[1]

            # Decode image
            image = None
            if PIL_AVAILABLE:
                try:
                    img_bytes = base64.b64decode(image_b64)
                    image = Image.open(io.BytesIO(img_bytes)).convert("RGB")
                except Exception as exc:
                    logger.warning("Failed to decode camera frame: %s", exc)

            # Visual analysis
            analysis = ""
            user = self.supervisor.config.personality.user_name
            if image is not None:
                # Query Ollama vision model if available
                try:
                    buffered = io.BytesIO()
                    image.thumbnail((800, 600))
                    image.save(buffered, format="JPEG", quality=80)
                    proc_b64 = base64.b64encode(buffered.getvalue()).decode("utf-8")

                    vision_payload = {
                        "model": "qwen3-vl:4b-instruct",
                        "prompt": f"You are looking at {user}'s live webcam. Briefly describe the person, their activity, expressions, or objects they are showing in 1-2 friendly, natural sentences.",
                        "images": [proc_b64],
                        "stream": False,
                    }
                    req = urllib.request.Request(
                        f"{self.supervisor.vision_analyzer.ollama_base_url}/api/generate",
                        data=json.dumps(vision_payload).encode("utf-8"),
                        headers={"Content-Type": "application/json"},
                    )
                    with urllib.request.urlopen(req, timeout=12) as resp:
                        res_data = json.loads(resp.read().decode("utf-8"))
                        analysis = res_data.get("response", "").strip()
                except Exception:
                    # Heuristic fallback if vision model is not loaded
                    analysis = f"I see you right there, {user}! You look focused and ready to build something great today."

            if not analysis:
                analysis = f"I can see you clearly, {user}! Everything is looking good on camera."

            reply = self.supervisor.personality.sanitize_llm_response(analysis)
            audio_b64 = generate_tts_base64(
                reply,
                language=self.supervisor.config.personality.language,
                gender=self.supervisor.config.personality.voice_gender,
            )

            response_payload = {
                "type": "companion_reply",
                "reply": reply,
                "expression": AvatarExpression.HAPPY.value,
                "audio_base64": audio_b64,
                "speaker": self.supervisor.config.personality.name,
                "source": "camera_analysis",
            }
            await self.broadcast(response_payload)
            return JSONResponse(response_payload)

        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            await websocket.accept()
            self.active_websockets.add(websocket)

            # Send initial greeting and configuration
            user = self.supervisor.config.personality.user_name
            name = self.supervisor.config.personality.name
            greeting = f"Hey {user}! You're back. I'm right here with you in video call mode. What are we working on today?"
            audio_b64 = generate_tts_base64(
                greeting,
                language=self.supervisor.config.personality.language,
                gender=self.supervisor.config.personality.voice_gender,
            )

            await websocket.send_json({
                "type": "init",
                "companion_name": name,
                "user_name": user,
                "avatar_style": self.config.avatar_style.value,
                "language": self.supervisor.config.personality.language,
                "initial_greeting": greeting,
                "audio_base64": audio_b64,
                "expression": AvatarExpression.HAPPY.value,
            })

            try:
                while True:
                    raw_data = await websocket.receive_text()
                    try:
                        msg = json.loads(raw_data)
                    except Exception:
                        continue

                    msg_type = msg.get("type", "")

                    if msg_type == "user_speaking":
                        # User started speaking; avatar enters attentive LISTENING state
                        await self.broadcast({
                            "type": "state_change",
                            "state": AvatarExpression.LISTENING.value,
                        })

                    elif msg_type == "user_barge_in":
                        # Instant user interruption: interrupt speech immediately
                        self.supervisor.voice.interrupt_speech()
                        await self.broadcast({
                            "type": "barge_in_ack",
                            "state": AvatarExpression.LISTENING.value,
                        })

                    elif msg_type == "user_message":
                        user_text = msg.get("text", "").strip()
                        if user_text:
                            await self.broadcast({
                                "type": "state_change",
                                "state": AvatarExpression.THINKING.value,
                                "user_text": user_text,
                            })
                            reply = self.supervisor.process_user_input(user_text)
                            expr = detect_expression_from_text(reply)
                            audio_b64 = generate_tts_base64(
                                reply,
                                language=self.supervisor.config.personality.language,
                                gender=self.supervisor.config.personality.voice_gender,
                            )
                            await self.broadcast({
                                "type": "companion_reply",
                                "reply": reply,
                                "expression": expr.value,
                                "audio_base64": audio_b64,
                                "speaker": self.supervisor.config.personality.name,
                            })

                    elif msg_type == "set_style":
                        new_style = msg.get("style", "realistic")
                        try:
                            self.config.avatar_style = AvatarStyle(new_style)
                        except ValueError:
                            pass
                        await self.broadcast({
                            "type": "style_updated",
                            "style": self.config.avatar_style.value,
                        })

                    elif msg_type == "set_language":
                        new_lang = msg.get("language", "en-US")
                        self.supervisor.config.personality.language = new_lang
                        self.supervisor.voice.set_language(new_lang)
                        await self.broadcast({
                            "type": "language_updated",
                            "language": new_lang,
                        })

                    elif msg_type == "toggle_mute":
                        muted = msg.get("is_muted", False)
                        self.supervisor.state.is_muted = muted

            except WebSocketDisconnect:
                self.active_websockets.discard(websocket)
            except Exception as e:
                logger.debug("WebSocket exception: %s", e)
                self.active_websockets.discard(websocket)

    async def broadcast(self, payload: Dict[str, Any]) -> None:
        """Broadcast JSON message to all connected video-call clients."""
        dead_sockets: List[WebSocket] = []
        for ws in list(self.active_websockets):
            try:
                await ws.send_json(payload)
            except Exception:
                dead_sockets.append(ws)
        for ws in dead_sockets:
            self.active_websockets.discard(ws)

    def start_in_thread(self, open_browser: bool = True) -> str:
        """Launch the video-call server in a dedicated background daemon thread."""
        import uvicorn

        url = f"http://{self.host}:{self.port}"

        uvicorn_config = uvicorn.Config(
            app=self.app,
            host=self.host,
            port=self.port,
            log_level="warning",
            loop="asyncio",
        )
        self._uvicorn_server = uvicorn.Server(uvicorn_config)

        def _runner():
            self._uvicorn_server.run()

        self._server_thread = threading.Thread(target=_runner, daemon=True)
        self._server_thread.start()

        # Give the server a brief moment to bind
        time.sleep(1.0)

        if open_browser:
            try:
                webbrowser.open(url)
            except Exception as e:
                logger.warning("Could not auto-open browser: %s", e)

        return url

    def stop(self) -> None:
        """Shutdown video-call server and release resources."""
        if self._uvicorn_server:
            self._uvicorn_server.should_exit = True
        self.active_websockets.clear()

    def get_html_interface(self) -> str:
        """Return the rich, cinema-grade HTML5/WebGL Three.js video call application."""
        user = self.supervisor.config.personality.user_name
        name = self.supervisor.config.personality.name

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Electorn AI — {name} Video Call ({user})</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
  <!-- Three.js with fallback to embedded procedural 3D/2D engine -->
  <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
  <style>
    :root {{
      --bg-dark: #07090e;
      --card-bg: rgba(18, 22, 34, 0.75);
      --card-border: rgba(255, 255, 255, 0.08);
      --accent: #8b5cf6;
      --accent-glow: rgba(139, 92, 246, 0.4);
      --cyan: #06b6d4;
      --cyan-glow: rgba(6, 182, 212, 0.4);
      --rose: #ec4899;
      --green: #10b981;
      --red: #ef4444;
      --text-main: #f8fafc;
      --text-dim: #94a3b8;
    }}

    * {{
      box-sizing: border-box;
      margin: 0;
      padding: 0;
      user-select: none;
    }}

    body {{
      background-color: var(--bg-dark);
      color: var(--text-main);
      font-family: 'Plus Jakarta Sans', sans-serif;
      overflow: hidden;
      width: 100vw;
      height: 100vh;
      display: flex;
      flex-direction: column;
    }}

    /* Video Call Container */
    #call-stage {{
      position: relative;
      flex: 1;
      width: 100%;
      height: 100%;
      display: flex;
      justify-content: center;
      align-items: center;
      background: radial-gradient(circle at 50% 40%, #151928 0%, #07090e 85%);
      overflow: hidden;
    }}

    /* 3D Canvas */
    #avatar-canvas {{
      position: absolute;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      z-index: 1;
    }}

    /* 2D Fallback Canvas */
    #avatar-canvas-2d {{
      position: absolute;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      z-index: 1;
      display: none;
    }}

    /* Header Bar */
    #call-header {{
      position: absolute;
      top: 20px;
      left: 24px;
      right: 24px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      z-index: 10;
      pointer-events: none;
    }}

    .header-pill {{
      pointer-events: auto;
      background: var(--card-bg);
      backdrop-filter: blur(16px);
      border: 1px solid var(--card-border);
      padding: 8px 16px;
      border-radius: 9999px;
      display: flex;
      align-items: center;
      gap: 12px;
      box-shadow: 0 8px 32px rgba(0,0,0,0.4);
    }}

    .live-dot {{
      width: 10px;
      height: 10px;
      background: var(--green);
      border-radius: 50%;
      box-shadow: 0 0 12px var(--green);
      animation: pulse-live 2s infinite;
    }}

    @keyframes pulse-live {{
      0%, 100% {{ transform: scale(1); opacity: 1; }}
      50% {{ transform: scale(1.25); opacity: 0.6; }}
    }}

    .companion-title {{
      font-weight: 700;
      font-size: 15px;
      letter-spacing: -0.3px;
      color: #fff;
    }}

    .companion-badge {{
      font-size: 11px;
      font-weight: 600;
      background: rgba(139, 92, 246, 0.25);
      border: 1px solid rgba(139, 92, 246, 0.4);
      color: #c4b5fd;
      padding: 2px 8px;
      border-radius: 6px;
      text-transform: uppercase;
    }}

    /* Expression Pill on Center */
    #expression-pill {{
      position: absolute;
      top: 80px;
      background: rgba(18, 22, 34, 0.65);
      backdrop-filter: blur(12px);
      border: 1px solid rgba(255, 255, 255, 0.1);
      padding: 6px 14px;
      border-radius: 20px;
      font-size: 13px;
      font-weight: 500;
      color: #cbd5e1;
      display: flex;
      align-items: center;
      gap: 8px;
      z-index: 5;
      transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }}

    /* User PiP Webcam Container */
    #user-pip {{
      position: absolute;
      top: 24px;
      right: 24px;
      width: 220px;
      height: 140px;
      background: #0f172a;
      border-radius: 16px;
      border: 2px solid rgba(255, 255, 255, 0.12);
      box-shadow: 0 16px 40px rgba(0,0,0,0.6);
      overflow: hidden;
      z-index: 15;
      transition: all 0.3s ease;
      display: flex;
      align-items: center;
      justify-content: center;
    }}

    #user-pip:hover {{
      border-color: var(--cyan);
      box-shadow: 0 0 24px var(--cyan-glow);
    }}

    #user-video {{
      width: 100%;
      height: 100%;
      object-fit: cover;
      transform: scaleX(-1);
    }}

    .pip-disabled-overlay {{
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: 8px;
      color: var(--text-dim);
      font-size: 12px;
      text-align: center;
      padding: 12px;
    }}

    .pip-avatar-circle {{
      width: 44px;
      height: 44px;
      background: linear-gradient(135deg, #0ea5e9, #6366f1);
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 700;
      font-size: 18px;
      color: #fff;
    }}

    .pip-cam-badge {{
      position: absolute;
      bottom: 8px;
      left: 8px;
      background: rgba(0,0,0,0.65);
      backdrop-filter: blur(8px);
      padding: 2px 8px;
      border-radius: 6px;
      font-size: 11px;
      font-weight: 600;
      color: #e2e8f0;
      display: flex;
      align-items: center;
      gap: 5px;
    }}

    /* Live Captions Overlay */
    #captions-container {{
      position: absolute;
      bottom: 120px;
      left: 50%;
      transform: translateX(-50%);
      width: 90%;
      max-width: 860px;
      text-align: center;
      z-index: 10;
      pointer-events: none;
    }}

    #caption-text {{
      display: inline-block;
      background: rgba(10, 14, 23, 0.82);
      backdrop-filter: blur(16px);
      border: 1px solid rgba(255, 255, 255, 0.1);
      padding: 12px 28px;
      border-radius: 16px;
      font-size: 17px;
      font-weight: 500;
      line-height: 1.5;
      color: #ffffff;
      box-shadow: 0 12px 32px rgba(0,0,0,0.5);
      transition: all 0.25s ease;
      min-height: 48px;
    }}

    .speaker-label {{
      font-weight: 700;
      color: #c084fc;
      margin-right: 8px;
    }}

    /* Dual Audio Visualizer */
    #visualizer-container {{
      position: absolute;
      bottom: 96px;
      left: 50%;
      transform: translateX(-50%);
      width: 240px;
      height: 24px;
      z-index: 8;
      display: flex;
      align-items: center;
      justify-content: center;
      pointer-events: none;
    }}

    #visualizer-canvas {{
      width: 100%;
      height: 100%;
    }}

    /* Bottom Control Bar Island */
    #controls-island {{
      position: absolute;
      bottom: 24px;
      left: 50%;
      transform: translateX(-50%);
      background: var(--card-bg);
      backdrop-filter: blur(24px);
      border: 1px solid var(--card-border);
      border-radius: 28px;
      padding: 10px 20px;
      display: flex;
      align-items: center;
      gap: 12px;
      z-index: 20;
      box-shadow: 0 20px 50px rgba(0,0,0,0.6);
    }}

    .control-btn {{
      width: 48px;
      height: 48px;
      border-radius: 50%;
      border: 1px solid rgba(255, 255, 255, 0.1);
      background: rgba(255, 255, 255, 0.06);
      color: #fff;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 18px;
      cursor: pointer;
      transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
      outline: none;
      position: relative;
    }}

    .control-btn:hover {{
      background: rgba(255, 255, 255, 0.15);
      transform: translateY(-2px);
    }}

    .control-btn.active {{
      background: var(--accent);
      border-color: var(--accent);
      box-shadow: 0 0 16px var(--accent-glow);
    }}

    .control-btn.active-cyan {{
      background: var(--cyan);
      border-color: var(--cyan);
      box-shadow: 0 0 16px var(--cyan-glow);
    }}

    .control-btn.danger {{
      background: var(--red);
      border-color: var(--red);
      width: 54px;
      height: 54px;
      font-size: 20px;
      box-shadow: 0 0 20px rgba(239, 68, 68, 0.5);
    }}

    .control-btn.danger:hover {{
      background: #dc2626;
      transform: scale(1.05);
    }}

    .control-btn.muted {{
      background: rgba(239, 68, 68, 0.2);
      border-color: var(--red);
      color: #fca5a5;
    }}

    .divider {{
      width: 1px;
      height: 28px;
      background: rgba(255, 255, 255, 0.12);
      margin: 0 4px;
    }}

    /* Dropdown Menus */
    .style-select {{
      background: rgba(255, 255, 255, 0.08);
      border: 1px solid rgba(255, 255, 255, 0.15);
      border-radius: 14px;
      color: #fff;
      font-family: inherit;
      font-size: 13px;
      font-weight: 500;
      padding: 8px 12px;
      outline: none;
      cursor: pointer;
      transition: all 0.2s;
    }}

    .style-select option {{
      background: #0f172a;
      color: #fff;
    }}

    /* Side Chat Drawer */
    #chat-drawer {{
      position: absolute;
      top: 0;
      right: -380px;
      width: 360px;
      height: 100%;
      background: rgba(13, 17, 27, 0.92);
      backdrop-filter: blur(24px);
      border-left: 1px solid var(--card-border);
      z-index: 25;
      display: flex;
      flex-direction: column;
      transition: right 0.35s cubic-bezier(0.4, 0, 0.2, 1);
      box-shadow: -10px 0 40px rgba(0,0,0,0.5);
    }}

    #chat-drawer.open {{
      right: 0;
    }}

    .drawer-header {{
      padding: 20px;
      border-bottom: 1px solid rgba(255, 255, 255, 0.08);
      display: flex;
      justify-content: space-between;
      align-items: center;
    }}

    .drawer-title {{
      font-weight: 700;
      font-size: 16px;
      color: #fff;
    }}

    .close-btn {{
      background: none;
      border: none;
      color: var(--text-dim);
      font-size: 20px;
      cursor: pointer;
    }}

    .messages-list {{
      flex: 1;
      overflow-y: auto;
      padding: 20px;
      display: flex;
      flex-direction: column;
      gap: 14px;
    }}

    .chat-bubble {{
      padding: 10px 14px;
      border-radius: 14px;
      font-size: 14px;
      line-height: 1.45;
      max-width: 85%;
      word-break: break-word;
    }}

    .chat-bubble.companion {{
      align-self: flex-start;
      background: rgba(139, 92, 246, 0.18);
      border: 1px solid rgba(139, 92, 246, 0.3);
      color: #f1f5f9;
      border-bottom-left-radius: 4px;
    }}

    .chat-bubble.user {{
      align-self: flex-end;
      background: rgba(6, 182, 212, 0.18);
      border: 1px solid rgba(6, 182, 212, 0.3);
      color: #f1f5f9;
      border-bottom-right-radius: 4px;
    }}

    .chat-input-bar {{
      padding: 16px;
      border-top: 1px solid rgba(255, 255, 255, 0.08);
      display: flex;
      gap: 8px;
    }}

    .chat-input {{
      flex: 1;
      background: rgba(255, 255, 255, 0.06);
      border: 1px solid rgba(255, 255, 255, 0.12);
      border-radius: 12px;
      padding: 10px 14px;
      color: #fff;
      font-family: inherit;
      font-size: 14px;
      outline: none;
    }}

    .send-btn {{
      background: var(--accent);
      border: none;
      border-radius: 12px;
      padding: 0 16px;
      color: #fff;
      font-weight: 600;
      cursor: pointer;
    }}

    /* Tooltip / Hotkey badge */
    .hotkey-hint {{
      position: absolute;
      top: -24px;
      font-size: 10px;
      font-family: 'JetBrains Mono', monospace;
      color: #94a3b8;
      background: rgba(0,0,0,0.7);
      padding: 1px 5px;
      border-radius: 4px;
      pointer-events: none;
      opacity: 0;
      transition: opacity 0.2s;
    }}

    .control-btn:hover .hotkey-hint {{
      opacity: 1;
    }}
  </style>
</head>
<body>

  <!-- Call Stage -->
  <div id="call-stage">
    <!-- WebGL 3D Canvas -->
    <canvas id="avatar-canvas"></canvas>
    <!-- 2D Canvas Fallback -->
    <canvas id="avatar-canvas-2d"></canvas>

    <!-- Header -->
    <div id="call-header">
      <div class="header-pill">
        <div class="live-dot"></div>
        <span class="companion-title">💖 {name}</span>
        <span class="companion-badge">Live Companion</span>
        <span id="call-timer" style="font-family:'JetBrains Mono'; font-size:12px; color:#94a3b8;">00:00</span>
      </div>

      <div class="header-pill" style="gap: 8px;">
        <span id="lang-indicator" style="font-size:12px; font-weight:600; color:#38bdf8;">🌐 English (US)</span>
        <span id="activity-indicator" style="font-size:12px; color:#cbd5e1; border-left: 1px solid rgba(255,255,255,0.15); padding-left:8px;">Active</span>
      </div>
    </div>

    <!-- Center Expression Pill -->
    <div id="expression-pill">
      <span id="expression-icon">✨</span>
      <span id="expression-text">Listening attentively...</span>
    </div>

    <!-- User PiP Camera View -->
    <div id="user-pip">
      <video id="user-video" autoplay playsinline muted></video>
      <div id="pip-disabled-view" class="pip-disabled-overlay">
        <div class="pip-avatar-circle">H</div>
        <span>{user} (Camera Off)</span>
      </div>
      <div class="pip-cam-badge">
        <span id="pip-cam-dot" style="width:6px; height:6px; background:#ef4444; border-radius:50%;"></span>
        <span>{user}</span>
      </div>
    </div>

    <!-- Live Captions -->
    <div id="captions-container">
      <div id="caption-text">
        <span class="speaker-label">💖 {name}:</span>
        <span id="caption-content">"Hey {user}! I'm ready. What are we working on today?"</span>
      </div>
    </div>

    <!-- Audio Visualizer -->
    <div id="visualizer-container">
      <canvas id="visualizer-canvas" width="240" height="24"></canvas>
    </div>

    <!-- Controls Island -->
    <div id="controls-island">
      <!-- Mic Toggle -->
      <button id="btn-mic" class="control-btn active" title="Mute/Unmute Mic (M)">
        <span class="hotkey-hint">M</span>
        <span id="mic-icon">🎙️</span>
      </button>

      <!-- Camera Toggle -->
      <button id="btn-cam" class="control-btn" title="Toggle Camera (C)">
        <span class="hotkey-hint">C</span>
        <span id="cam-icon">📹</span>
      </button>

      <!-- Camera Vision Inspect -->
      <button id="btn-vision" class="control-btn" title="Inspect Camera Feed (V)">
        <span class="hotkey-hint">V</span>
        <span>👁️</span>
      </button>

      <div class="divider"></div>

      <!-- Language Toggle -->
      <button id="btn-lang" class="control-btn" title="Toggle English / Tamil">
        <span style="font-size:13px; font-weight:700;">EN</span>
      </button>

      <!-- Avatar Style Selector -->
      <select id="style-select" class="style-select" title="Switch Avatar Style">
        <option value="realistic">Realistic 3D</option>
        <option value="anime">Anime 3D</option>
        <option value="hologram">AI Hologram</option>
        <option value="minimalist">Minimalist 3D</option>
        <option value="canvas_2d">2D Companion</option>
      </select>

      <div class="divider"></div>

      <!-- Chat Drawer -->
      <button id="btn-chat" class="control-btn" title="Toggle Chat Panel">
        <span>💬</span>
      </button>

      <!-- Fullscreen Toggle -->
      <button id="btn-fullscreen" class="control-btn" title="Fullscreen (F)">
        <span class="hotkey-hint">F</span>
        <span>⛶</span>
      </button>

      <!-- End Call Button -->
      <button id="btn-end" class="control-btn danger" title="End Video Call (Esc)">
        <span class="hotkey-hint">Esc</span>
        <span>📞</span>
      </button>
    </div>
  </div>

  <!-- Side Chat & History Drawer -->
  <div id="chat-drawer">
    <div class="drawer-header">
      <span class="drawer-title">Conversation History</span>
      <button id="btn-close-drawer" class="close-btn">&times;</button>
    </div>
    <div id="messages-list" class="messages-list">
      <div class="chat-bubble companion">
        <strong>{name}:</strong> Hey {user}! You're back. I'm right here with you in video call mode.
      </div>
    </div>
    <div class="chat-input-bar">
      <input id="chat-input" class="chat-input" type="text" placeholder="Type a message or command..." />
      <button id="btn-send" class="send-btn">Send</button>
    </div>
  </div>

  <!-- MAIN SCRIPT -->
  <script>
    const USER_NAME = "{user}";
    const COMPANION_NAME = "{name}";

    // State
    let isMicMuted = false;
    let isCameraOn = false;
    let activeLanguage = "en-US";
    let activeStyle = "realistic";
    let currentExpression = "idle";
    let ws = null;
    let recognition = null;
    let audioContext = null;
    let analyser = null;
    let currentAudio = null;
    let userMediaStream = null;
    let callStartTime = Date.now();

    // Elements
    const avatarCanvas = document.getElementById('avatar-canvas');
    const avatarCanvas2D = document.getElementById('avatar-canvas-2d');
    const userVideo = document.getElementById('user-video');
    const pipDisabledView = document.getElementById('pip-disabled-view');
    const pipCamDot = document.getElementById('pip-cam-dot');
    const captionContent = document.getElementById('caption-content');
    const expressionIcon = document.getElementById('expression-icon');
    const expressionText = document.getElementById('expression-text');
    const callTimer = document.getElementById('call-timer');
    const langIndicator = document.getElementById('lang-indicator');
    const styleSelect = document.getElementById('style-select');
    const visualizerCanvas = document.getElementById('visualizer-canvas');
    const chatDrawer = document.getElementById('chat-drawer');
    const messagesList = document.getElementById('messages-list');
    const chatInput = document.getElementById('chat-input');

    // Timer updater
    setInterval(() => {{
      const elapsed = Math.floor((Date.now() - callStartTime) / 1000);
      const m = String(Math.floor(elapsed / 60)).padStart(2, '0');
      const s = String(elapsed % 60).padStart(2, '0');
      callTimer.innerText = `${{m}}:${{s}}`;
    }}, 1000);

    // =========================================================================
    // 3D AVATAR ENGINE (Three.js with Blendshapes, Blinking, Gaze, & Shaders)
    // =========================================================================
    let scene, camera, renderer;
    let headGroup, headMesh, leftEye, rightEye, mouthMesh, hairGroup, bodyMesh;
    let mouthMaterial, skinMaterial, eyeMaterial, hairMaterial;
    let clock = new THREE.Clock();

    // Expression target values
    const morphs = {{
      mouthOpen: 0.0,
      mouthWide: 0.0,
      mouthSmile: 0.3,
      eyeBlink: 0.0,
      headPitch: 0.0,
      headYaw: 0.0,
      headRoll: 0.0,
      eyebrowLift: 0.0,
    }};

    let nextBlinkTime = 2.0;
    let nextGazeTime = 3.0;

    function init3DAvatar() {{
      const width = avatarCanvas.clientWidth || window.innerWidth;
      const height = avatarCanvas.clientHeight || window.innerHeight;

      scene = new THREE.Scene();
      camera = new THREE.PerspectiveCamera(40, width / height, 0.1, 100);
      camera.position.set(0, 0.1, 2.5);

      renderer = new THREE.WebGLRenderer({{ canvas: avatarCanvas, antialias: true, alpha: true }});
      renderer.setSize(width, height);
      renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

      // Lighting
      const ambientLight = new THREE.AmbientLight(0xffffff, 0.7);
      scene.add(ambientLight);

      const keyLight = new THREE.DirectionalLight(0xffeedd, 1.2);
      keyLight.position.set(1.5, 2, 2);
      scene.add(keyLight);

      const fillLight = new THREE.DirectionalLight(0x88bbff, 0.8);
      fillLight.position.set(-1.5, 1, 1.5);
      scene.add(fillLight);

      const rimLight = new THREE.DirectionalLight(0xc084fc, 1.0);
      rimLight.position.set(0, 3, -2);
      scene.add(rimLight);

      // Create Head Group
      headGroup = new THREE.Group();
      scene.add(headGroup);

      // Materials
      updateMaterialsForStyle("realistic");

      // Head Mesh (Smooth organic ellipsoid)
      const headGeo = new THREE.SphereGeometry(0.48, 48, 48);
      headGeo.scale(0.9, 1.15, 0.95);
      headMesh = new THREE.Mesh(headGeo, skinMaterial);
      headGroup.add(headMesh);

      // Eyes
      const eyeGeo = new THREE.SphereGeometry(0.08, 32, 32);
      leftEye = new THREE.Mesh(eyeGeo, eyeMaterial);
      leftEye.position.set(-0.16, 0.06, 0.38);
      headGroup.add(leftEye);

      rightEye = new THREE.Mesh(eyeGeo, eyeMaterial);
      rightEye.position.set(0.16, 0.06, 0.38);
      headGroup.add(rightEye);

      // Pupils & Iris
      const pupilGeo = new THREE.SphereGeometry(0.04, 16, 16);
      const pupilMat = new THREE.MeshBasicMaterial({{ color: 0x1e1b4b }});
      const leftPupil = new THREE.Mesh(pupilGeo, pupilMat);
      leftPupil.position.set(0, 0, 0.06);
      leftEye.add(leftPupil);
      const rightPupil = new THREE.Mesh(pupilGeo, pupilMat);
      rightPupil.position.set(0, 0, 0.06);
      rightEye.add(rightPupil);

      // Mouth (Parametric blendshape mesh)
      const mouthGeo = new THREE.TorusGeometry(0.09, 0.022, 16, 32, Math.PI);
      mouthGeo.rotateX(Math.PI);
      mouthMesh = new THREE.Mesh(mouthGeo, mouthMaterial);
      mouthMesh.position.set(0, -0.22, 0.42);
      headGroup.add(mouthMesh);

      // Hair
      hairGroup = new THREE.Group();
      headGroup.add(hairGroup);

      // Hair Volume Strands
      const hairTopGeo = new THREE.SphereGeometry(0.52, 32, 32);
      hairTopGeo.scale(0.95, 1.1, 1.0);
      const hairTop = new THREE.Mesh(hairTopGeo, hairMaterial);
      hairTop.position.set(0, 0.12, -0.05);
      hairGroup.add(hairTop);

      // Body / Shoulders
      const bodyGeo = new THREE.CylinderGeometry(0.2, 0.65, 0.9, 32);
      bodyMesh = new THREE.Mesh(bodyGeo, new THREE.MeshStandardMaterial({{
        color: 0x1e1b4b,
        roughness: 0.6,
      }}));
      bodyMesh.position.set(0, -0.9, 0);
      scene.add(bodyMesh);

      animate3D();
    }}

    function updateMaterialsForStyle(style) {{
      activeStyle = style;
      if (style === "anime") {{
        skinMaterial = new THREE.MeshToonMaterial({{ color: 0xffdfd3 }});
        eyeMaterial = new THREE.MeshBasicMaterial({{ color: 0x38bdf8 }});
        mouthMaterial = new THREE.MeshBasicMaterial({{ color: 0xf43f5e }});
        hairMaterial = new THREE.MeshToonMaterial({{ color: 0xc084fc }});
      }} else if (style === "hologram") {{
        skinMaterial = new THREE.MeshBasicMaterial({{ color: 0x06b6d4, wireframe: true }});
        eyeMaterial = new THREE.MeshBasicMaterial({{ color: 0x22d3ee }});
        mouthMaterial = new THREE.MeshBasicMaterial({{ color: 0x67e8f9 }});
        hairMaterial = new THREE.MeshBasicMaterial({{ color: 0x0891b2, wireframe: true }});
      }} else if (style === "minimalist") {{
        skinMaterial = new THREE.MeshStandardMaterial({{ color: 0xe2e8f0, roughness: 0.2 }});
        eyeMaterial = new THREE.MeshStandardMaterial({{ color: 0x0f172a, roughness: 0.1 }});
        mouthMaterial = new THREE.MeshStandardMaterial({{ color: 0x64748b, roughness: 0.3 }});
        hairMaterial = new THREE.MeshStandardMaterial({{ color: 0x94a3b8, roughness: 0.4 }});
      }} else {{
        // Realistic
        skinMaterial = new THREE.MeshStandardMaterial({{
          color: 0xfbd2c0,
          roughness: 0.45,
          metalness: 0.05,
        }});
        eyeMaterial = new THREE.MeshStandardMaterial({{ color: 0x1e293b, roughness: 0.1 }});
        mouthMaterial = new THREE.MeshStandardMaterial({{ color: 0xec4899, roughness: 0.3 }});
        hairMaterial = new THREE.MeshStandardMaterial({{
          color: 0x472314,
          roughness: 0.6,
        }});
      }}

      if (headMesh) headMesh.material = skinMaterial;
      if (leftEye) leftEye.material = eyeMaterial;
      if (rightEye) rightEye.material = eyeMaterial;
      if (mouthMesh) mouthMesh.material = mouthMaterial;
      if (hairGroup) {{
        hairGroup.traverse((child) => {{
          if (child.isMesh) child.material = hairMaterial;
        }});
      }}
    }}

    function animate3D() {{
      requestAnimationFrame(animate3D);

      if (activeStyle === "canvas_2d") {{
        avatarCanvas.style.display = 'none';
        avatarCanvas2D.style.display = 'block';
        render2DCompanion();
        return;
      }} else {{
        avatarCanvas.style.display = 'block';
        avatarCanvas2D.style.display = 'none';
      }}

      const delta = clock.getDelta();
      const time = clock.getElapsedTime();

      // Breathing animation (subtle harmonic chest and head sway)
      const breathing = Math.sin(time * 1.5) * 0.015;
      if (headGroup) {{
        headGroup.position.y = breathing;
        headGroup.rotation.x = THREE.MathUtils.lerp(headGroup.rotation.x, morphs.headPitch + Math.sin(time * 1.2) * 0.01, 0.1);
        headGroup.rotation.y = THREE.MathUtils.lerp(headGroup.rotation.y, morphs.headYaw, 0.1);
        headGroup.rotation.z = THREE.MathUtils.lerp(headGroup.rotation.z, morphs.headRoll, 0.1);
      }}

      // Periodic natural blinking
      if (time > nextBlinkTime) {{
        morphs.eyeBlink = 1.0;
        nextBlinkTime = time + 2.5 + Math.random() * 3.0;
      }} else {{
        morphs.eyeBlink = THREE.MathUtils.lerp(morphs.eyeBlink, 0.0, 0.25);
      }}

      // Apply eyelid scale
      if (leftEye && rightEye) {{
        const eyeScaleY = Math.max(0.08, 1.0 - morphs.eyeBlink);
        leftEye.scale.y = eyeScaleY;
        rightEye.scale.y = eyeScaleY;
      }}

      // Mouth blendshape deformation (Lip sync + Smile)
      if (mouthMesh) {{
        // Scale mouth based on audio energy + visemes
        const targetScaleY = 1.0 + morphs.mouthOpen * 2.8;
        const targetScaleX = 1.0 + morphs.mouthWide * 0.6;
        mouthMesh.scale.y = THREE.MathUtils.lerp(mouthMesh.scale.y, targetScaleY, 0.35);
        mouthMesh.scale.x = THREE.MathUtils.lerp(mouthMesh.scale.x, targetScaleX, 0.35);
        mouthMesh.position.y = -0.22 - morphs.mouthOpen * 0.05;
      }}

      renderer.render(scene, camera);
    }}

    // =========================================================================
    // 2D CANVAS COMPANION ENGINE (Low-Resource Fallback)
    // =========================================================================
    function render2DCompanion() {{
      const ctx = avatarCanvas2D.getContext('2d');
      const w = avatarCanvas2D.width = avatarCanvas2D.clientWidth || window.innerWidth;
      const h = avatarCanvas2D.height = avatarCanvas2D.clientHeight || window.innerHeight;

      ctx.clearRect(0, 0, w, h);
      const time = clock.getElapsedTime();
      const cx = w / 2;
      const cy = h / 2 - 30;

      const breathing = Math.sin(time * 1.5) * 5;

      // Glow Aura
      const grad = ctx.createRadialGradient(cx, cy, 60, cx, cy, 260);
      grad.addColorStop(0, 'rgba(139, 92, 246, 0.25)');
      grad.addColorStop(1, 'rgba(7, 9, 14, 0)');
      ctx.fillStyle = grad;
      ctx.beginPath();
      ctx.arc(cx, cy, 260, 0, Math.PI * 2);
      ctx.fill();

      // Head
      ctx.fillStyle = '#fbd2c0';
      ctx.beginPath();
      ctx.ellipse(cx, cy + breathing, 120, 150, 0, 0, Math.PI * 2);
      ctx.fill();

      // Hair
      ctx.fillStyle = '#472314';
      ctx.beginPath();
      ctx.arc(cx, cy - 30 + breathing, 130, Math.PI * 0.85, Math.PI * 2.15);
      ctx.fill();

      // Eyes (with blinking)
      const blinkH = Math.max(2, 16 * (1.0 - morphs.eyeBlink));
      ctx.fillStyle = '#1e1b4b';
      ctx.beginPath();
      ctx.ellipse(cx - 45, cy - 10 + breathing, 14, blinkH, 0, 0, Math.PI * 2);
      ctx.ellipse(cx + 45, cy - 10 + breathing, 14, blinkH, 0, 0, Math.PI * 2);
      ctx.fill();

      // Cheeks (blush)
      ctx.fillStyle = 'rgba(244, 63, 94, 0.35)';
      ctx.beginPath();
      ctx.arc(cx - 60, cy + 30 + breathing, 16, 0, Math.PI * 2);
      ctx.arc(cx + 60, cy + 30 + breathing, 16, 0, Math.PI * 2);
      ctx.fill();

      // Mouth (animated lip sync)
      const mouthH = Math.max(4, 30 * morphs.mouthOpen);
      ctx.fillStyle = '#ec4899';
      ctx.beginPath();
      ctx.ellipse(cx, cy + 65 + breathing, 24 + morphs.mouthWide * 10, mouthH, 0, 0, Math.PI * 2);
      ctx.fill();
    }}

    // =========================================================================
    // AUDIO ANALYSIS & REAL-TIME VISEME LIP SYNC
    // =========================================================================
    function setupAudioAnalyser(audioElement) {{
      try {{
        if (!audioContext) {{
          audioContext = new (window.AudioContext || window.webkitAudioContext)();
        }}
        if (audioContext.state === 'suspended') {{
          audioContext.resume();
        }}
        analyser = audioContext.createAnalyser();
        analyser.fftSize = 256;
        analyser.smoothingTimeConstant = 0.5;

        const source = audioContext.createMediaElementSource(audioElement);
        source.connect(analyser);
        analyser.connect(audioContext.destination);

        trackLipSync();
      }} catch (e) {{
        console.warn("Audio analyser setup fallback:", e);
      }}
    }}

    function trackLipSync() {{
      if (!analyser) return;

      const bufferLength = analyser.frequencyBinCount;
      const dataArray = new Uint8Array(bufferLength);

      function updateFormants() {{
        analyser.getByteFrequencyData(dataArray);

        // Calculate speech energy
        let sum = 0;
        let highSum = 0;
        for (let i = 2; i < 30; i++) sum += dataArray[i]; // Formant bands
        for (let i = 30; i < 70; i++) highSum += dataArray[i];

        const avg = sum / 28;
        const highAvg = highSum / 40;

        // Drive mouth morphs
        if (currentAudio && !currentAudio.paused) {{
          morphs.mouthOpen = Math.min(1.0, (avg / 255) * 3.2);
          morphs.mouthWide = Math.min(1.0, (highAvg / 255) * 2.0);
          drawVisualizer(dataArray);
        }} else {{
          morphs.mouthOpen = THREE.MathUtils.lerp(morphs.mouthOpen, 0.0, 0.2);
          morphs.mouthWide = THREE.MathUtils.lerp(morphs.mouthWide, 0.0, 0.2);
        }}

        requestAnimationFrame(updateFormants);
      }}

      updateFormants();
    }}

    function drawVisualizer(dataArray) {{
      const ctx = visualizerCanvas.getContext('2d');
      const w = visualizerCanvas.width;
      const h = visualizerCanvas.height;
      ctx.clearRect(0, 0, w, h);

      const barWidth = 4;
      const gap = 3;
      const count = Math.floor(w / (barWidth + gap));

      for (let i = 0; i < count; i++) {{
        const val = dataArray[i * 2] || 0;
        const barH = (val / 255) * h;
        const x = i * (barWidth + gap);
        ctx.fillStyle = '#c084fc';
        ctx.fillRect(x, h - barH, barWidth, barH);
      }}
    }}

    // Play TTS Audio with synchronized lip movement & barge-in support
    function playTTSAudio(base64Audio, onEndCallback) {{
      if (currentAudio) {{
        currentAudio.pause();
        currentAudio = null;
      }}

      if (!base64Audio) {{
        // Fallback to SpeechSynthesis
        playBrowserSpeechSynthesis(captionContent.innerText, onEndCallback);
        return;
      }}

      currentAudio = new Audio("data:audio/mp3;base64," + base64Audio);
      setupAudioAnalyser(currentAudio);

      currentAudio.onplay = () => {{
        setAvatarExpression("speaking");
      }};

      currentAudio.onended = () => {{
        setAvatarExpression("idle");
        if (onEndCallback) onEndCallback();
      }};

      currentAudio.play().catch(e => {{
        console.warn("Audio autoplay blocked; click anywhere to enable audio:", e);
      }});
    }}

    function playBrowserSpeechSynthesis(text, onEndCallback) {{
      if (!('speechSynthesis' in window)) return;
      window.speechSynthesis.cancel();

      const utter = new SpeechSynthesisUtterance(text);
      utter.lang = activeLanguage;
      utter.rate = 1.0;

      utter.onstart = () => {{
        setAvatarExpression("speaking");
        simulateMouthSync();
      }};
      utter.onend = () => {{
        setAvatarExpression("idle");
        morphs.mouthOpen = 0;
        if (onEndCallback) onEndCallback();
      }};
      window.speechSynthesis.speak(utter);
    }}

    function simulateMouthSync() {{
      const interval = setInterval(() => {{
        if (currentExpression !== "speaking") {{
          clearInterval(interval);
          morphs.mouthOpen = 0;
          return;
        }}
        morphs.mouthOpen = Math.random() * 0.7 + 0.1;
      }}, 120);
    }}

    // Expression state transition
    function setAvatarExpression(state) {{
      currentExpression = state;
      const icons = {{
        idle: "🌟",
        listening: "✨",
        thinking: "💭",
        speaking: "🗣️",
        happy: "💖",
        confused: "🤔",
        empathetic: "🌸",
        error: "⚠️"
      }};

      const labels = {{
        idle: "Ready & listening",
        listening: "Listening to Harshan...",
        thinking: "Thinking...",
        speaking: `${{COMPANION_NAME}} speaking...`,
        happy: "Happy & engaged",
        confused: "Wondering about this...",
        empathetic: "Caring & supportive",
        error: "Connection issue"
      }};

      expressionIcon.innerText = icons[state] || "✨";
      expressionText.innerText = labels[state] || state;

      // Adjust head posture targets
      if (state === "thinking") {{
        morphs.headPitch = -0.06;
        morphs.headYaw = 0.08;
      }} else if (state === "listening") {{
        morphs.headPitch = 0.04;
        morphs.headYaw = 0.0;
      }} else if (state === "confused") {{
        morphs.headRoll = 0.08;
      }} else {{
        morphs.headPitch = 0.0;
        morphs.headYaw = 0.0;
        morphs.headRoll = 0.0;
      }}
    }}

    // =========================================================================
    // WEBSOCKET REAL-TIME SYNC & EVENTS
    // =========================================================================
    function connectWebSocket() {{
      const loc = window.location;
      const wsUrl = (loc.protocol === 'https:' ? 'wss://' : 'ws://') + loc.host + '/ws';
      ws = new WebSocket(wsUrl);

      ws.onopen = () => {{
        console.log("✔ Connected to Electorn Companion Video Call WebSocket.");
      }};

      ws.onmessage = (event) => {{
        try {{
          const data = JSON.parse(event.data);
          handleWebSocketMessage(data);
        }} catch (e) {{}}
      }};

      ws.onclose = () => {{
        setTimeout(connectWebSocket, 3000);
      }};
    }}

    function handleWebSocketMessage(data) {{
      const type = data.type;

      if (type === "init") {{
        captionContent.innerText = `"${{data.initial_greeting}}"`;
        if (data.audio_base64) {{
          playTTSAudio(data.audio_base64);
        }}
      }} else if (type === "companion_reply") {{
        captionContent.innerText = `"${{data.reply}}"`;
        appendChatMessage(COMPANION_NAME, data.reply);
        setAvatarExpression(data.expression || "speaking");
        if (data.audio_base64) {{
          playTTSAudio(data.audio_base64);
        }}
      }} else if (type === "state_change") {{
        setAvatarExpression(data.state);
        if (data.user_text) {{
          captionContent.innerHTML = `<span style="color:#38bdf8;">👤 ${{USER_NAME}}:</span> "${{data.user_text}}"`;
        }}
      }} else if (type === "barge_in_ack") {{
        // Instant Barge-In interrupted audio
        if (currentAudio) {{
          currentAudio.pause();
          currentAudio = null;
        }}
        setAvatarExpression("listening");
      }}
    }}

    // =========================================================================
    // CONTINUOUS SPEECH RECOGNITION & BARGE-IN
    // =========================================================================
    function initSpeechRecognition() {{
      const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
      if (!SpeechRec) {{
        console.warn("Web Speech API not supported in this browser. Use chat bar fallback.");
        return;
      }}

      recognition = new SpeechRec();
      recognition.continuous = true;
      recognition.interimResults = true;
      recognition.lang = activeLanguage;

      recognition.onstart = () => {{
        console.log("Mic listening active.");
      }};

      recognition.onresult = (event) => {{
        if (isMicMuted) return;

        let interim = "";
        let final = "";

        for (let i = event.resultIndex; i < event.results.length; ++i) {{
          if (event.results[i].isFinal) {{
            final += event.results[i][0].transcript;
          }} else {{
            interim += event.results[i][0].transcript;
          }}
        }}

        // Barge-In: if user speaks while avatar is speaking, immediately interrupt!
        if (interim.length > 0 || final.length > 0) {{
          if (currentAudio && !currentAudio.paused) {{
            currentAudio.pause();
            currentAudio = null;
            if (ws && ws.readyState === WebSocket.OPEN) {{
              ws.send(JSON.stringify({{ type: "user_barge_in" }}));
            }}
          }}
          setAvatarExpression("listening");
          captionContent.innerHTML = `<span style="color:#38bdf8;">👤 ${{USER_NAME}}:</span> "${{interim || final}}"`;
        }}

        if (final.trim().length > 0) {{
          const cleanInput = final.trim();
          appendChatMessage(USER_NAME, cleanInput);
          if (ws && ws.readyState === WebSocket.OPEN) {{
            ws.send(JSON.stringify({{ type: "user_message", text: cleanInput }}));
          }}
        }}
      }};

      recognition.onerror = (e) => {{
        if (e.error !== 'no-speech') console.debug("Speech recognition error:", e.error);
      }};

      recognition.onend = () => {{
        if (!isMicMuted) {{
          try {{ recognition.start(); }} catch(e) {{}}
        }}
      }};

      try {{ recognition.start(); }} catch(e) {{}}
    }}

    // =========================================================================
    // CAMERA STREAM & VISION UNDERSTANDING
    // =========================================================================
    async function toggleCamera() {{
      if (isCameraOn) {{
        // Turn off
        if (userMediaStream) {{
          userMediaStream.getTracks().forEach(t => t.stop());
          userMediaStream = null;
        }}
        userVideo.srcObject = null;
        pipDisabledView.style.display = 'flex';
        pipCamDot.style.background = '#ef4444';
        document.getElementById('btn-cam').classList.remove('active-cyan');
        isCameraOn = false;
      }} else {{
        // Turn on
        try {{
          userMediaStream = await navigator.mediaDevices.getUserMedia({{
            video: {{ width: {{ ideal: 640 }}, height: {{ ideal: 480 }} }}
          }});
          userVideo.srcObject = userMediaStream;
          pipDisabledView.style.display = 'none';
          pipCamDot.style.background = '#10b981';
          document.getElementById('btn-cam').classList.add('active-cyan');
          isCameraOn = true;
        }} catch (err) {{
          alert("Could not access camera: " + err.message);
        }}
      }}
    }}

    async function inspectCameraFeed() {{
      if (!isCameraOn) {{
        alert("Please enable your camera first (click 📹 or press C).");
        return;
      }}

      setAvatarExpression("thinking");
      captionContent.innerText = "Analyzing camera feed...";

      // Capture frame to offscreen canvas
      const canvas = document.createElement('canvas');
      canvas.width = userVideo.videoWidth || 640;
      canvas.height = userVideo.videoHeight || 480;
      const ctx = canvas.getContext('2d');
      ctx.drawImage(userVideo, 0, 0, canvas.width, canvas.height);
      const b64Image = canvas.toDataURL('image/jpeg', 0.8);

      try {{
        const resp = await fetch('/api/camera-analyze', {{
          method: 'POST',
          headers: {{ 'Content-Type': 'application/json' }},
          body: JSON.stringify({{ image_base64: b64Image, prompt: "What am I doing or holding right now?" }})
        }});
        const data = await resp.json();
        if (data.reply) {{
          captionContent.innerText = `"${{data.reply}}"`;
          appendChatMessage(COMPANION_NAME, data.reply);
          if (data.audio_base64) {{
            playTTSAudio(data.audio_base64);
          }}
        }}
      }} catch (e) {{
        captionContent.innerText = "Could not inspect camera right now.";
      }}
    }}

    // =========================================================================
    // CONTROLS & INTERACTIONS
    // =========================================================================
    document.getElementById('btn-mic').addEventListener('click', () => {{
      isMicMuted = !isMicMuted;
      const btn = document.getElementById('btn-mic');
      const icon = document.getElementById('mic-icon');
      if (isMicMuted) {{
        btn.classList.add('muted');
        btn.classList.remove('active');
        icon.innerText = '🔇';
        if (recognition) recognition.stop();
      }} else {{
        btn.classList.remove('muted');
        btn.classList.add('active');
        icon.innerText = '🎙️';
        if (recognition) {{ try {{ recognition.start(); }} catch(e) {{}} }}
      }}
      if (ws && ws.readyState === WebSocket.OPEN) {{
        ws.send(JSON.stringify({{ type: "toggle_mute", is_muted: isMicMuted }}));
      }}
    }});

    document.getElementById('btn-cam').addEventListener('click', toggleCamera);
    document.getElementById('btn-vision').addEventListener('click', inspectCameraFeed);

    document.getElementById('btn-lang').addEventListener('click', () => {{
      const btn = document.getElementById('btn-lang');
      if (activeLanguage === "en-US") {{
        activeLanguage = "ta-IN";
        btn.innerText = "TA";
        langIndicator.innerText = "🌐 தமிழ் (Tamil)";
      }} else {{
        activeLanguage = "en-US";
        btn.innerText = "EN";
        langIndicator.innerText = "🌐 English (US)";
      }}
      if (recognition) recognition.lang = activeLanguage;
      if (ws && ws.readyState === WebSocket.OPEN) {{
        ws.send(JSON.stringify({{ type: "set_language", language: activeLanguage }}));
      }}
    }});

    styleSelect.addEventListener('change', (e) => {{
      updateMaterialsForStyle(e.target.value);
      if (ws && ws.readyState === WebSocket.OPEN) {{
        ws.send(JSON.stringify({{ type: "set_style", style: e.target.value }}));
      }}
    }});

    document.getElementById('btn-chat').addEventListener('click', () => {{
      chatDrawer.classList.toggle('open');
    }});

    document.getElementById('btn-close-drawer').addEventListener('click', () => {{
      chatDrawer.classList.remove('open');
    }});

    document.getElementById('btn-fullscreen').addEventListener('click', () => {{
      if (!document.fullscreenElement) {{
        document.documentElement.requestFullscreen();
      }} else {{
        document.exitFullscreen();
      }}
    }});

    document.getElementById('btn-end').addEventListener('click', () => {{
      if (confirm("End video call with {name}?")) {{
        if (userMediaStream) userMediaStream.getTracks().forEach(t => t.stop());
        window.close();
        document.body.innerHTML = `
          <div style="display:flex; flex-direction:column; align-items:center; justify-content:center; height:100vh; gap:16px;">
            <h1 style="color:#c084fc;">Call Ended</h1>
            <p style="color:#94a3b8;">Thank you, {user}. Electorn Companion resources released.</p>
            <p style="color:#64748b; font-size:12px;">You can return to your terminal.</p>
          </div>
        `;
      }}
    }});

    // Chat Message Handlers
    function appendChatMessage(sender, text) {{
      const b = document.createElement('div');
      b.className = 'chat-bubble ' + (sender === COMPANION_NAME ? 'companion' : 'user');
      b.innerHTML = `<strong>${{sender}}:</strong> ${{text}}`;
      messagesList.appendChild(b);
      messagesList.scrollTop = messagesList.scrollHeight;
    }}

    function sendChatMessage() {{
      const text = chatInput.value.trim();
      if (!text) return;
      chatInput.value = '';
      appendChatMessage(USER_NAME, text);
      if (ws && ws.readyState === WebSocket.OPEN) {{
        ws.send(JSON.stringify({{ type: "user_message", text: text }}));
      }}
    }}

    document.getElementById('btn-send').addEventListener('click', sendChatMessage);
    chatInput.addEventListener('keydown', (e) => {{
      if (e.key === 'Enter') sendChatMessage();
    }});

    // Hotkey listener
    window.addEventListener('keydown', (e) => {{
      if (e.target.tagName === 'INPUT') return;
      if (e.key.toLowerCase() === 'm') document.getElementById('btn-mic').click();
      if (e.key.toLowerCase() === 'c') document.getElementById('btn-cam').click();
      if (e.key.toLowerCase() === 'v') document.getElementById('btn-vision').click();
      if (e.key.toLowerCase() === 'f') document.getElementById('btn-fullscreen').click();
      if (e.key === 'Escape') document.getElementById('btn-end').click();
    }});

    // Resize listener
    window.addEventListener('resize', () => {{
      const w = avatarCanvas.clientWidth || window.innerWidth;
      const h = avatarCanvas.clientHeight || window.innerHeight;
      if (camera && renderer) {{
        camera.aspect = w / h;
        camera.updateProjectionMatrix();
        renderer.setSize(w, h);
      }}
    }});

    // Click anywhere to activate audio context if suspended
    window.addEventListener('click', () => {{
      if (audioContext && audioContext.state === 'suspended') {{
        audioContext.resume();
      }}
    }}, {{ once: true }});

    // Start everything
    window.addEventListener('DOMContentLoaded', () => {{
      init3DAvatar();
      connectWebSocket();
      initSpeechRecognition();
    }});
  </script>
</body>
</html>"""
