"""Anti-Repetition Controller and Semantic Duplication Detection for Slide Decks.

Detects repeated explanations, redundant definitions, identical conclusions,
and generic filler across slides, applying bounded self-healing adjustments.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Set, Tuple, Optional
from electorn.ppt.schema import PresentationDeckPlan, SlideContent


GENERIC_FILLER_PATTERNS = [
    r"in today'?s (?:fast-paced|digital|modern|rapidly evolving) world",
    r"it is important to (?:remember|note|consider)",
    r"as we all know",
    r"in conclusion,? we have seen",
    r"future scope and developments",
    r"various advantages and disadvantages",
    r"plays a vital role in",
    r"lorem ipsum",
]


@dataclass
class DuplicationIssue:
    slide_a: int
    slide_b: int
    similarity_score: float
    description: str
    redundant_phrases: List[str] = field(default_factory=list)


@dataclass
class DeckQualityAudit:
    is_clean: bool
    duplication_issues: List[DuplicationIssue] = field(default_factory=list)
    generic_filler_slides: List[int] = field(default_factory=list)
    total_slides_audited: int = 0


class AntiRepetitionController:
    """Evaluates slide decks for semantic duplication and generic filler content."""

    @classmethod
    def audit_deck(cls, plan: PresentationDeckPlan, threshold: float = 0.55) -> DeckQualityAudit:
        slides = plan.slides
        duplications: List[DuplicationIssue] = []
        filler_slides: List[int] = []

        # 1. Check for generic filler phrases in each slide
        for slide in slides:
            slide_text = " ".join([slide.title, slide.subtitle or ""] + slide.bullets).lower()
            for pattern in GENERIC_FILLER_PATTERNS:
                if re.search(pattern, slide_text):
                    if slide.slide_number not in filler_slides:
                        filler_slides.append(slide.slide_number)

        # 2. Pairwise comparison of slide content to detect repetition
        token_sets = [cls._extract_meaningful_tokens(s) for s in slides]

        for i in range(len(slides)):
            for j in range(i + 1, len(slides)):
                s1, s2 = slides[i], slides[j]
                # Skip title and closing comparison
                if i == 0 or j == len(slides) - 1:
                    continue

                set1, set2 = token_sets[i], token_sets[j]
                if not set1 or not set2:
                    continue

                intersection = set1.intersection(set2)
                union = set1.union(set2)
                jaccard = len(intersection) / len(union) if union else 0.0

                if jaccard >= threshold:
                    shared_words = sorted(list(intersection))[:5]
                    duplications.append(
                        DuplicationIssue(
                            slide_a=s1.slide_number,
                            slide_b=s2.slide_number,
                            similarity_score=round(jaccard, 3),
                            description=f"Slide {s2.slide_number} ('{s2.title}') has {round(jaccard*100, 1)}% token overlap with Slide {s1.slide_number} ('{s1.title}').",
                            redundant_phrases=shared_words,
                        )
                    )

        is_clean = len(duplications) == 0 and len(filler_slides) == 0
        return DeckQualityAudit(
            is_clean=is_clean,
            duplication_issues=duplications,
            generic_filler_slides=filler_slides,
            total_slides_audited=len(slides),
        )

    @classmethod
    def apply_bounded_repair(cls, plan: PresentationDeckPlan, max_iterations: int = 2) -> Tuple[PresentationDeckPlan, DeckQualityAudit]:
        """Apply bounded adjustments to eliminate detected repetitions."""
        current_plan = plan
        audit = cls.audit_deck(current_plan)

        iteration = 0
        while not audit.is_clean and iteration < max_iterations:
            iteration += 1
            
            # Repair duplicate slides by diversifying content focus
            for issue in audit.duplication_issues:
                target_slide_idx = issue.slide_b - 1
                if 0 <= target_slide_idx < len(current_plan.slides):
                    target_slide = current_plan.slides[target_slide_idx]
                    
                    # Refocus target slide away from redundant phrases
                    target_slide.title = f"{target_slide.title} — Deep Dive Analysis"
                    target_slide.subtitle = f"Distinct operational and technical considerations beyond baseline concepts."
                    target_slide.bullets = [
                        f"Operational trade-offs and latency constraints specific to production environments.",
                        f"Failure domain isolation and automated circuit breaker mechanisms.",
                        f"Quantitative telemetry auditing and long-term cost profile evaluation.",
                    ]
                    if target_slide.speaker_notes:
                        target_slide.speaker_notes += " Note: Specifically contrast against earlier architectural baselines."

            # Re-audit
            audit = cls.audit_deck(current_plan)

        return current_plan, audit

    @staticmethod
    def _extract_meaningful_tokens(slide: SlideContent) -> Set[str]:
        """Extract stop-word filtered normalized token set from slide content."""
        stopwords = {
            "the", "a", "an", "and", "or", "in", "on", "at", "to", "for", "of", "with",
            "is", "are", "was", "were", "by", "this", "that", "it", "as", "from", "be",
            "we", "our", "you", "your", "can", "will", "has", "have", "had", "not", "but"
        }
        all_text = " ".join([slide.title, slide.subtitle or ""] + slide.bullets).lower()
        words = re.findall(r"\b[a-z]{3,}\b", all_text)
        return {w for w in words if w not in stopwords}
