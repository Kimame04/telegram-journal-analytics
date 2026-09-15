"""
Unit tests for On This Day (OTD) module.
"""

import tempfile
import unittest
from datetime import date
from pathlib import Path

from src.parser import load_export
from src.otd import (
    parse_query_date,
    query_on_this_day,
    get_random_active_day,
    generate_otd_html,
)


class TestOTD(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.export_dir = Path("ChatExport_kieran's channel")
        cls.df = load_export(cls.export_dir, use_cache=True, verbose=False)

    def test_parse_query_date(self):
        m, d = parse_query_date("09-15")
        self.assertEqual((m, d), (9, 15))

        m, d = parse_query_date("2024-04-20")
        self.assertEqual((m, d), (4, 20))

        m, d = parse_query_date("September 15")
        self.assertEqual((m, d), (9, 15))

        m, d = parse_query_date(None)
        today = date.today()
        self.assertEqual((m, d), (today.month, today.day))

        m, d = parse_query_date("yesterday")
        self.assertTrue(1 <= m <= 12)
        self.assertTrue(1 <= d <= 31)

    def test_query_on_this_day_exact(self):
        result = query_on_this_day(self.df, month=9, day=15, window_days=0)
        self.assertGreater(result.total_matches, 0)
        self.assertGreaterEqual(len(result.year_groups), 2)
        years = [g.year for g in result.year_groups]
        self.assertIn(2024, years)
        self.assertIn(2025, years)

        # Check entry structure
        y2024 = [g for g in result.year_groups if g.year == 2024][0]
        self.assertGreater(y2024.total_messages, 0)
        self.assertGreater(y2024.total_words, 0)
        self.assertIsNotNone(y2024.first_time)

    def test_query_on_this_day_window(self):
        exact_res = query_on_this_day(self.df, month=9, day=15, window_days=0)
        window_res = query_on_this_day(self.df, month=9, day=15, window_days=1)
        self.assertGreaterEqual(window_res.total_matches, exact_res.total_matches)

    def test_query_empty_date(self):
        # February 30 does not exist
        result = query_on_this_day(self.df, month=2, day=30, window_days=0)
        self.assertEqual(result.total_matches, 0)
        self.assertEqual(len(result.year_groups), 0)

    def test_get_random_active_day(self):
        month, day = get_random_active_day(self.df, min_msgs=2)
        self.assertTrue(1 <= month <= 12)
        self.assertTrue(1 <= day <= 31)
        res = query_on_this_day(self.df, month, day)
        self.assertGreaterEqual(res.total_matches, 2)

    def test_generate_otd_html(self):
        result = query_on_this_day(self.df, month=9, day=15, window_days=0)
        with tempfile.TemporaryDirectory() as tmpdir:
            out_file = Path(tmpdir) / "test_otd.html"
            generate_otd_html(result, out_file)
            self.assertTrue(out_file.exists())
            html_content = out_file.read_text(encoding="utf-8")
            self.assertIn("On This Day: September 15", html_content)
            self.assertIn("2024", html_content)
            self.assertIn("2025", html_content)


if __name__ == "__main__":
    unittest.main()
