"""
On This Day (OTD) Module.

Surfaces journal memories and thoughts posted on the same calendar day across past years.
Includes multi-year aggregation, fuzzy date windowing, random memory discovery,
and interactive HTML memory card generation.
"""

from __future__ import annotations

import html
import random
from dataclasses import dataclass
from datetime import datetime, date
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from src.lifecycle import TAG_PALETTE


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

    # Try standard ISO formats
    for fmt in ("%Y-%m-%d", "%m-%d", "%d/%m", "%m/%d", "%B %d", "%b %d", "%d %B", "%d %b"):
        try:
            dt = datetime.strptime(s, fmt)
            return dt.month, dt.day
        except ValueError:
            pass

    # Try splitting by - or /
    parts = [p for p in s.replace("/", "-").split("-") if p]
    if len(parts) >= 2:
        try:
            # If 3 parts (YYYY-MM-DD), take parts 1 and 2
            if len(parts) == 3 and len(parts[0]) == 4:
                return int(parts[1]), int(parts[2])
            # If 2 parts, assume MM-DD
            m, d = int(parts[0]), int(parts[1])
            if 1 <= m <= 12 and 1 <= d <= 31:
                return m, d
            # Maybe DD-MM
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
        # Invalid calendar date
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

    # Filter by calendar date or window
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
                tags_list = list(row["tags"]) if isinstance(row["tags"], (list, tuple)) else []
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


def generate_otd_html(
    result: OTDResult,
    output_path: Path | str,
) -> Path:
    """
    Generate an interactive, standalone HTML card showcasing past memories for this day.
    """
    out_file = Path(output_path).expanduser().resolve()
    out_file.parent.mkdir(parents=True, exist_ok=True)

    tag_to_color = {t: TAG_PALETTE[i % len(TAG_PALETTE)] for i, t in enumerate(result.all_tags)}

    year_cards_html = []
    for g in result.year_groups:
        tag_badges = "".join(
            [
                f"<span class='tag-pill' style='background:{tag_to_color.get(t, '#444')};'>#{t} ({cnt})</span>"
                for t, cnt in g.tags_summary
            ]
        )

        entries_html = []
        for e in g.entries:
            text_clean = e.text.strip()
            highlighted_text = html.escape(text_clean)
            for t in e.tags:
                escaped_tag = html.escape(f"[{t}]")
                c = tag_to_color.get(t, "#4A5568")
                badge = f"<span class='entry-tag' style='background:{c};'>[{html.escape(t)}]</span>"
                highlighted_text = highlighted_text.replace(escaped_tag, badge)

            highlighted_text = highlighted_text.replace("\r\n", "\n")
            while "\n\n\n" in highlighted_text:
                highlighted_text = highlighted_text.replace("\n\n\n", "\n\n")
            highlighted_text = highlighted_text.replace("\n", "<br>")
            time_icon = "🌙" if e.timestamp.hour >= 22 or e.timestamp.hour < 5 else "☀️"

            entries_html.append(
                f"""
                <div class="message-card">
                    <div class="message-meta">
                        <span class="time-badge">{time_icon} {e.time_str}</span>
                        {f"<span class='media-badge'>📷 photo</span>" if e.has_photo else ""}
                    </div>
                    <div class="message-body">
                        {highlighted_text if highlighted_text else "<i>(media attachment)</i>"}
                    </div>
                </div>
                """
            )

        year_cards_html.append(
            f"""
            <div class="year-section">
                <div class="year-header">
                    <div class="year-title-row">
                        <span class="year-title">{g.label}</span>
                        <span class="year-stats-badge">{g.total_messages} messages</span>
                    </div>
                    {f"<div class='year-summary-row'><div class='tag-badges-container'>{tag_badges}</div></div>" if tag_badges else ""}
                </div>
                <div class="messages-container">
                    {"".join(entries_html)}
                </div>
            </div>
            """
        )

    content_body = "".join(year_cards_html) if year_cards_html else """
    <div class="empty-state">
        <div class="empty-icon">🍃</div>
        <h2>No memories found for this calendar day</h2>
        <p>Try expanding the day window (e.g. <code>--window 2</code>) or query a different date.</p>
    </div>
    """

    total_years_active = len(result.year_groups)

    html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>On This Day: {result.date_title}</title>
    <style>
        :root {{
            --bg-color: #0d1117;
            --surface-color: #161b22;
            --surface-border: #30363d;
            --text-primary: #f0f6fc;
            --text-secondary: #8b949e;
            --accent-blue: #58a6ff;
            --accent-green: #3fb950;
            --accent-orange: #d29922;
        }}
        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background-color: var(--bg-color);
            color: var(--text-primary);
            padding: 1.5rem 1rem;
            line-height: 1.45;
        }}
        .container {{
            max-width: 900px;
            margin: 0 auto;
        }}
        header {{
            text-align: center;
            margin-bottom: 1.5rem;
            padding-bottom: 1rem;
            border-bottom: 1px solid var(--surface-border);
        }}
        .super-title {{
            font-size: 0.8rem;
            text-transform: uppercase;
            letter-spacing: 1.5px;
            color: var(--accent-blue);
            font-weight: 700;
            margin-bottom: 0.25rem;
        }}
        h1 {{
            font-size: 1.85rem;
            font-weight: 800;
            letter-spacing: -0.5px;
            color: #ffffff;
            margin-bottom: 0.35rem;
        }}
        .subtitle {{
            color: var(--text-secondary);
            font-size: 0.92rem;
        }}
        .overview-stats {{
            display: flex;
            justify-content: center;
            gap: 1.2rem;
            margin-top: 1rem;
            flex-wrap: wrap;
        }}
        .stat-box {{
            background: var(--surface-color);
            border: 1px solid var(--surface-border);
            border-radius: 6px;
            padding: 0.4rem 1.2rem;
            text-align: center;
            min-width: 110px;
        }}
        .stat-value {{
            font-size: 1.3rem;
            font-weight: 700;
            color: #ffffff;
        }}
        .stat-label {{
            font-size: 0.72rem;
            text-transform: uppercase;
            color: var(--text-secondary);
            letter-spacing: 0.8px;
        }}
        .year-section {{
            background: var(--surface-color);
            border: 1px solid var(--surface-border);
            border-radius: 10px;
            margin-bottom: 1.25rem;
            overflow: hidden;
            box-shadow: 0 3px 12px rgba(0, 0, 0, 0.2);
        }}
        .year-header {{
            padding: 0.7rem 1.1rem;
            background: rgba(255, 255, 255, 0.02);
            border-bottom: 1px solid var(--surface-border);
        }}
        .year-title-row {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 0.35rem;
        }}
        .year-title {{
            font-size: 1.15rem;
            font-weight: 700;
            color: #ffffff;
        }}
        .year-stats-badge {{
            font-size: 0.78rem;
            color: var(--text-secondary);
            background: rgba(255, 255, 255, 0.05);
            padding: 0.2rem 0.55rem;
            border-radius: 16px;
        }}
        .year-summary-row {{
            display: flex;
            align-items: center;
            flex-wrap: wrap;
            gap: 0.4rem;
        }}
        .tag-pill {{
            display: inline-block;
            color: #ffffff;
            font-size: 0.72rem;
            font-weight: 600;
            padding: 0.15rem 0.45rem;
            border-radius: 10px;
            margin-right: 0.3rem;
            margin-bottom: 0.2rem;
        }}
        .messages-container {{
            padding: 0.7rem 1.1rem;
            display: flex;
            flex-direction: column;
            gap: 0.45rem;
        }}
        .message-card {{
            background: rgba(255, 255, 255, 0.025);
            border-left: 3px solid var(--accent-blue);
            border-radius: 0 6px 6px 0;
            padding: 0.55rem 0.85rem;
            transition: background 0.15s ease;
        }}
        .message-card:hover {{
            background: rgba(255, 255, 255, 0.045);
        }}
        .message-meta {{
            display: flex;
            align-items: center;
            gap: 0.6rem;
            font-size: 0.75rem;
            color: var(--text-secondary);
            margin-bottom: 0.25rem;
        }}
        .time-badge {{
            font-weight: 600;
            color: #ffffff;
        }}
        .media-badge {{
            color: var(--accent-orange);
            font-weight: 600;
        }}
        .message-body {{
            font-size: 0.92rem;
            line-height: 1.45;
            color: #e6edf3;
            word-break: break-word;
        }}
        .entry-tag {{
            display: inline-block;
            font-size: 0.78rem;
            font-weight: 600;
            color: #ffffff;
            padding: 0.08rem 0.4rem;
            border-radius: 4px;
            margin: 0 0.15rem;
        }}
        .empty-state {{
            text-align: center;
            padding: 3rem 1.5rem;
            background: var(--surface-color);
            border: 1px dashed var(--surface-border);
            border-radius: 10px;
        }}
        .empty-icon {{
            font-size: 2.5rem;
            margin-bottom: 0.75rem;
        }}
        footer {{
            text-align: center;
            margin-top: 2rem;
            padding-bottom: 1rem;
            color: var(--text-secondary);
            font-size: 0.78rem;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="super-title">Telegram Journal Time Capsule</div>
            <h1>On This Day: {result.date_title}</h1>
            <div class="subtitle">Looking back across past years of thoughts, fixations, and daily life</div>
            <div class="overview-stats">
                <div class="stat-box">
                    <div class="stat-value">{result.total_matches}</div>
                    <div class="stat-label">Total Messages</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value">{total_years_active}</div>
                    <div class="stat-label">Years Recorded</div>
                </div>
            </div>
        </header>

        <main>
            {content_body}
        </main>

        <footer>
            Generated by <b>Telegram Journal Analytics</b> · Decoupled universal parser
        </footer>
    </div>
</body>
</html>
"""

    with open(out_file, "w", encoding="utf-8") as f:
        f.write(html_template)

    return out_file
