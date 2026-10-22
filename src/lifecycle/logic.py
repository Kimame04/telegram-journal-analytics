"""
Tag & Hobby Lifecycles - Pure Domain Logic.

Computes monthly topic frequencies, active spans, peak eras,
and classifies interests into lifespans:
  - 🌟 Evergreen Passions (>12 months continuous)
  - ⚡ Seasonal Bursts (1-4 months hyperfixations)
  - 🌱 Emerging Eras (recent active habits)
Zero dependencies on plotting libraries or HTML templates.
"""

from __future__ import annotations

from datetime import datetime
from typing import Tuple
import pandas as pd


def compute_tag_lifecycles(df: pd.DataFrame, min_count: int = 5) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Compute lifecycle statistics and monthly time-series for tags.

    Returns:
        (tag_stats_df, monthly_pivot_df)
    """
    # Explode tags so each tag mention is a row
    exploded = df.explode("tags").dropna(subset=["tags"])
    exploded = exploded[exploded["tags"].str.strip() != ""]

    if exploded.empty:
        return pd.DataFrame(), pd.DataFrame()

    # Tag counts
    tag_counts = exploded["tags"].value_counts()
    valid_tags = tag_counts[tag_counts >= min_count].index.tolist()
    exploded_filtered = exploded[exploded["tags"].isin(valid_tags)]

    # Monthly time-series pivot
    # Get complete list of all months from min date to max date
    all_months = pd.period_range(
        start=df["timestamp"].min().to_period("M"),
        end=df["timestamp"].max().to_period("M"),
        freq="M",
    ).astype(str).tolist()

    monthly_counts = exploded_filtered.groupby(["year_month", "tags"]).size().unstack(fill_value=0)
    monthly_counts = monthly_counts.reindex(all_months, fill_value=0)

    # Compute stats per tag
    stats_records = []
    latest_month = all_months[-1]
    # Months in the last 4 months of the export
    recent_window = set(all_months[-4:])

    for tag in valid_tags:
        series = monthly_counts[tag]
        active_series = series[series > 0]
        if active_series.empty:
            continue

        first_month = active_series.index[0]
        last_month = active_series.index[-1]
        peak_month = series.idxmax()
        peak_count = int(series.max())
        total_count = int(tag_counts[tag])
        months_active = len(active_series)

        # Compute span in months
        dt_first = datetime.strptime(first_month, "%Y-%m")
        dt_last = datetime.strptime(last_month, "%Y-%m")
        span_months = (dt_last.year - dt_first.year) * 12 + (dt_last.month - dt_first.month) + 1

        # Classify lifecycle behavior:
        # 1. Emerging: started recently (2025 or 2026) and active in recent months
        # 2. Evergreen: active over >= 12 months and active in at least 5 distinct months
        # 3. Burst / Seasonal: intense short-lived fixation
        if dt_first.year >= 2025 and last_month in recent_window and span_months <= 12:
            category = "Emerging Era"
        elif span_months >= 12 and months_active >= 5:
            category = "Evergreen Passion"
        else:
            category = "Seasonal Burst"

        stats_records.append(
            {
                "tag": tag,
                "total_count": total_count,
                "first_month": first_month,
                "last_month": last_month,
                "peak_month": peak_month,
                "peak_count": peak_count,
                "span_months": span_months,
                "months_active": months_active,
                "category": category,
            }
        )

    tag_stats_df = pd.DataFrame(stats_records)
    return tag_stats_df, monthly_counts
