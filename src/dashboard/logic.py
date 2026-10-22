"""
Unified Master Dashboard - Pure Domain Logic.

Aggregates analytical results across Circadian, Lifecycle, Wrapped, and
On-This-Day modules into a unified dashboard data container.
Zero dependencies on plotting libraries or HTML templates.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from src.circadian.logic import compute_circadian_metrics
from src.lifecycle.logic import compute_tag_lifecycles
from src.wrapped.logic import compute_wrapped, WrappedData
from src.otd.logic import parse_query_date, query_on_this_day, get_random_active_day, OTDResult


@dataclass
class DashboardData:
    """Master data container for the unified journal intelligence dashboard."""
    date_span: str
    total_messages: int
    total_words: int
    total_chars: int
    book_pages: float
    reading_time_mins: int
    active_days: int
    active_days_pct: float
    longest_streak_days: int
    circadian_metrics: Dict[str, Any]
    tag_stats_df: pd.DataFrame
    monthly_counts: pd.DataFrame
    lifecycle_summary: Dict[str, Any]
    evergreen_records: List[Dict[str, Any]]
    burst_records: List[Dict[str, Any]]
    emerging_records: List[Dict[str, Any]]
    wrapped_data: WrappedData
    otd_result: OTDResult
    is_otd_fallback: bool


def build_dashboard_context(
    df: pd.DataFrame,
    year: Optional[int] = None,
    otd_date: Optional[str] = None,
    window_days: int = 0,
    min_tag_count: int = 5,
) -> DashboardData:
    """
    Execute analytics pipelines across all feature domains and compile a unified DashboardData instance.
    """
    # 1. Circadian Analytics
    circadian_metrics = compute_circadian_metrics(df)

    # 2. Tag & Hobby Lifecycles
    tag_stats_df, monthly_counts = compute_tag_lifecycles(df, min_count=min_tag_count)

    evergreens = []
    bursts = []
    emerging = []
    evergreen_records = []
    burst_records = []
    emerging_records = []
    top_tag = "None"
    top_tag_count = 0

    if not tag_stats_df.empty:
        evergreens = tag_stats_df[tag_stats_df["category"] == "Evergreen Passion"]["tag"].tolist()
        bursts = tag_stats_df[tag_stats_df["category"] == "Seasonal Burst"]["tag"].tolist()
        emerging = tag_stats_df[tag_stats_df["category"] == "Emerging Era"]["tag"].tolist()

        evergreen_records = (
            tag_stats_df[tag_stats_df["category"] == "Evergreen Passion"]
            .sort_values("total_count", ascending=False)
            .to_dict(orient="records")
        )
        burst_records = (
            tag_stats_df[tag_stats_df["category"] == "Seasonal Burst"]
            .sort_values("total_count", ascending=False)
            .to_dict(orient="records")
        )
        emerging_records = (
            tag_stats_df[tag_stats_df["category"] == "Emerging Era"]
            .sort_values("total_count", ascending=False)
            .to_dict(orient="records")
        )

        top_row = tag_stats_df.sort_values("total_count", ascending=False).iloc[0]
        top_tag = top_row["tag"]
        top_tag_count = int(top_row["total_count"])

    lifecycle_summary = {
        "total_tags_analyzed": len(tag_stats_df),
        "evergreens": evergreens,
        "bursts": bursts,
        "emerging": emerging,
        "top_tag": top_tag,
        "top_tag_count": top_tag_count,
    }

    # 3. Channel-Wrapped Retrospective
    wrapped_data = compute_wrapped(df, year=year)

    # 4. On This Day Time Capsule
    is_otd_fallback = False
    if otd_date:
        otd_month, otd_day = parse_query_date(otd_date)
        otd_result = query_on_this_day(df, otd_month, otd_day, window_days=window_days)
    else:
        today_dt = date.today()
        otd_result = query_on_this_day(df, today_dt.month, today_dt.day, window_days=window_days)
        # If no entries on today's calendar date, pick a random active memory anchor
        if otd_result.total_matches == 0 and not df.empty:
            rnd_m, rnd_d = get_random_active_day(df, min_msgs=2)
            otd_result = query_on_this_day(df, rnd_m, rnd_d, window_days=window_days)
            is_otd_fallback = True

    # High-level date span & volume KPIs
    date_span = circadian_metrics.get("date_span", "")
    total_messages = circadian_metrics.get("total_messages", len(df))
    total_words = wrapped_data.total_words
    total_chars = wrapped_data.total_chars
    book_pages = wrapped_data.book_pages_equivalent
    reading_time_mins = wrapped_data.reading_time_minutes
    active_days = wrapped_data.active_days
    active_days_pct = wrapped_data.active_days_pct
    longest_streak_days = wrapped_data.longest_streak_days

    return DashboardData(
        date_span=date_span,
        total_messages=total_messages,
        total_words=total_words,
        total_chars=total_chars,
        book_pages=book_pages,
        reading_time_mins=reading_time_mins,
        active_days=active_days,
        active_days_pct=active_days_pct,
        longest_streak_days=longest_streak_days,
        circadian_metrics=circadian_metrics,
        tag_stats_df=tag_stats_df,
        monthly_counts=monthly_counts,
        lifecycle_summary=lifecycle_summary,
        evergreen_records=evergreen_records,
        burst_records=burst_records,
        emerging_records=emerging_records,
        wrapped_data=wrapped_data,
        otd_result=otd_result,
        is_otd_fallback=is_otd_fallback,
    )
