#!/usr/bin/env python3
"""
Daily "On This Day" (OTD) Flashback Dispatcher for Telegram.
Sends past reflections for today's calendar date to your Telegram DM or journal channel.

Usage:
    # Send today's flashback using credentials from .env
    python -m scripts.send_daily_otd

    # Preview message in terminal without calling Telegram API
    python -m scripts.send_daily_otd --dry-run

    # Send flashback for a specific date (MM-DD or Month Day)
    python -m scripts.send_daily_otd --date 09-15

    # Test against synthetic demo dataset
    python -m scripts.send_daily_otd --export-dir ChatExport_sample --dry-run
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from src.bot.client import TelegramClient, TelegramAPIError
from src.bot.config import load_config
from src.bot.formatter import format_otd_message
from src.bot.handlers import resolve_export_dir
from src.bot.live_sync import load_unified_journal
from src.otd.logic import parse_query_date, query_on_this_day


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Dispatch daily 'On This Day' journal memories to Telegram."
    )
    parser.add_argument(
        "--date",
        "-d",
        type=str,
        default=None,
        help="Date to query: 'MM-DD', 'YYYY-MM-DD', 'Month Day', 'yesterday', or leave blank for today.",
    )
    parser.add_argument(
        "--window",
        "-w",
        type=int,
        default=0,
        help="Day window radius (±N days around target date, default: 0).",
    )
    parser.add_argument(
        "--export-dir",
        "-i",
        type=str,
        default=None,
        help="Path to Telegram ChatExport directory (auto-detected if omitted).",
    )
    parser.add_argument(
        "--chat-id",
        "-c",
        type=str,
        default=None,
        help="Override Telegram Chat ID (defaults to TELEGRAM_CHAT_ID from .env).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print formatted Telegram message to terminal without sending over network.",
    )
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Suppress informational stdout output (ideal for cron jobs).",
    )

    args = parser.parse_args()

    # Load configuration
    config = load_config()
    chat_id = args.chat_id or config.chat_id

    if not args.dry_run:
        if not config.bot_token:
            print("❌ Error: TELEGRAM_BOT_TOKEN not configured in .env!", file=sys.stderr)
            sys.exit(1)
        if not chat_id:
            print("❌ Error: TELEGRAM_CHAT_ID not configured! Run 'python -m scripts.get_chat_id' first.", file=sys.stderr)
            sys.exit(1)

    # Resolve export directory
    preferred_dir = args.export_dir or config.export_dir
    export_dir = resolve_export_dir(preferred_dir)
    if not args.quiet:
        print(f"[OTD Bot] Using export archive: {export_dir.name}")

    # Load unified dataset (Base Archive + Live Delta)
    df = load_unified_journal(export_dir, verbose=not args.quiet)

    # Parse target date
    target_month, target_day = parse_query_date(args.date)

    # Query OTD memories
    otd_result = query_on_this_day(
        df,
        month=target_month,
        day=target_day,
        window_days=args.window,
    )

    # Format messages
    messages = format_otd_message(otd_result)

    if args.dry_run:
        print("\n" + "=" * 60)
        print("🔍 DRY RUN — Formatted Telegram HTML Output:")
        print("=" * 60)
        for i, chunk in enumerate(messages, 1):
            if len(messages) > 1:
                print(f"\n--- [Message Chunk {i}/{len(messages)} ({len(chunk)} chars)] ---")
            print(chunk)
        print("\n" + "=" * 60)
        print(f"✅ Dry run completed ({len(messages)} message chunk(s), 0 network calls).")
        return

    # Send via Telegram API
    client = TelegramClient(config.bot_token)
    try:
        for i, chunk in enumerate(messages, 1):
            client.send_message(chat_id, chunk)
            if not args.quiet:
                print(f"[OTD Bot] Successfully sent chunk {i}/{len(messages)} to chat {chat_id}.")
        if not args.quiet:
            print("🎉 Daily OTD flashback dispatched successfully!")
    except TelegramAPIError as e:
        print(f"❌ Failed to send Telegram message: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
