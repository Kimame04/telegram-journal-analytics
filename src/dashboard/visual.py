"""
Unified Master Dashboard - Visual Generation.

Generates dark-mode Plotly figures, card components, and renders the
unified all-in-one HTML master dashboard via Jinja2 templates.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple
import pandas as pd

from src.circadian.visual import build_circadian_figures, build_circadian_chart_divs
from src.lifecycle.visual import build_lifecycle_figures, build_lifecycle_chart_divs
from src.otd.visual import format_otd_year_cards
from src.renderer import render_to_file
from .logic import build_dashboard_context, DashboardData


def generate_dashboard(
    df: pd.DataFrame,
    output_path: Path | str,
    year: Optional[int] = None,
    otd_date: Optional[str] = None,
    window_days: int = 0,
    top_n_tags: int = 16,
    min_tag_count: int = 5,
) -> Tuple[DashboardData, Path]:
    """
    Generate the complete, unified all-in-one HTML dashboard.

    Returns:
        (DashboardData, Path to rendered HTML file)
    """
    out_file = Path(output_path).expanduser().resolve()

    # 1. Pure domain aggregation
    data = build_dashboard_context(
        df,
        year=year,
        otd_date=otd_date,
        window_days=window_days,
        min_tag_count=min_tag_count,
    )

    # 2. Circadian figures & divs
    circadian_figs = build_circadian_figures(df, data.circadian_metrics)
    circadian_charts = build_circadian_chart_divs(circadian_figs)

    # 3. Lifecycle figures & divs
    lifecycle_charts = {}
    if not data.tag_stats_df.empty:
        lifecycle_figs = build_lifecycle_figures(
            data.monthly_counts,
            data.tag_stats_df,
            top_n=top_n_tags,
        )
        lifecycle_charts = build_lifecycle_chart_divs(lifecycle_figs)

    # 4. On This Day card structures
    otd_year_cards = format_otd_year_cards(data.otd_result)

    # 5. Reactions summary string for Wrapped section
    rx_summary = " ".join([
        f"{k}{int(v) if v is not None else ''}"
        for k, v in data.wrapped_data.most_reacted_reactions.items()
    ])

    context = {
        "data": data,
        "metrics": data.circadian_metrics,
        "p": data.wrapped_data.persona,
        "wrapped": data.wrapped_data,
        "summary": data.lifecycle_summary,
        "evergreen_records": data.evergreen_records,
        "burst_records": data.burst_records,
        "emerging_records": data.emerging_records,
        "circadian_charts": circadian_charts,
        "lifecycle_charts": lifecycle_charts,
        "otd_result": data.otd_result,
        "otd_year_cards": otd_year_cards,
        "is_otd_fallback": data.is_otd_fallback,
        "rx_summary": rx_summary,
    }

    render_to_file("dashboard.html", context, out_file)
    return data, out_file
