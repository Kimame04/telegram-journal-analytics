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
        self.assertEqual(metrics["peak_hour"], 23)
        self.assertIn(metrics["peak_day"], ["Saturday", "Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday"])
        self.assertGreater(metrics["night_owl_pct"], 25.0)


if __name__ == "__main__":
    unittest.main()
