"""Intelligent slide planner generating coherent narratives and layout mappings."""

from __future__ import annotations

import json
from typing import Optional
from electorn.ppt.document_ingestion import DocumentAnalysis
from electorn.ppt.schema import (
    ArchComponent,
    KeyMetric,
    PresentationDeckPlan,
    PresentationStyle,
    ProcessStep,
    SlideContent,
    SlideLayoutType,
    TableData,
    TimelineItem,
)
from electorn.runtime.ollama_client import OllamaClient


class PresentationPlanner:
    """Creates structured, content-aware narrative plans for slide decks.
    
    Generates high-variety layouts: statistics, processes, architecture,
    two-column comparisons, tables, code, and editorial layouts.
    """

    def __init__(self, client: Optional[OllamaClient] = None, model: Optional[str] = None) -> None:
        self.client = client
        self.model = model

    def plan_presentation(
        self,
        topic: str,
        target_slide_count: int = 10,
        style: PresentationStyle = PresentationStyle.PREMIUM_DARK,
        audience: str = "general",
        doc_analysis: Optional[DocumentAnalysis] = None,
    ) -> PresentationDeckPlan:
        """Create a validated, complete PresentationDeckPlan."""
        target_count = max(4, min(30, target_slide_count))

        # 1. If LLM is available, attempt intelligent schema expansion
        if self.client and self.client.is_available() and self.model:
            try:
                llm_plan = self._plan_with_llm(topic, target_count, style, audience, doc_analysis)
                if llm_plan and len(llm_plan.slides) >= target_count - 2:
                    return llm_plan
            except Exception:
                pass

        # 2. Deterministic narrative synthesis (zero-cloud / offline guaranteed)
        return self._plan_deterministic(topic, target_count, style, audience, doc_analysis)

    def _plan_deterministic(
        self,
        topic: str,
        count: int,
        style: PresentationStyle,
        audience: str,
        doc: Optional[DocumentAnalysis],
    ) -> PresentationDeckPlan:
        slides: list[SlideContent] = []

        # Slide 1: Title Slide
        title_sub = f"Strategic Overview & Deep Dive for {audience.title()} Audience"
        if doc:
            title_sub = f"Executive Presentation based on {doc.source_file}"

        slides.append(
            SlideContent(
                slide_id="slide_1",
                slide_number=1,
                layout_type=SlideLayoutType.TITLE,
                title=doc.title if doc else topic,
                subtitle=title_sub,
                category_badge="KEYNOTE BRIEFING",
                speaker_notes=f"Welcome everyone. Today we are presenting a comprehensive overview on {topic}.",
            )
        )

        # Slide 2: Executive Summary / Context
        slides.append(
            SlideContent(
                slide_id="slide_2",
                slide_number=2,
                layout_type=SlideLayoutType.EDITORIAL,
                title="Executive Summary & Context",
                subtitle="High-level background, current paradigms, and core imperatives.",
                category_badge="OVERVIEW",
                bullets=[
                    f"Fundamental shift in modern approaches towards {topic.lower()}.",
                    "Accelerating demand for scalability, deterministic verification, and automated workflows.",
                    "Strategic necessity of aligning technical execution with long-term organizational goals.",
                    "Key takeaways and actionable pathways detailed across this presentation.",
                ],
                speaker_notes=f"Let us establish the foundational context and why {topic} is critical today.",
            )
        )

        # Slide 3: Statistical Metrics
        if count >= 4:
            slides.append(
                SlideContent(
                    slide_id="slide_3",
                    slide_number=3,
                    layout_type=SlideLayoutType.STATISTICS,
                    title="Key Metrics & Industry Benchmark",
                    subtitle="Empirical performance indicators and quantitative metrics.",
                    category_badge="METRICS",
                    metrics=[
                        KeyMetric(value="10x", label="Efficiency Velocity", description="Accelerated execution vs legacy methods"),
                        KeyMetric(value="99.4%", label="Deterministic Accuracy", description="Verified completion across environments"),
                        KeyMetric(value="< 50ms", label="Latency Threshold", description="Optimized runtime responsiveness"),
                    ],
                    bullets=[
                        "Quantitative data underscores dramatic reduction in manual interventions.",
                        "Systemic improvements observed across reliability and throughput metrics.",
                    ],
                    speaker_notes="Examining the empirical performance indicators and quantitative metrics.",
                )
            )

        # Middle Slides: Procedural, Architecture, Comparison, Table, etc.
        idx = 4
        while idx < count - 1:
            step_mod = idx % 5
            if step_mod == 4:
                # System Architecture Slide
                slides.append(
                    SlideContent(
                        slide_id=f"slide_{idx}",
                        slide_number=idx,
                        layout_type=SlideLayoutType.ARCHITECTURE,
                        title="System Architecture & Flow",
                        subtitle="Modular decomposition and multi-tier component interaction.",
                        category_badge="ENGINEERING",
                        architecture=[
                            ArchComponent(layer="Interface Layer", name="Client & Ingestion", items=["Voice Stream", "Web Inspector", "Document Parser"]),
                            ArchComponent(layer="Intelligence Core", name="Orchestration & Planning", items=["Task Planner", "Verification Engine", "Self-Healing"]),
                            ArchComponent(layer="Execution Engine", name="Automation Runtime", items=["OS Native Automation", "Selenium Driver", "Process Runner"]),
                        ],
                        speaker_notes="Here is the architectural decomposition showing clean separation of concerns.",
                    )
                )
            elif step_mod == 0:
                # Process Flow Slide
                slides.append(
                    SlideContent(
                        slide_id=f"slide_{idx}",
                        slide_number=idx,
                        layout_type=SlideLayoutType.PROCESS,
                        title="End-to-End Implementation Workflow",
                        subtitle="Sequential lifecycle from initial discovery to deployment.",
                        category_badge="PROCESS",
                        process_steps=[
                            ProcessStep(number=1, title="Discovery & Ingestion", description="Extract raw requirements and parse domain documents."),
                            ProcessStep(number=2, title="Autonomous Synthesis", description="Formulate structured plans and validate constraints."),
                            ProcessStep(number=3, title="Execution & Validation", description="Run verifiable automation steps with fallback recovery."),
                            ProcessStep(number=4, title="Verification & Delivery", description="Audit outcomes and export deliverables seamlessly."),
                        ],
                        speaker_notes="Walking through the sequential execution pipeline.",
                    )
                )
            elif step_mod == 1:
                # Two-Column Comparison
                slides.append(
                    SlideContent(
                        slide_id=f"slide_{idx}",
                        slide_number=idx,
                        layout_type=SlideLayoutType.COMPARISON,
                        title="Comparative Analysis & Trade-offs",
                        subtitle="Contrasting traditional paradigms against modern autonomous architectures.",
                        category_badge="ANALYSIS",
                        left_column_title="Traditional / Manual Approach",
                        left_column_bullets=[
                            "Manual configuration and fragmented toolsets",
                            "Vulnerable to human latency and manual errors",
                            "High operational overhead with brittle scripting",
                            "No automated fallback recovery or post-verification",
                        ],
                        right_column_title="Autonomous Electorn Architecture",
                        right_column_bullets=[
                            "Unified multi-agent task planning and coordination",
                            "Zero-touch auto-healing with continuous error recovery",
                            "Deterministic verification for every action before signoff",
                            "Cross-platform execution across OS and Web environments",
                        ],
                        speaker_notes="Notice the dramatic advantages in reliability and operational efficiency.",
                    )
                )
            elif step_mod == 2:
                # Table Data Slide
                slides.append(
                    SlideContent(
                        slide_id=f"slide_{idx}",
                        slide_number=idx,
                        layout_type=SlideLayoutType.TABLE,
                        title="Capability Matrix & Evaluation",
                        subtitle="Detailed matrix comparing core system specifications.",
                        category_badge="EVALUATION",
                        table=TableData(
                            headers=["Dimension", "Standard Baseline", "Target Requirement", "Electorn AI"],
                            rows=[
                                ["Automation Scope", "Scripted Macros", "Full OS & Browser", "Unified Agentic Core"],
                                ["Speech Intelligence", "Cloud-only STT", "Local Neural TTS", "Edge TTS & SAPI Fallback"],
                                ["Verification Check", "Exit code only", "State & File Audit", "Deterministic Multi-Tier"],
                                ["Local Resilience", "Requires Setup", "Zero-Touch Config", "Automated Auto-Start"],
                            ]
                        ),
                        speaker_notes="Reviewing the quantitative matrix against industry requirements.",
                    )
                )
            else:
                # Timeline Slide
                slides.append(
                    SlideContent(
                        slide_id=f"slide_{idx}",
                        slide_number=idx,
                        layout_type=SlideLayoutType.TIMELINE,
                        title="Strategic Roadmap & Milestones",
                        subtitle="Key phases and developmental milestones for deployment.",
                        category_badge="ROADMAP",
                        timeline=[
                            TimelineItem(step="Phase 1", title="Foundation", description="Core runtime integration and environment verification."),
                            TimelineItem(step="Phase 2", title="Automation", description="Native OS controls, web drivers, and voice capabilities."),
                            TimelineItem(step="Phase 3", title="Scale & Audit", description="Enterprise hardening, compliance, and multi-deck exports."),
                        ],
                        speaker_notes="Here is our strategic deployment roadmap covering key developmental milestones.",
                    )
                )
            idx += 1

        # References Slide (included for 5+ slides)
        if count >= 5:
            slides.append(
                SlideContent(
                    slide_id=f"slide_{count-1}",
                    slide_number=count - 1,
                    layout_type=SlideLayoutType.REFERENCES,
                    title="References & Technical Documentation",
                    subtitle="Authoritative standards, documentation references, and source assets.",
                    category_badge="REFERENCES",
                    citations=[
                        "Electorn AI Technical Architecture Specification v0.1.0",
                        "Windows UI Automation and Accessibility Protocol Standards (Microsoft)",
                        "W3C WebDriver Specification & Selenium Manager Architecture",
                        "Edge Neural Speech Synthesis Protocol (Microsoft Cognitive Services)",
                    ],
                    speaker_notes="All claims and technical standards referenced in this presentation.",
                )
            )

        # Slide N: Closing Keynote Slide
        slides.append(
            SlideContent(
                slide_id=f"slide_{count}",
                slide_number=count,
                layout_type=SlideLayoutType.CLOSING,
                title="Thank You & Discussion",
                subtitle=f"Q&A • Connect at https://hs-ai-studio.onrender.com/",
                category_badge="CLOSING",
                bullets=[
                    "Open for collaborative architecture discussion and technical Q&A.",
                    "Live demonstrations and source documentation available in Electorn AI.",
                ],
                speaker_notes="Thank you for your time. I am now delighted to open the floor for any questions.",
            )
        )

        return PresentationDeckPlan(
            topic=topic,
            audience=audience,
            style=style,
            target_slide_count=count,
            slides=slides,
            manifest_metadata={
                "generator": "Electorn AI Presentation Engine v0.1.0",
                "total_slides": len(slides),
                "source_document": doc.source_file if doc else None,
            }
        )

    def _plan_with_llm(
        self,
        topic: str,
        count: int,
        style: PresentationStyle,
        audience: str,
        doc: Optional[DocumentAnalysis],
    ) -> Optional[PresentationDeckPlan]:
        """Prompt LLM to generate enriched structured slide plan."""
        context_prompt = f"Topic: {topic}\nTarget Slides: {count}\nAudience: {audience}\nStyle: {style.value}\n"
        if doc:
            context_prompt += f"\nSource Document Summary:\n{doc.summary}\nSections: {', '.join([s.title for s in doc.sections[:5]])}\n"

        prompt = (
            f"Generate a structured JSON presentation plan for:\n{context_prompt}\n"
            f"Available layouts: title, editorial, statistics, two_column, comparison, timeline, process, architecture, table, references, closing.\n"
            f"Output a valid JSON object matching this schema:\n"
            f'{{"topic": "{topic}", "target_slide_count": {count}, "slides": ['
            f'{{"slide_id": "slide_1", "slide_number": 1, "layout_type": "title", "title": "...", "subtitle": "...", "bullets": [], "speaker_notes": "..."}}'
            f']}}\n'
            f"Ensure exactly {count} slides with rich varied layouts. Pure JSON only."
        )

        resp = self.client.generate(model=self.model, prompt=prompt, format_json=True)
        data = resp.parse_json()
        if "slides" in data and isinstance(data["slides"], list):
            parsed_slides = []
            for i, s in enumerate(data["slides"]):
                s["slide_number"] = i + 1
                s["slide_id"] = f"slide_{i+1}"
                try:
                    parsed_slides.append(SlideContent.model_validate(s))
                except Exception:
                    continue
            if len(parsed_slides) >= count - 2:
                return PresentationDeckPlan(
                    topic=topic,
                    audience=audience,
                    style=style,
                    target_slide_count=len(parsed_slides),
                    slides=parsed_slides,
                    manifest_metadata={"engine": "llm_enhanced", "model": self.model},
                )
        return None
