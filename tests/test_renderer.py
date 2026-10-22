"""
Unit tests for centralized Jinja2 template rendering engine.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import jinja2

from src.renderer import (
    TEMPLATES_DIR,
    get_jinja_env,
    render_template,
    render_to_file,
    _format_commas,
    _round_num,
)


class TestRenderer(unittest.TestCase):

    def test_templates_directory_exists(self):
        """Ensure templates directory exists and contains expected templates."""
        self.assertTrue(TEMPLATES_DIR.exists())
        self.assertTrue((TEMPLATES_DIR / "wrapped.html").exists())
        self.assertTrue((TEMPLATES_DIR / "on_this_day.html").exists())
        self.assertTrue((TEMPLATES_DIR / "circadian.html").exists())
        self.assertTrue((TEMPLATES_DIR / "tag_lifecycle.html").exists())
        self.assertTrue((TEMPLATES_DIR / "dashboard.html").exists())

    def test_jinja_filters(self):
        """Test custom filters for numbers and rounding."""
        self.assertEqual(_format_commas(1234567), "1,234,567")
        self.assertEqual(_format_commas(0), "0")
        self.assertEqual(_format_commas(None), "0")
        self.assertEqual(_round_num(3.14159, 2), "3.14")
        self.assertEqual(_round_num(5, 1), "5.0")
        self.assertEqual(_round_num(None), "0.0")

    def test_get_jinja_env(self):
        """Test Jinja2 environment initialization and configuration."""
        env = get_jinja_env()
        self.assertIsInstance(env, jinja2.Environment)
        self.assertIn("commas", env.filters)
        self.assertIn("round_num", env.filters)

    def test_render_missing_template(self):
        """Ensure attempting to render a non-existent template raises TemplateNotFound."""
        with self.assertRaises(jinja2.TemplateNotFound):
            render_template("non_existent_template_xyz.html", {})

    def test_render_to_file(self):
        """Test writing rendered template to a file path."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            out_file = Path(tmp_dir) / "sub_dir" / "rendered.html"
            result_path = render_to_file(
                "on_this_day.html",
                {
                    "result": type("Result", (), {
                        "date_title": "September 15",
                        "total_matches": 5,
                    })(),
                    "total_years_active": 2,
                    "year_cards": [],
                },
                out_file,
            )
            self.assertEqual(result_path, out_file)
            self.assertTrue(out_file.exists())
            content = out_file.read_text(encoding="utf-8")
            self.assertIn("On This Day: September 15", content)
            self.assertIn("Total Messages", content)

    def test_render_circadian_template(self):
        """Test rendering circadian.html template."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            out_file = Path(tmp_dir) / "circadian.html"
            result_path = render_to_file(
                "circadian.html",
                {
                    "metrics": {
                        "peak_hour": 23,
                        "peak_hour_count": 50,
                        "night_owl_pct": 45.2,
                        "night_owl_count": 80,
                        "peak_day": "Sunday",
                        "peak_day_count": 60,
                        "total_messages": 200,
                        "busiest_date": "2024-05-01",
                        "date_span": "Dec 2023 – Sep 2026",
                    },
                    "charts": {
                        "weekly_heatmap": "<div>heatmap</div>",
                        "hourly_distribution": "<div>hourly</div>",
                        "longitudinal_shift": "<div>shift</div>",
                    },
                },
                out_file,
            )
            self.assertTrue(result_path.exists())
            content = result_path.read_text(encoding="utf-8")
            self.assertIn("Circadian & Habit Profile", content)
            self.assertIn("23:00", content)
            self.assertIn("45.2%", content)

    def test_render_tag_lifecycle_template(self):
        """Test rendering tag_lifecycle.html template."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            out_file = Path(tmp_dir) / "tag_lifecycle.html"
            result_path = render_to_file(
                "tag_lifecycle.html",
                {
                    "summary": {
                        "evergreens": ["reading", "coding"],
                        "bursts": ["mai"],
                        "emerging": ["ai agents"],
                        "top_tag": "reading",
                        "top_tag_count": 120,
                    },
                    "charts": {
                        "streamgraph": "<div>streamgraph</div>",
                        "ranked_bars": "<div>ranked_bars</div>",
                    },
                    "evergreen_records": [{"tag": "reading", "total_count": 120, "peak_month": "2024-03"}],
                    "burst_records": [{"tag": "mai", "total_count": 30, "peak_month": "2024-08"}],
                    "emerging_records": [{"tag": "ai agents", "total_count": 15, "first_month": "2026-01"}],
                    "date_span": "Dec 2023 – Sep 2026",
                },
                out_file,
            )
            self.assertTrue(result_path.exists())
            content = result_path.read_text(encoding="utf-8")
            self.assertIn("Tag & Hobby Lifecycle Explorer", content)
            self.assertIn("[reading]", content)
            self.assertIn("🌟 Evergreen Passions", content)


if __name__ == "__main__":
    unittest.main()
