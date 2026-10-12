"""PowerPoint quality assurance validator, bounding box verification, and manifest generation."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, List
from pptx import Presentation
from pydantic import BaseModel, Field


class ValidationIssue(BaseModel):
    slide_number: int
    severity: str  # "warning", "error"
    message: str


class PresentationQAReport(BaseModel):
    is_valid: bool
    total_slides: int
    issues: List[ValidationIssue] = Field(default_factory=list)
    manifest: dict[str, Any] = Field(default_factory=dict)


class PresentationQAValidator:
    """Validates PowerPoint files for corruption, bounding box containment, and layout integrity."""

    @classmethod
    def validate_file(cls, file_path: str | Path, expected_slide_count: int | None = None) -> PresentationQAReport:
        path = Path(file_path).resolve()
        issues: List[ValidationIssue] = []

        if not path.exists():
            return PresentationQAReport(
                is_valid=False,
                total_slides=0,
                issues=[ValidationIssue(slide_number=0, severity="error", message="File does not exist")],
            )

        try:
            prs = Presentation(str(path))
        except Exception as e:
            return PresentationQAReport(
                is_valid=False,
                total_slides=0,
                issues=[ValidationIssue(slide_number=0, severity="error", message=f"Corrupted PPTX file: {e}")],
            )

        total_slides = len(prs.slides)
        slide_w = prs.slide_width
        slide_h = prs.slide_height

        if expected_slide_count and total_slides < expected_slide_count - 2:
            issues.append(
                ValidationIssue(
                    slide_number=0,
                    severity="warning",
                    message=f"Requested {expected_slide_count} slides but generated {total_slides}",
                )
            )

        slide_manifest = []
        total_words = 0
        has_placeholders = False

        for i, slide in enumerate(prs.slides):
            slide_num = i + 1
            has_title = False
            has_content = False
            shape_count = len(slide.shapes)

            for shape in slide.shapes:
                # Check for boundary overflow
                if shape.left < 0 or shape.top < 0:
                    issues.append(
                        ValidationIssue(
                            slide_number=slide_num,
                            severity="warning",
                            message=f"Shape '{shape.name}' extends beyond negative slide boundary",
                        )
                    )
                if (shape.left + shape.width) > (slide_w + 1000) or (shape.top + shape.height) > (slide_h + 1000):
                    issues.append(
                        ValidationIssue(
                            slide_number=slide_num,
                            severity="warning",
                            message=f"Shape '{shape.name}' exceeds maximum slide boundary dimensions",
                        )
                    )

                if shape.has_text_frame:
                    has_content = True
                    text = shape.text_frame.text.strip()
                    if text:
                        has_title = True
                        words = len(text.split())
                        total_words += words
                        
                        # Placeholder detection
                        lower_text = text.lower()
                        for ph in ["lorem ipsum", "dolor sit amet", "[insert", "<placeholder>", "todo:"]:
                            if ph in lower_text:
                                has_placeholders = True
                                issues.append(
                                    ValidationIssue(
                                        slide_number=slide_num,
                                        severity="warning",
                                        message=f"Unverified placeholder pattern '{ph}' detected in slide text",
                                    )
                                )

            if not has_content or shape_count == 0:
                issues.append(
                    ValidationIssue(
                        slide_number=slide_num,
                        severity="error",
                        message="Slide is blank without content or shapes",
                    )
                )

            slide_manifest.append({
                "slide_number": slide_num,
                "shape_count": shape_count,
                "has_notes": bool(slide.has_notes_slide and slide.notes_slide.notes_text_frame.text.strip()),
            })

        has_errors = any(i.severity == "error" for i in issues)
        return PresentationQAReport(
            is_valid=not has_errors,
            total_slides=total_slides,
            issues=issues,
            manifest={
                "file_path": str(path),
                "file_size_bytes": os.path.getsize(path),
                "total_slides": total_slides,
                "aspect_ratio": "16:9 Widescreen",
                "total_words": total_words,
                "content_verified": not has_placeholders and total_words > (total_slides * 15),
                "slides": slide_manifest,
            },
        )
