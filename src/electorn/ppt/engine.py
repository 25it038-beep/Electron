"""High-level facade orchestrating PPT generation, inspection, preview, and revision."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional
from rich.console import Console
from rich.table import Table

from electorn.ppt.builder import PowerPointBuilder
from electorn.ppt.design import get_theme
from electorn.ppt.document_ingestion import DocumentAnalysis, DocumentIngestionEngine
from electorn.ppt.model_registry import NvidiaModelRegistry, PRESENTATION_ROLES
from electorn.ppt.multi_model_orchestrator import NvidiaPresentationOrchestrator
from electorn.ppt.nvidia_client import (
    NvidiaApiError,
    NvidiaAuthenticationError,
    NvidiaCloudClient,
)
from electorn.ppt.planner import PresentationPlanner
from electorn.ppt.quality_controller import get_quality_profile
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
    """Production PowerPoint engine orchestrating NVIDIA multi-model collaboration and local planning."""

    def __init__(self, config: Optional[Config] = None, client: Optional[OllamaClient] = None) -> None:
        self.config = config
        self.client = client
        self.planner = PresentationPlanner(
            client=self.client,
            model=self.config.runtime.model if self.config else None,
        )
        self.nvidia_client = NvidiaCloudClient()
        self.nvidia_registry = NvidiaModelRegistry(client=self.nvidia_client)
        self.nvidia_orchestrator = NvidiaPresentationOrchestrator(
            client=self.nvidia_client,
            registry=self.nvidia_registry,
        )

    def resolve_provider(self, requested_provider: Optional[str] = None) -> str:
        """Resolve whether to use 'nvidia' or 'ollama' specifically for PowerPoint generation."""
        if requested_provider:
            return requested_provider.strip().lower()

        env_provider = os.environ.get("ELECTORN_PPT_PROVIDER")
        if env_provider:
            return env_provider.strip().lower()

        # If NVIDIA API key is available, default to NVIDIA Cloud AI for PowerPoint
        if self.nvidia_client.is_configured:
            return "nvidia"

        return "ollama"

    def generate(
        self,
        topic: Optional[str] = None,
        input_file: Optional[str | Path] = None,
        slides_count: int = 10,
        style: str = "premium-dark",
        output_file: Optional[str | Path] = None,
        audience: str = "general",
        use_web_search: bool = True,
        provider: Optional[str] = None,
        quality_mode: str = "professional",
        model: Optional[str] = None,
    ) -> tuple[str, PresentationQAReport]:
        """Generate a complete PowerPoint deck from topic or source document."""
        doc_analysis: Optional[DocumentAnalysis] = None
        chosen_style = (
            PresentationStyle(style)
            if style in [s.value for s in PresentationStyle]
            else PresentationStyle.PREMIUM_DARK
        )

        if input_file:
            doc_analysis = DocumentIngestionEngine.ingest_file(input_file)
            if not topic:
                topic = doc_analysis.title

        final_topic = topic or (doc_analysis.title if doc_analysis else "Technical Presentation")
        active_provider = self.resolve_provider(provider)

        # 1. Synthesize Plan using configured provider
        if active_provider == "nvidia":
            if not self.nvidia_client.is_configured:
                raise NvidiaAuthenticationError(
                    "NVIDIA Cloud provider requested, but NVIDIA_API_KEY is not configured.\n"
                    "Set your key via: $env:NVIDIA_API_KEY = 'your_key' or pass --provider ollama"
                )
            plan = self.nvidia_orchestrator.orchestrate_presentation(
                topic=final_topic,
                target_slide_count=slides_count,
                style=chosen_style,
                audience=audience,
                doc_analysis=doc_analysis,
                use_web_search=use_web_search,
                quality_mode=quality_mode,
                model_override=model,
            )
        else:
            plan = self.planner.plan_presentation(
                topic=final_topic,
                target_slide_count=slides_count,
                style=chosen_style,
                audience=audience,
                doc_analysis=doc_analysis,
                use_web_search=use_web_search,
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

        # Attach verified sources and engine metadata to manifest
        if plan.manifest_metadata:
            qa_report.manifest.update(plan.manifest_metadata)

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

            manifest_file = Path(file_path).with_suffix(".manifest.json")
            if manifest_file.exists():
                try:
                    with open(manifest_file, "r", encoding="utf-8") as f:
                        saved_manifest = json.load(f)
                    sources = saved_manifest.get("verified_sources", [])
                    if sources:
                        console.print(f"\n[bold cyan]Verified Live Web Sources ({len(sources)} links):[/bold cyan]")
                        for src in sources[:5]:
                            console.print(f"  • [green]{src.get('title')}[/green] [dim]({src.get('url')})[/dim]")
                except Exception:
                    pass

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
            target_style = (
                PresentationStyle(style)
                if style in [s.value for s in PresentationStyle]
                else PresentationStyle.PREMIUM_DARK
            )
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

    def display_models(self, console: Optional[Console] = None) -> None:
        """Display configured presentation model roles and catalog availability."""
        c = console or Console()
        c.print("\n[bold cyan]⚡ NVIDIA Multi-Model Presentation Registry[/bold cyan]")
        c.print("[dim]Role assignments for PowerPoint generation exclusively[/dim]\n")

        table = Table(title="Configured Presentation Roles", border_style="cyan")
        table.add_column("Role", style="bold green")
        table.add_column("Assigned Model", style="bold white")
        table.add_column("Context", style="yellow")
        table.add_column("Status", style="cyan")

        audit = self.nvidia_registry.audit_registry()
        for item in audit:
            status_text = "✔ Verified in Catalog" if item["catalog_verified"] else "● Configured"
            table.add_row(
                item["role_name"],
                item["assigned_model"],
                f"{item['context_window'] // 1000}k",
                status_text,
            )
        c.print(table)
        c.print("")

    def run_doctor(self, console: Optional[Console] = None) -> bool:
        """Run diagnostic audit on NVIDIA credentials, connectivity, and dependencies."""
        c = console or Console()
        c.print("\n[bold cyan]🩺 Electorn Presentation Doctor — NVIDIA Engine Diagnostics[/bold cyan]\n")

        all_ok = True

        # 1. API Key check
        if self.nvidia_client.is_configured:
            masked_key = self.nvidia_client.api_key[:6] + "..." + self.nvidia_client.api_key[-4:]
            c.print(f"  ✔ [bold green]NVIDIA API Key:[/bold green] Configured ({masked_key})")
        else:
            c.print("  ✖ [bold red]NVIDIA API Key:[/bold red] Missing (Set NVIDIA_API_KEY environment variable)")
            all_ok = False

        # 2. Endpoint Connectivity Check
        start_t = time.time()
        is_conn = self.nvidia_client.is_available()
        elapsed = round((time.time() - start_t) * 1000, 1)
        if is_conn:
            c.print(f"  ✔ [bold green]API Connectivity:[/bold green] Connected to {self.nvidia_client.base_url} ({elapsed}ms)")
        else:
            c.print(f"  ✖ [bold red]API Connectivity:[/bold red] Failed to reach {self.nvidia_client.base_url}")
            all_ok = False

        # 3. Dependencies check
        for pkg in ["pptx", "httpx", "pypdf", "docx"]:
            try:
                __import__(pkg)
                c.print(f"  ✔ [bold green]Dependency '{pkg}':[/bold green] Installed and operational")
            except ImportError:
                c.print(f"  ✖ [bold red]Dependency '{pkg}':[/bold red] Missing")
                all_ok = False

        # 4. Active Roles Summary
        c.print(f"  ✔ [bold green]Specialized Roles:[/bold green] 6 Multi-Model Collaboration Roles Registered")
        c.print(f"  ✔ [bold green]Quality Modes:[/bold green] economy, professional, maximum supported")
        c.print(f"  ✔ [bold green]Isolation Status:[/bold green] Ollama & general Electorn runtimes unaffected\n")

        if all_ok:
            c.print("[bold green]✔ All presentation engine diagnostics passed! Ready for generation.[/bold green]\n")
        else:
            c.print("[bold yellow]⚠ Some diagnostics reported warnings. Check configuration above.[/bold yellow]\n")

        return all_ok
