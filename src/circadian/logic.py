"""
Circadian & Habit Profiling - Pure Domain Logic.

Computes 24-hour message distribution, peak reflection hours, night-owl metrics,
and longitudinal circadian statistics from parsed journal data.
Zero dependencies on plotting libraries or HTML templates.
"""

from __future__ import annotations

from typing import Any, Dict
import pandas as pd


DAYS_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def compute_circadian_metrics(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Compute high-level circadian and temporal habit metrics from raw journal messages.
    """
    total_messages = len(df)
    hour_counts = df["hour"].value_counts().sort_index()
    peak_hour = int(hour_counts.idxmax()) if not hour_counts.empty else 0
    peak_hour_count = int(hour_counts.max()) if not hour_counts.empty else 0

    day_counts = df["day_name"].value_counts().reindex(DAYS_ORDER, fill_value=0)
    peak_day = str(day_counts.idxmax()) if not day_counts.empty else "Monday"
    peak_day_count = int(day_counts.max()) if not day_counts.empty else 0

    # Night owl index: messages between 22:00 (10 PM) and 04:00 (4 AM)
    night_owl_mask = (df["hour"] >= 22) | (df["hour"] < 4)
    night_owl_count = int(night_owl_mask.sum())
    night_owl_pct = (night_owl_count / total_messages * 100) if total_messages else 0.0

    # Early morning index: 05:00 to 09:00
    morning_mask = (df["hour"] >= 5) & (df["hour"] < 9)
    morning_count = int(morning_mask.sum())
    morning_pct = (morning_count / total_messages * 100) if total_messages else 0.0

    # Busiest single calendar day
    daily_counts = df.groupby("date").size()
    busiest_date = str(daily_counts.idxmax()) if not daily_counts.empty else "N/A"
    busiest_date_count = int(daily_counts.max()) if not daily_counts.empty else 0

    # Dynamic date span
    if not df.empty and "timestamp" in df.columns:
        min_dt = df["timestamp"].min()
        max_dt = df["timestamp"].max()
        start_date = min_dt.strftime("%Y-%m-%d")
        end_date = max_dt.strftime("%Y-%m-%d")
        date_span = f"{min_dt.strftime('%b %Y')} – {max_dt.strftime('%b %Y')}"
    else:
        start_date = ""
        end_date = ""
        date_span = ""

    return {
        "total_messages": total_messages,
        "peak_hour": peak_hour,
        "peak_hour_count": peak_hour_count,
        "peak_day": peak_day,
        "peak_day_count": peak_day_count,
        "night_owl_count": night_owl_count,
        "night_owl_pct": round(night_owl_pct, 1),
        "morning_count": morning_count,
        "morning_pct": round(morning_pct, 1),
        "busiest_date": busiest_date,
        "busiest_date_count": busiest_date_count,
        "start_date": start_date,
        "end_date": end_date,
        "date_span": date_span,
    }
