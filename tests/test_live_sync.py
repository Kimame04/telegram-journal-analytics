"""
Unit tests for Live Channel Ingestion and Delta Sync.
Verifies post parsing, Parquet delta storage, edit updates, and unified dataset merging.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock

import pandas as pd

from src.bot.client import TelegramClient
from src.bot.config import BotConfig
from src.bot.handlers import BotDispatcher
from src.bot.live_sync import (
    _save_delta_df,
    ingest_channel_post,
    load_unified_journal,
    parse_channel_post,
)


class TestLiveSync(unittest.TestCase):
    def test_parse_channel_post(self):
        sample_post = {
            "message_id": 501,
            "date": 1729684800,  # 2024-10-23 12:00:00 UTC
            "chat": {
                "id": -1001987654321,
                "title": "Kieran Journal",
                "type": "channel"
            },
            "text": "Finished testing the live subsea autonomous sync! [robotics] [ros2]",
            "photo": [{"file_id": "photo_123"}]
        }

        row = parse_channel_post(sample_post)
        self.assertEqual(row["id"], 501)
        self.assertIn("robotics", row["tags"])
        self.assertIn("ros2", row["tags"])
        self.assertEqual(row["first_tag"], "robotics")
        self.assertEqual(row["word_count"], 9)
        self.assertTrue(row["has_photo"])
        self.assertFalse(row["has_media"])
        self.assertEqual(row["year"], 2024)
        self.assertEqual(row["month"], 10)
        self.assertEqual(row["day"], 23)

    def test_ingest_and_edit_channel_post(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            delta_file = Path(tmp_dir) / "test_live_messages.parquet"

            post1 = {
                "message_id": 1001,
                "date": 1729684800,
                "chat": {"id": -1001234567890, "type": "channel"},
                "text": "Initial reflection before lunch. [work]"
            }

            # 1. First ingestion
            row1, is_new1 = ingest_channel_post(post1, delta_path=delta_file)
            self.assertTrue(is_new1)
            self.assertTrue(delta_file.exists())

            df1 = pd.read_parquet(delta_file)
            self.assertEqual(len(df1), 1)
            self.assertEqual(df1.iloc[0]["id"], 1001)
            self.assertIn("Initial reflection", df1.iloc[0]["text"])

            # 2. Edit of the same post
            post1_edited = {
                "message_id": 1001,
                "date": 1729684900,
                "chat": {"id": -1001234567890, "type": "channel"},
                "text": "Edited reflection after lunch! [work] [food]"
            }
            row1_edit, is_new2 = ingest_channel_post(post1_edited, delta_path=delta_file)
            self.assertFalse(is_new2, "Existing ID edit should not be marked as new")

            df2 = pd.read_parquet(delta_file)
            self.assertEqual(len(df2), 1, "Should upsert in place without duplicating row")
            self.assertIn("Edited reflection after lunch", df2.iloc[0]["text"])
            self.assertIn("food", df2.iloc[0]["tags"])

            # 3. New separate post
            post2 = {
                "message_id": 1002,
                "date": 1729685000,
                "chat": {"id": -1001234567890, "type": "channel"},
                "text": "Evening reflection. [reading]"
            }
            row2, is_new3 = ingest_channel_post(post2, delta_path=delta_file)
            self.assertTrue(is_new3)

            df3 = pd.read_parquet(delta_file)
            self.assertEqual(len(df3), 2)

    def test_load_unified_journal_deduplication(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            delta_file = tmp_path / "live.parquet"

            # Create mock live delta with an updated entry #100 and a new entry #200
            live_rows = [
                {
                    "id": 100,
                    "timestamp": pd.to_datetime("2024-10-23 14:00:00"),
                    "text": "Overwritten version of post 100",
                    "word_count": 5,
                    "char_count": 31,
                    "tags": ["updated"],
                    "first_tag": "updated",
                    "reactions": {},
                    "total_reactions": 0,
                    "reply_to_id": None,
                    "has_photo": False,
                    "has_media": False,
                    "date": datetime(2024, 10, 23).date(),
                    "year": 2024,
                    "month": 10,
                    "year_month": "2024-10",
                    "day": 23,
                    "day_of_week": 2,
                    "day_name": "Wednesday",
                    "hour": 14,
                    "minute": 0,
                },
                {
                    "id": 200,
                    "timestamp": pd.to_datetime("2024-10-23 15:00:00"),
                    "text": "Completely new live entry 200",
                    "word_count": 5,
                    "char_count": 28,
                    "tags": ["new"],
                    "first_tag": "new",
                    "reactions": {},
                    "total_reactions": 0,
                    "reply_to_id": None,
                    "has_photo": False,
                    "has_media": False,
                    "date": datetime(2024, 10, 23).date(),
                    "year": 2024,
                    "month": 10,
                    "year_month": "2024-10",
                    "day": 23,
                    "day_of_week": 2,
                    "day_name": "Wednesday",
                    "hour": 15,
                    "minute": 0,
                }
            ]
            _save_delta_df(pd.DataFrame(live_rows), delta_file)

            # Use synthetic sample as base export
            sample_dir = Path(__file__).resolve().parent.parent / "ChatExport_sample"
            if not sample_dir.exists():
                self.skipTest("ChatExport_sample not found.")

            unified_df = load_unified_journal(sample_dir, delta_path=delta_file)
            self.assertFalse(unified_df.empty)
            self.assertIn(200, unified_df["id"].values)
            matching_100 = unified_df[unified_df["id"] == 100]
            if not matching_100.empty:
                self.assertEqual(matching_100.iloc[0]["text"], "Overwritten version of post 100")

    def test_bot_dispatcher_channel_post_filtering(self):
        client = MagicMock()
        config = BotConfig(bot_token="test_tok", chat_id="123", channel_id="-100123")
        initial_df = pd.DataFrame([{
            "id": 1,
            "timestamp": pd.to_datetime("2024-01-01 10:00:00"),
            "text": "First post",
            "word_count": 2,
            "char_count": 10,
            "tags": [],
            "first_tag": None,
            "reactions": {},
            "total_reactions": 0,
            "reply_to_id": None,
            "has_photo": False,
            "has_media": False,
            "date": datetime(2024, 1, 1).date(),
            "year": 2024,
            "month": 1,
            "year_month": "2024-01",
            "day": 1,
            "day_of_week": 0,
            "day_name": "Monday",
            "hour": 10,
            "minute": 0,
        }])

        with tempfile.TemporaryDirectory() as tmp_dir:
            delta_path = Path(tmp_dir) / "dispatcher_delta.parquet"
            dispatcher = BotDispatcher(client, config, initial_df, delta_path=delta_path)

            # 1. Post from unauthorized channel
            rogue_post = {
                "message_id": 99,
                "date": 1729684800,
                "chat": {"id": -100999999, "type": "channel"},
                "text": "Ignored spam post"
            }
            res_rogue = dispatcher.handle_channel_post(rogue_post)
            self.assertIsNone(res_rogue)
            self.assertEqual(len(dispatcher.df), 1)

            # 2. Post from designated channel
            valid_post = {
                "message_id": 2,
                "date": 1729685800,
                "chat": {"id": -100123, "type": "channel"},
                "text": "Legit journal thought [mai]"
            }
            res_valid = dispatcher.handle_channel_post(valid_post)
            self.assertIsNotNone(res_valid)
            self.assertEqual(len(dispatcher.df), 2)
            self.assertIn("mai", dispatcher.df.iloc[-1]["tags"])

    def test_unauthorized_user_dm_blocked(self):
        client = MagicMock()
        config = BotConfig(bot_token="test_tok", chat_id="12345")  # Kieran's ID is 12345
        dispatcher = BotDispatcher(client, config, pd.DataFrame())

        # Stranger attempts /otd command
        stranger_msg = {
            "chat": {"id": 99999},
            "from": {"id": 99999, "first_name": "Stranger"},
            "text": "/otd"
        }
        dispatcher.dispatch_message(stranger_msg)

        # Verify client sent Access Denied message
        client.send_message.assert_called_once()
        args = client.send_message.call_args[0]
        self.assertEqual(args[0], 99999)
        self.assertIn("Access Denied", args[1])


if __name__ == "__main__":
    unittest.main()
