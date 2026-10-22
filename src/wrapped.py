"""
Channel-Wrapped Retrospective Engine.

Generates an annual or all-time retrospective summary ("Spotify Wrapped" style)
for personal Telegram journal channels. Computes journaling streaks, circadian personas,
volume equivalents, top fixations, expressiveness metrics, and standout memories.
Exports a formatted terminal summary and an interactive, standalone HTML story deck.
"""

from __future__ import annotations

import html
import math
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, date
from itertools import combinations
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd


@dataclass
class PersonaInfo:
    """Represents a circadian journaling persona."""
    name: str
    emoji: str
    tagline: str
    night_owl_pct: float
    morning_pct: float
    peak_hour: int
    peak_hour_formatted: str
    peak_day: str


@dataclass
class WrappedData:
    """Complete dataset for a Channel-Wrapped retrospective."""
    period_label: str
    year: Optional[int]
    total_messages: int
    total_words: int
    total_chars: int
    avg_words_per_message: float
    reading_time_minutes: int
    book_pages_equivalent: float
    active_days: int
    total_period_days: int
    active_days_pct: float
    busiest_date: str
    busiest_date_count: int
    busiest_month: str
    busiest_month_count: int
    favorite_day_of_week: str
    favorite_day_count: int
    longest_streak_days: int
    longest_streak_start: str
    longest_streak_end: str
    longest_gap_days: int
    longest_gap_start: str
    longest_gap_end: str
    persona: PersonaInfo
    top_tags: List[Tuple[str, int, float]]  # (tag, count, pct_of_tagged)
    top_tag_pairs: List[Tuple[str, str, int]]  # (tag1, tag2, co_occurrences)
    era_tag: Optional[str]
    total_reactions: int
    top_reactions: List[Tuple[str, int]]
    photo_count: int
    media_count: int
    self_reply_count: int
    magnum_opus_id: Optional[int]
    magnum_opus_date: str
    magnum_opus_words: int
    magnum_opus_snippet: str
    most_reacted_id: Optional[int]
    most_reacted_date: str
    most_reacted_count: int
    most_reacted_reactions: Dict[str, int]
    most_reacted_snippet: str


def _format_hour_12h(hour: int) -> str:
    """Format hour (0-23) into 12-hour AM/PM string."""
    if hour == 0:
        return "12:00 AM"
    elif hour < 12:
        return f"{hour}:00 AM"
    elif hour == 12:
        return "12:00 PM"
    else:
        return f"{hour - 12}:00 PM"


def determine_persona(df: pd.DataFrame) -> PersonaInfo:
    """
    Classify the journaler into a circadian persona based on their hourly posting distribution.
    """
    total = len(df)
    if total == 0:
        return PersonaInfo(
            name="The Blank Slate",
            emoji="✨",
            tagline="A journal waiting for its very first thoughts to unfold.",
            night_owl_pct=0.0,
            morning_pct=0.0,
            peak_hour=12,
            peak_hour_formatted="12:00 PM",
            peak_day="Unknown",
        )

    hour_counts = df["hour"].value_counts()
    peak_hour = int(hour_counts.idxmax())

    day_counts = df["day_name"].value_counts()
    peak_day = str(day_counts.idxmax()) if not day_counts.empty else "Sunday"

    # Percentage calculations
    night_mask = (df["hour"] >= 22) | (df["hour"] < 4)
    late_night_mask = (df["hour"] >= 0) & (df["hour"] < 4)
    morning_mask = (df["hour"] >= 5) & (df["hour"] < 9)
    midday_mask = (df["hour"] >= 11) & (df["hour"] < 15)
    evening_mask = (df["hour"] >= 17) & (df["hour"] < 22)

    night_owl_pct = round((night_mask.sum() / total) * 100, 1)
    late_night_pct = round((late_night_mask.sum() / total) * 100, 1)
    morning_pct = round((morning_mask.sum() / total) * 100, 1)
    midday_pct = round((midday_mask.sum() / total) * 100, 1)
    evening_pct = round((evening_mask.sum() / total) * 100, 1)

    # Classification logic
    if late_night_pct >= 22.0 or peak_hour in (0, 1, 2, 3):
        name = "The 2 AM Luminary"
        emoji = "🌌"
        tagline = "Your most profound thoughts strike in the deepest quiet of the night."
    elif night_owl_pct >= 40.0 or peak_hour in (22, 23):
        name = "The Midnight Philosopher"
        emoji = "🦉"
        tagline = "Most reflective when the world winds down, decompressing under the moonlight."
    elif morning_pct >= 22.0 or peak_hour in (5, 6, 7, 8):
        name = "The Dawn Chronicler"
        emoji = "🌅"
        tagline = "Greeting the day with clarity, setting intentions before the chaos begins."
    elif midday_pct >= 30.0 or peak_hour in (11, 12, 13, 14):
        name = "The Midday Brain-Dumper"
        emoji = "☕"
        tagline = "Channeling caffeine surges into spontaneous, fast-paced thought bursts."
    elif evening_pct >= 35.0 or peak_hour in (17, 18, 19, 20, 21):
        name = "The Twilight Decompressor"
        emoji = "🌇"
        tagline = "Unwinding at dusk, processing the day's triumphs, lessons, and serendipity."
    else:
        name = "The Steady Observer"
        emoji = "⏱️"
        tagline = "Mindfully capturing moments as they happen, keeping an even pulse all day long."

    return PersonaInfo(
        name=name,
        emoji=emoji,
        tagline=tagline,
        night_owl_pct=night_owl_pct,
        morning_pct=morning_pct,
        peak_hour=peak_hour,
        peak_hour_formatted=_format_hour_12h(peak_hour),
        peak_day=peak_day,
    )


def compute_streaks(
    df: pd.DataFrame,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> Tuple[int, str, str, int, str, str]:
    """
    Compute longest consecutive active day streak and longest hiatus gap.
    Returns:
        (longest_streak_days, streak_start_str, streak_end_str,
         longest_gap_days, gap_start_str, gap_end_str)
    """
    if df.empty:
        return 0, "", "", 0, "", ""

    # Parse and sort unique active dates
    unique_dates = sorted(pd.to_datetime(df["date"]).dt.date.unique())
    if not unique_dates:
        return 0, "", "", 0, "", ""

    # 1. Longest consecutive active day streak
    longest_streak = 1
    current_streak = 1
    best_streak_start = unique_dates[0]
    best_streak_end = unique_dates[0]
    curr_streak_start = unique_dates[0]

    for i in range(1, len(unique_dates)):
        prev_d = unique_dates[i - 1]
        curr_d = unique_dates[i]
        diff = (curr_d - prev_d).days

        if diff == 1:
            current_streak += 1
            if current_streak > longest_streak:
                longest_streak = current_streak
                best_streak_start = curr_streak_start
                best_streak_end = curr_d
        else:
            current_streak = 1
            curr_streak_start = curr_d

    # 2. Longest gap / hiatus between consecutive entries
    longest_gap = 0
    best_gap_start = unique_dates[0]
    best_gap_end = unique_dates[0]

    for i in range(1, len(unique_dates)):
        prev_d = unique_dates[i - 1]
        curr_d = unique_dates[i]
        gap_days = (curr_d - prev_d).days - 1
        if gap_days > longest_gap:
            longest_gap = gap_days
            best_gap_start = prev_d
            best_gap_end = curr_d

    # Also check gap from start_date to first entry if provided
    if start_date and unique_dates[0] > start_date:
        initial_gap = (unique_dates[0] - start_date).days
        if initial_gap > longest_gap:
            longest_gap = initial_gap
            best_gap_start = start_date
            best_gap_end = unique_dates[0]

    # And check gap from last entry to end_date if provided
    if end_date and end_date > unique_dates[-1]:
        tail_gap = (end_date - unique_dates[-1]).days
        if tail_gap > longest_gap:
            longest_gap = tail_gap
            best_gap_start = unique_dates[-1]
            best_gap_end = end_date

    return (
        longest_streak,
        best_streak_start.strftime("%b %d, %Y"),
        best_streak_end.strftime("%b %d, %Y"),
        longest_gap,
        best_gap_start.strftime("%b %d, %Y"),
        best_gap_end.strftime("%b %d, %Y"),
    )


def compute_wrapped(df: pd.DataFrame, year: Optional[int] = None) -> WrappedData:
    """
    Compute comprehensive Channel-Wrapped retrospective data for a specific year or all-time.
    """
    if year is not None:
        period_df = df[df["year"] == year].copy()
        period_label = str(year)
        # Period day count (account for leap years)
        is_leap = (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)
        total_period_days = 366 if is_leap else 365
        cal_start = date(year, 1, 1)
        cal_end = date(year, 12, 31)
    else:
        period_df = df.copy()
        if not period_df.empty:
            min_yr = int(period_df["year"].min())
            max_yr = int(period_df["year"].max())
            period_label = f"All-Time ({min_yr}–{max_yr})" if min_yr != max_yr else f"All-Time ({min_yr})"
            min_date = pd.to_datetime(period_df["date"]).min().date()
            max_date = pd.to_datetime(period_df["date"]).max().date()
            total_period_days = max(1, (max_date - min_date).days + 1)
            cal_start = min_date
            cal_end = max_date
        else:
            period_label = "All-Time"
            total_period_days = 365
            cal_start = None
            cal_end = None

    total_messages = len(period_df)
    total_words = int(period_df["word_count"].sum()) if total_messages else 0
    total_chars = int(period_df["char_count"].sum()) if total_messages else 0
    avg_words_per_message = round(total_words / total_messages, 1) if total_messages else 0.0

    # Reading metaphors: 220 wpm reading speed, 275 words per book page
    reading_time_minutes = int(math.ceil(total_words / 220)) if total_words else 0
    book_pages_equivalent = round(total_words / 275, 1) if total_words else 0.0

    # Active days
    unique_active_days = period_df["date"].nunique() if total_messages else 0
    active_days_pct = (
        round((unique_active_days / total_period_days) * 100, 1) if total_period_days else 0.0
    )

    # Busiest day
    if total_messages:
        daily_counts = period_df.groupby("date").size()
        busiest_date_raw = str(daily_counts.idxmax())
        busiest_date = datetime.strptime(busiest_date_raw, "%Y-%m-%d").strftime("%B %d, %Y")
        busiest_date_count = int(daily_counts.max())
    else:
        busiest_date = "N/A"
        busiest_date_count = 0

    # Busiest month
    if total_messages:
        month_order = [
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December"
        ]
        month_series = pd.to_datetime(period_df["timestamp"]).dt.strftime("%B")
        month_counts = month_series.value_counts()
        busiest_month = str(month_counts.idxmax())
        busiest_month_count = int(month_counts.max())
    else:
        busiest_month = "N/A"
        busiest_month_count = 0

    # Favorite day of the week
    if total_messages:
        day_counts = period_df["day_name"].value_counts()
        favorite_day = str(day_counts.idxmax())
        favorite_day_count = int(day_counts.max())
    else:
        favorite_day = "N/A"
        favorite_day_count = 0

    # Streaks & Hiatuses
    (
        longest_streak,
        streak_start,
        streak_end,
        longest_gap,
        gap_start,
        gap_end,
    ) = compute_streaks(period_df, cal_start, cal_end)

    # Circadian Persona
    persona = determine_persona(period_df)

    # Tags & Fixations
    all_tags: List[str] = []
    pair_counter: Counter = Counter()
    tagged_messages_count = 0

    if "tags" in period_df.columns:
        for tags_list in period_df["tags"]:
            if tags_list is not None and len(tags_list) > 0:
                cleaned_tags = sorted(list(set(str(t).lower().strip() for t in tags_list if t)))
                if cleaned_tags:
                    tagged_messages_count += 1
                    all_tags.extend(cleaned_tags)
                    if len(cleaned_tags) >= 2:
                        for pair in combinations(cleaned_tags, 2):
                            pair_counter[pair] += 1

    tag_counter = Counter(all_tags)
    top_tags: List[Tuple[str, int, float]] = []
    for tag, count in tag_counter.most_common(5):
        pct = round((count / tagged_messages_count * 100), 1) if tagged_messages_count else 0.0
        top_tags.append((tag, count, pct))

    top_tag_pairs: List[Tuple[str, str, int]] = [
        (pair[0], pair[1], count) for pair, count in pair_counter.most_common(3)
    ]

    # Detect Era of the year (tag with the highest concentration in a single quarter/period)
    era_tag: Optional[str] = None
    if top_tags:
        era_tag = top_tags[0][0]

    # Expressiveness & Reactions
    total_reactions = int(period_df["total_reactions"].sum()) if "total_reactions" in period_df else 0
    emoji_counter: Counter = Counter()
    for rx_dict in period_df.get("reactions", []):
        if isinstance(rx_dict, dict):
            for emoji_char, count in rx_dict.items():
                try:
                    c_int = int(count) if count is not None else 1
                except (ValueError, TypeError):
                    c_int = 1
                emoji_counter[emoji_char] += c_int

    top_reactions: List[Tuple[str, int]] = emoji_counter.most_common(5)

    photo_count = int(period_df["has_photo"].sum()) if "has_photo" in period_df else 0
    media_count = int(period_df["has_media"].sum()) if "has_media" in period_df else 0

    # Thought Monologues (Self-Replies)
    self_replies = 0
    if "reply_to_id" in period_df:
        self_replies = int(period_df["reply_to_id"].notna().sum() - (period_df["reply_to_id"] == 0).sum())
        self_replies = max(0, self_replies)

    # The Magnum Opus (Longest Reflection Message)
    magnum_opus_id = None
    magnum_opus_date = "N/A"
    magnum_opus_words = 0
    magnum_opus_snippet = ""

    if total_messages and "word_count" in period_df:
        longest_row = period_df.loc[period_df["word_count"].idxmax()]
        magnum_opus_id = int(longest_row["id"]) if pd.notna(longest_row["id"]) else None
        magnum_opus_words = int(longest_row["word_count"])
        ts = pd.to_datetime(longest_row["timestamp"])
        magnum_opus_date = ts.strftime("%B %d, %Y at %I:%M %p")
        raw_snippet = str(longest_row["text"]).strip().replace("\n", " ")
        if len(raw_snippet) > 220:
            magnum_opus_snippet = raw_snippet[:217] + "..."
        else:
            magnum_opus_snippet = raw_snippet

    # Most Reacted Message
    most_reacted_id = None
    most_reacted_date = "N/A"
    most_reacted_count = 0
    most_reacted_reactions: Dict[str, int] = {}
    most_reacted_snippet = ""

    if total_messages and total_reactions > 0 and "total_reactions" in period_df:
        reacted_row = period_df.loc[period_df["total_reactions"].idxmax()]
        most_reacted_count = int(reacted_row["total_reactions"])
        if most_reacted_count > 0:
            most_reacted_id = int(reacted_row["id"]) if pd.notna(reacted_row["id"]) else None
            ts = pd.to_datetime(reacted_row["timestamp"])
            most_reacted_date = ts.strftime("%B %d, %Y at %I:%M %p")
            most_reacted_reactions = reacted_row.get("reactions", {})
            raw_rx_snippet = str(reacted_row["text"]).strip().replace("\n", " ")
            if len(raw_rx_snippet) > 220:
                most_reacted_snippet = raw_rx_snippet[:217] + "..."
            else:
                most_reacted_snippet = raw_rx_snippet

    return WrappedData(
        period_label=period_label,
        year=year,
        total_messages=total_messages,
        total_words=total_words,
        total_chars=total_chars,
        avg_words_per_message=avg_words_per_message,
        reading_time_minutes=reading_time_minutes,
        book_pages_equivalent=book_pages_equivalent,
        active_days=unique_active_days,
        total_period_days=total_period_days,
        active_days_pct=active_days_pct,
        busiest_date=busiest_date,
        busiest_date_count=busiest_date_count,
        busiest_month=busiest_month,
        busiest_month_count=busiest_month_count,
        favorite_day_of_week=favorite_day,
        favorite_day_count=favorite_day_count,
        longest_streak_days=longest_streak,
        longest_streak_start=streak_start,
        longest_streak_end=streak_end,
        longest_gap_days=longest_gap,
        longest_gap_start=gap_start,
        longest_gap_end=gap_end,
        persona=persona,
        top_tags=top_tags,
        top_tag_pairs=top_tag_pairs,
        era_tag=era_tag,
        total_reactions=total_reactions,
        top_reactions=top_reactions,
        photo_count=photo_count,
        media_count=media_count,
        self_reply_count=self_replies,
        magnum_opus_id=magnum_opus_id,
        magnum_opus_date=magnum_opus_date,
        magnum_opus_words=magnum_opus_words,
        magnum_opus_snippet=magnum_opus_snippet,
        most_reacted_id=most_reacted_id,
        most_reacted_date=most_reacted_date,
        most_reacted_count=most_reacted_count,
        most_reacted_reactions=most_reacted_reactions,
        most_reacted_snippet=most_reacted_snippet,
    )


def render_wrapped_terminal(data: WrappedData) -> str:
    """
    Render a clean, structured CLI summary deck of Channel-Wrapped.
    """
    lines = []
    divider = "─" * 64

    lines.append("")
    lines.append(f" ✨ CHANNEL-WRAPPED RETROSPECTIVE: {data.period_label} ✨ ".center(64, "═"))
    lines.append("")

    # Card 1: Volume & Dedication
    lines.append(" 📖  SLIDE 1: VOLUME & DEDICATION ".center(64, "─"))
    lines.append(f"  • Total Entries:       {data.total_messages:,} messages")
    lines.append(f"  • Words Inscribed:     {data.total_words:,} words ({data.total_chars:,} characters)")
    lines.append(f"  • Average Depth:       {data.avg_words_per_message:.1f} words/entry")
    lines.append(f"  • Real-World Metaphor: ~{data.book_pages_equivalent:.1f} book pages (~{data.reading_time_minutes} min read)")
    lines.append(f"  • Consistency:         {data.active_days}/{data.total_period_days} active days ({data.active_days_pct}%)")
    lines.append(f"  • Peak Journal Day:    {data.busiest_date} ({data.busiest_date_count} entries)")
    lines.append("")

    # Card 2: Streaks & Cadence
    lines.append(" ⚡  SLIDE 2: CADENCE & STREAKS ".center(64, "─"))
    if data.longest_streak_days > 1:
        lines.append(f"  • Longest Streak:      {data.longest_streak_days} consecutive days ({data.longest_streak_start} → {data.longest_streak_end})")
    else:
        lines.append(f"  • Longest Streak:      {data.longest_streak_days} day")
    if data.longest_gap_days > 0:
        lines.append(f"  • Longest Hiatus:      {data.longest_gap_days} days pause ({data.longest_gap_start} → {data.longest_gap_end})")
    lines.append(f"  • Top Reflection Month:{data.busiest_month} ({data.busiest_month_count} entries)")
    lines.append(f"  • Favorite Weekday:    {data.favorite_day_of_week} ({data.favorite_day_count} entries)")
    lines.append("")

    # Card 3: Circadian Persona
    p = data.persona
    lines.append(f" {p.emoji}  SLIDE 3: CIRCADIAN PERSONA ".center(64, "─"))
    lines.append(f"  • Archetype:           {p.name} {p.emoji}")
    lines.append(f"  • Persona Vibe:        \"{p.tagline}\"")
    lines.append(f"  • Peak Reflection Hour:{p.peak_hour_formatted} (24h: {p.peak_hour:02d}:00)")
    lines.append(f"  • Night Owl Index:     {p.night_owl_pct}% logged between 10 PM and 4 AM")
    lines.append(f"  • Morning Share:       {p.morning_pct}% logged between 5 AM and 9 AM")
    lines.append("")

    # Card 4: Top Fixations & Tag Eras
    lines.append(" 🏷️  SLIDE 4: TOP FIXATIONS & ERAS ".center(64, "─"))
    if data.top_tags:
        for idx, (tag, count, pct) in enumerate(data.top_tags, start=1):
            bar = "█" * int(min(20, max(1, count / (data.top_tags[0][1] or 1) * 20)))
            lines.append(f"  #{idx} [{tag:<14}] {bar:<20} {count:>3} mentions ({pct:>4.1f}%)")
        if data.top_tag_pairs:
            pair_strs = [f"[{p[0]}] + [{p[1]}] ({p[2]}x)" for p in data.top_tag_pairs]
            lines.append(f"  • Companion Topics:    {', '.join(pair_strs)}")
    else:
        lines.append("  • No bracket tags detected in this period.")
    lines.append("")

    # Card 5: Expressiveness & Reactions
    lines.append(" 🎭  SLIDE 5: EXPRESSIVENESS & MEDIA ".center(64, "─"))
    if data.top_reactions:
        rx_str = " ".join([f"{emoji} ({cnt})" for emoji, cnt in data.top_reactions])
        lines.append(f"  • Total Reactions:     {data.total_reactions:,} recorded")
        lines.append(f"  • Top Reactions:       {rx_str}")
    else:
        lines.append("  • Total Reactions:     0 recorded")
    lines.append(f"  • Visual Archive:      {data.photo_count} photos, {data.media_count} total media files")
    lines.append(f"  • Thought Monologues:  {data.self_reply_count} self-replies / follow-up updates")
    lines.append("")

    # Card 6: The Magnum Opus & Memory
    lines.append(" 🏆  SLIDE 6: THE MAGNUM OPUS & STANDOUTS ".center(64, "─"))
    if data.magnum_opus_words > 0:
        lines.append(f"  • Longest Reflection:  {data.magnum_opus_words:,} words on {data.magnum_opus_date}")
        lines.append(f"    Excerpt: \"{data.magnum_opus_snippet}\"")
    if data.most_reacted_count > 0:
        rx_icons = " ".join([f"{k}x{int(v) if v is not None else 1}" for k, v in data.most_reacted_reactions.items()])
        lines.append(f"  • Most Reacted Entry:  {data.most_reacted_count} reactions ({rx_icons}) on {data.most_reacted_date}")
        lines.append(f"    Excerpt: \"{data.most_reacted_snippet}\"")
    lines.append("")
    lines.append("═" * 64)
    lines.append("")

    return "\n".join(lines)


def generate_wrapped_html(data: WrappedData, output_path: Path) -> Path:
    """
    Generate an interactive, standalone Spotify Wrapped-style dark-mode HTML deck.
    100% offline, zero external CDN or trackers.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    p = data.persona

    # Build Tag Bars HTML
    tag_bars_html = []
    if data.top_tags:
        max_tag_count = data.top_tags[0][1] or 1
        for idx, (tag, count, pct) in enumerate(data.top_tags, start=1):
            bar_w = int((count / max_tag_count) * 100)
            tag_bars_html.append(f"""
            <div class="tag-row">
                <div class="tag-meta">
                    <span class="tag-rank">#{idx}</span>
                    <span class="tag-name">[{html.escape(tag)}]</span>
                    <span class="tag-count">{count} mentions ({pct}%)</span>
                </div>
                <div class="tag-bar-track">
                    <div class="tag-bar-fill" style="width: {bar_w}%;"></div>
                </div>
            </div>
            """)
    else:
        tag_bars_html.append("<p class='empty-note'>No bracket tags recorded during this period.</p>")

    # Build Companion Tags HTML
    companion_html = ""
    if data.top_tag_pairs:
        pairs_chips = "".join([
            f"<span class='chip'>[{html.escape(p1)}] + [{html.escape(p2)}] <em>({cnt}x)</em></span>"
            for p1, p2, cnt in data.top_tag_pairs
        ])
        companion_html = f"""
        <div class="companions-box">
            <span class="companions-label">Favorite Companions:</span>
            <div class="chips-wrap">{pairs_chips}</div>
        </div>
        """

    # Build Reactions HTML
    reactions_html = ""
    if data.top_reactions:
        rx_chips = "".join([
            f"<span class='rx-chip'><span class='rx-emoji'>{html.escape(em)}</span> <span class='rx-count'>{cnt}</span></span>"
            for em, cnt in data.top_reactions
        ])
        reactions_html = f"<div class='rx-chips-row'>{rx_chips}</div>"

    # Magnum Opus HTML
    magnum_html = ""
    if data.magnum_opus_words > 0:
        magnum_html = f"""
        <div class="highlight-card">
            <div class="highlight-badge">🏆 Longest Reflection · {data.magnum_opus_words:,} words</div>
            <div class="highlight-date">{html.escape(data.magnum_opus_date)}</div>
            <div class="highlight-snippet">"{html.escape(data.magnum_opus_snippet)}"</div>
        </div>
        """

    # Most Reacted HTML
    most_reacted_html = ""
    if data.most_reacted_count > 0:
        rx_summary = " ".join([f"{k}{int(v) if v is not None else ''}" for k, v in data.most_reacted_reactions.items()])
        most_reacted_html = f"""
        <div class="highlight-card" style="margin-top: 1rem;">
            <div class="highlight-badge">💖 Most Resonating · {data.most_reacted_count} reactions ({html.escape(rx_summary)})</div>
            <div class="highlight-date">{html.escape(data.most_reacted_date)}</div>
            <div class="highlight-snippet">"{html.escape(data.most_reacted_snippet)}"</div>
        </div>
        """

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Channel-Wrapped · {html.escape(data.period_label)}</title>
    <style>
        :root {{
            --bg-base: #090d16;
            --bg-card: rgba(22, 27, 46, 0.75);
            --bg-card-border: rgba(255, 255, 255, 0.12);
            --accent-purple: #9d4edd;
            --accent-violet: #7928ca;
            --accent-blue: #3a86ff;
            --accent-cyan: #00f5d4;
            --accent-pink: #ff007f;
            --accent-amber: #ffbe0b;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --text-faint: #64748b;
        }}
        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}
        body {{
            background: var(--bg-base);
            background-image: 
                radial-gradient(circle at 15% 15%, rgba(121, 40, 202, 0.25) 0%, transparent 45%),
                radial-gradient(circle at 85% 80%, rgba(58, 134, 255, 0.22) 0%, transparent 50%),
                radial-gradient(circle at 50% 50%, rgba(255, 0, 127, 0.12) 0%, transparent 60%);
            min-height: 100vh;
            color: var(--text-main);
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 1.5rem 1rem;
            overflow-x: hidden;
        }}
        .wrapped-wrapper {{
            width: 100%;
            max-width: 580px;
            display: flex;
            flex-direction: column;
            align-items: center;
        }}
        /* Story Progress Bar */
        .story-bars {{
            width: 100%;
            display: flex;
            gap: 6px;
            margin-bottom: 1rem;
        }}
        .story-segment {{
            height: 4px;
            flex: 1;
            background: rgba(255, 255, 255, 0.2);
            border-radius: 2px;
            cursor: pointer;
            overflow: hidden;
            position: relative;
        }}
        .story-segment.active {{
            background: var(--text-main);
            box-shadow: 0 0 8px rgba(255, 255, 255, 0.6);
        }}
        .story-segment.seen {{
            background: rgba(255, 255, 255, 0.6);
        }}
        /* Main Slide Card */
        .deck-container {{
            width: 100%;
            position: relative;
            min-height: 560px;
        }}
        .slide {{
            background: var(--bg-card);
            border: 1px solid var(--bg-card-border);
            border-radius: 24px;
            padding: 2.25rem 2rem;
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.6), 0 0 30px -10px rgba(121, 40, 202, 0.3);
            display: none;
            flex-direction: column;
            justify-content: space-between;
            min-height: 560px;
            animation: fadeIn 0.3s cubic-bezier(0.16, 1, 0.3, 1);
        }}
        .slide.active {{
            display: flex;
        }}
        @keyframes fadeIn {{
            from {{ opacity: 0; transform: scale(0.97) translateY(8px); }}
            to {{ opacity: 1; transform: scale(1) translateY(0); }}
        }}
        /* Slide Header */
        .slide-header {{
            margin-bottom: 1.5rem;
        }}
        .pill-tag {{
            display: inline-block;
            font-size: 0.72rem;
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: 1.6px;
            color: var(--accent-cyan);
            background: rgba(0, 245, 212, 0.1);
            border: 1px solid rgba(0, 245, 212, 0.25);
            padding: 4px 10px;
            border-radius: 999px;
            margin-bottom: 0.75rem;
        }}
        .slide-title {{
            font-size: 1.85rem;
            font-weight: 800;
            letter-spacing: -0.5px;
            line-height: 1.2;
            color: #ffffff;
        }}
        .slide-subtitle {{
            font-size: 0.95rem;
            color: var(--text-muted);
            margin-top: 0.35rem;
        }}
        /* Big Stat Callout */
        .stat-giant {{
            text-align: center;
            margin: 1.25rem 0;
        }}
        .stat-giant-num {{
            font-size: 3.4rem;
            font-weight: 900;
            letter-spacing: -1.5px;
            line-height: 1;
            background: linear-gradient(135deg, #ffffff 0%, #cbd5e1 60%, var(--accent-blue) 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        .stat-giant-label {{
            font-size: 0.88rem;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 1.2px;
            margin-top: 0.4rem;
            font-weight: 600;
        }}
        /* Metrics Grid */
        .metrics-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 0.85rem;
            margin: 1rem 0;
        }}
        .metric-card {{
            background: rgba(255, 255, 255, 0.04);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 14px;
            padding: 0.9rem 1rem;
        }}
        .metric-val {{
            font-size: 1.35rem;
            font-weight: 800;
            color: #ffffff;
        }}
        .metric-lbl {{
            font-size: 0.75rem;
            color: var(--text-muted);
            margin-top: 2px;
            text-transform: uppercase;
            letter-spacing: 0.6px;
        }}
        /* Metaphor Box */
        .metaphor-box {{
            background: linear-gradient(135deg, rgba(121, 40, 202, 0.15), rgba(58, 134, 255, 0.15));
            border: 1px solid rgba(121, 40, 202, 0.3);
            border-radius: 14px;
            padding: 1rem 1.15rem;
            margin: 0.75rem 0;
            font-size: 0.9rem;
            line-height: 1.45;
            color: #e2e8f0;
        }}
        .metaphor-box strong {{
            color: var(--accent-cyan);
        }}
        /* Persona Slide */
        .persona-badge-wrap {{
            text-align: center;
            margin: 1.25rem 0 1rem;
        }}
        .persona-emoji {{
            font-size: 4rem;
            line-height: 1;
            filter: drop-shadow(0 0 20px rgba(157, 78, 221, 0.6));
        }}
        .persona-name {{
            font-size: 2rem;
            font-weight: 900;
            letter-spacing: -0.5px;
            margin-top: 0.5rem;
            background: linear-gradient(135deg, #ffbe0b 0%, #ff007f 70%, #9d4edd 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        .persona-tagline {{
            font-size: 0.95rem;
            color: var(--text-muted);
            font-style: italic;
            margin-top: 0.4rem;
            line-height: 1.4;
            max-width: 440px;
            margin-left: auto;
            margin-right: auto;
        }}
        /* Tag Bars */
        .tag-row {{
            margin-bottom: 0.85rem;
        }}
        .tag-meta {{
            display: flex;
            justify-content: space-between;
            font-size: 0.84rem;
            margin-bottom: 0.3rem;
        }}
        .tag-rank {{
            font-weight: 800;
            color: var(--accent-pink);
            margin-right: 6px;
        }}
        .tag-name {{
            font-weight: 700;
            color: #ffffff;
            flex: 1;
        }}
        .tag-count {{
            color: var(--text-muted);
            font-size: 0.78rem;
        }}
        .tag-bar-track {{
            height: 7px;
            background: rgba(255, 255, 255, 0.08);
            border-radius: 999px;
            overflow: hidden;
        }}
        .tag-bar-fill {{
            height: 100%;
            border-radius: 999px;
            background: linear-gradient(90deg, var(--accent-purple), var(--accent-cyan));
        }}
        .companions-box {{
            margin-top: 1rem;
            padding-top: 0.85rem;
            border-top: 1px solid rgba(255, 255, 255, 0.1);
        }}
        .companions-label {{
            font-size: 0.76rem;
            text-transform: uppercase;
            letter-spacing: 0.8px;
            color: var(--text-muted);
            display: block;
            margin-bottom: 0.4rem;
        }}
        .chips-wrap {{
            display: flex;
            flex-wrap: wrap;
            gap: 0.4rem;
        }}
        .chip {{
            background: rgba(255, 255, 255, 0.06);
            border: 1px solid rgba(255, 255, 255, 0.12);
            padding: 3px 9px;
            border-radius: 6px;
            font-size: 0.78rem;
            color: #cbd5e1;
        }}
        .chip em {{
            color: var(--accent-cyan);
            font-style: normal;
        }}
        /* Reactions Row */
        .rx-chips-row {{
            display: flex;
            gap: 0.5rem;
            flex-wrap: wrap;
            margin-top: 0.6rem;
        }}
        .rx-chip {{
            background: rgba(255, 255, 255, 0.06);
            border: 1px solid rgba(255, 255, 255, 0.12);
            border-radius: 999px;
            padding: 4px 12px;
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }}
        .rx-emoji {{
            font-size: 1.1rem;
        }}
        .rx-count {{
            font-size: 0.82rem;
            font-weight: 700;
            color: #ffffff;
        }}
        /* Highlight Cards */
        .highlight-card {{
            background: rgba(255, 255, 255, 0.04);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            padding: 0.95rem 1.1rem;
        }}
        .highlight-badge {{
            font-size: 0.76rem;
            font-weight: 800;
            color: var(--accent-amber);
            text-transform: uppercase;
            letter-spacing: 0.8px;
        }}
        .highlight-date {{
            font-size: 0.76rem;
            color: var(--text-faint);
            margin-top: 2px;
        }}
        .highlight-snippet {{
            font-size: 0.88rem;
            font-style: italic;
            color: #e2e8f0;
            line-height: 1.45;
            margin-top: 0.5rem;
        }}
        /* Footer Navigation Controls */
        .deck-footer {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-top: 1.25rem;
            width: 100%;
        }}
        .nav-btn {{
            background: rgba(255, 255, 255, 0.08);
            border: 1px solid rgba(255, 255, 255, 0.15);
            color: var(--text-main);
            padding: 0.6rem 1.2rem;
            border-radius: 999px;
            font-weight: 700;
            font-size: 0.88rem;
            cursor: pointer;
            transition: all 0.2s ease;
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }}
        .nav-btn:hover {{
            background: rgba(255, 255, 255, 0.18);
            transform: translateY(-1px);
        }}
        .nav-btn:disabled {{
            opacity: 0.3;
            cursor: not-allowed;
            transform: none;
        }}
        .slide-counter {{
            font-size: 0.82rem;
            color: var(--text-muted);
            font-weight: 600;
        }}
        /* Mode switch (Story vs All Cards) */
        .mode-toggle {{
            margin-top: 1rem;
            font-size: 0.8rem;
            color: var(--text-muted);
            cursor: pointer;
            text-decoration: underline;
            text-underline-offset: 3px;
            background: none;
            border: none;
        }}
        .mode-toggle:hover {{
            color: var(--text-main);
        }}
        /* Grid view class */
        .deck-container.grid-mode {{
            display: flex;
            flex-direction: column;
            gap: 1.5rem;
        }}
        .deck-container.grid-mode .slide {{
            display: flex !important;
            min-height: auto;
        }}
    </style>
</head>
<body>
    <div class="wrapped-wrapper">
        <!-- Story Progress Bars -->
        <div class="story-bars" id="storyBars">
            <div class="story-segment active" onclick="goToSlide(0)"></div>
            <div class="story-segment" onclick="goToSlide(1)"></div>
            <div class="story-segment" onclick="goToSlide(2)"></div>
            <div class="story-segment" onclick="goToSlide(3)"></div>
            <div class="story-segment" onclick="goToSlide(4)"></div>
            <div class="story-segment" onclick="goToSlide(5)"></div>
        </div>

        <!-- Slide Deck Container -->
        <div class="deck-container" id="deckContainer">
            <!-- SLIDE 1: Volume & Dedication -->
            <div class="slide active">
                <div class="slide-header">
                    <span class="pill-tag">Chapter 01 · Dedication</span>
                    <h2 class="slide-title">Your Year in Words</h2>
                    <p class="slide-subtitle">The thoughts and memories you committed to ink in {html.escape(data.period_label)}.</p>
                </div>
                
                <div class="stat-giant">
                    <div class="stat-giant-num">{data.total_words:,}</div>
                    <div class="stat-giant-label">Total Words Written</div>
                </div>

                <div class="metaphor-box">
                    That is equivalent to roughly <strong>{data.book_pages_equivalent:.1f} pages of a book</strong>, taking approximately <strong>{data.reading_time_minutes} minutes</strong> to read cover-to-cover.
                </div>

                <div class="metrics-grid">
                    <div class="metric-card">
                        <div class="metric-val">{data.total_messages:,}</div>
                        <div class="metric-lbl">Total Entries</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-val">{data.active_days}/{data.total_period_days}</div>
                        <div class="metric-lbl">Active Days ({data.active_days_pct}%)</div>
                    </div>
                </div>

                <div style="font-size: 0.8rem; color: var(--text-muted); text-align: center; margin-top: 0.5rem;">
                    Busiest reflection day: <strong>{html.escape(data.busiest_date)}</strong> ({data.busiest_date_count} entries)
                </div>
            </div>

            <!-- SLIDE 2: Cadence & Consistency -->
            <div class="slide">
                <div class="slide-header">
                    <span class="pill-tag">Chapter 02 · Rhythm</span>
                    <h2 class="slide-title">Streaks & Pauses</h2>
                    <p class="slide-subtitle">Finding your stride across months, weekdays, and seasons.</p>
                </div>

                <div class="stat-giant">
                    <div class="stat-giant-num">{data.longest_streak_days}</div>
                    <div class="stat-giant-label">Day Longest Consecutive Streak</div>
                </div>

                <div class="metrics-grid">
                    <div class="metric-card">
                        <div class="metric-val">{html.escape(data.busiest_month)}</div>
                        <div class="metric-lbl">Prime Month ({data.busiest_month_count} msgs)</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-val">{html.escape(data.favorite_day_of_week)}</div>
                        <div class="metric-lbl">Favorite Weekday ({data.favorite_day_count} msgs)</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-val">{data.avg_words_per_message:.0f} words</div>
                        <div class="metric-lbl">Avg Words / Entry</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-val">{data.longest_gap_days} days</div>
                        <div class="metric-lbl">Longest Hiatus</div>
                    </div>
                </div>

                <div class="metaphor-box">
                    {"Your longest uninterrupted streak ran from <strong>" + html.escape(data.longest_streak_start) + "</strong> to <strong>" + html.escape(data.longest_streak_end) + "</strong>." if data.longest_streak_days > 1 else "Every single entry was a thoughtful, deliberate milestone."}
                </div>
            </div>

            <!-- SLIDE 3: Circadian Persona -->
            <div class="slide">
                <div class="slide-header">
                    <span class="pill-tag">Chapter 03 · Alter-Ego</span>
                    <h2 class="slide-title">Your Journaling Persona</h2>
                    <p class="slide-subtitle">When your mind is most alive to reflect and write.</p>
                </div>

                <div class="persona-badge-wrap">
                    <div class="persona-emoji">{p.emoji}</div>
                    <div class="persona-name">{html.escape(p.name)}</div>
                    <div class="persona-tagline">"{html.escape(p.tagline)}"</div>
                </div>

                <div class="metrics-grid">
                    <div class="metric-card">
                        <div class="metric-val">{html.escape(p.peak_hour_formatted)}</div>
                        <div class="metric-lbl">Peak Hour</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-val">{p.night_owl_pct}%</div>
                        <div class="metric-lbl">Night Owl Share</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-val">{p.morning_pct}%</div>
                        <div class="metric-lbl">Dawn Share</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-val">{html.escape(p.peak_day)}</div>
                        <div class="metric-lbl">Peak Rhythm Day</div>
                    </div>
                </div>
            </div>

            <!-- SLIDE 4: Top Fixations & Tag Eras -->
            <div class="slide">
                <div class="slide-header">
                    <span class="pill-tag">Chapter 04 · Fixations</span>
                    <h2 class="slide-title">Top Topics & Eras</h2>
                    <p class="slide-subtitle">The passions, hobbies, and ideas that took center stage.</p>
                </div>

                <div class="tag-bars-container">
                    {"".join(tag_bars_html)}
                </div>

                {companion_html}
            </div>

            <!-- SLIDE 5: Expressiveness & Reactions -->
            <div class="slide">
                <div class="slide-header">
                    <span class="pill-tag">Chapter 05 · Resonance</span>
                    <h2 class="slide-title">Expressiveness & Media</h2>
                    <p class="slide-subtitle">Capturing moments with imagery, reactions, and follow-ups.</p>
                </div>

                <div class="stat-giant">
                    <div class="stat-giant-num">{data.total_reactions:,}</div>
                    <div class="stat-giant-label">Total Reactions Recorded</div>
                </div>

                {reactions_html}

                <div class="metrics-grid" style="margin-top: 1.25rem;">
                    <div class="metric-card">
                        <div class="metric-val">{data.photo_count} photos</div>
                        <div class="metric-lbl">Visual Snaps</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-val">{data.self_reply_count} threads</div>
                        <div class="metric-lbl">Thought Continuations</div>
                    </div>
                </div>

                <div class="metaphor-box">
                    You replied to your past entries <strong>{data.self_reply_count} times</strong>, keeping ongoing conversations alive with your past thoughts.
                </div>
            </div>

            <!-- SLIDE 6: The Magnum Opus & Standouts -->
            <div class="slide">
                <div class="slide-header">
                    <span class="pill-tag">Chapter 06 · Milestones</span>
                    <h2 class="slide-title">Standout Memories</h2>
                    <p class="slide-subtitle">The reflections that defined {html.escape(data.period_label)}.</p>
                </div>

                {magnum_html}
                {most_reacted_html}

                <div style="text-align: center; margin-top: 1.2rem; font-size: 0.82rem; color: var(--text-muted);">
                    Generated with <strong>Telegram Journal Analytics</strong> · Privacy First & Offline
                </div>
            </div>
        </div>

        <!-- Navigation Footer -->
        <div class="deck-footer" id="deckFooter">
            <button class="nav-btn" id="prevBtn" onclick="prevSlide()" disabled>← Prev</button>
            <span class="slide-counter" id="slideCounter">1 / 6</span>
            <button class="nav-btn" id="nextBtn" onclick="nextSlide()">Next →</button>
        </div>

        <!-- View Mode Switch -->
        <button class="mode-toggle" id="modeToggle" onclick="toggleViewMode()">Switch to Scrollable Deck Mode</button>
    </div>

    <script>
        let currentSlide = 0;
        const totalSlides = 6;
        const slides = document.querySelectorAll('.slide');
        const segments = document.querySelectorAll('.story-segment');
        const prevBtn = document.getElementById('prevBtn');
        const nextBtn = document.getElementById('nextBtn');
        const counter = document.getElementById('slideCounter');
        const deckContainer = document.getElementById('deckContainer');
        const deckFooter = document.getElementById('deckFooter');
        const storyBars = document.getElementById('storyBars');
        const modeToggle = document.getElementById('modeToggle');
        let isGridMode = false;

        function updateSlide() {{
            slides.forEach((s, idx) => {{
                s.classList.toggle('active', idx === currentSlide);
            }});
            segments.forEach((seg, idx) => {{
                seg.classList.remove('active', 'seen');
                if (idx === currentSlide) {{
                    seg.classList.add('active');
                }} else if (idx < currentSlide) {{
                    seg.classList.add('seen');
                }}
            }});
            counter.innerText = (currentSlide + 1) + " / " + totalSlides;
            prevBtn.disabled = (currentSlide === 0);
            nextBtn.disabled = (currentSlide === totalSlides - 1);
        }}

        function nextSlide() {{
            if (currentSlide < totalSlides - 1) {{
                currentSlide++;
                updateSlide();
            }}
        }}

        function prevSlide() {{
            if (currentSlide > 0) {{
                currentSlide--;
                updateSlide();
            }}
        }}

        function goToSlide(n) {{
            if (n >= 0 && n < totalSlides) {{
                currentSlide = n;
                updateSlide();
            }}
        }}

        function toggleViewMode() {{
            isGridMode = !isGridMode;
            deckContainer.classList.toggle('grid-mode', isGridMode);
            deckFooter.style.display = isGridMode ? 'none' : 'flex';
            storyBars.style.display = isGridMode ? 'none' : 'flex';
            modeToggle.innerText = isGridMode ? 'Switch to Story Card Mode' : 'Switch to Scrollable Deck Mode';
        }}

        // Keyboard navigation
        document.addEventListener('keydown', (e) => {{
            if (isGridMode) return;
            if (e.key === 'ArrowRight' || e.key === ' ') {{
                nextSlide();
            }} else if (e.key === 'ArrowLeft') {{
                prevSlide();
            }}
        }});
    </script>
</body>
</html>
"""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    return output_path
