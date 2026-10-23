"""
On This Day (OTD) - Pure Domain Logic.

Surfaces journal memories and reflections posted on matching calendar days across all recorded years.
Includes multi-year aggregation, date range windowing, and random memory discovery.
Zero dependencies on HTML templates or CSS rendering.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, date
import random
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd


@dataclass
class OTDEntry:
    """Represents an individual journal entry on this day."""
    id: int
    timestamp: datetime
    time_str: str
    date_str: str
    year: int
    text: str
    word_count: int
    tags: List[str]
    reactions: Dict[str, int]
    total_reactions: int
    has_photo: bool
    has_media: bool


@dataclass
class OTDYearGroup:
    """Summary of memories from a specific past year."""
    year: int
    years_ago: int
    label: str
    entries: List[OTDEntry]
    total_messages: int
    total_words: int
    tags_summary: List[Tuple[str, int]]
    top_reactions: List[Tuple[str, int]]
    first_time: Optional[str]
    last_time: Optional[str]


@dataclass
class OTDResult:
    """Complete result container for an On This Day query."""
    target_month: int
    target_day: int
    date_title: str
    window_days: int
    total_matches: int
    year_groups: List[OTDYearGroup]
    all_tags: List[str]


def parse_query_date(date_str: Optional[str] = None) -> Tuple[int, int]:
    """
    Parse a user-supplied date string into (month, day).
    Supports:
      - None or 'today': today's date
      - 'yesterday': yesterday's date
      - 'YYYY-MM-DD' or 'MM-DD' or 'DD/MM' or 'Month Day' (e.g. 'Sep 15')
    """
    today = date.today()
    if date_str is None or date_str.strip().lower() in ("today", "now"):
        return today.month, today.day

    s = date_str.strip().lower()
    if s == "yesterday":
        yest = date.fromordinal(today.toordinal() - 1)
        return yest.month, yest.day

    for fmt in ("%Y-%m-%d", "%m-%d", "%d/%m", "%m/%d", "%B %d", "%b %d", "%d %B", "%d %b"):
        try:
            dt = datetime.strptime(s, fmt)
            return dt.month, dt.day
        except ValueError:
            pass

    parts = [p for p in s.replace("/", "-").split("-") if p]
    if len(parts) >= 2:
        try:
            if len(parts) == 3 and len(parts[0]) == 4:
                return int(parts[1]), int(parts[2])
            m, d = int(parts[0]), int(parts[1])
            if 1 <= m <= 12 and 1 <= d <= 31:
                return m, d
            if 1 <= d <= 12 and 1 <= m <= 31:
                return d, m
        except ValueError:
            pass

    raise ValueError(f"Could not parse date format: '{date_str}'. Try 'MM-DD', 'YYYY-MM-DD', or 'Month Day'.")


def query_on_this_day(
    df: pd.DataFrame,
    month: int,
    day: int,
    window_days: int = 0,
    reference_year: Optional[int] = None,
) -> OTDResult:
    """
    Filter dataframe for entries matching month and day across all years,
    optionally including a window of +/- window_days around the date.
    """
    try:
        date_title = datetime(2024, month, day).strftime("%B %d")
    except ValueError:
        date_title = f"{month:02d}-{day:02d}"
        return OTDResult(
            target_month=month,
            target_day=day,
            date_title=date_title,
            window_days=window_days,
            total_matches=0,
            year_groups=[],
            all_tags=[],
        )

    if df.empty:
        return OTDResult(
            target_month=month,
            target_day=day,
            date_title=date_title,
            window_days=window_days,
            total_matches=0,
            year_groups=[],
            all_tags=[],
        )

    ref_year = reference_year or datetime.now().year

    if window_days <= 0:
        mask = (df["month"] == month) & (df["day"] == day)
    else:
        target_ref_dt = datetime(2024, month, min(day, 28 if month == 2 else 30 if month in (4, 6, 9, 11) else 31))

        def is_within_window(ts: pd.Timestamp) -> bool:
            safe_day = min(ts.day, 28 if ts.month == 2 else 30 if ts.month in (4, 6, 9, 11) else 31)
            ts_ref = datetime(2024, ts.month, safe_day)
            diff = abs((ts_ref - target_ref_dt).days)
            return diff <= window_days or abs(diff - 365) <= window_days

        mask = df["timestamp"].apply(is_within_window)

    filtered = df[mask].sort_values("timestamp").reset_index(drop=True)

    if window_days > 0:
        date_title += f" (±{window_days}d window)"

    year_groups: List[OTDYearGroup] = []
    all_tags_set = set()

    if not filtered.empty:
        for yr, group in filtered.groupby("year", sort=True):
            years_ago = ref_year - int(yr)
            today_dt = date.today()
            is_actually_today = (month == today_dt.month and day == today_dt.day)
            if years_ago == 0:
                label = f"Today ({yr})" if is_actually_today else f"This Year ({yr})"
            elif years_ago == 1:
                label = f"1 Year Ago ({yr})"
            else:
                label = f"{years_ago} Years Ago ({yr})"

            entries: List[OTDEntry] = []
            yr_reactions: Dict[str, int] = {}
            yr_tags: Dict[str, int] = {}

            for _, row in group.iterrows():
                ts = row["timestamp"]
                t_str = ts.strftime("%I:%M %p").lstrip("0")
                d_str = ts.strftime("%A, %d %B %Y")
                tags_list = list(row["tags"]) if hasattr(row["tags"], "__iter__") and not isinstance(row["tags"], (str, bytes)) else []
                raw_reactions = dict(row["reactions"]) if isinstance(row["reactions"], dict) else {}

                clean_reactions: Dict[str, int] = {}
                for r, c in raw_reactions.items():
                    val = 1 if c is None or pd.isna(c) else int(c)
                    clean_reactions[r] = val
                    yr_reactions[r] = yr_reactions.get(r, 0) + val

                for t in tags_list:
                    yr_tags[t] = yr_tags.get(t, 0) + 1
                    all_tags_set.add(t)

                entries.append(
                    OTDEntry(
                        id=int(row["id"]) if pd.notna(row["id"]) else 0,
                        timestamp=ts,
                        time_str=t_str,
                        date_str=d_str,
                        year=int(yr),
                        text=str(row["text"]) if pd.notna(row["text"]) else "",
                        word_count=int(row["word_count"]) if pd.notna(row["word_count"]) else 0,
                        tags=tags_list,
                        reactions=clean_reactions,
                        total_reactions=sum(clean_reactions.values()),
                        has_photo=bool(row.get("has_photo", False)),
                        has_media=bool(row.get("has_media", False)),
                    )
                )

            entries.sort(key=lambda e: e.timestamp)

            sorted_tags = sorted(yr_tags.items(), key=lambda x: x[1], reverse=True)
            sorted_reactions = sorted(yr_reactions.items(), key=lambda x: x[1], reverse=True)

            first_time = entries[0].time_str if entries else None
            last_time = entries[-1].time_str if entries else None

            year_groups.append(
                OTDYearGroup(
                    year=int(yr),
                    years_ago=years_ago,
                    label=label,
                    entries=entries,
                    total_messages=len(entries),
                    total_words=sum(e.word_count for e in entries),
                    tags_summary=sorted_tags,
                    top_reactions=sorted_reactions,
                    first_time=first_time,
                    last_time=last_time,
                )
            )

    year_groups.sort(key=lambda g: g.year, reverse=True)

    return OTDResult(
        target_month=month,
        target_day=day,
        date_title=date_title,
        window_days=window_days,
        total_matches=len(filtered),
        year_groups=year_groups,
        all_tags=sorted(all_tags_set),
    )


def get_random_active_day(df: pd.DataFrame, min_msgs: int = 3) -> Tuple[int, int]:
    """
    Select a random (month, day) that has at least min_msgs across past years.
    """
    if df.empty:
        return 9, 15

    day_counts = df.groupby(["month", "day"]).size()
    valid_days = day_counts[day_counts >= min_msgs].index.tolist()

    if not valid_days:
        valid_days = day_counts.index.tolist()

    choice = random.choice(valid_days)
    return int(choice[0]), int(choice[1])
