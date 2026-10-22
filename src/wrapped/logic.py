"""
Channel-Wrapped Retrospective - Pure Domain Logic.

Computes annual and all-time retrospective metrics:
  - Total volume, word counts, reading metaphors, active day consistency
  - Longest active streaks and hiatus intervals
  - Circadian persona classification
  - Top fixations, companion tags, and reaction expressiveness
  - The Magnum Opus (longest reflection) and standout moments
Zero dependencies on plotting libraries, terminal styling, or HTML templates.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime, date
from itertools import combinations
import math
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
    top_tags: List[Tuple[str, int, float]]
    top_tag_pairs: List[Tuple[str, str, int]]
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

    unique_dates = sorted(pd.to_datetime(df["date"]).dt.date.unique())
    if not unique_dates:
        return 0, "", "", 0, "", ""

    # 1. Longest streak
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

    # 2. Longest gap
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

    if start_date and unique_dates[0] > start_date:
        initial_gap = (unique_dates[0] - start_date).days
        if initial_gap > longest_gap:
            longest_gap = initial_gap
            best_gap_start = start_date
            best_gap_end = unique_dates[0]

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

    reading_time_minutes = int(math.ceil(total_words / 220)) if total_words else 0
    book_pages_equivalent = round(total_words / 275, 1) if total_words else 0.0

    unique_active_days = period_df["date"].nunique() if total_messages else 0
    active_days_pct = (
        round((unique_active_days / total_period_days) * 100, 1) if total_period_days else 0.0
    )

    if total_messages:
        daily_counts = period_df.groupby("date").size()
        busiest_date_raw = str(daily_counts.idxmax())
        busiest_date = datetime.strptime(busiest_date_raw, "%Y-%m-%d").strftime("%B %d, %Y")
        busiest_date_count = int(daily_counts.max())
    else:
        busiest_date = "N/A"
        busiest_date_count = 0

    if total_messages:
        month_series = pd.to_datetime(period_df["timestamp"]).dt.strftime("%B")
        month_counts = month_series.value_counts()
        busiest_month = str(month_counts.idxmax())
        busiest_month_count = int(month_counts.max())
    else:
        busiest_month = "N/A"
        busiest_month_count = 0

    if total_messages:
        day_counts = period_df["day_name"].value_counts()
        favorite_day = str(day_counts.idxmax())
        favorite_day_count = int(day_counts.max())
    else:
        favorite_day = "N/A"
        favorite_day_count = 0

    (
        longest_streak,
        streak_start,
        streak_end,
        longest_gap,
        gap_start,
        gap_end,
    ) = compute_streaks(period_df, cal_start, cal_end)

    persona = determine_persona(period_df)

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

    era_tag: Optional[str] = None
    if top_tags:
        era_tag = top_tags[0][0]

    total_reactions = int(period_df["total_reactions"].sum()) if "total_reactions" in period_df else 0
    emoji_counter: Counter = Counter()
    for rx_dict in period_df.get("reactions", []):
        if isinstance(rx_dict, dict):
            for emoji_char, count in rx_dict.items():
                if count is not None:
                    try:
                        c_int = int(count)
                        if c_int > 0:
                            emoji_counter[emoji_char] += c_int
                    except (ValueError, TypeError):
                        pass

    top_reactions: List[Tuple[str, int]] = emoji_counter.most_common(5)

    photo_count = int(period_df["has_photo"].sum()) if "has_photo" in period_df else 0
    media_count = int(period_df["has_media"].sum()) if "has_media" in period_df else 0

    self_replies = 0
    if "reply_to_id" in period_df:
        self_replies = int(period_df["reply_to_id"].notna().sum() - (period_df["reply_to_id"] == 0).sum())
        self_replies = max(0, self_replies)

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
            raw_rx = reacted_row.get("reactions", {})
            most_reacted_reactions = {
                str(k): int(v)
                for k, v in raw_rx.items()
                if v is not None and int(v) > 0
            } if isinstance(raw_rx, dict) else {}
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
