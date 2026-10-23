"""
Unit tests for Telegram Bot message formatters.
Verifies HTML escaping, message chunking, and metadata rendering.
"""

from __future__ import annotations

from datetime import datetime
import unittest

from src.bot.formatter import (
    escape_html,
    format_entry_snippet,
    format_otd_message,
    format_stats_message,
    format_tag_message,
    MAX_TELEGRAM_MESSAGE_LEN,
)
from src.otd.logic import OTDEntry, OTDResult, OTDYearGroup


class TestBotFormatter(unittest.TestCase):
    def test_escape_html(self):
        raw = "Testing <script>alert('xss')</script> & other 'quotes' > 5"
        escaped = escape_html(raw)
        self.assertNotIn("<script>", escaped)
        self.assertIn("&lt;script&gt;", escaped)
        self.assertIn("&amp;", escaped)
        self.assertIn("&gt;", escaped)

    def test_format_empty_otd(self):
        otd = OTDResult(
            target_month=9,
            target_day=15,
            date_title="September 15",
            window_days=0,
            total_matches=0,
            year_groups=[],
            all_tags=[],
        )
        messages = format_otd_message(otd)
        self.assertEqual(len(messages), 1)
        self.assertIn("No journal entries recorded", messages[0])
        self.assertIn("September 15", messages[0])

    def test_format_multi_year_otd(self):
        entry1 = OTDEntry(
            id=101,
            timestamp=datetime(2024, 9, 15, 23, 10),
            time_str="23:10",
            date_str="2024-09-15",
            year=2024,
            text="Completed the robotics perception module! [robotics] [ros]",
            word_count=7,
            tags=["robotics", "ros"],
            reactions={"🔥": 2, "❤️": 1},
            total_reactions=3,
            has_photo=False,
            has_media=False,
        )
        group1 = OTDYearGroup(
            year=2024,
            years_ago=2,
            label="2 years ago",
            entries=[entry1],
            total_messages=1,
            total_words=7,
            tags_summary=[("robotics", 1), ("ros", 1)],
            top_reactions=[("🔥", 2)],
            first_time="23:10",
            last_time="23:10",
        )
        otd = OTDResult(
            target_month=9,
            target_day=15,
            date_title="September 15",
            window_days=0,
            total_matches=1,
            year_groups=[group1],
            all_tags=["robotics", "ros"],
        )

        messages = format_otd_message(otd)
        self.assertEqual(len(messages), 1)
        chunk = messages[0]
        self.assertIn("September 15", chunk)
        self.assertIn("2024", chunk)
        self.assertIn("robotics perception module", chunk)
        self.assertIn("<code>#robotics</code>", chunk)
        self.assertIn("🔥2", chunk)
        self.assertTrue(len(chunk) <= MAX_TELEGRAM_MESSAGE_LEN)

    def test_message_chunking_on_long_content(self):
        # Create multiple large year groups to force splitting across chunks
        long_text = "Detailed daily reflection about machine vision and software architecture. " * 30
        groups = []
        for yr in range(2010, 2026):
            entries = [
                OTDEntry(
                    id=yr * 10,
                    timestamp=datetime(yr, 9, 15, 12, 0),
                    time_str="12:00",
                    date_str=f"{yr}-09-15",
                    year=yr,
                    text=f"Year {yr}: {long_text}",
                    word_count=len(long_text.split()),
                    tags=["reflection"],
                    reactions={},
                    total_reactions=0,
                    has_photo=False,
                    has_media=False,
                )
            ]
            groups.append(
                OTDYearGroup(
                    year=yr,
                    years_ago=2026 - yr,
                    label=f"{2026 - yr} years ago",
                    entries=entries,
                    total_messages=1,
                    total_words=len(long_text.split()),
                    tags_summary=[("reflection", 1)],
                    top_reactions=[],
                    first_time="12:00",
                    last_time="12:00",
                )
            )

        otd = OTDResult(
            target_month=9,
            target_day=15,
            date_title="September 15",
            window_days=0,
            total_matches=len(groups),
            year_groups=groups,
            all_tags=["reflection"],
        )

        messages = format_otd_message(otd)
        self.assertGreater(len(messages), 1, "Should split into multiple messages when content is large")
        for chunk in messages:
            self.assertLessEqual(len(chunk), MAX_TELEGRAM_MESSAGE_LEN)

    def test_format_stats_message(self):
        stats = {
            "persona": "The Midnight Philosopher 🌙",
            "night_owl_pct": 65.5,
            "peak_hour": 23,
            "total_messages": 850,
            "total_words": 52000,
            "pages": 208,
            "consistency_pct": 74.2,
            "streak": 21,
            "top_tags": ["coding", "reading", "mai"],
        }
        msg = format_stats_message(stats)
        self.assertIn("The Midnight Philosopher", msg)
        self.assertIn("65.5%", msg)
        self.assertIn("52,000", msg)
        self.assertIn("208", msg)
        self.assertIn("[coding]", msg)

    def test_format_tag_message(self):
        msg = format_tag_message(
            tag="[bumblebee]",
            count=42,
            first_seen="Jan 10, 2024",
            last_seen="Oct 20, 2026",
            sample_text="Worked on subsea autonomous docking algorithms.",
        )
        self.assertIn("Tag Dossier: [bumblebee]", msg)
        self.assertIn("42", msg)
        self.assertIn("Jan 10, 2024", msg)
        self.assertIn("subsea autonomous docking", msg)


if __name__ == "__main__":
    unittest.main()
