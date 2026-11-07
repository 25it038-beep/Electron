"""Optical Character Recognition for screen tokens."""

from __future__ import annotations

from typing import List, Optional, Tuple

from ..types import BoundingBox, OCRToken


class OCRProcessor:
    """Extracts on-screen words and calculates bounding boxes."""

    def extract_tokens(self, window_title: str, resolution: Tuple[int, int]) -> List[OCRToken]:
        tokens: List[OCRToken] = []
        # Uses Windows OCR or token parser
        return tokens

    def find_text_coordinates(self, text: str, tokens: List[OCRToken]) -> Optional[Tuple[int, int]]:
        clean = text.strip().lower()
        for tok in tokens:
            if clean in tok.text.lower():
                return tok.location
        return None
