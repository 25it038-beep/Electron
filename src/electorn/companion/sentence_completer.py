"""Sentence Completion & Syntactic Continuation Intelligence.

Evaluates whether speech transcript is grammatically and semantically complete
or an in-progress fragment waiting for sentence continuation.
Supports English, Tamil, and bilingual Tamil-English code-switching.
"""
from __future__ import annotations

import logging
import re
from typing import List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


class SentenceCompleter:
    """Analyzes utterance syntactic completeness and stitches multi-segment transcripts."""

    # English trailing continuation conjunctions & sub-clauses
    ENGLISH_TRAILING_CONJUNCTIONS: Set[str] = {
        "and", "because", "but", "if", "when", "that", "which", "where",
        "while", "though", "although", "since", "unless", "until", "or",
        "so", "then", "whether", "as", "whereas", "however", "therefore",
        "also", "plus", "besides", "even",
    }

    # English trailing prepositions & particles
    ENGLISH_TRAILING_PREPOSITIONS: Set[str] = {
        "to", "with", "for", "by", "from", "at", "in", "on", "into",
        "through", "about", "towards", "against", "over", "under", "between",
        "of", "off", "onto", "out",
    }

    # English trailing determiners & articles
    ENGLISH_TRAILING_DETERMINERS: Set[str] = {
        "a", "an", "the", "my", "your", "his", "her", "their", "our",
        "this", "that", "these", "those", "some", "any", "every", "all",
    }

    # Incomplete auxiliary / modal / intent stems
    ENGLISH_INCOMPLETE_VERB_STEMS: Set[str] = {
        "want", "wants", "wanted", "need", "needs", "needed", "like", "likes",
        "going", "try", "trying", "plan", "planning", "hope", "hoping",
        "start", "starting", "create", "creating", "make", "making",
        "build", "building", "open", "opening", "find", "finding", "search",
        "searching", "tell", "telling", "ask", "asking", "give", "giving",
    }

    # Tamil trailing continuation markers, conjunctions & participial verbs
    TAMIL_TRAILING_MARKERS: Set[str] = {
        "அப்புறம்",     # appuram (and then)
        "ஆனா",          # aana (but)
        "ஏன்னா",        # yen-na (because)
        "கூட",          # kooda (also/even)
        "இருந்தாலும்",   # irunthaalum (although)
        "அதோட",         # adhoda (in addition)
        "பண்ணிட்டு",     # pannittu (having done / after doing)
        "வந்து",         # vandhu (um / well / filler)
        "பண்ணி",        # panni (do and...)
        "போய்",         # poi (go and...)
        "எடுத்து",       # yeduthu (take and...)
        "பாத்து",       # paathu (look and...)
        "சொல்லி",       # solli (say and...)
        "வெச்சு",       # vechu (keep and...)
        "என்ற",         # endra (that...)
        "என்று",        # endru (that...)
        "மாதிரி",       # maadhiri (like...)
        "எல்லாம்",       # ellaam (all...)
    }

    # Tamil transliterated English markers (Tanglish)
    TANGLISH_TRAILING_MARKERS: Set[str] = {
        "appuram", "apram", "aana", "aanalum", "yenna", "yendral", "kooda",
        "irundhalum", "adhoda", "adhuvum", "vandhu", "pannitu", "panni",
        "poi", "eduthu", "paathu", "solli",
    }

    def is_complete(self, text: str) -> Tuple[bool, str]:
        """Determine if an utterance is syntactically complete.

        Returns (is_complete, reason).
        """
        clean = text.strip()
        if not clean:
            return False, "empty_text"

        # Split by whitespace and strip outer punctuation to preserve full Unicode Indic words
        tokens = [w.strip(".,!?;:\"'") for w in clean.lower().split() if w.strip(".,!?;:\"'")]
        if not tokens:
            return False, "no_tokens"

        # Very short single words are usually incomplete unless a direct command like "stop" or "yes"
        standalone_single_words = {"stop", "halt", "yes", "no", "sure", "cancel", "mute", "unmute", "quit", "exit"}
        if len(tokens) == 1 and tokens[0] not in standalone_single_words:
            return False, "single_word_fragment"

        last_token = tokens[-1]
        second_last = tokens[-2] if len(tokens) >= 2 else ""

        # 1. Punctuation checks
        if clean.endswith("...") or clean.endswith("…"):
            return False, "trailing_ellipsis"
        if clean.endswith(",") or clean.endswith("-") or clean.endswith("—"):
            return False, "trailing_comma_or_dash"

        # 2. English conjunction check
        if last_token in self.ENGLISH_TRAILING_CONJUNCTIONS:
            return False, f"trailing_conjunction_{last_token}"

        # 3. English preposition check
        if last_token in self.ENGLISH_TRAILING_PREPOSITIONS:
            return False, f"trailing_preposition_{last_token}"

        # 4. English determiner check
        if last_token in self.ENGLISH_TRAILING_DETERMINERS:
            return False, f"trailing_determiner_{last_token}"

        # 5. Incomplete verb phrase: "want to", "going to", "create a", "open the"
        if second_last in self.ENGLISH_INCOMPLETE_VERB_STEMS and last_token in {"to", "a", "an", "the", "my"}:
            return False, f"incomplete_verb_phrase_{second_last}_{last_token}"

        # 6. Tamil markers
        if last_token in self.TAMIL_TRAILING_MARKERS or last_token in self.TANGLISH_TRAILING_MARKERS:
            return False, f"tamil_continuation_{last_token}"

        # 7. Check if sentence ends with trailing filler sounds
        if last_token in {"uh", "um", "er", "ah", "hmm"}:
            return False, f"trailing_filler_{last_token}"

        return True, "complete_sentence"

    def stitch_segments(self, prior_text: str, new_text: str) -> str:
        """Combine prior speech fragment with newly recognized speech, eliminating boundary duplicates."""
        prior = prior_text.strip()
        new = new_text.strip()

        if not prior:
            return new
        if not new:
            return prior

        # Clean trailing ellipses or hyphens from prior segment
        prior_clean = re.sub(r"[\s\.\,\-]+$", "", prior)

        prior_words = prior_clean.split()
        new_words = new.split()

        # Deduplicate overlap at junction:
        # e.g. prior="open browser and", new="and search" -> overlap 1 word "and"
        overlap_len = 0
        max_check = min(len(prior_words), len(new_words), 4)

        for n in range(max_check, 0, -1):
            prior_slice = [w.lower() for w in prior_words[-n:]]
            new_slice = [w.lower() for w in new_words[:n]]
            if prior_slice == new_slice:
                overlap_len = n
                break

        if overlap_len > 0:
            stitched_words = prior_words + new_words[overlap_len:]
        else:
            stitched_words = prior_words + new_words

        return " ".join(stitched_words)
