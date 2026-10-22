"""
Unit tests for Tag & Hobby Lifecycles module.
"""

import unittest
from pathlib import Path
import pandas as pd

from src.parser import load_export
from src.lifecycle import compute_tag_lifecycles, generate_lifecycle_report
from tests.helpers import get_test_export_dir


class TestTagLifecycle(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.export_dir = get_test_export_dir()
        cls.df = load_export(cls.export_dir, use_cache=True, verbose=False)

    def test_compute_tag_lifecycles(self):
        tag_stats, monthly_counts = compute_tag_lifecycles(self.df, min_count=5)
        self.assertFalse(tag_stats.empty)
        self.assertFalse(monthly_counts.empty)
        self.assertIn("tag", tag_stats.columns)
        self.assertIn("category", tag_stats.columns)
        self.assertIn("peak_month", tag_stats.columns)

        # Verify known tags exist (either sample or real dataset)
        tags = set(tag_stats["tag"].tolist())
        has_expected_tags = any(t in tags for t in ["reading", "coding", "fitness", "f1", "mai", "project sekai"])
        self.assertTrue(has_expected_tags)

        # Verify classifications contain Evergreen
        categories = tag_stats["category"].tolist()
        self.assertIn("Evergreen Passion", categories)

    def test_generate_lifecycle_report(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            summary = generate_lifecycle_report(self.df, tmpdir, top_n=10, min_count=5)
            self.assertGreaterEqual(summary["total_tags_analyzed"], 5)
            self.assertTrue(Path(tmpdir, "tag_streamgraph.png").exists())
            self.assertTrue(Path(tmpdir, "tag_lifespans_gantt.png").exists())
            self.assertTrue(Path(tmpdir, "tag_monthly_heatmap.png").exists())
            html_path = Path(tmpdir, "tag_lifecycle_report.html")
            self.assertTrue(html_path.exists())
            html_text = html_path.read_text(encoding="utf-8")
            self.assertIn("Tag & Hobby Lifecycle Explorer", html_text)
            self.assertIn("Interactive Hobby Streamgraph", html_text)
            self.assertIn("Lifespan Archetypes Breakdown", html_text)


if __name__ == "__main__":
    unittest.main()
