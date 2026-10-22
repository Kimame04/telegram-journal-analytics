"""
Circadian & Habit Profiling - Visual Generation.

Generates publication-quality static PNG charts and dark-mode Plotly figures
for circadian rhythms, weekly habit heatmaps, and longitudinal shifts.
Renders the standalone HTML dashboard via Jinja2 templates.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import matplotlib.pyplot as plt
import pandas as pd
import plotly.graph_objects as go
import seaborn as sns

from .logic import DAYS_ORDER, compute_circadian_metrics


def plot_weekday_hourly_heatmap(df: pd.DataFrame, output_path: Path) -> None:
    """Generate 24h x 7d static heatmap (Monday to Sunday vs Hour 0-23)."""
    pivot = df.pivot_table(
        index="day_name",
        columns="hour",
        values="id",
        aggfunc="count",
        fill_value=0,
    ).reindex(DAYS_ORDER, fill_value=0)

    for h in range(24):
        if h not in pivot.columns:
            pivot[h] = 0
    pivot = pivot[sorted(pivot.columns)]

    plt.figure(figsize=(14, 6), dpi=300)
    sns.set_theme(style="white")

    ax = sns.heatmap(
        pivot,
        cmap="YlGnBu",
        annot=True,
        fmt="d",
        cbar_kws={"label": "Number of Messages"},
        linewidths=0.5,
        linecolor="#f0f0f0",
    )

    ax.set_title("Weekly Journaling Rhythm (Day of Week vs. Hour of Day)", fontsize=16, fontweight="bold", pad=15)
    ax.set_xlabel("Hour of Day (00:00 - 23:00)", fontsize=12, labelpad=10)
    ax.set_ylabel("Day of Week", fontsize=12)
    ax.set_xticklabels([f"{h:02d}:00" for h in range(24)], rotation=45, ha="right")

    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()


def plot_hourly_distribution(df: pd.DataFrame, output_path: Path, metrics: Dict[str, Any]) -> None:
    """Generate 24-hour circadian profile bar and trend chart."""
    hour_counts = df["hour"].value_counts().reindex(range(24), fill_value=0)
    hours = list(range(24))
    counts = hour_counts.values

    plt.figure(figsize=(12, 5), dpi=300)
    sns.set_theme(style="whitegrid")

    colors = ["#ff7f0e" if (h >= 22 or h < 4) else "#1f77b4" for h in hours]
    plt.bar(hours, counts, color=colors, width=0.8, edgecolor="none", alpha=0.85)
    plt.plot(hours, counts, color="#2ca02c", linewidth=2.5, marker="o", markersize=5)

    peak_h = metrics["peak_hour"]
    peak_c = metrics["peak_hour_count"]
    plt.annotate(
        f"Peak: {peak_h:02d}:00 ({peak_c:,} msgs)",
        xy=(peak_h, peak_c),
        xytext=(max(0, peak_h - 4), peak_c * 0.95),
        arrowprops=dict(facecolor="black", shrink=0.08, width=1.5, headwidth=8),
        fontweight="bold",
        fontsize=11,
        bbox=dict(boxstyle="round,pad=0.3", fc="#ffffcc", ec="orange", lw=1),
    )

    plt.axvspan(-0.5, 3.5, color="orange", alpha=0.12, label="Late Night Window (22:00 - 04:00)")
    plt.axvspan(21.5, 23.5, color="orange", alpha=0.12)

    plt.title("24-Hour Circadian Profile (Distribution of Journal Entries)", fontsize=15, fontweight="bold", pad=15)
    plt.xlabel("Hour of Day", fontsize=12)
    plt.ylabel("Total Messages", fontsize=12)
    plt.xticks(hours, [f"{h:02d}" for h in hours])
    plt.xlim(-0.6, 23.6)
    plt.legend(loc="upper left")

    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()


def plot_longitudinal_hourly_shift(df: pd.DataFrame, output_path: Path) -> None:
    """Generate Year-Month vs Hour heatmap showing how circadian patterns shifted over time."""
    pivot = df.pivot_table(
        index="year_month",
        columns="hour",
        values="id",
        aggfunc="count",
        fill_value=0,
    )
    for h in range(24):
        if h not in pivot.columns:
            pivot[h] = 0
    pivot = pivot[sorted(pivot.columns)]

    row_sums = pivot.sum(axis=1)
    pivot_pct = pivot.div(row_sums, axis=0) * 100

    plt.figure(figsize=(14, max(8, len(pivot) * 0.35)), dpi=300)
    sns.set_theme(style="white")

    ax = sns.heatmap(
        pivot_pct,
        cmap="mako",
        cbar_kws={"label": "% of Month's Messages"},
        linewidths=0.2,
        linecolor="#ffffff",
    )

    ax.set_title("Longitudinal Circadian Shift (Month vs. Hour of Day)", fontsize=16, fontweight="bold", pad=15)
    ax.set_xlabel("Hour of Day (00:00 - 23:00)", fontsize=12, labelpad=10)
    ax.set_ylabel("Year - Month", fontsize=12)
    ax.set_xticklabels([f"{h:02d}:00" for h in range(24)], rotation=45, ha="right")

    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()


def build_circadian_figures(df: pd.DataFrame, metrics: Dict[str, Any]) -> Dict[str, go.Figure]:
    """
    Build interactive Plotly figures in dark mode for circadian analysis.

    Returns:
        Dictionary mapping figure keys ('weekly_heatmap', 'hourly_distribution', 'longitudinal_shift')
        to Plotly go.Figure objects.
    """
    # 1. Weekly pivot
    pivot_week = df.pivot_table(
        index="day_name",
        columns="hour",
        values="id",
        aggfunc="count",
        fill_value=0,
    ).reindex(DAYS_ORDER, fill_value=0)
    for h in range(24):
        if h not in pivot_week.columns:
            pivot_week[h] = 0
    pivot_week = pivot_week[sorted(pivot_week.columns)]

    hover_matrix = []
    for day in DAYS_ORDER:
        row_hover = []
        for h in range(24):
            subset = df[(df["day_name"] == day) & (df["hour"] == h)]
            cnt = len(subset)
            tag_counts = {}
            for tags in subset["tags"]:
                for t in tags:
                    tag_counts[t] = tag_counts.get(t, 0) + 1
            top_t = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:3]
            top_t_str = ", ".join([f"[{k}] ({v})" for k, v in top_t]) if top_t else "None"
            hover_text = (
                f"<b>{day} at {h:02d}:00</b><br>"
                f"Messages: <b>{cnt:,}</b><br>"
                f"Top Topics: {top_t_str}"
            )
            row_hover.append(hover_text)
        hover_matrix.append(row_hover)

    fig_week = go.Figure(
        data=go.Heatmap(
            z=pivot_week.values,
            x=[f"{h:02d}:00" for h in range(24)],
            y=DAYS_ORDER,
            hoverinfo="text",
            text=hover_matrix,
            colorscale="Tealgrn",
            colorbar=dict(
                title=dict(text="Messages", font=dict(color="#8b949e", size=12)),
                tickfont=dict(color="#8b949e"),
            ),
        )
    )
    fig_week.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif", color="#c9d1d9"),
        margin=dict(l=75, r=40, t=25, b=45),
        height=380,
    )
    fig_week.update_xaxes(tickangle=-45, gridcolor="rgba(255,255,255,0.06)")
    fig_week.update_yaxes(gridcolor="rgba(255,255,255,0.06)")

    # 2. Hourly distribution bar chart
    hour_counts = df["hour"].value_counts().reindex(range(24), fill_value=0)
    bar_colors = ["#ff9800" if (h >= 22 or h < 4) else "#58a6ff" for h in range(24)]

    fig_hourly = go.Figure(
        data=go.Bar(
            x=[f"{h:02d}:00" for h in range(24)],
            y=hour_counts.values,
            marker_color=bar_colors,
            name="Hourly Volume",
            hovertemplate="Hour %{x}: <b>%{y:,}</b> messages<extra></extra>",
        )
    )
    fig_hourly.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif", color="#c9d1d9"),
        margin=dict(l=65, r=30, t=25, b=45),
        height=340,
        showlegend=False,
    )
    fig_hourly.update_xaxes(
        title=dict(text="Hour of Day (00:00 - 23:00)", font=dict(color="#8b949e", size=12)),
        tickangle=-45,
        gridcolor="rgba(255,255,255,0.06)",
    )
    fig_hourly.update_yaxes(
        title=dict(text="Messages", font=dict(color="#8b949e", size=12)),
        gridcolor="rgba(255,255,255,0.06)",
    )

    # 3. Monthly pivot
    pivot_month = df.pivot_table(
        index="year_month",
        columns="hour",
        values="id",
        aggfunc="count",
        fill_value=0,
    )
    for h in range(24):
        if h not in pivot_month.columns:
            pivot_month[h] = 0
    pivot_month = pivot_month[sorted(pivot_month.columns)]
    pivot_month_pct = pivot_month.div(pivot_month.sum(axis=1), axis=0) * 100

    fig_month = go.Figure(
        data=go.Heatmap(
            z=pivot_month_pct.values,
            x=[f"{h:02d}:00" for h in range(24)],
            y=list(pivot_month_pct.index),
            colorscale="Viridis",
            colorbar=dict(
                title=dict(text="% Share", font=dict(color="#8b949e", size=12)),
                tickfont=dict(color="#8b949e"),
            ),
            hovertemplate="Month: %{y}<br>Hour: %{x}<br>Share: <b>%{z:.1f}%</b><extra></extra>",
        )
    )
    fig_month.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif", color="#c9d1d9"),
        margin=dict(l=75, r=40, t=25, b=45),
        height=max(400, len(pivot_month_pct) * 22),
    )
    fig_month.update_xaxes(
        title=dict(text="Hour of Day", font=dict(color="#8b949e", size=12)),
        tickangle=-45,
        gridcolor="rgba(255,255,255,0.06)",
    )
    fig_month.update_yaxes(
        title=dict(text="Year - Month", font=dict(color="#8b949e", size=12)),
        gridcolor="rgba(255,255,255,0.06)",
    )

    return {
        "weekly_heatmap": fig_week,
        "hourly_distribution": fig_hourly,
        "longitudinal_shift": fig_month,
    }


def build_circadian_chart_divs(figures: Dict[str, go.Figure]) -> Dict[str, str]:
    """Convert Plotly figures to embeddable HTML div strings."""
    return {
        name: fig.to_html(full_html=False, include_plotlyjs=False)
        for name, fig in figures.items()
    }


def generate_interactive_html_report(
    df: pd.DataFrame,
    metrics: Dict[str, Any],
    output_path: Path,
) -> None:
    """Generate an interactive, responsive Plotly HTML report via Jinja2 template."""
    from src.renderer import render_to_file

    figures = build_circadian_figures(df, metrics)
    chart_divs = build_circadian_chart_divs(figures)

    context = {
        "metrics": metrics,
        "charts": chart_divs,
    }
    render_to_file("circadian.html", context, output_path)


def generate_circadian_report(
    df: pd.DataFrame,
    output_dir_path: str | Path,
) -> Dict[str, Any]:
    """
    Main entry point for generating all Circadian & Habit Heatmap assets.

    Returns:
        metrics dict with key findings.
    """
    out_dir = Path(output_dir_path).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1. Pure domain logic
    metrics = compute_circadian_metrics(df)

    # 2. Visual assets (PNGs)
    heatmap_png = out_dir / "circadian_weekly_heatmap.png"
    plot_weekday_hourly_heatmap(df, heatmap_png)

    distribution_png = out_dir / "hourly_circadian_distribution.png"
    plot_hourly_distribution(df, distribution_png, metrics)

    monthly_shift_png = out_dir / "longitudinal_circadian_shift.png"
    plot_longitudinal_hourly_shift(df, monthly_shift_png)

    # 3. Interactive HTML Dashboard
    interactive_html = out_dir / "circadian_report.html"
    generate_interactive_html_report(df, metrics, interactive_html)

    return metrics
