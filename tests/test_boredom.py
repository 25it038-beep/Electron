"""Unit tests for BoredomEngine (Trivia, Coding Challenges, Text Adventure RPG, Startup Ideas)."""

import tempfile
from pathlib import Path
import pytest

from electorn.companion.boredom_engine import BoredomEngine


def test_boredom_trigger_menu():
    with tempfile.TemporaryDirectory() as tmp_dir:
        engine = BoredomEngine(storage_dir=Path(tmp_dir))
        res = engine.handle_boredom_trigger("i feel so bored", user_name="Harshan")
        assert res["activity"] == "menu"
        assert "Harshan" in res["message"]
        assert "Quick Tech Trivia" in res["message"]
        assert "options" in res


def test_trivia_evaluation():
    with tempfile.TemporaryDirectory() as tmp_dir:
        engine = BoredomEngine(storage_dir=Path(tmp_dir))
        item = engine.get_random_trivia()
        assert len(item.options) == 4
        assert 0 <= item.correct_idx <= 3

        # Test correct
        correct_eval = engine.evaluate_trivia_answer(item, item.correct_idx)
        assert correct_eval["is_correct"] is True
        assert "Correct" in correct_eval["message"]

        # Test incorrect
        wrong_idx = (item.correct_idx + 1) % 4
        wrong_eval = engine.evaluate_trivia_answer(item, wrong_idx)
        assert wrong_eval["is_correct"] is False


def test_coding_challenge():
    with tempfile.TemporaryDirectory() as tmp_dir:
        engine = BoredomEngine(storage_dir=Path(tmp_dir))
        ch = engine.get_random_challenge()
        assert ch.title != ""
        assert "def " in ch.starter_code
        assert len(ch.solution) > 0
        assert len(ch.hints) > 0


def test_adventure_rpg_progression():
    with tempfile.TemporaryDirectory() as tmp_dir:
        engine = BoredomEngine(storage_dir=Path(tmp_dir))
        start_node = engine.get_adventure_node("start")
        assert start_node["node_id"] == "start"
        assert "Cyberdyne" in start_node["narrative"]
        assert "decryptor_chip" in start_node["inventory"]

        # Advance to terminal_hack
        hack_node = engine.get_adventure_node("terminal_hack")
        assert hack_node["node_id"] == "terminal_hack"
        assert len(hack_node["options"]) > 0
