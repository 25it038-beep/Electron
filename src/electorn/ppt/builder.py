"""PowerPoint presentation builder synthesizing editable layouts, native shapes, and typography."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt

from electorn.ppt.design import DesignTheme, get_theme
from electorn.ppt.schema import (
    PresentationDeckPlan,
    PresentationStyle,
    SlideContent,
    SlideLayoutType,
)


class PowerPointBuilder:
    """Renders structured PresentationDeckPlan into professional .pptx presentation decks.
    
    Adheres strictly to the requirement:
    - Genuine editable shapes, text boxes, and tables
    - Clean typography, margins, and contrast
    - High-variety slide layouts (statistics, architecture, process, timeline, tables, comparisons)
    """

    SLIDE_WIDTH = Inches(13.333)  # Standard 16:9 Widescreen
    SLIDE_HEIGHT = Inches(7.5)

    def __init__(self, style: PresentationStyle = PresentationStyle.PREMIUM_DARK) -> None:
        self.theme: DesignTheme = get_theme(style)

    def build_deck(self, plan: PresentationDeckPlan, output_path: str | Path) -> str:
        """Render all slides in the plan to disk and return absolute file path."""
        prs = Presentation()
        prs.slide_width = self.SLIDE_WIDTH
        prs.slide_height = self.SLIDE_HEIGHT

        # Blank slide layout in standard template
        blank_slide_layout = prs.slide_layouts[6]

        for slide_data in plan.slides:
            slide = prs.slides.add_slide(blank_slide_layout)
            self._render_background(slide)
            self._render_slide_content(slide, slide_data)
            self._render_speaker_notes(slide, slide_data)

        out_path = Path(output_path).resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        prs.save(str(out_path))
        return str(out_path)

    def _render_background(self, slide) -> None:
        """Fill slide background with theme background color."""
        background = slide.background
        fill = background.fill
        fill.solid()
        fill.fore_color.rgb = self.theme.colors.background

    def _render_speaker_notes(self, slide, data: SlideContent) -> None:
        """Attach speaker notes if provided."""
        if data.speaker_notes:
            notes_slide = slide.notes_slide
            tf = notes_slide.notes_text_frame
            tf.text = data.speaker_notes

    def _render_slide_content(self, slide, data: SlideContent) -> None:
        """Dispatch rendering based on specific layout type."""
        layout = data.layout_type

        if layout == SlideLayoutType.TITLE:
            self._render_title_slide(slide, data)
        elif layout == SlideLayoutType.SECTION_HEADER:
            self._render_section_slide(slide, data)
        elif layout == SlideLayoutType.STATISTICS:
            self._render_statistics_slide(slide, data)
        elif layout == SlideLayoutType.COMPARISON or layout == SlideLayoutType.TWO_COLUMN:
            self._render_comparison_slide(slide, data)
        elif layout == SlideLayoutType.PROCESS:
            self._render_process_slide(slide, data)
        elif layout == SlideLayoutType.ARCHITECTURE:
            self._render_architecture_slide(slide, data)
        elif layout == SlideLayoutType.TIMELINE:
            self._render_timeline_slide(slide, data)
        elif layout == SlideLayoutType.TABLE:
            self._render_table_slide(slide, data)
        elif layout == SlideLayoutType.CODE:
            self._render_code_slide(slide, data)
        elif layout == SlideLayoutType.REFERENCES:
            self._render_references_slide(slide, data)
        elif layout == SlideLayoutType.CLOSING:
            self._render_closing_slide(slide, data)
        else:
            self._render_editorial_slide(slide, data)

    # -------------------------------------------------------------
    # Shared Header & Badge Renderer
    # -------------------------------------------------------------
    def _render_header(self, slide, data: SlideContent) -> None:
        """Render badge, slide title, subtitle, and accent divider."""
        # Category Badge
        if data.category_badge:
            badge_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.55), Inches(4.0), Inches(0.35))
            btf = badge_box.text_frame
            btf.word_wrap = True
            bp = btf.paragraphs[0]
            bp.text = data.category_badge.upper()
            bp.font.name = self.theme.typography.title_font
            bp.font.size = self.theme.typography.caption_size
            bp.font.bold = True
            bp.font.color.rgb = self.theme.colors.accent_primary

        # Title
        title_top = Inches(0.85) if data.category_badge else Inches(0.6)
        title_box = slide.shapes.add_textbox(Inches(0.8), title_top, Inches(11.7), Inches(0.8))
        ttf = title_box.text_frame
        ttf.word_wrap = True
        tp = ttf.paragraphs[0]
        tp.text = data.title
        tp.font.name = self.theme.typography.title_font
        tp.font.size = self.theme.typography.section_size
        tp.font.bold = True
        tp.font.color.rgb = self.theme.colors.text_primary

        # Subtitle
        if data.subtitle:
            sub_top = title_top + Inches(0.65)
            sub_box = slide.shapes.add_textbox(Inches(0.8), sub_top, Inches(11.7), Inches(0.5))
            stf = sub_box.text_frame
            stf.word_wrap = True
            sp = stf.paragraphs[0]
            sp.text = data.subtitle
            sp.font.name = self.theme.typography.body_font
            sp.font.size = self.theme.typography.body_size
            sp.font.color.rgb = self.theme.colors.text_muted

        # Subtle Accent Bar
        bar_top = title_top + Inches(1.2) if data.subtitle else title_top + Inches(0.75)
        bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), bar_top, Inches(1.5), Inches(0.04))
        bar.fill.solid()
        bar.fill.fore_color.rgb = self.theme.colors.accent_primary
        bar.line.fill.background()

    # -------------------------------------------------------------
    # 1. Title Slide
    # -------------------------------------------------------------
    def _render_title_slide(self, slide, data: SlideContent) -> None:
        # Decorative side accent glow / card
        accent_card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.5), Inches(0.15), Inches(4.2))
        accent_card.fill.solid()
        accent_card.fill.fore_color.rgb = self.theme.colors.accent_primary
        accent_card.line.fill.background()

        # Badge
        badge_box = slide.shapes.add_textbox(Inches(1.2), Inches(1.6), Inches(6.0), Inches(0.4))
        bp = badge_box.text_frame.paragraphs[0]
        bp.text = (data.category_badge or "ELECTORN AI PRESENTATION").upper()
        bp.font.name = self.theme.typography.title_font
        bp.font.size = Pt(13)
        bp.font.bold = True
        bp.font.color.rgb = self.theme.colors.accent_primary

        # Main Title
        title_box = slide.shapes.add_textbox(Inches(1.2), Inches(2.1), Inches(10.5), Inches(2.0))
        ttf = title_box.text_frame
        ttf.word_wrap = True
        tp = ttf.paragraphs[0]
        tp.text = data.title
        tp.font.name = self.theme.typography.title_font
        tp.font.size = self.theme.typography.title_size
        tp.font.bold = True
        tp.font.color.rgb = self.theme.colors.text_primary

        # Subtitle
        if data.subtitle:
            sub_box = slide.shapes.add_textbox(Inches(1.2), Inches(4.3), Inches(10.5), Inches(1.2))
            stf = sub_box.text_frame
            stf.word_wrap = True
            sp = stf.paragraphs[0]
            sp.text = data.subtitle
            sp.font.name = self.theme.typography.body_font
            sp.font.size = self.theme.typography.subtitle_size
            sp.font.color.rgb = self.theme.colors.text_secondary

        # Footer attribution
        footer_box = slide.shapes.add_textbox(Inches(1.2), Inches(6.2), Inches(10.5), Inches(0.4))
        fp = footer_box.text_frame.paragraphs[0]
        fp.text = "Generated by Electorn AI Autonomous Engine • HS AI Solutions"
        fp.font.name = self.theme.typography.body_font
        fp.font.size = Pt(11)
        fp.font.color.rgb = self.theme.colors.text_muted

    # -------------------------------------------------------------
    # 2. Section Header Slide
    # -------------------------------------------------------------
    def _render_section_slide(self, slide, data: SlideContent) -> None:
        self._render_header(slide, data)
        card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(2.6), Inches(11.7), Inches(3.8))
        card.fill.solid()
        card.fill.fore_color.rgb = self.theme.colors.surface
        card.line.color.rgb = self.theme.colors.surface_border

        if data.bullets:
            tf = card.text_frame
            tf.word_wrap = True
            for i, b in enumerate(data.bullets):
                p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
                p.text = f"•  {b}"
                p.font.name = self.theme.typography.body_font
                p.font.size = Pt(16)
                p.font.color.rgb = self.theme.colors.text_primary
                p.space_before = Pt(14)

    # -------------------------------------------------------------
    # 3. Statistics & Metrics Slide
    # -------------------------------------------------------------
    def _render_statistics_slide(self, slide, data: SlideContent) -> None:
        self._render_header(slide, data)
        metrics = data.metrics or [
            {"value": "95%", "label": "Benchmark Precision"},
            {"value": "3.5x", "label": "Performance Lift"},
            {"value": "< 100ms", "label": "Latency Score"},
        ]
        num_cards = len(metrics)
        card_w = Inches(11.7 / num_cards - 0.25)
        card_h = Inches(2.6)

        for i, m in enumerate(metrics):
            if isinstance(m, dict):
                val = str(m.get("value", ""))
                lbl = str(m.get("label", ""))
                desc = str(m.get("description", ""))
            else:
                val = str(getattr(m, "value", ""))
                lbl = str(getattr(m, "label", ""))
                desc = str(getattr(m, "description", "") or "")

            left = Inches(0.8 + i * (11.7 / num_cards))
            card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, Inches(2.4), card_w, card_h)
            card.fill.solid()
            card.fill.fore_color.rgb = self.theme.colors.surface
            card.line.color.rgb = self.theme.colors.surface_border

            # Number Text
            num_box = slide.shapes.add_textbox(left, Inches(2.6), card_w, Inches(1.0))
            np = num_box.text_frame.paragraphs[0]
            np.text = val
            np.alignment = PP_ALIGN.CENTER
            np.font.name = self.theme.typography.title_font
            np.font.size = self.theme.typography.metric_size
            np.font.bold = True
            np.font.color.rgb = self.theme.colors.accent_primary

            # Label Text
            lbl_box = slide.shapes.add_textbox(left + Inches(0.1), Inches(3.6), card_w - Inches(0.2), Inches(0.6))
            lp = lbl_box.text_frame.paragraphs[0]
            lp.text = lbl
            lp.alignment = PP_ALIGN.CENTER
            lp.font.name = self.theme.typography.body_font
            lp.font.size = Pt(14)
            lp.font.bold = True
            lp.font.color.rgb = self.theme.colors.text_primary

            # Description
            if desc:
                desc_box = slide.shapes.add_textbox(left + Inches(0.1), Inches(4.2), card_w - Inches(0.2), Inches(0.6))
                dp = desc_box.text_frame.paragraphs[0]
                dp.text = desc
                dp.alignment = PP_ALIGN.CENTER
                dp.font.name = self.theme.typography.body_font
                dp.font.size = Pt(11)
                dp.font.color.rgb = self.theme.colors.text_muted

        # Supporting text bullets below cards
        if data.bullets:
            bottom_box = slide.shapes.add_textbox(Inches(0.8), Inches(5.3), Inches(11.7), Inches(1.5))
            btf = bottom_box.text_frame
            btf.word_wrap = True
            for i, b in enumerate(data.bullets[:3]):
                bp = btf.paragraphs[0] if i == 0 else btf.add_paragraph()
                bp.text = f"•  {b}"
                bp.font.name = self.theme.typography.body_font
                bp.font.size = self.theme.typography.body_size
                bp.font.color.rgb = self.theme.colors.text_secondary
                bp.space_before = Pt(6)

    # -------------------------------------------------------------
    # 4. Comparison & Two-Column Slide
    # -------------------------------------------------------------
    def _render_comparison_slide(self, slide, data: SlideContent) -> None:
        self._render_header(slide, data)
        col_w = Inches(5.7)
        col_h = Inches(4.5)

        # Left Column Card
        left_card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(2.4), col_w, col_h)
        left_card.fill.solid()
        left_card.fill.fore_color.rgb = self.theme.colors.surface
        left_card.line.color.rgb = self.theme.colors.surface_border

        left_title = data.left_column_title or "Standard Overview"
        lt_box = slide.shapes.add_textbox(Inches(1.0), Inches(2.6), col_w - Inches(0.4), Inches(0.6))
        lp = lt_box.text_frame.paragraphs[0]
        lp.text = left_title
        lp.font.name = self.theme.typography.title_font
        lp.font.size = Pt(18)
        lp.font.bold = True
        lp.font.color.rgb = self.theme.colors.accent_secondary

        # Left Column Bullets
        bullets_l = data.left_column_bullets or data.bullets[:4]
        lb_box = slide.shapes.add_textbox(Inches(1.0), Inches(3.2), col_w - Inches(0.4), col_h - Inches(1.0))
        ltf = lb_box.text_frame
        ltf.word_wrap = True
        for i, b in enumerate(bullets_l):
            bp = ltf.paragraphs[0] if i == 0 else ltf.add_paragraph()
            bp.text = f"•  {b}"
            bp.font.name = self.theme.typography.body_font
            bp.font.size = self.theme.typography.body_size
            bp.font.color.rgb = self.theme.colors.text_secondary
            bp.space_before = Pt(8)

        # Right Column Card
        right_card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(6.8), Inches(2.4), col_w, col_h)
        right_card.fill.solid()
        right_card.fill.fore_color.rgb = self.theme.colors.surface
        right_card.line.color.rgb = self.theme.colors.accent_primary

        right_title = data.right_column_title or "Optimized Autonomous Architecture"
        rt_box = slide.shapes.add_textbox(Inches(7.0), Inches(2.6), col_w - Inches(0.4), Inches(0.6))
        rp = rt_box.text_frame.paragraphs[0]
        rp.text = right_title
        rp.font.name = self.theme.typography.title_font
        rp.font.size = Pt(18)
        rp.font.bold = True
        rp.font.color.rgb = self.theme.colors.accent_primary

        # Right Column Bullets
        bullets_r = data.right_column_bullets or data.bullets[4:8] or data.bullets
        rb_box = slide.shapes.add_textbox(Inches(7.0), Inches(3.2), col_w - Inches(0.4), col_h - Inches(1.0))
        rtf = rb_box.text_frame
        rtf.word_wrap = True
        for i, b in enumerate(bullets_r):
            bp = rtf.paragraphs[0] if i == 0 else rtf.add_paragraph()
            bp.text = f"✔  {b}"
            bp.font.name = self.theme.typography.body_font
            bp.font.size = self.theme.typography.body_size
            bp.font.color.rgb = self.theme.colors.text_primary
            bp.space_before = Pt(8)

    # -------------------------------------------------------------
    # 5. Process & Step Flow Slide
    # -------------------------------------------------------------
    def _render_process_slide(self, slide, data: SlideContent) -> None:
        self._render_header(slide, data)
        steps = data.process_steps or [
            {"number": 1, "title": "Phase 1: Ingestion", "description": "Extract content from multi-format docs"},
            {"number": 2, "title": "Phase 2: Planning", "description": "Synthesize narrative structures"},
            {"number": 3, "title": "Phase 3: Generation", "description": "Build editable PowerPoint elements"},
            {"number": 4, "title": "Phase 4: Verification", "description": "Validate typography and bounding boxes"},
        ]
        num_steps = len(steps)
        card_w = Inches(11.7 / num_steps - 0.25)
        card_h = Inches(4.2)

        for i, s in enumerate(steps):
            if isinstance(s, dict):
                num = s.get("number", i + 1)
                title = str(s.get("title", ""))
                desc = str(s.get("description", ""))
            else:
                num = getattr(s, "number", i + 1)
                title = str(getattr(s, "title", ""))
                desc = str(getattr(s, "description", ""))

            left = Inches(0.8 + i * (11.7 / num_steps))
            card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, Inches(2.4), card_w, card_h)
            card.fill.solid()
            card.fill.fore_color.rgb = self.theme.colors.surface
            card.line.color.rgb = self.theme.colors.surface_border

            # Number pill badge
            pill = slide.shapes.add_shape(MSO_SHAPE.OVAL, left + Inches(0.2), Inches(2.6), Inches(0.55), Inches(0.55))
            pill.fill.solid()
            pill.fill.fore_color.rgb = self.theme.colors.accent_primary
            pill.line.fill.background()
            pp = pill.text_frame.paragraphs[0]
            pp.text = str(num)
            pp.alignment = PP_ALIGN.CENTER
            pp.font.bold = True
            pp.font.size = Pt(14)
            pp.font.color.rgb = RGBColor(11, 15, 25)

            # Step Title
            st_box = slide.shapes.add_textbox(left + Inches(0.2), Inches(3.3), card_w - Inches(0.4), Inches(0.8))
            stp = st_box.text_frame.paragraphs[0]
            stp.text = title
            stp.font.name = self.theme.typography.title_font
            stp.font.size = Pt(15)
            stp.font.bold = True
            stp.font.color.rgb = self.theme.colors.text_primary

            # Step Description
            sd_box = slide.shapes.add_textbox(left + Inches(0.2), Inches(4.2), card_w - Inches(0.4), Inches(2.0))
            sdf = sd_box.text_frame
            sdf.word_wrap = True
            sdp = sdf.paragraphs[0]
            sdp.text = desc
            sdp.font.name = self.theme.typography.body_font
            sdp.font.size = Pt(12)
            sdp.font.color.rgb = self.theme.colors.text_secondary

    # -------------------------------------------------------------
    # 6. Technical Architecture Slide
    # -------------------------------------------------------------
    def _render_architecture_slide(self, slide, data: SlideContent) -> None:
        self._render_header(slide, data)
        arch = data.architecture or [
            {"layer": "Layer 1: Input", "name": "Ingestion Core", "items": ["PDF", "DOCX", "Markdown"]},
            {"layer": "Layer 2: AI Core", "name": "Planning & Reasoning", "items": ["Agent Planner", "Schema Validator"]},
            {"layer": "Layer 3: Output", "name": "PowerPoint Engine", "items": ["python-pptx", "QA Verifier"]},
        ]
        layer_h = Inches(1.3)
        for i, comp in enumerate(arch):
            top = Inches(2.4 + i * 1.45)
            if isinstance(comp, dict):
                layer_name = str(comp.get("layer", ""))
                name = str(comp.get("name", ""))
                items = comp.get("items", [])
            else:
                layer_name = str(getattr(comp, "layer", ""))
                name = str(getattr(comp, "name", ""))
                items = getattr(comp, "items", [])

            # Outer Layer Box
            box = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), top, Inches(11.7), layer_h)
            box.fill.solid()
            box.fill.fore_color.rgb = self.theme.colors.surface
            box.line.color.rgb = self.theme.colors.surface_border

            # Layer Header
            lh_box = slide.shapes.add_textbox(Inches(1.0), top + Inches(0.1), Inches(3.0), Inches(0.4))
            lhp = lh_box.text_frame.paragraphs[0]
            lhp.text = f"{layer_name} • {name}"
            lhp.font.bold = True
            lhp.font.size = Pt(13)
            lhp.font.color.rgb = self.theme.colors.accent_primary

            # Component sub-cards
            item_w = Inches(2.5)
            for j, item in enumerate(items[:4]):
                item_card = slide.shapes.add_shape(
                    MSO_SHAPE.RECTANGLE,
                    Inches(1.0 + j * 2.7),
                    top + Inches(0.55),
                    item_w,
                    Inches(0.55)
                )
                item_card.fill.solid()
                item_card.fill.fore_color.rgb = self.theme.colors.code_bg
                item_card.line.color.rgb = self.theme.colors.surface_border
                ip = item_card.text_frame.paragraphs[0]
                ip.text = item
                ip.alignment = PP_ALIGN.CENTER
                ip.font.size = Pt(12)
                ip.font.color.rgb = self.theme.colors.text_primary

    # -------------------------------------------------------------
    # 7. Timeline Slide
    # -------------------------------------------------------------
    def _render_timeline_slide(self, slide, data: SlideContent) -> None:
        self._render_header(slide, data)
        items = data.timeline or [
            {"step": "Milestone 1", "title": "Discovery", "description": "System architecture and scope mapping"},
            {"step": "Milestone 2", "title": "Prototyping", "description": "Engine synthesis and testing"},
            {"step": "Milestone 3", "title": "Production", "description": "Enterprise deployment and verification"},
        ]
        # Horizontal Connecting Line
        line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(1.5), Inches(3.2), Inches(10.3), Inches(0.04))
        line.fill.solid()
        line.fill.fore_color.rgb = self.theme.colors.accent_primary
        line.line.fill.background()

        num_items = len(items)
        spacing = 10.3 / max(1, num_items - 1) if num_items > 1 else 5.0

        for i, item in enumerate(items):
            if isinstance(item, dict):
                step = str(item.get("step", ""))
                title = str(item.get("title", ""))
                desc = str(item.get("description", ""))
            else:
                step = str(getattr(item, "step", ""))
                title = str(getattr(item, "title", ""))
                desc = str(getattr(item, "description", ""))

            center_x = Inches(1.5 + i * spacing)

            # Node Dot
            dot = slide.shapes.add_shape(MSO_SHAPE.OVAL, center_x - Inches(0.2), Inches(3.02), Inches(0.4), Inches(0.4))
            dot.fill.solid()
            dot.fill.fore_color.rgb = self.theme.colors.accent_secondary
            dot.line.color.rgb = self.theme.colors.background

            # Step label above
            top_box = slide.shapes.add_textbox(center_x - Inches(1.5), Inches(2.4), Inches(3.0), Inches(0.5))
            tp = top_box.text_frame.paragraphs[0]
            tp.text = step.upper()
            tp.alignment = PP_ALIGN.CENTER
            tp.font.bold = True
            tp.font.size = Pt(11)
            tp.font.color.rgb = self.theme.colors.accent_primary

            # Content card below
            card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, center_x - Inches(1.4), Inches(3.7), Inches(2.8), Inches(2.8))
            card.fill.solid()
            card.fill.fore_color.rgb = self.theme.colors.surface
            card.line.color.rgb = self.theme.colors.surface_border

            ct_box = slide.shapes.add_textbox(center_x - Inches(1.3), Inches(3.8), Inches(2.6), Inches(0.5))
            ctp = ct_box.text_frame.paragraphs[0]
            ctp.text = title
            ctp.font.bold = True
            ctp.font.size = Pt(14)
            ctp.font.color.rgb = self.theme.colors.text_primary

            cd_box = slide.shapes.add_textbox(center_x - Inches(1.3), Inches(4.3), Inches(2.6), Inches(2.0))
            cdf = cd_box.text_frame
            cdf.word_wrap = True
            cdp = cdf.paragraphs[0]
            cdp.text = desc
            cdp.font.size = Pt(11)
            cdp.font.color.rgb = self.theme.colors.text_secondary

    # -------------------------------------------------------------
    # 8. Table Slide
    # -------------------------------------------------------------
    def _render_table_slide(self, slide, data: SlideContent) -> None:
        self._render_header(slide, data)
        table_data = data.table

        headers = table_data.headers if table_data else ["Criteria", "Traditional Method", "Electorn Engine"]
        rows = table_data.rows if table_data else [
            ["Generation Speed", "Hours manual", "Seconds autonomous"],
            ["Verification", "Manual review", "Automated QA inspector"],
            ["Editable Shapes", "No (Screenshots)", "Yes (Native Vector)"],
        ]

        num_rows = len(rows) + 1
        num_cols = len(headers)
        table_shape = slide.shapes.add_table(num_rows, num_cols, Inches(0.8), Inches(2.4), Inches(11.7), Inches(4.4))
        tbl = table_shape.table

        # Format Header Row
        for col_idx, h in enumerate(headers):
            cell = tbl.cell(0, col_idx)
            cell.text = str(h)
            cell.fill.solid()
            cell.fill.fore_color.rgb = self.theme.colors.surface
            p = cell.text_frame.paragraphs[0]
            p.font.name = self.theme.typography.title_font
            p.font.size = Pt(13)
            p.font.bold = True
            p.font.color.rgb = self.theme.colors.accent_primary

        # Format Data Rows
        for row_idx, r in enumerate(rows):
            for col_idx, val in enumerate(r[:num_cols]):
                cell = tbl.cell(row_idx + 1, col_idx)
                cell.text = str(val)
                cell.fill.solid()
                cell.fill.fore_color.rgb = self.theme.colors.code_bg
                p = cell.text_frame.paragraphs[0]
                p.font.name = self.theme.typography.body_font
                p.font.size = Pt(12)
                p.font.color.rgb = self.theme.colors.text_primary

    # -------------------------------------------------------------
    # 9. Code Slide
    # -------------------------------------------------------------
    def _render_code_slide(self, slide, data: SlideContent) -> None:
        self._render_header(slide, data)
        code_text = data.code_snippet or 'print("Electorn AI autonomous execution active")'

        card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(2.4), Inches(11.7), Inches(4.4))
        card.fill.solid()
        card.fill.fore_color.rgb = self.theme.colors.code_bg
        card.line.color.rgb = self.theme.colors.surface_border

        code_box = slide.shapes.add_textbox(Inches(1.1), Inches(2.6), Inches(11.1), Inches(4.0))
        ctf = code_box.text_frame
        ctf.word_wrap = True
        lines = code_text.split("\n")
        for i, line in enumerate(lines):
            p = ctf.paragraphs[0] if i == 0 else ctf.add_paragraph()
            p.text = line
            p.font.name = self.theme.typography.code_font
            p.font.size = Pt(12)
            p.font.color.rgb = self.theme.colors.text_primary

    # -------------------------------------------------------------
    # 10. References Slide
    # -------------------------------------------------------------
    def _render_references_slide(self, slide, data: SlideContent) -> None:
        self._render_header(slide, data)
        citations = data.citations or [
            "Official Electorn AI Documentation & Technical Blueprint v0.1.0",
            "IEEE Autonomous Agents and Multi-Tier Orchestration Standards",
            "W3C Architecture Recommendations for Automation Runtimes",
        ]

        card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(2.4), Inches(11.7), Inches(4.4))
        card.fill.solid()
        card.fill.fore_color.rgb = self.theme.colors.surface
        card.line.color.rgb = self.theme.colors.surface_border

        ref_box = slide.shapes.add_textbox(Inches(1.2), Inches(2.7), Inches(11.0), Inches(3.8))
        rtf = ref_box.text_frame
        rtf.word_wrap = True
        for i, cite in enumerate(citations):
            p = rtf.paragraphs[0] if i == 0 else rtf.add_paragraph()
            p.text = f"[{i+1}]  {cite}"
            p.font.name = self.theme.typography.body_font
            p.font.size = Pt(14)
            p.font.color.rgb = self.theme.colors.text_secondary
            p.space_before = Pt(14)

    # -------------------------------------------------------------
    # 11. Closing Slide
    # -------------------------------------------------------------
    def _render_closing_slide(self, slide, data: SlideContent) -> None:
        self._render_header(slide, data)
        card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(2.4), Inches(11.7), Inches(4.4))
        card.fill.solid()
        card.fill.fore_color.rgb = self.theme.colors.surface
        card.line.color.rgb = self.theme.colors.accent_primary

        tb = slide.shapes.add_textbox(Inches(1.2), Inches(3.0), Inches(11.0), Inches(3.0))
        tf = tb.text_frame
        tf.word_wrap = True

        p1 = tf.paragraphs[0]
        p1.text = "Discussion & Questions"
        p1.font.name = self.theme.typography.title_font
        p1.font.size = Pt(28)
        p1.font.bold = True
        p1.font.color.rgb = self.theme.colors.text_primary

        p2 = tf.add_paragraph()
        p2.text = "Thank you for your attendance and engagement."
        p2.font.size = Pt(16)
        p2.font.color.rgb = self.theme.colors.text_secondary
        p2.space_before = Pt(12)

        p3 = tf.add_paragraph()
        p3.text = "Explore the full product suite: https://hs-ai-studio.onrender.com/"
        p3.font.size = Pt(13)
        p3.font.color.rgb = self.theme.colors.accent_primary
        p3.space_before = Pt(18)

    # -------------------------------------------------------------
    # 12. Editorial / General Slide
    # -------------------------------------------------------------
    def _render_editorial_slide(self, slide, data: SlideContent) -> None:
        self._render_header(slide, data)
        card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(2.4), Inches(11.7), Inches(4.4))
        card.fill.solid()
        card.fill.fore_color.rgb = self.theme.colors.surface
        card.line.color.rgb = self.theme.colors.surface_border

        bullets = data.bullets or ["Comprehensive analysis of core parameters", "Systemic evaluation and benchmark results"]
        tb = slide.shapes.add_textbox(Inches(1.2), Inches(2.7), Inches(11.0), Inches(3.8))
        tf = tb.text_frame
        tf.word_wrap = True
        for i, b in enumerate(bullets):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            p.text = f"•  {b}"
            p.font.name = self.theme.typography.body_font
            p.font.size = self.theme.typography.body_size
            p.font.color.rgb = self.theme.colors.text_primary
            p.space_before = Pt(12)
