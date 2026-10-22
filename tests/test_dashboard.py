"""
Unit tests for the Unified Master Journal Dashboard.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.parser import load_export
from src.dashboard import build_dashboard_context, generate_dashboard, DashboardData
from tests.helpers import get_test_export_dir


class TestDashboard(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.export_dir = get_test_export_dir()
        cls.df = load_export(cls.export_dir, use_cache=True, verbose=False)

    def test_build_dashboard_context(self):
        """Verify multi-domain metric synthesis produces valid DashboardData."""
        data = build_dashboard_context(self.df, year=None, otd_date="09-15")
        self.assertIsInstance(data, DashboardData)
        self.assertGreater(data.total_messages, 0)
        self.assertGreater(data.total_words, 0)
        self.assertIn("peak_hour", data.circadian_metrics)
        self.assertIsNotNone(data.wrapped_data.persona)
        self.assertEqual(data.otd_result.target_month, 9)
        self.assertEqual(data.otd_result.target_day, 15)

    def test_generate_dashboard_file(self):
        """Test end-to-end HTML dashboard generation and content integrity."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            out_file = Path(tmp_dir) / "test_dashboard.html"
            data, result_path = generate_dashboard(
                self.df,
                output_path=out_file,
                otd_date="09-15",
            )
            self.assertEqual(result_path, out_file.resolve())
            self.assertTrue(out_file.exists())

            content = out_file.read_text(encoding="utf-8")
            # Verify layout & navigation
            self.assertIn("Personal Journal Master Dashboard", content)
            self.assertIn("Telegram Journal Dossier", content)
            self.assertIn("#circadian", content)
            self.assertIn("#lifecycles", content)
            self.assertIn("#wrapped", content)
            self.assertIn("#otd", content)

            # Verify sections are rendered
            self.assertIn("Circadian &amp; Habit Profile", content.replace("&", "&amp;"))
            self.assertIn("Tag &amp; Hobby Lifecycles", content.replace("&", "&amp;"))
            self.assertIn("Channel-Wrapped Retrospective", content)
            self.assertIn("On This Day Time Capsule", content)

            # Verify no un-rendered Jinja2 expressions
            self.assertNotIn("{{", content)
            self.assertNotIn("{%", content)


if __name__ == "__main__":
    unittest.main()
