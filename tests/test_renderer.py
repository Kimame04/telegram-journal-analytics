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


if __name__ == "__main__":
    unittest.main()
