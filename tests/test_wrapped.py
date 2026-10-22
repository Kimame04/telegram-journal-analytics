"""
Unit tests for Channel-Wrapped retrospective analytics and story deck generator.
"""

from __future__ import annotations

import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path

import pandas as pd

from src.parser import load_export
from src.wrapped import (
    PersonaInfo,
    WrappedData,
    compute_streaks,
    compute_wrapped,
    determine_persona,
    generate_wrapped_html,
    render_wrapped_terminal,
)
from tests.helpers import get_test_export_dir


class TestChannelWrapped(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.export_dir = get_test_export_dir()
        cls.df = load_export(cls.export_dir, use_cache=True, verbose=False)

    def test_compute_wrapped_specific_year(self):
        """Test Wrapped metric calculation for a single year."""
        wrapped = compute_wrapped(self.df, year=2024)
        self.assertEqual(wrapped.period_label, "2024")
        self.assertEqual(wrapped.year, 2024)
        self.assertGreater(wrapped.total_messages, 50)
        self.assertGreater(wrapped.total_words, 500)
        self.assertGreater(wrapped.total_chars, 3000)
        self.assertGreater(wrapped.avg_words_per_message, 0.0)
        self.assertGreater(wrapped.active_days, 10)
        self.assertGreater(wrapped.total_period_days, 360)
        self.assertGreater(wrapped.longest_streak_days, 0)
        self.assertIsInstance(wrapped.persona, PersonaInfo)
        self.assertTrue(len(wrapped.top_tags) > 0)
        self.assertGreater(wrapped.reading_time_minutes, 0)
        self.assertGreater(wrapped.book_pages_equivalent, 0.0)

    def test_compute_wrapped_all_time(self):
        """Test Wrapped metric calculation across all recorded years."""
        wrapped = compute_wrapped(self.df, year=None)
        self.assertTrue(wrapped.period_label.startswith("All-Time"))
        self.assertIsNone(wrapped.year)
        self.assertGreaterEqual(wrapped.total_messages, 300)
        self.assertGreater(len(wrapped.top_tags), 0)
        self.assertGreater(wrapped.total_reactions, 0)

    def test_streaks_calculation_known_series(self):
        """Test streak and hiatus gap calculation on deterministic mock dates."""
        mock_df = pd.DataFrame({
            "date": [
                "2024-03-01",
                "2024-03-02",
                "2024-03-03",
                "2024-03-04",  # 4-day streak
                "2024-03-10",  # 5-day gap (Mar 4 -> Mar 10)
                "2024-03-11",
            ]
        })
        streak, s_start, s_end, gap, g_start, g_end = compute_streaks(mock_df)
        self.assertEqual(streak, 4)
        self.assertIn("Mar 01", s_start)
        self.assertIn("Mar 04", s_end)
        self.assertEqual(gap, 5)
        self.assertIn("Mar 04", g_start)
        self.assertIn("Mar 10", g_end)

    def test_persona_classification_archetypes(self):
        """Verify rule-based circadian persona assignment."""
        # 1. Night Owl
        night_df = pd.DataFrame({
            "hour": [23, 23, 23, 0, 1, 2, 23],
            "day_name": ["Friday"] * 7,
        })
        night_persona = determine_persona(night_df)
        self.assertIn(night_persona.name, ["The Midnight Philosopher", "The 2 AM Luminary"])
        self.assertGreater(night_persona.night_owl_pct, 50.0)

        # 2. Early Bird
        morning_df = pd.DataFrame({
            "hour": [6, 6, 7, 7, 8, 8, 6],
            "day_name": ["Monday"] * 7,
        })
        morning_persona = determine_persona(morning_df)
        self.assertEqual(morning_persona.name, "The Dawn Chronicler")
        self.assertEqual(morning_persona.emoji, "🌅")

        # 3. Empty Dataframe fallback
        empty_df = pd.DataFrame(columns=["hour", "day_name"])
        empty_persona = determine_persona(empty_df)
        self.assertEqual(empty_persona.name, "The Blank Slate")

    def test_terminal_rendering(self):
        """Verify CLI terminal output formatting."""
        wrapped = compute_wrapped(self.df, year=2024)
        terminal_output = render_wrapped_terminal(wrapped)
        self.assertIn("CHANNEL-WRAPPED RETROSPECTIVE: 2024", terminal_output)
        self.assertIn("SLIDE 1: VOLUME & DEDICATION", terminal_output)
        self.assertIn("SLIDE 2: CADENCE & STREAKS", terminal_output)
        self.assertIn("SLIDE 3: CIRCADIAN PERSONA", terminal_output)
        self.assertIn("SLIDE 4: TOP FIXATIONS & ERAS", terminal_output)
        self.assertIn("SLIDE 5: EXPRESSIVENESS & MEDIA", terminal_output)
        self.assertIn("SLIDE 6: THE MAGNUM OPUS & STANDOUTS", terminal_output)

    def test_html_story_deck_generation(self):
        """Verify HTML story deck file generation and structural tags."""
        wrapped = compute_wrapped(self.df, year=2024)
        with tempfile.TemporaryDirectory() as tmp_dir:
            out_file = Path(tmp_dir) / "wrapped_test.html"
            generate_wrapped_html(wrapped, out_file)

            self.assertTrue(out_file.exists())
            self.assertGreater(out_file.stat().st_size, 1000)

            content = out_file.read_text(encoding="utf-8")
            self.assertIn("<!DOCTYPE html>", content)
            self.assertIn("Channel-Wrapped", content)
            self.assertIn("storyBars", content)
            self.assertIn(wrapped.persona.name, content)
            self.assertIn("Total Words Written", content)
            self.assertIn("Switch to Scrollable Deck Mode", content)


if __name__ == "__main__":
    unittest.main()
