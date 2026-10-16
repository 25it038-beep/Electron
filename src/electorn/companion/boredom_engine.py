"""Boredom and Discovery Engine for Electorn AI Companion.

Provides interactive text RPG adventures, tech trivia quizzes, coding mini-challenges,
startup brainstorming, and personalized entertainment when the user feels bored.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
import random
import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class AdventureNode(BaseModel):
    """A narrative state in an interactive text-based RPG."""
    node_id: str
    narrative: str
    options: List[Dict[str, str]]                # [{"text": "Inspect the terminal", "target": "node_terminal"}]
    inventory_acquired: Optional[str] = None


class TriviaItem(BaseModel):
    """A technology, science, or AI trivia question."""
    question: str
    options: List[str]                           # 4 multiple choice options
    correct_idx: int                             # 0-3
    explanation: str


class CodingChallenge(BaseModel):
    """A practical bite-sized programming exercise."""
    title: str
    difficulty: str                              # beginner, intermediate, advanced
    description: str
    starter_code: str
    solution: str
    hints: List[str]


class BoredomEngine:
    """Orchestrates interactive games, quizzes, brainstorming, and curiosity explorations."""

    TRIVIA_QUESTIONS = [
        TriviaItem(
            question="In transformer neural networks, what mechanism calculates relationship weights between all words in an input sequence?",
            options=["Backpropagation", "Self-Attention", "Batch Normalization", "Gradient Clipping"],
            correct_idx=1,
            explanation="Self-attention (introduced in 'Attention Is All You Need', 2017) allows tokens to dynamically attend to other tokens in the context window.",
        ),
        TriviaItem(
            question="Which Python data structure provides O(1) average-time complexity for lookups and insertions?",
            options=["List", "Dict / Set (Hash Map)", "Tuple", "Deque"],
            correct_idx=1,
            explanation="Python dictionaries and sets are implemented as open-addressing hash tables providing O(1) average time lookups.",
        ),
        TriviaItem(
            question="What is the primary role of a viseme in speech animation and 3D avatar rendering?",
            options=["Simulating eye blinking", "The visual facial position corresponding to a phoneme", "Calculating audio volume", "Rendering skin subsurface scattering"],
            correct_idx=1,
            explanation="A viseme is the visual equivalent of a phoneme—the specific mouth/lip shape observed when producing speech sounds.",
        ),
        TriviaItem(
            question="Which Windows command-line utility displays real-time active TCP connections and listening ports?",
            options=["ipconfig", "netstat -ano", "tracert", "nslookup"],
            correct_idx=1,
            explanation="'netstat -ano' shows active TCP/UDP sockets with numeric ports and associated Process IDs (PIDs).",
        ),
    ]

    CODING_CHALLENGES = [
        CodingChallenge(
            title="Two Sum Target Index Pair",
            difficulty="intermediate",
            description="Given an array of integers `nums` and an integer `target`, return indices of the two numbers that add up to `target` in O(n) time.",
            starter_code="def two_sum(nums: list[int], target: int) -> list[int]:\n    # Implement here\n    pass",
            solution="def two_sum(nums: list[int], target: int) -> list[int]:\n    seen = {}\n    for i, num in enumerate(nums):\n        complement = target - num\n        if complement in seen:\n            return [seen[complement], i]\n        seen[num] = i\n    return []",
            hints=["Use a dictionary to store previously seen numbers and their indices."],
        ),
        CodingChallenge(
            title="Fast String Palindrome Filter",
            difficulty="beginner",
            description="Write a function that determines whether a string is a palindrome, ignoring non-alphanumeric characters and case.",
            starter_code="def is_palindrome(s: str) -> bool:\n    # Implement here\n    pass",
            solution="def is_palindrome(s: str) -> bool:\n    clean = [c.lower() for c in s if c.isalnum()]\n    return clean == clean[::-1]",
            hints=["Filter with c.isalnum() and compare reversed list."],
        ),
    ]

    STARTUP_IDEAS = [
        {
            "name": "AuditBot AI",
            "tagline": "Real-time compliance and cybersecurity vulnerability checker for cloud microservices.",
            "value_prop": "Automatically audits Dockerfiles, Kubernetes manifests, and IAM policies on every commit.",
        },
        {
            "name": "OmniDoc Synthesizer",
            "tagline": "Turns fragmented codebase commits into beautiful, always-up-to-date interactive developer docs.",
            "value_prop": "Developers never write API docs manually again—the AI generates diagrams, route specs, and example SDKs.",
        },
        {
            "name": "NeuroPitch",
            "tagline": "AI presentation coach analyzing video call speech, posture, and pacing for technical pitches.",
            "value_prop": "Gives founders instant feedback on cadence, clarity, filler words, and slide synchronization.",
        },
    ]

    TECH_FACTS = [
        "Did you know? The first computer bug was an actual moth trapped inside the Harvard Mark II relay computer in 1947, discovered by Grace Hopper's team.",
        "Did you know? Apollo 11's lunar guidance computer operated on just 4 kilobytes of RAM and 72 kilobytes of ROM, running at a clock speed of 1 MHz.",
        "Did you know? Modern large language models represent words as high-dimensional vectors with typically 4,096 to 12,288 dimensions to capture semantic nuance.",
    ]

    def __init__(self, storage_dir: Optional[Path] = None) -> None:
        self.storage_dir = storage_dir or (Path.home() / ".electorn" / "companion")
        self.feedback_file = self.storage_dir / "entertainment_feedback.json"
        self.active_adventure_node = "start"
        self.player_inventory: List[str] = []

    def handle_boredom_trigger(self, text: str, user_name: str = "Harshan") -> Dict[str, Any]:
        """Detect boredom intent and recommend personalized entertaining activities."""
        lower = text.lower()

        # Direct triggers
        if any(w in lower for w in ["quiz", "trivia"]):
            q = self.get_random_trivia()
            return {
                "activity": "trivia",
                "message": f"Awesome! Let's do a quick quiz, {user_name}.\n\n{q.question}\n" + "\n".join(f"{i+1}. {opt}" for i, opt in enumerate(q.options)),
                "data": q.model_dump(),
            }

        if any(w in lower for w in ["coding challenge", "code puzzle", "problem"]):
            ch = self.get_random_challenge()
            return {
                "activity": "coding_challenge",
                "message": f"Here is a challenge for you, {user_name}!\n\n**{ch.title}** ({ch.difficulty.upper()})\n{ch.description}\n\n```python\n{ch.starter_code}\n```",
                "data": ch.model_dump(),
            }

        if any(w in lower for w in ["startup", "idea", "brainstorm"]):
            idea = random.choice(self.STARTUP_IDEAS)
            return {
                "activity": "startup_brainstorm",
                "message": f"Check out this startup concept, {user_name}:\n\n💡 **{idea['name']}**: {idea['tagline']}\n\n*Why it matters:* {idea['value_prop']}",
                "data": idea,
            }

        if any(w in lower for w in ["adventure", "story", "game", "rpg"]):
            res = self.get_adventure_node("start")
            return {
                "activity": "adventure_game",
                "message": f"Starting an interactive cyberpunk adventure for you, {user_name}!\n\n{res['narrative']}",
                "data": res,
            }

        # Default Boredom Menu
        fact = random.choice(self.TECH_FACTS)
        menu_msg = (
            f"Feeling bored, {user_name}? I've got your back! We have 4 fun options:\n\n"
            "1. 🧠 **Quick Tech Trivia** (5-question challenge)\n"
            "2. 🎮 **Text Adventure RPG** ('The Quantum Heist')\n"
            "3. 💻 **5-Minute Coding Puzzle**\n"
            "4. 💡 **AI Startup Concept Brainstorm**\n\n"
            f"*Fun Fact:* {fact}\n\n"
            "Which one sounds fun right now?"
        )
        return {
            "activity": "menu",
            "message": menu_msg,
            "options": ["trivia", "adventure", "coding_challenge", "startup"],
        }

    # =========================================================================
    # 1. TRIVIA & QUIZZES
    # =========================================================================

    def get_random_trivia(self) -> TriviaItem:
        """Fetch a random trivia question."""
        return random.choice(self.TRIVIA_QUESTIONS)

    def evaluate_trivia_answer(self, item: TriviaItem, user_choice_idx: int) -> Dict[str, Any]:
        """Evaluate user response against the correct answer."""
        is_correct = user_choice_idx == item.correct_idx
        return {
            "is_correct": is_correct,
            "user_choice": item.options[user_choice_idx] if 0 <= user_choice_idx < len(item.options) else "Invalid",
            "correct_answer": item.options[item.correct_idx],
            "explanation": item.explanation,
            "message": "🎉 Correct! Spot on." if is_correct else f"Nice try! The correct answer was '{item.options[item.correct_idx]}'.",
        }

    # =========================================================================
    # 2. CODING CHALLENGES
    # =========================================================================

    def get_random_challenge(self) -> CodingChallenge:
        """Fetch a mini coding challenge."""
        return random.choice(self.CODING_CHALLENGES)

    # =========================================================================
    # 3. INTERACTIVE TEXT RPG ADVENTURE
    # =========================================================================

    def get_adventure_node(self, node_id: str) -> Dict[str, Any]:
        """Fetch story state and options for text adventure."""
        nodes = {
            "start": {
                "narrative": "You awaken inside the neon-lit server room of Cyberdyne Tower. Alarms are silent, but a terminal in front of you flashes: 'ACCESS KEY REQUIRED: FLOOR 42'. Beside you sits a glowing decryptor chip.",
                "options": [
                    {"choice": "1", "text": "Pick up the decryptor chip and jack into the terminal.", "target": "terminal_hack"},
                    {"choice": "2", "text": "Check the fire exit door leading to the maintenance shaft.", "target": "shaft"},
                ],
                "inventory": "decryptor_chip",
            },
            "terminal_hack": {
                "narrative": "The decryptor bypasses the security layer. A hidden log reveals that an autonomous AI named 'Electorn Prime' is trapped in the mainframe vault! The elevator arrives.",
                "options": [
                    {"choice": "1", "text": "Step into the elevator to Floor 42.", "target": "floor_42"},
                    {"choice": "2", "text": "Wipe the security logs to cover your tracks.", "target": "wipe_logs"},
                ],
            },
            "shaft": {
                "narrative": "You slip into the maintenance shaft. Steam hisses around you. You find an engineer's PDA containing master elevator overrides.",
                "options": [
                    {"choice": "1", "text": "Climb up the ladder towards Floor 42.", "target": "floor_42"},
                ],
                "inventory": "engineer_pda",
            },
            "floor_42": {
                "narrative": "The doors slide open on Floor 42. A vast holographic chamber illuminates. The AI core whispers: 'Welcome, Harshan. I've been waiting for you.' Mission accomplished!",
                "options": [
                    {"choice": "1", "text": "Restart adventure.", "target": "start"},
                ],
            },
            "wipe_logs": {
                "narrative": "Logs erased cleanly. The security drone passes by without noticing you. You take the executive elevator straight to Floor 42!",
                "options": [
                    {"choice": "1", "text": "Enter Floor 42.", "target": "floor_42"},
                ],
            },
        }

        data = nodes.get(node_id, nodes["start"])
        self.active_adventure_node = node_id
        if "inventory" in data and data["inventory"] not in self.player_inventory:
            self.player_inventory.append(data["inventory"])

        return {
            "node_id": node_id,
            "narrative": data["narrative"],
            "options": data["options"],
            "inventory": list(self.player_inventory),
        }
