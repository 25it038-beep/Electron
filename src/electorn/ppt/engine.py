"""High-level facade orchestrating PPT generation, inspection, preview, and revision."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional
from rich.console import Console
from rich.table import Table

from electorn.ppt.builder import PowerPointBuilder
from electorn.ppt.design import get_theme
from electorn.ppt.document_ingestion import DocumentAnalysis, DocumentIngestionEngine
from electorn.ppt.planner import PresentationPlanner
from electorn.ppt.schema import (
    PresentationDeckPlan,
    PresentationStyle,
    SlideContent,
    SlideLayoutType,
)
from electorn.ppt.validator import PresentationQAReport, PresentationQAValidator
from electorn.runtime.ollama_client import OllamaClient
from electorn.storage.config import Config


class PresentationEngine:
    """Production PowerPoint engine orchestrating planning, synthesis, inspection, and revision."""

    def __init__(self, config: Optional[Config] = None, client: Optional[OllamaClient] = None) -> None:
        self.config = config
        self.client = client
        self.planner = PresentationPlanner(
            client=self.client,
            model=self.config.runtime.model if self.config else None,
        )

    def generate(
        self,
        topic: Optional[str] = None,
        input_file: Optional[str | Path] = None,
        slides_count: int = 10,
        style: str = "premium-dark",
        output_file: Optional[str | Path] = None,
        audience: str = "general",
    ) -> tuple[str, PresentationQAReport]:
        """Generate a complete PowerPoint deck from topic or source document."""
        doc_analysis: Optional[DocumentAnalysis] = None
        chosen_style = PresentationStyle(style) if style in [s.value for s in PresentationStyle] else PresentationStyle.PREMIUM_DARK

        if input_file:
            doc_analysis = DocumentIngestionEngine.ingest_file(input_file)
            if not topic:
                topic = doc_analysis.title

        final_topic = topic or (doc_analysis.title if doc_analysis else "Technical Presentation")

        # 1. Plan Narrative
        plan = self.planner.plan_presentation(
            topic=final_topic,
            target_slide_count=slides_count,
            style=chosen_style,
            audience=audience,
            doc_analysis=doc_analysis,
        )

        # 2. Determine Output Destination
        if not output_file:
            safe_name = "".join(c for c in final_topic if c.isalnum() or c in (" ", "-", "_")).strip()
            safe_name = safe_name.replace(" ", "_").lower()[:40] or "presentation"
            out_path = Path.cwd() / f"{safe_name}.pptx"
        else:
            out_path = Path(output_file).resolve()
            if out_path.suffix.lower() != ".pptx":
                out_path = out_path.with_suffix(".pptx")

        # 3. Build PPTX Deck
        builder = PowerPointBuilder(style=chosen_style)
        saved_file = builder.build_deck(plan, out_path)

        # 4. QA Validation
        qa_report = PresentationQAValidator.validate_file(saved_file, expected_slide_count=slides_count)

        # Save manifest alongside PPTX
        manifest_path = Path(saved_file).with_suffix(".manifest.json")
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(qa_report.manifest, f, indent=2)

        return saved_file, qa_report

    def inspect(self, file_path: str | Path, console: Optional[Console] = None) -> PresentationQAReport:
        """Inspect slides, layout structure, and QA diagnostics of an existing deck."""
        qa = PresentationQAValidator.validate_file(file_path)
        if console:
            manifest = qa.manifest
            table = Table(title=f"Deck Inspection: {Path(file_path).name}", border_style="cyan")
            table.add_column("Slide #", style="bold cyan")
            table.add_column("Shapes", style="white")
            table.add_column("Speaker Notes", style="green")

            for s in manifest.get("slides", []):
                table.add_row(
                    str(s["slide_number"]),
                    str(s["shape_count"]),
                    "✔ Yes" if s["has_notes"] else "✖ None",
                )
            console.print(table)
            if qa.issues:
                console.print(f"\n[yellow]QA Diagnostics ({len(qa.issues)} items):[/yellow]")
                for issue in qa.issues:
                    color = "red" if issue.severity == "error" else "yellow"
                    console.print(f"  [{color}]Slide {issue.slide_number}: {issue.message}[/{color}]")
        return qa

    def preview(self, file_path: str | Path, console: Optional[Console] = None) -> None:
        """Render ASCII summary preview of slides in deck."""
        from pptx import Presentation
        prs = Presentation(str(file_path))
        c = console or Console()
        c.print(f"\n[bold cyan]⚡ Presentation Preview: {Path(file_path).name}[/bold cyan]")
        c.print(f"[dim]Total Slides: {len(prs.slides)} • Dimensions: 16:9 Widescreen[/dim]\n")

        for idx, slide in enumerate(prs.slides):
            texts = []
            for shape in slide.shapes:
                if shape.has_text_frame:
                    t = shape.text_frame.text.strip()
                    if t:
                        texts.append(t.split("\n")[0])
            title = texts[0] if texts else "Untitled Slide"
            notes = slide.notes_slide.notes_text_frame.text.strip() if slide.has_notes_slide else ""
            c.print(f"  [bold green]Slide {idx+1}:[/bold green] [bold white]{title}[/bold white]")
            if len(texts) > 1:
                c.print(f"    [dim]Preview: {' | '.join(texts[1:3])[:100]}[/dim]")
            if notes:
                c.print(f"    [dim italic]Notes: {notes[:80]}...[/dim italic]")
        c.print("")

    def revise(
        self,
        file_path: str | Path,
        slide_number: Optional[int] = None,
        instruction: str = "",
        style: Optional[str] = None,
    ) -> str:
        """Revise specific slides or apply new global theme styling."""
        from pptx import Presentation
        path = Path(file_path).resolve()
        prs = Presentation(str(path))

        # If theme revision requested
        if style:
            target_style = PresentationStyle(style) if style in [s.value for s in PresentationStyle] else PresentationStyle.PREMIUM_DARK
            # Rebuild with new theme
            plan = self.planner.plan_presentation(
                topic=path.stem.replace("_", " ").title(),
                target_slide_count=len(prs.slides),
                style=target_style,
            )
            builder = PowerPointBuilder(style=target_style)
            return builder.build_deck(plan, path)

        # Targeted slide revision
        if slide_number and 1 <= slide_number <= len(prs.slides):
            target_slide = prs.slides[slide_number - 1]
            # Attach instruction note
            notes = target_slide.notes_slide.notes_text_frame
            notes.text = (notes.text + f"\n[Revised]: {instruction}").strip()
            prs.save(str(path))
            return str(path)

        prs.save(str(path))
        return str(path)
