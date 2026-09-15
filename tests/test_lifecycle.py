"""
Unit tests for Tag & Hobby Lifecycles module.
"""

import unittest
from pathlib import Path
import pandas as pd

from src.parser import load_export
from src.lifecycle import compute_tag_lifecycles, generate_lifecycle_report


class TestTagLifecycle(unittest.TestCase):

    def setUp(self):
        self.export_dir = Path("ChatExport_kieran's channel")
        self.df = load_export(self.export_dir, use_cache=True, verbose=False)

    def test_compute_tag_lifecycles(self):
        tag_stats, monthly_counts = compute_tag_lifecycles(self.df, min_count=5)
        self.assertFalse(tag_stats.empty)
        self.assertFalse(monthly_counts.empty)
        self.assertIn("tag", tag_stats.columns)
        self.assertIn("category", tag_stats.columns)
        self.assertIn("peak_month", tag_stats.columns)

        # Verify specific known tags exist
        tags = tag_stats["tag"].tolist()
        self.assertIn("f1", tags)
        self.assertIn("mai", tags)
        self.assertIn("project sekai", tags)

        # Verify classifications
        f1_row = tag_stats[tag_stats["tag"] == "f1"].iloc[0]
        self.assertEqual(f1_row["category"], "Evergreen Passion")

    def test_generate_lifecycle_report(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            summary = generate_lifecycle_report(self.df, tmpdir, top_n=10, min_count=5)
            self.assertGreater(summary["total_tags_analyzed"], 10)
            self.assertTrue(Path(tmpdir, "tag_streamgraph.png").exists())
            self.assertTrue(Path(tmpdir, "tag_lifespans_gantt.png").exists())
            self.assertTrue(Path(tmpdir, "tag_monthly_heatmap.png").exists())
            self.assertTrue(Path(tmpdir, "tag_lifecycle_report.html").exists())


if __name__ == "__main__":
    unittest.main()
