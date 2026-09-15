"""
Circadian & Habit Heatmap Analysis.

Visualizes 24-hour mental clock, weekly rhythms, and longitudinal circadian shifts.
Exports publication-quality static PNGs and an interactive Plotly HTML report.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import plotly.graph_objects as go
from plotly.subplots import make_subplots


DAYS_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def compute_circadian_metrics(df: pd.DataFrame) -> Dict[str, Any]:
    """Compute high-level circadian and temporal habit metrics."""
    total_messages = len(df)
    hour_counts = df["hour"].value_counts().sort_index()
    peak_hour = int(hour_counts.idxmax())
    peak_hour_count = int(hour_counts.max())

    day_counts = df["day_name"].value_counts().reindex(DAYS_ORDER, fill_value=0)
    peak_day = str(day_counts.idxmax())
    peak_day_count = int(day_counts.max())

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
    busiest_date = str(daily_counts.idxmax())
    busiest_date_count = int(daily_counts.max())

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
    }


def plot_weekday_hourly_heatmap(df: pd.DataFrame, output_path: Path) -> None:
    """Generate 24h x 7d static heatmap (Monday to Sunday vs Hour 0-23)."""
    # Create pivot table
    pivot = df.pivot_table(
        index="day_name",
        columns="hour",
        values="id",
        aggfunc="count",
        fill_value=0,
    ).reindex(DAYS_ORDER, fill_value=0)

    # Ensure all 24 hours are present in columns
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

    # Bar chart with custom color highlighting the late-night peak
    colors = ["#ff7f0e" if (h >= 22 or h < 4) else "#1f77b4" for h in hours]
    bars = plt.bar(hours, counts, color=colors, width=0.8, edgecolor="none", alpha=0.85)

    # Add trend spline/curve
    plt.plot(hours, counts, color="#2ca02c", linewidth=2.5, marker="o", markersize=5)

    # Annotate peak
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

    # Night owl legend patch indicator
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

    # Row-normalize to show relative percentage per month (highlights sleep/habit shifts regardless of volume)
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


def generate_interactive_html_report(
    df: pd.DataFrame,
    metrics: Dict[str, Any],
    output_path: Path,
) -> None:
    """Generate an interactive, responsive Plotly HTML report."""
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

    # Build custom hovertext with top tags for that specific day & hour
    hover_matrix = []
    for day in DAYS_ORDER:
        row_hover = []
        for h in range(24):
            subset = df[(df["day_name"] == day) & (df["hour"] == h)]
            cnt = len(subset)
            # Find top tags in this slot
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

    # 2. Hourly counts
    hour_counts = df["hour"].value_counts().reindex(range(24), fill_value=0)

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

    fig = make_subplots(
        rows=3,
        cols=1,
        vertical_spacing=0.1,
        subplot_titles=(
            "Weekly Journaling Rhythm (Day of Week vs. Hour of Day)",
            "Circadian Profile Across 24 Hours",
            "Longitudinal Circadian Shift (Month vs. Hour of Day, % Distribution)",
        ),
        row_heights=[0.35, 0.25, 0.4],
    )

    # Heatmap 1: Weekday x Hour
    fig.add_trace(
        go.Heatmap(
            z=pivot_week.values,
            x=[f"{h:02d}:00" for h in range(24)],
            y=DAYS_ORDER,
            hoverinfo="text",
            text=hover_matrix,
            colorscale="Tealgrn",
            colorbar=dict(title="Messages", len=0.3, y=0.85),
        ),
        row=1,
        col=1,
    )

    # Bar chart 2: Hourly profile
    bar_colors = ["#ff9800" if (h >= 22 or h < 4) else "#0288d1" for h in range(24)]
    fig.add_trace(
        go.Bar(
            x=[f"{h:02d}:00" for h in range(24)],
            y=hour_counts.values,
            marker_color=bar_colors,
            name="Hourly Volume",
            hovertemplate="Hour %{x}: <b>%{y:,}</b> messages<extra></extra>",
        ),
        row=2,
        col=1,
    )

    # Heatmap 3: Month x Hour
    fig.add_trace(
        go.Heatmap(
            z=pivot_month_pct.values,
            x=[f"{h:02d}:00" for h in range(24)],
            y=list(pivot_month_pct.index),
            colorscale="Viridis",
            colorbar=dict(title="% of Month", len=0.35, y=0.18),
            hovertemplate="Month: %{y}<br>Hour: %{x}<br>Share: <b>%{z:.1f}%</b><extra></extra>",
        ),
        row=3,
        col=1,
    )

    fig.update_layout(
        title=dict(
            text=(
                f"Personal Journal Circadian & Habit Report "
                f"({metrics['total_messages']:,} entries | Dec 2023 - Sep 2026)<br>"
                f"<sup>Peak Hour: <b>{metrics['peak_hour']:02d}:00</b> ({metrics['peak_hour_count']:,} msgs) | "
                f"Night Owl Share (10 PM - 4 AM): <b>{metrics['night_owl_pct']}%</b> | "
                f"Peak Day: <b>{metrics['peak_day']}</b></sup>"
            ),
            font=dict(size=18),
            x=0.5,
            xanchor="center",
        ),
        height=1300,
        template="plotly_white",
        showlegend=False,
    )

    fig.write_html(output_path, include_plotlyjs="cdn")


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

    metrics = compute_circadian_metrics(df)

    # 1. Weekday x Hourly Heatmap (PNG)
    heatmap_png = out_dir / "circadian_weekly_heatmap.png"
    plot_weekday_hourly_heatmap(df, heatmap_png)

    # 2. Hourly Distribution (PNG)
    distribution_png = out_dir / "hourly_circadian_distribution.png"
    plot_hourly_distribution(df, distribution_png, metrics)

    # 3. Longitudinal Monthly Shift (PNG)
    monthly_shift_png = out_dir / "longitudinal_circadian_shift.png"
    plot_longitudinal_hourly_shift(df, monthly_shift_png)

    # 4. Interactive Plotly Report (HTML)
    interactive_html = out_dir / "circadian_report.html"
    generate_interactive_html_report(df, metrics, interactive_html)

    return metrics
