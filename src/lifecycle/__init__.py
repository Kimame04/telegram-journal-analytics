"""
Tag & Hobby Lifecycles Package.

Exports tag lifecycle classification logic, palettes, and visual plot/report generators.
"""

from .logic import compute_tag_lifecycles
from .visual import (
    TAG_PALETTE,
    plot_tag_streamgraph,
    plot_tag_lifespan_gantt,
    plot_tag_turnover_heatmap,
    build_lifecycle_figures,
    build_lifecycle_chart_divs,
    generate_interactive_lifecycle_html,
    generate_lifecycle_report,
)

__all__ = [
    "compute_tag_lifecycles",
    "TAG_PALETTE",
    "plot_tag_streamgraph",
    "plot_tag_lifespan_gantt",
    "plot_tag_turnover_heatmap",
    "build_lifecycle_figures",
    "build_lifecycle_chart_divs",
    "generate_interactive_lifecycle_html",
    "generate_lifecycle_report",
]
