#!/usr/bin/env python3
"""
Interactive Telegram Companion Bot Daemon for telegram-journal-analytics.
Listens for user commands (/otd, /random, /stats, /tag) and callback queries.

Usage:
    python -m scripts.run_bot
    python -m scripts.run_bot --export-dir ChatExport_sample
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
import time

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from src.bot.client import TelegramClient, TelegramAPIError
from src.bot.config import load_config
from src.bot.handlers import BotDispatcher, resolve_export_dir
from src.parser import load_export


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run interactive Telegram companion bot for journal analytics."
    )
    parser.add_argument(
        "--export-dir",
        "-i",
        type=str,
        default=None,
        help="Path to Telegram ChatExport directory (auto-detected if omitted).",
    )
    args = parser.parse_args()

    config = load_config()
    if not config.bot_token:
        print("❌ Error: TELEGRAM_BOT_TOKEN not configured in .env!", file=sys.stderr)
        sys.exit(1)

    client = TelegramClient(config.bot_token)
    try:
        me = client.get_me()
        bot_username = me.get("username", "Unknown")
        bot_name = me.get("first_name", "Bot")
    except TelegramAPIError as e:
        print(f"❌ Failed to connect to Telegram Bot API: {e}", file=sys.stderr)
        sys.exit(1)

    print("=" * 60)
    print(f"🤖 Starting {bot_name} (@{bot_username})...")
    print("=" * 60)

    # Resolve export directory and load journal archive
    export_dir = resolve_export_dir(args.export_dir or config.export_dir)
    print(f"[Bot] Loading journal archive from: {export_dir.name}")
    df = load_export(export_dir, verbose=False)
    print(f"[Bot] Loaded {len(df):,} journal entries successfully.")

    dispatcher = BotDispatcher(client, config, df)

    print("\n🟢 Bot is live and listening for messages!")
    print(f"👉 Open Telegram and chat with: https://t.me/{bot_username}")
    print("Commands supported: /otd, /random, /stats, /tag <name>, /help")
    print("Press Ctrl+C to terminate.\n")

    offset = None
    # Flush pending messages on startup
    try:
        pending = client.get_updates(timeout=1)
        if pending:
            offset = pending[-1]["update_id"] + 1
            print(f"[Bot] Flushed {len(pending)} pending update(s).")
    except Exception:
        pass

    consecutive_errors = 0
    while True:
        try:
            updates = client.get_updates(offset=offset, timeout=20)
            consecutive_errors = 0

            for update in updates:
                offset = update["update_id"] + 1

                # Handle text messages
                if "message" in update:
                    msg = update["message"]
                    sender = msg.get("from", {}).get("first_name", "User")
                    text = msg.get("text", "")
                    print(f"📩 [{sender}]: {text}")
                    dispatcher.dispatch_message(msg)

                # Handle inline callback queries
                elif "callback_query" in update:
                    cb = update["callback_query"]
                    sender = cb.get("from", {}).get("first_name", "User")
                    data = cb.get("data", "")
                    print(f"🔘 [{sender} clicked]: {data}")
                    dispatcher.dispatch_callback_query(cb)

        except KeyboardInterrupt:
            print("\n🛑 Shutting down Telegram bot...")
            break
        except TelegramAPIError as e:
            consecutive_errors += 1
            print(f"⚠️ Telegram API Error ({consecutive_errors}): {e}")
            time.sleep(min(30, 2 ** consecutive_errors))
        except Exception as e:
            consecutive_errors += 1
            print(f"⚠️ Unexpected error ({consecutive_errors}): {e}")
            time.sleep(min(30, 2 ** consecutive_errors))


if __name__ == "__main__":
    main()
