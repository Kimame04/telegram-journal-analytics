"""
Circadian & Habit Profiling Package.

Exports pure analytical metrics logic and visual chart/report generators.
"""

from .logic import DAYS_ORDER, compute_circadian_metrics
from .visual import (
    plot_weekday_hourly_heatmap,
    plot_hourly_distribution,
    plot_longitudinal_hourly_shift,
    build_circadian_figures,
    build_circadian_chart_divs,
    generate_interactive_html_report,
    generate_circadian_report,
)

__all__ = [
    "DAYS_ORDER",
    "compute_circadian_metrics",
    "plot_weekday_hourly_heatmap",
    "plot_hourly_distribution",
    "plot_longitudinal_hourly_shift",
    "build_circadian_figures",
    "build_circadian_chart_divs",
    "generate_interactive_html_report",
    "generate_circadian_report",
]
