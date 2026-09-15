"""
Synthetic Dataset Generator for Telegram Journal Analytics.

Generates realistic mock Telegram Desktop HTML exports (messages.html, messages2.html)
with customizable message volume, circadian curves, interest lifecycles, and multi-year
On This Day anchors for automated testing and demonstrations without private data.
"""

from __future__ import annotations

import html
import random
from dataclasses import dataclass
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class SyntheticMessage:
    """Represents a simulated journal entry."""
    id: int
    timestamp: datetime
    text: str
    tags: List[str]
    has_photo: bool
    reactions: Dict[str, int]


# Hourly probability distribution modeling a night-owl circadian profile
# Peak at 23:00, quiet morning (05:00-08:00), modest afternoon bump (13:00-15:00)
CIRCADIAN_WEIGHTS = {
    0: 8, 1: 6, 2: 3, 3: 1, 4: 1, 5: 1, 6: 1, 7: 2,
    8: 4, 9: 6, 10: 7, 11: 8, 12: 9, 13: 10, 14: 9, 15: 8,
    16: 8, 17: 9, 18: 10, 19: 11, 20: 12, 21: 14, 22: 18, 23: 24,
}

# Tag definitions with lifespans
TAG_CONFIGS = [
    # Evergreen (continuous throughout 2023-2026)
    {"tag": "reading", "type": "evergreen", "start": (2023, 12), "end": (2026, 9), "freq": 0.20},
    {"tag": "fitness", "type": "evergreen", "start": (2023, 12), "end": (2026, 9), "freq": 0.16},
    {"tag": "coding", "type": "evergreen", "start": (2023, 12), "end": (2026, 9), "freq": 0.18},
    {"tag": "coffee", "type": "evergreen", "start": (2024, 1), "end": (2026, 9), "freq": 0.12},

    # Seasonal Bursts (high density in narrow window, then dormant)
    {"tag": "elden ring", "type": "burst", "start": (2024, 2), "end": (2024, 6), "freq": 0.35},
    {"tag": "baking", "type": "burst", "start": (2024, 8), "end": (2024, 11), "freq": 0.30},
    {"tag": "japan trip", "type": "burst", "start": (2025, 3), "end": (2025, 5), "freq": 0.40},
    {"tag": "synthv", "type": "burst", "start": (2025, 6), "end": (2025, 10), "freq": 0.28},

    # Emerging (started recently in 2026)
    {"tag": "ai agents", "type": "emerging", "start": (2026, 2), "end": (2026, 9), "freq": 0.25},
    {"tag": "running", "type": "emerging", "start": (2026, 5), "end": (2026, 9), "freq": 0.22},
]

SAMPLE_SNIPPETS = {
    "reading": [
        "Finished chapter 4 of the book. Really loving the world-building.",
        "Picked up a new paperback today during lunch break.",
        "Quiet evening with a book and some tea. Page 150 reached.",
        "The plot twist in this chapter caught me completely off guard.",
    ],
    "fitness": [
        "Solid workout session today. Hit a new personal record on bench.",
        "Leg day done, definitely going to feel this tomorrow morning.",
        "Quick 30 minute mobility and core routine before dinner.",
        "Rest day today, body needed the recovery after a busy week.",
    ],
    "coding": [
        "Finally resolved a stubborn caching bug that bugged me for days.",
        "Refactored the parser layer into clean modular functions.",
        "Writing automated unit tests to keep code coverage high.",
        "Playing with new UI components and dark mode color palettes.",
    ],
    "coffee": [
        "Tried an Ethiopian single-origin pour over today, fruity notes.",
        "Morning brew hit just right before the 9am call.",
        "Exploring local coffee roasters this afternoon.",
    ],
    "elden ring": [
        "Defeated the boss after 12 attempts! Hands still shaking.",
        "Exploring the underground river well area, the atmosphere is incredible.",
        "Upgraded my weapon to +15, damage output is noticeably higher.",
    ],
    "baking": [
        "Baked sourdough focaccia with rosemary and flaky sea salt.",
        "Second attempt at matcha cookies turned out much better.",
        "Proofing dough overnight for fresh bread tomorrow morning.",
    ],
    "japan trip": [
        "Booked train tickets from Tokyo to Kyoto, itinerary taking shape.",
        "Checked out local ramen joints in Shibuya, fantastic broth.",
        "Walked 25,000 steps around the temple district today.",
    ],
    "synthv": [
        "Tuning vocal tracks for a new cover project, pitch bends taking time.",
        "Experimenting with different vocal breath parameters.",
        "Exported the final audio mixdown, sounds balanced and clean.",
    ],
    "ai agents": [
        "Testing multi-agent collaboration flows for coding tasks.",
        "Fascinating to see autonomous planning loops resolve edge cases.",
        "Built a dedicated tool harness for file analysis.",
    ],
    "running": [
        "Early evening 5k run around the neighborhood park.",
        "Consistent pacing today, averaged 5:20/km without feeling exhausted.",
        "New running shoes arrived, excited to break them in this weekend.",
    ],
    "general": [
        "Had a productive day clearing backlogged tasks and emails.",
        "Caught a beautiful sunset on the walk back home.",
        "Quick reminder to drink more water and get to sleep earlier tonight.",
        "Quiet Sunday reflections. Prepped everything for the week ahead.",
        "Cooked dinner at home today instead of ordering takeout.",
    ],
}


def _is_active_in_month(cfg: Dict[str, Any], year: int, month: int) -> bool:
    s_yr, s_mo = cfg["start"]
    e_yr, e_mo = cfg["end"]
    cur = year * 12 + month
    return (s_yr * 12 + s_mo) <= cur <= (e_yr * 12 + e_mo)


def _sample_hour(rng: random.Random) -> int:
    hours = list(CIRCADIAN_WEIGHTS.keys())
    weights = [CIRCADIAN_WEIGHTS[h] for h in hours]
    return rng.choices(hours, weights=weights, k=1)[0]


def generate_synthetic_journal(
    num_messages: int = 400,
    start_date: date = date(2023, 12, 1),
    end_date: date = date(2026, 9, 15),
    seed: int = 42,
) -> List[SyntheticMessage]:
    """
    Generate a deterministic synthetic journal dataset with realistic distributions.
    """
    rng = random.Random(seed)
    total_days = (end_date - start_date).days
    messages: List[SyntheticMessage] = []
    msg_id_counter = 1

    # 1. Seed Multi-Year Anchors for "On This Day" (e.g. 09-15, 04-20, 06-22 across 2024, 2025, 2026)
    anchor_dates = [(9, 15), (4, 20), (6, 22)]
    anchor_years = [2024, 2025, 2026]

    for m, d in anchor_dates:
        for yr in anchor_years:
            anchor_dt = date(yr, m, d)
            if start_date <= anchor_dt <= end_date:
                # Add 2-4 messages on this anchor day
                for _ in range(rng.randint(2, 4)):
                    hr = _sample_hour(rng)
                    minute = rng.randint(0, 59)
                    sec = rng.randint(0, 59)
                    ts = datetime(yr, m, d, hr, minute, sec)

                    # Determine active tags
                    active_tags = [
                        c["tag"] for c in TAG_CONFIGS
                        if _is_active_in_month(c, yr, m) and rng.random() < c["freq"]
                    ]

                    # Pick tag and text
                    if active_tags:
                        chosen_tag = rng.choice(active_tags)
                        snippets = SAMPLE_SNIPPETS.get(chosen_tag, SAMPLE_SNIPPETS["general"])
                        text = f"[{chosen_tag}] {rng.choice(snippets)}"
                        tag_list = [chosen_tag]
                    else:
                        text = rng.choice(SAMPLE_SNIPPETS["general"])
                        tag_list = []

                    has_photo = rng.random() < 0.12
                    reactions = {}
                    if rng.random() < 0.25:
                        rx_emoji = rng.choice(["👍", "❤", "🔥", "🎉"])
                        reactions[rx_emoji] = rng.randint(1, 3)

                    messages.append(
                        SyntheticMessage(
                            id=msg_id_counter,
                            timestamp=ts,
                            text=text,
                            tags=tag_list,
                            has_photo=has_photo,
                            reactions=reactions,
                        )
                    )
                    msg_id_counter += 1

    # 2. Generate the remaining messages across the full timespan
    remaining = max(0, num_messages - len(messages))
    for _ in range(remaining):
        day_offset = rng.randint(0, total_days)
        cur_date = start_date + timedelta(days=day_offset)
        yr, mo = cur_date.year, cur_date.month

        hr = _sample_hour(rng)
        minute = rng.randint(0, 59)
        sec = rng.randint(0, 59)
        ts = datetime(yr, mo, cur_date.day, hr, minute, sec)

        # Decide on tags
        active_tags = [
            c["tag"] for c in TAG_CONFIGS
            if _is_active_in_month(c, yr, mo) and rng.random() < c["freq"]
        ]

        if active_tags:
            chosen_tag = rng.choice(active_tags)
            snippets = SAMPLE_SNIPPETS.get(chosen_tag, SAMPLE_SNIPPETS["general"])
            text = f"[{chosen_tag}] {rng.choice(snippets)}"
            # Occasionally add a second tag
            if len(active_tags) > 1 and rng.random() < 0.15:
                second_tag = rng.choice([t for t in active_tags if t != chosen_tag])
                text += f" Also spent time on [{second_tag}]."
                tag_list = [chosen_tag, second_tag]
            else:
                tag_list = [chosen_tag]
        else:
            text = rng.choice(SAMPLE_SNIPPETS["general"])
            tag_list = []

        # 10% photo messages, 2% photo-only (no caption)
        has_photo = rng.random() < 0.12
        if has_photo and rng.random() < 0.15:
            text = ""  # media-only entry

        # Reactions
        reactions = {}
        if rng.random() < 0.3:
            rx_emoji = rng.choice(["👍", "❤", "🔥", "🎉", "👏"])
            reactions[rx_emoji] = rng.randint(1, 4)

        messages.append(
            SyntheticMessage(
                id=msg_id_counter,
                timestamp=ts,
                text=text,
                tags=tag_list,
                has_photo=has_photo,
                reactions=reactions,
            )
        )
        msg_id_counter += 1

    # Sort deterministically by timestamp
    messages.sort(key=lambda m: m.timestamp)

    # Re-assign sequential IDs
    for idx, m in enumerate(messages, 1):
        m.id = idx

    return messages


def export_to_telegram_html(
    messages: List[SyntheticMessage],
    output_dir: Path | str,
    channel_name: str = "Synthetic Journal Channel",
    messages_per_file: int = 250,
) -> List[Path]:
    """
    Serialize SyntheticMessage list into Telegram Desktop HTML files
    (messages.html, messages2.html, etc.) matching exact DOM selectors.
    """
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    # Split into paginated chunks
    chunks: List[List[SyntheticMessage]] = []
    for i in range(0, len(messages), messages_per_file):
        chunks.append(messages[i : i + messages_per_file])

    if not chunks:
        chunks = [[]]

    created_files: List[Path] = []
    num_pages = len(chunks)

    for page_idx, chunk in enumerate(chunks, 1):
        file_name = "messages.html" if page_idx == 1 else f"messages{page_idx}.html"
        target_file = out_path / file_name

        message_divs_html = []
        for m in chunk:
            ts_str = f"{m.timestamp.day} {m.timestamp.strftime('%B %Y, %H:%M:%S')}"
            time_short = m.timestamp.strftime("%H:%M")
            escaped_text = html.escape(m.text).replace("\n", "<br>")

            photo_html = ""
            if m.has_photo:
                photo_html = """
                <div class="media_wrap clearfix">
                    <div class="media_photo">
                        <a class="photo_wrap clearfix" href="#">
                            <img class="photo" src="photos/dummy.jpg" width="300" height="200" alt="photo" />
                        </a>
                    </div>
                </div>
                """

            text_html = f'<div class="text">{escaped_text}</div>' if escaped_text else ""

            rx_html = ""
            if m.reactions:
                rx_items = "".join(
                    f'<span class="reaction"><span class="emoji">{r}</span><span class="count">{c}</span></span>'
                    for r, c in m.reactions.items()
                )
                rx_html = f'<div class="reactions">{rx_items}</div>'

            msg_div = f"""
            <div class="message default clearfix" id="message{m.id}">
                <div class="body">
                    <div class="pull_right date details" title="{ts_str}">{time_short}</div>
                    {photo_html}
                    {text_html}
                    {rx_html}
                </div>
            </div>
            """
            message_divs_html.append(msg_div)

        page_nav_html = ""
        if num_pages > 1:
            links = []
            for p in range(1, num_pages + 1):
                p_file = "messages.html" if p == 1 else f"messages{p}.html"
                links.append(f'<a href="{p_file}">{p}</a>')
            page_nav_html = f'<div class="pagination">Pages: {" ".join(links)}</div>'

        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{html.escape(channel_name)}</title>
    <link rel="stylesheet" href="css/style.css">
</head>
<body>
    <div class="page_wrap">
        <div class="page_header">
            <div class="text bold">{html.escape(channel_name)}</div>
        </div>
        <div class="page_body chat_page">
            <div class="history">
                {"".join(message_divs_html)}
            </div>
            {page_nav_html}
        </div>
    </div>
</body>
</html>
"""
        with open(target_file, "w", encoding="utf-8") as f:
            f.write(html_content)

        created_files.append(target_file)

    # Create dummy css directory
    css_dir = out_path / "css"
    css_dir.mkdir(exist_ok=True)
    (css_dir / "style.css").write_text("/* Telegram export style */", encoding="utf-8")

    return created_files
