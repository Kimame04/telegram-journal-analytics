"""
Unit tests for Telegram export parser and circadian habit analysis.
"""

import unittest
from pathlib import Path
import tempfile
import pandas as pd

from src.parser import _extract_bracket_tags, load_export
from src.circadian import compute_circadian_metrics
from tests.helpers import get_test_export_dir


class TestParserAndCircadian(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.export_dir = get_test_export_dir()
        cls.df = load_export(cls.export_dir, use_cache=True, verbose=False)

    def test_extract_bracket_tags(self):
        text = "[f1] Quali was insane today! [project sekai] grind later. Also [f1] again."
        tags = _extract_bracket_tags(text)
        self.assertEqual(tags, ["f1", "project sekai"])

    def test_load_export_dataset(self):
        self.assertGreaterEqual(len(self.df), 300)
        self.assertIn("timestamp", self.df.columns)
        self.assertIn("hour", self.df.columns)
        self.assertIn("day_name", self.df.columns)
        self.assertIn("tags", self.df.columns)
        self.assertIn("reactions", self.df.columns)

    def test_circadian_metrics(self):
        metrics = compute_circadian_metrics(self.df)
        self.assertIn("peak_hour", metrics)
        self.assertIn(metrics["peak_day"], ["Saturday", "Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday"])
        self.assertGreater(metrics["night_owl_pct"], 20.0)

    def test_reaction_sanitization_and_parquet_fidelity(self):
        from src.parser import _sanitize_reactions
        raw_dirty = {"❤": None, "🔥": 3, "👍": 0, "👏": -1}
        cleaned = _sanitize_reactions(raw_dirty)
        self.assertEqual(cleaned, {"🔥": 3})

        # Verify all rows in loaded dataset have clean reactions
        for rx, tot in zip(self.df["reactions"], self.df["total_reactions"]):
            self.assertIsInstance(rx, dict)
            for k, v in rx.items():
                self.assertIsNotNone(v)
                self.assertGreater(v, 0)
            self.assertEqual(tot, sum(rx.values()))

    def test_generate_circadian_report(self):
        from src.circadian import generate_circadian_report
        with tempfile.TemporaryDirectory() as tmpdir:
            metrics = generate_circadian_report(self.df, tmpdir)
            self.assertIn("peak_hour", metrics)
            self.assertTrue(Path(tmpdir, "circadian_weekly_heatmap.png").exists())
            self.assertTrue(Path(tmpdir, "hourly_circadian_distribution.png").exists())
            self.assertTrue(Path(tmpdir, "longitudinal_circadian_shift.png").exists())
            html_path = Path(tmpdir, "circadian_report.html")
            self.assertTrue(html_path.exists())
            html_text = html_path.read_text(encoding="utf-8")
            self.assertIn("Circadian & Habit Profile", html_text)
            self.assertIn("Peak Journaling Hour", html_text)
            self.assertIn("Night Owl Index", html_text)


if __name__ == "__main__":
    unittest.main()
