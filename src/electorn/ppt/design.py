"""Design theme presets, color palettes, and typographic hierarchies for PowerPoint slides."""

from __future__ import annotations

from dataclasses import dataclass
from pptx.dml.color import RGBColor
from pptx.util import Pt
from electorn.ppt.schema import PresentationStyle


@dataclass
class ColorPalette:
    background: RGBColor
    surface: RGBColor
    surface_border: RGBColor
    accent_primary: RGBColor
    accent_secondary: RGBColor
    text_primary: RGBColor
    text_secondary: RGBColor
    text_muted: RGBColor
    code_bg: RGBColor


@dataclass
class Typography:
    title_font: str
    body_font: str
    code_font: str
    title_size: Pt
    subtitle_size: Pt
    section_size: Pt
    body_size: Pt
    caption_size: Pt
    metric_size: Pt


@dataclass
class DesignTheme:
    style: PresentationStyle
    colors: ColorPalette
    typography: Typography
    is_dark: bool


# Pre-configured production design palettes
THEMES: dict[PresentationStyle, DesignTheme] = {
    PresentationStyle.PREMIUM_DARK: DesignTheme(
        style=PresentationStyle.PREMIUM_DARK,
        is_dark=True,
        colors=ColorPalette(
            background=RGBColor(11, 15, 25),         # #0B0F19 Obsidian
            surface=RGBColor(17, 24, 39),            # #111827 Dark card
            surface_border=RGBColor(31, 41, 55),     # #1F2937 Border
            accent_primary=RGBColor(6, 182, 212),     # #06B6D4 Electric Cyan
            accent_secondary=RGBColor(99, 102, 241),  # #6366F1 Violet
            text_primary=RGBColor(248, 250, 252),    # #F8FAFC
            text_secondary=RGBColor(203, 213, 225),  # #CBD5E1
            text_muted=RGBColor(148, 163, 184),      # #94A3B8
            code_bg=RGBColor(15, 23, 42),            # #0F172A
        ),
        typography=Typography(
            title_font="Segoe UI",
            body_font="Segoe UI",
            code_font="Consolas",
            title_size=Pt(36),
            subtitle_size=Pt(18),
            section_size=Pt(28),
            body_size=Pt(14),
            caption_size=Pt(11),
            metric_size=Pt(44),
        )
    ),
    PresentationStyle.MINIMALIST_LIGHT: DesignTheme(
        style=PresentationStyle.MINIMALIST_LIGHT,
        is_dark=False,
        colors=ColorPalette(
            background=RGBColor(255, 255, 255),      # Clean White
            surface=RGBColor(248, 250, 252),         # Slate 50
            surface_border=RGBColor(226, 232, 240),  # Slate 200
            accent_primary=RGBColor(15, 23, 42),      # Deep Navy/Charcoal
            accent_secondary=RGBColor(37, 99, 235),  # Cobalt Blue
            text_primary=RGBColor(15, 23, 42),       # Slate 900
            text_secondary=RGBColor(71, 85, 105),    # Slate 600
            text_muted=RGBColor(148, 163, 184),      # Slate 400
            code_bg=RGBColor(241, 245, 249),         # Slate 100
        ),
        typography=Typography(
            title_font="Segoe UI",
            body_font="Segoe UI",
            code_font="Consolas",
            title_size=Pt(36),
            subtitle_size=Pt(18),
            section_size=Pt(28),
            body_size=Pt(14),
            caption_size=Pt(11),
            metric_size=Pt(44),
        )
    ),
    PresentationStyle.ACADEMIC: DesignTheme(
        style=PresentationStyle.ACADEMIC,
        is_dark=False,
        colors=ColorPalette(
            background=RGBColor(250, 250, 249),      # Warm Paper
            surface=RGBColor(255, 255, 255),         # Clean Card
            surface_border=RGBColor(214, 211, 209),  # Stone 300
            accent_primary=RGBColor(120, 53, 15),    # Rich Amber / Mahogany
            accent_secondary=RGBColor(30, 58, 138),  # Academic Blue
            text_primary=RGBColor(28, 25, 23),       # Stone 900
            text_secondary=RGBColor(68, 64, 60),     # Stone 700
            text_muted=RGBColor(120, 113, 108),      # Stone 500
            code_bg=RGBColor(245, 245, 244),         # Stone 100
        ),
        typography=Typography(
            title_font="Georgia",
            body_font="Calibri",
            code_font="Consolas",
            title_size=Pt(34),
            subtitle_size=Pt(17),
            section_size=Pt(26),
            body_size=Pt(14),
            caption_size=Pt(10),
            metric_size=Pt(42),
        )
    ),
    PresentationStyle.RESEARCH: DesignTheme(
        style=PresentationStyle.RESEARCH,
        is_dark=False,
        colors=ColorPalette(
            background=RGBColor(248, 250, 252),      # Lab Light
            surface=RGBColor(255, 255, 255),
            surface_border=RGBColor(203, 213, 225),
            accent_primary=RGBColor(3, 105, 161),    # Scientific Cyan/Teal
            accent_secondary=RGBColor(13, 148, 136), # Emerald Accent
            text_primary=RGBColor(15, 23, 42),
            text_secondary=RGBColor(51, 65, 85),
            text_muted=RGBColor(100, 116, 139),
            code_bg=RGBColor(241, 245, 249),
        ),
        typography=Typography(
            title_font="Segoe UI",
            body_font="Segoe UI",
            code_font="Consolas",
            title_size=Pt(34),
            subtitle_size=Pt(17),
            section_size=Pt(26),
            body_size=Pt(14),
            caption_size=Pt(10),
            metric_size=Pt(42),
        )
    ),
    PresentationStyle.CORPORATE_PITCH: DesignTheme(
        style=PresentationStyle.CORPORATE_PITCH,
        is_dark=True,
        colors=ColorPalette(
            background=RGBColor(10, 25, 47),         # Pitch Navy
            surface=RGBColor(17, 34, 64),            # Navy surface
            surface_border=RGBColor(35, 53, 84),
            accent_primary=RGBColor(100, 255, 218),  # Mint Cyan
            accent_secondary=RGBColor(56, 189, 248), # Sky Blue
            text_primary=RGBColor(204, 214, 246),
            text_secondary=RGBColor(136, 146, 176),
            text_muted=RGBColor(100, 116, 139),
            code_bg=RGBColor(15, 23, 42),
        ),
        typography=Typography(
            title_font="Segoe UI",
            body_font="Segoe UI",
            code_font="Consolas",
            title_size=Pt(36),
            subtitle_size=Pt(18),
            section_size=Pt(28),
            body_size=Pt(14),
            caption_size=Pt(11),
            metric_size=Pt(46),
        )
    ),
    PresentationStyle.DATA_REPORT: DesignTheme(
        style=PresentationStyle.DATA_REPORT,
        is_dark=False,
        colors=ColorPalette(
            background=RGBColor(255, 255, 255),
            surface=RGBColor(248, 250, 252),
            surface_border=RGBColor(226, 232, 240),
            accent_primary=RGBColor(14, 116, 144),   # Data Cyan
            accent_secondary=RGBColor(16, 185, 129), # Growth Emerald
            text_primary=RGBColor(15, 23, 42),
            text_secondary=RGBColor(71, 85, 105),
            text_muted=RGBColor(148, 163, 184),
            code_bg=RGBColor(241, 245, 249),
        ),
        typography=Typography(
            title_font="Segoe UI",
            body_font="Segoe UI",
            code_font="Consolas",
            title_size=Pt(34),
            subtitle_size=Pt(17),
            section_size=Pt(26),
            body_size=Pt(13),
            caption_size=Pt(10),
            metric_size=Pt(42),
        )
    ),
    PresentationStyle.CINEMATIC: DesignTheme(
        style=PresentationStyle.CINEMATIC,
        is_dark=True,
        colors=ColorPalette(
            background=RGBColor(5, 5, 5),            # Pure Cinema Black
            surface=RGBColor(23, 23, 23),            # Neutral 900
            surface_border=RGBColor(38, 38, 38),     # Neutral 800
            accent_primary=RGBColor(245, 158, 11),   # Golden Amber
            accent_secondary=RGBColor(239, 68, 68),  # Crimson Red
            text_primary=RGBColor(255, 255, 255),
            text_secondary=RGBColor(212, 212, 216),
            text_muted=RGBColor(113, 113, 122),
            code_bg=RGBColor(15, 15, 15),
        ),
        typography=Typography(
            title_font="Segoe UI",
            body_font="Segoe UI",
            code_font="Consolas",
            title_size=Pt(38),
            subtitle_size=Pt(20),
            section_size=Pt(30),
            body_size=Pt(15),
            caption_size=Pt(11),
            metric_size=Pt(48),
        )
    ),
}


def get_theme(style: PresentationStyle | str) -> DesignTheme:
    """Resolve theme instance by style name or enum."""
    if isinstance(style, str):
        try:
            style = PresentationStyle(style.lower().strip())
        except ValueError:
            style = PresentationStyle.PREMIUM_DARK
    return THEMES.get(style, THEMES[PresentationStyle.PREMIUM_DARK])
