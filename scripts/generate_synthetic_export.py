#!/usr/bin/env python3
"""
CLI tool to generate a synthetic Telegram channel export.

Usage:
    python -m scripts.generate_synthetic_export
    python -m scripts.generate_synthetic_export --output-dir "ChatExport_sample" --num-messages 500
"""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
from collections import Counter

from src.synthetic import generate_synthetic_journal, export_to_telegram_html


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a realistic synthetic Telegram channel export for testing and demonstration."
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        type=str,
        default="ChatExport_sample",
        help="Directory to place the generated synthetic export (default: ChatExport_sample).",
    )
    parser.add_argument(
        "--num-messages",
        "-n",
        type=int,
        default=400,
        help="Total number of simulated messages to generate (default: 400).",
    )
    parser.add_argument(
        "--start-date",
        type=str,
        default="2023-12-01",
        help="Start date in YYYY-MM-DD format (default: 2023-12-01).",
    )
    parser.add_argument(
        "--end-date",
        type=str,
        default="2026-09-15",
        help="End date in YYYY-MM-DD format (default: 2026-09-15).",
    )
    parser.add_argument(
        "--seed",
        "-s",
        type=int,
        default=42,
        help="Random seed for deterministic output (default: 42).",
    )
    parser.add_argument(
        "--split-size",
        type=int,
        default=250,
        help="Messages per HTML file to test multi-page pagination (default: 250).",
    )

    args = parser.parse_args()

    s_date = datetime.strptime(args.start_date, "%Y-%m-%d").date()
    e_date = datetime.strptime(args.end_date, "%Y-%m-%d").date()

    print(f"\n🎲 Generating {args.num_messages} synthetic messages ({s_date} -> {e_date})...")

    messages = generate_synthetic_journal(
        num_messages=args.num_messages,
        start_date=s_date,
        end_date=e_date,
        seed=args.seed,
    )

    out_dir = Path(args.output_dir)
    created_files = export_to_telegram_html(
        messages=messages,
        output_dir=out_dir,
        messages_per_file=args.split_size,
    )

    tag_counts = Counter()
    for m in messages:
        for t in m.tags:
            tag_counts[t] += 1

    print("=" * 65)
    print("✨ Synthetic Telegram Export Generated Successfully!")
    print("=" * 65)
    print(f"📁 Destination Folder: {out_dir.resolve()}")
    print(f"📄 Generated Files:    {', '.join(f.name for f in created_files)}")
    print(f"📊 Total Messages:     {len(messages)}")
    print(f"⏱️  Timespan:           {messages[0].timestamp.strftime('%Y-%m-%d')} -> {messages[-1].timestamp.strftime('%Y-%m-%d')}")
    print(f"🏷️  Unique Tags ({len(tag_counts)}):")
    for tag, count in tag_counts.most_common(8):
        print(f"   - [{tag}]: {count} entries")
    print("=" * 65)
    print("\n💡 You can now test any runner against this synthetic dataset:")
    print(f"   python -m scripts.run_circadian --export-dir \"{args.output_dir}\"")
    print(f"   python -m scripts.run_tag_lifecycles --export-dir \"{args.output_dir}\"")
    print(f"   python -m scripts.run_otd --export-dir \"{args.output_dir}\" --date 09-15")
    print()


if __name__ == "__main__":
    main()
