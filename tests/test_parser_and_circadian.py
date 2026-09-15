"""
Unit tests for Telegram export parser and circadian habit analysis.
"""

import unittest
from pathlib import Path
import tempfile
import pandas as pd

from src.parser import _extract_bracket_tags, load_export
from src.circadian import compute_circadian_metrics


class TestParserAndCircadian(unittest.TestCase):

    def test_extract_bracket_tags(self):
        text = "[f1] Quali was insane today! [project sekai] grind later. Also [f1] again."
        tags = _extract_bracket_tags(text)
        self.assertEqual(tags, ["f1", "project sekai"])

    def test_load_export_actual_dataset(self):
        export_dir = Path("ChatExport_kieran's channel")
        df = load_export(export_dir, use_cache=True, verbose=False)
        self.assertGreater(len(df), 5000)
        self.assertIn("timestamp", df.columns)
        self.assertIn("hour", df.columns)
        self.assertIn("day_name", df.columns)
        self.assertIn("tags", df.columns)
        self.assertIn("reactions", df.columns)

    def test_circadian_metrics(self):
        export_dir = Path("ChatExport_kieran's channel")
        df = load_export(export_dir, use_cache=True, verbose=False)
        metrics = compute_circadian_metrics(df)
        self.assertIn("peak_hour", metrics)
        self.assertEqual(metrics["peak_hour"], 23)
        self.assertEqual(metrics["peak_day"], "Saturday")
        self.assertGreater(metrics["night_owl_pct"], 30.0)


if __name__ == "__main__":
    unittest.main()
