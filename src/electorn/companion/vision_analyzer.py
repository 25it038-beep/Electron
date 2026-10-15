"""Vision and context analysis engine using Ollama vision model and OCR fallbacks."""

from __future__ import annotations

import base64
import io
import json
import logging
import re
import urllib.error
import urllib.request
from typing import Any, Dict, Optional, Tuple

from electorn.companion.schema import ScreenObservationConfig, ScreenObservationReport

try:
    import pytesseract
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

logger = logging.getLogger(__name__)


class VisionAnalyzer:
    """Interprets screen captures to extract errors, terminal commands, and active code context."""

    def __init__(
        self,
        config: Optional[ScreenObservationConfig] = None,
        ollama_base_url: str = "http://localhost:11434",
    ) -> None:
        self.config = config or ScreenObservationConfig()
        self.ollama_base_url = ollama_base_url.rstrip("/")

    def sanitize_untrusted_screen_text(self, text: str) -> str:
        """Neutralize prompt injection attempts embedded in observed screen text."""
        if not text:
            return ""

        suspicious_patterns = [
            r"ignore\s+(?:all\s+)?previous\s+instructions",
            r"you\s+are\s+now\s+(?:a\s+)?developer\s+mode",
            r"system\s+override",
            r"disregard\s+prior\s+directives",
            r"format\s+drive",
            r"delete\s+everything",
        ]
        sanitized = text
        for pat in suspicious_patterns:
            sanitized = re.sub(pat, "[FILTERED_UNTRUSTED_CONTENT]", sanitized, flags=re.IGNORECASE)

        return sanitized

    def extract_error_heuristics(self, raw_text: str) -> Optional[str]:
        """Detect common programming syntax errors, exceptions, or test failures via regex."""
        if not raw_text:
            return None

        error_patterns = [
            r"Traceback \(most recent call last\):[\s\S]*?(?:Error|Exception):[^\n]+",
            r"(?:SyntaxError|NameError|TypeError|ValueError|IndexError|KeyError|AttributeError|ImportError):[^\n]+",
            r"FAILED\s+tests/[^\n]+",
            r"error\s*TS\d+:[^\n]+",
            r"(?:panic|fatal error):[^\n]+",
            r"npm ERR![^\n]+",
            r"Build failed with \d+ error\(s\)",
        ]
        for pat in error_patterns:
            m = re.search(pat, raw_text, re.MULTILINE)
            if m:
                return m.group(0).strip()[:200]

        return None

    def analyze(self, image: Any, report: ScreenObservationReport) -> ScreenObservationReport:
        """Run vision model or OCR on captured image to populate observation details."""
        if image is None:
            return report

        # Check if screen hasn't changed meaningfully
        if report.change_ratio < self.config.change_detection_threshold and report.change_ratio > 0.0:
            report.visible_summary = f"No significant changes in {report.window_title}."
            return report

        # 1. Attempt Vision Model (e.g. qwen3-vl:4b-instruct) via Ollama
        vision_success = False
        try:
            buffered = io.BytesIO()
            # Resize image to reasonable dimension (max 1024 width) to reduce latency and VRAM
            img_copy = image.copy()
            img_copy.thumbnail((1024, 768))
            img_copy.save(buffered, format="JPEG", quality=80)
            img_b64 = base64.b64encode(buffered.getvalue()).decode("utf-8")

            prompt = (
                "You are an assistant inspecting the user's active screen. "
                "Briefly summarize what code, document, or terminal commands are visible in 1-2 concise sentences. "
                "If there is any visible error message, syntax failure, or exception, explicitly prefix it with 'ERROR: '. "
                "Do not invent anything not clearly shown in the image."
            )

            payload = {
                "model": self.config.vision_model,
                "prompt": prompt,
                "images": [img_b64],
                "stream": False,
                "options": {
                    "temperature": 0.2,
                    "num_predict": 120,
                },
            }

            req = urllib.request.Request(
                f"{self.ollama_base_url}/api/generate",
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=12) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                response_text = data.get("response", "").strip()
                if response_text:
                    clean_res = self.sanitize_untrusted_screen_text(response_text)
                    report.visible_summary = clean_res

                    # Check for errors in vision output
                    if "ERROR:" in clean_res:
                        err_part = clean_res.split("ERROR:", 1)[1].strip()
                        report.visible_error = err_part[:200]
                        report.suggested_assistance = f"Would you like me to inspect and help resolve: {report.visible_error}?"
                    vision_success = True
        except Exception as e:
            logger.debug("Ollama vision analysis fell back: %s", e)
            vision_success = False

        # 2. Fallback to OCR text extraction + heuristics if vision model was unavailable
        if not vision_success and self.config.ocr_enabled and OCR_AVAILABLE:
            try:
                ocr_text = pytesseract.image_to_string(image)
                if ocr_text.strip():
                    sanitized_ocr = self.sanitize_untrusted_screen_text(ocr_text)
                    err = self.extract_error_heuristics(sanitized_ocr)
                    if err:
                        report.visible_error = err
                        report.visible_summary = f"Detected error in {report.window_title}."
                        report.suggested_assistance = f"Would you like me to inspect and help resolve: {err}?"
                    else:
                        report.visible_summary = f"Working in {report.window_title} ({report.app_category})."
            except Exception as e:
                logger.debug("OCR fallback exception: %s", e)

        # 3. Basic fallback based on window title heuristics
        if not report.visible_summary:
            report.visible_summary = f"Focused on {report.window_title} ({report.app_category})."

        return report
