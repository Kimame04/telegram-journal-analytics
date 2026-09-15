"""
Tag & Hobby Lifecycles Module.

Tracks how topics, hobbies, and hyperfixations rise, peak, fade, or persist over time.
Generates streamgraphs, lifespan Gantt charts, monthly turnover matrices, and an interactive Plotly dashboard.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Any, List, Tuple
from datetime import datetime

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import pandas as pd
import seaborn as sns
import plotly.graph_objects as go
from plotly.subplots import make_subplots


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


# Curated 16-color high-contrast, visually distinct qualitative palette
# Cycles across distinct color families (Blue, Orange, Green, Rose, Purple, Teal, Rust, Olive, etc.)
# avoiding muddy or washed-out adjacent hues.
TAG_PALETTE = [
    "#2E5B88",  # 1. Ocean Blue
    "#E65100",  # 2. Amber Orange
    "#2E7D32",  # 3. Forest Emerald
    "#C2185B",  # 4. Crimson Rose
    "#6A1B9A",  # 5. Royal Purple
    "#00838F",  # 6. Deep Teal
    "#D84315",  # 7. Rust Red
    "#558B2F",  # 8. Olive Moss
    "#1565C0",  # 9. Cobalt Blue
    "#AD1457",  # 10. Berry Magenta
    "#8D6E63",  # 11. Warm Cocoa
    "#00897B",  # 12. Persian Green
    "#EF6C00",  # 13. Tangerine
    "#283593",  # 14. Midnight Indigo
    "#7B1FA2",  # 15. Vivid Violet
    "#455A64",  # 16. Slate Steel
]


def plot_tag_streamgraph(
    monthly_counts: pd.DataFrame,
    tag_stats_df: pd.DataFrame,
    output_path: Path,
    top_n: int = 16,
) -> None:
    """Plot stacked area streamgraph of top hobbies over time, ranked by message volume."""
    top_stats = tag_stats_df.sort_values("total_count", ascending=False).head(top_n).reset_index(drop=True)
    top_tags = top_stats["tag"].tolist()
    data = monthly_counts[top_tags]

    # Convert period index strings to datetime for smooth plotting
    x_dates = [datetime.strptime(m, "%Y-%m") for m in data.index]

    plt.figure(figsize=(15, 7), dpi=300)
    sns.set_theme(style="whitegrid")

    # Use the curated, distinct qualitative color palette
    colors = [TAG_PALETTE[i % len(TAG_PALETTE)] for i in range(len(top_tags))]

    # Legend labels ranked with volume
    labels = [f"#{idx+1} [{row['tag']}] ({row['total_count']} msgs)" for idx, row in top_stats.iterrows()]

    plt.stackplot(
        x_dates,
        data.values.T,
        labels=labels,
        colors=colors,
        alpha=0.92,
    )

    plt.title("Hobby & Interest Streamgraph (Top Topics Ranked by Volume)", fontsize=16, fontweight="bold", pad=15)
    plt.xlabel("Timeline (Dec 2023 – Sep 2026)", fontsize=12, labelpad=10)
    plt.ylabel("Monthly Journal Mentions", fontsize=12)

    ax = plt.gca()
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    plt.xticks(rotation=45, ha="right")

    plt.legend(loc="upper left", bbox_to_anchor=(1.01, 1), title="Ranked Interests (Total Volume)", frameon=True)
    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()


def plot_tag_lifespan_gantt(
    tag_stats_df: pd.DataFrame,
    output_path: Path,
    top_n: int = 25,
) -> None:
    """Plot horizontal Gantt chart showing active lifespan and peak month for each interest."""
    # Take the top N most mentioned tags overall, then sort them by first_month for a clean chronological staircase
    df_top = tag_stats_df.sort_values("total_count", ascending=False).head(top_n)
    df_sorted = df_top.sort_values(["first_month", "total_count"], ascending=[False, False])

    y_pos = np.arange(len(df_sorted))
    fig, ax = plt.subplots(figsize=(15, max(8, len(df_sorted) * 0.38)), dpi=300)
    sns.set_theme(style="whitegrid")

    category_colors = {
        "Evergreen Passion": "#2E5B88",  # Navy
        "Seasonal Burst": "#E65100",     # Amber Orange
        "Emerging Era": "#2E7D32",       # Forest Green
    }

    max_x_date = datetime.strptime("2026-09", "%Y-%m")

    for idx, (_, row) in enumerate(df_sorted.iterrows()):
        dt_start = datetime.strptime(row["first_month"], "%Y-%m")
        dt_end = datetime.strptime(row["last_month"], "%Y-%m")
        dt_peak = datetime.strptime(row["peak_month"], "%Y-%m")

        # Bar width in days (minimum 28 days so single month is visible)
        days = max(28, (dt_end - dt_start).days + 28)
        color = category_colors.get(row["category"], "#7f7f7f")

        ax.barh(
            idx,
            days,
            left=mdates.date2num(dt_start),
            height=0.55,
            color=color,
            alpha=0.75,
            edgecolor=color,
            linewidth=1.2,
        )

        # Plot star on peak month
        ax.scatter(
            mdates.date2num(dt_peak),
            idx,
            marker="*",
            s=95,
            color="#D32F2F",
            zorder=5,
        )

        # Label count on right
        ax.text(
            mdates.date2num(dt_end) + 20,
            idx,
            f"{row['total_count']} msgs (peak: {row['peak_month']})",
            va="center",
            fontsize=8.5,
            color="#333333",
        )

    ax.set_yticks(y_pos)
    ax.set_yticklabels([f"[{t}]" for t in df_sorted["tag"]], fontsize=10)
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))

    # Add margin on the right for text labels
    dt_max_lim = datetime(2027, 4, 1)
    ax.set_xlim(right=mdates.date2num(dt_max_lim))

    plt.xticks(rotation=45, ha="right")

    ax.set_title("Interest Lifespans & Peak Eras (Gantt View - Top 25 Hobbies)", fontsize=16, fontweight="bold", pad=15)
    ax.set_xlabel("Timeline (Dec 2023 – Sep 2026)", fontsize=12, labelpad=10)

    # Custom legend for categories
    from matplotlib.patches import Patch
    from matplotlib.lines import Line2D
    legend_elements = [
        Patch(facecolor="#2E5B88", label="Evergreen Passion (> 1 yr)"),
        Patch(facecolor="#E65100", label="Seasonal Burst (1-4 mo)"),
        Patch(facecolor="#2E7D32", label="Emerging Era (2025/2026)"),
        Line2D([0], [0], marker="*", color="w", markerfacecolor="#D32F2F", markersize=11, label="Peak Activity Month"),
    ]
    ax.legend(handles=legend_elements, loc="lower right", frameon=True)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()


def plot_tag_turnover_heatmap(
    monthly_counts: pd.DataFrame,
    tag_stats_df: pd.DataFrame,
    output_path: Path,
    top_n: int = 24,
) -> None:
    """Plot heatmap of Top Tags x Months showing interest turnover across quarters."""
    # Top N tags by total volume, sorted chronologically by first appearance
    top_tags = (
        tag_stats_df.sort_values("total_count", ascending=False)
        .head(top_n)
        .sort_values(["first_month", "total_count"], ascending=[True, False])["tag"]
        .tolist()
    )
    data = monthly_counts[top_tags].T

    plt.figure(figsize=(15, max(8, len(top_tags) * 0.38)), dpi=300)
    sns.set_theme(style="white")

    ax = sns.heatmap(
        data,
        cmap="YlGnBu",
        cbar_kws={"label": "Monthly Message Volume"},
        linewidths=0.3,
        linecolor="#f0f0f0",
    )

    ax.set_title("Interest Turnover Matrix (Chronological Era Progression)", fontsize=16, fontweight="bold", pad=15)
    ax.set_xlabel("Year - Month", fontsize=12, labelpad=10)
    ax.set_ylabel("Tag / Hobby", fontsize=12)
    ax.set_yticklabels([f"[{t}]" for t in top_tags], rotation=0)
    plt.xticks(rotation=45, ha="right")

    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()


def generate_interactive_lifecycle_html(
    monthly_counts: pd.DataFrame,
    tag_stats_df: pd.DataFrame,
    output_path: Path,
    top_n: int = 16,
) -> None:
    """Generate an interactive Plotly HTML dashboard with interest stream and lifespan Gantt."""
    top_stats = tag_stats_df.sort_values("total_count", ascending=False).head(top_n).reset_index(drop=True)
    top_tags = top_stats["tag"].tolist()
    data = monthly_counts[top_tags]

    # Palette of distinct colors for the top N streams
    palette = [TAG_PALETTE[i % len(TAG_PALETTE)] for i in range(len(top_tags))]
    tag_to_color = {row["tag"]: palette[idx] for idx, row in top_stats.iterrows()}

    fig = make_subplots(
        rows=2,
        cols=1,
        vertical_spacing=0.15,
        subplot_titles=(
            "Interactive Interest Stream (Hover shows top 5 active hobbies for each month)",
            f"Top {top_n} Interests Ranked by Overall Message Volume",
        ),
        row_heights=[0.6, 0.4],
    )

    # 1. Stacked area / stream traces (ranked #1 to #N by total volume)
    for idx, row in top_stats.iterrows():
        rank = idx + 1
        tag = row["tag"]
        total_cnt = row["total_count"]
        color = tag_to_color[tag]

        fig.add_trace(
            go.Scatter(
                x=list(data.index),
                y=data[tag],
                mode="lines",
                line=dict(width=0.8, color=color),
                fillcolor=color,
                name=f"#{rank} [{tag}] ({total_cnt} msgs)",
                stackgroup="one",
                # Skip individual trace hover to keep hover card focused only on top 5
                hoverinfo="skip",
            ),
            row=1,
            col=1,
        )

    # Build Top 5 Hover Cards per month
    total_y = data.sum(axis=1).values
    max_stacked_y = float(max(total_y)) if len(total_y) else 10.0
    upper_limit = max(max_stacked_y * 1.05, 10.0)

    hover_cards = []
    for m in data.index:
        dt_m = datetime.strptime(m, "%Y-%m")
        month_title = dt_m.strftime("%B %Y")

        stream_series = data.loc[m]
        active_stream = stream_series[stream_series > 0].sort_values(ascending=False)
        stream_month_msgs = int(stream_series.sum())

        all_month_series = monthly_counts.loc[m]

        if active_stream.empty:
            card = f"<b>{month_title}</b><br><i>No stream activity</i>"
        else:
            top5 = active_stream.head(5)
            lines = [
                f"<b>{month_title}</b> ({stream_month_msgs} stream msgs)",
                "─────────────────────────",
            ]
            for r_idx, (t_name, t_cnt) in enumerate(top5.items(), start=1):
                t_color = tag_to_color[t_name]
                lines.append(
                    f"{r_idx}. <span style='color:{t_color}; font-size:15px;'>■</span> <b>[{t_name}]</b>: {int(t_cnt)} msgs"
                )

            # Check if there were other active tags that month outside the stream
            outside = (
                all_month_series[all_month_series > 0]
                .drop(index=data.columns, errors="ignore")
                .sort_values(ascending=False)
            )
            if not outside.empty:
                other_items = [f"[{t}] ({int(c)})" for t, c in outside.head(3).items()]
                other_str = " · ".join(other_items)
                lines.append(
                    f"<span style='font-size:11px; color:#555555;'><i>Also active:</i> {other_str}</span>"
                )

            card = "<br>".join(lines)
        hover_cards.append(card)

    # Transparent full-height bar overlay for instant, responsive hover across the month column
    fig.add_trace(
        go.Bar(
            x=list(data.index),
            y=[upper_limit] * len(data.index),
            hovertext=hover_cards,
            hoverinfo="text",
            marker=dict(color="rgba(0,0,0,0)"),
            showlegend=False,
            name="Top 5 Monthly",
        ),
        row=1,
        col=1,
    )

    # 2. Bar chart of top tags colored by each tag's signature stream color
    top_stats_bars = top_stats.sort_values("total_count", ascending=True).reset_index(drop=True)
    bar_colors = [tag_to_color[row["tag"]] for _, row in top_stats_bars.iterrows()]
    bar_labels = [
        f"#{top_stats[top_stats['tag'] == row['tag']].index[0] + 1} [{row['tag']}]"
        for _, row in top_stats_bars.iterrows()
    ]

    fig.add_trace(
        go.Bar(
            x=top_stats_bars["total_count"],
            y=bar_labels,
            orientation="h",
            marker_color=bar_colors,
            name="Total Messages",
            customdata=top_stats_bars[["category", "first_month", "last_month", "peak_month", "peak_count"]].values,
            hovertemplate="<b>%{y}</b><br>Total Messages: <b>%{x}</b><br>Category: <b>%{customdata[0]}</b><br>Span: %{customdata[1]} to %{customdata[2]}<br>Peak: %{customdata[3]} (%{customdata[4]} msgs)<extra></extra>",
        ),
        row=2,
        col=1,
    )

    fig.update_layout(
        title=dict(
            text="Personal Journal - Tag & Hobby Lifecycle Explorer (Dec 2023 – Sep 2026)",
            font=dict(size=18),
            x=0.5,
            xanchor="center",
        ),
        height=1050,
        barmode="overlay",
        template="plotly_white",
        hovermode="closest",
        hoverlabel=dict(
            bgcolor="rgba(255, 255, 255, 0.96)",
            font_size=13,
            font_family="system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
            bordercolor="#888888",
        ),
        legend=dict(
            title=dict(text="<b>Ranked Interests</b>"),
            orientation="h",
            y=-0.12,
            x=0.5,
            xanchor="center",
        ),
    )
    fig.update_yaxes(range=[0, upper_limit], row=1, col=1)

    fig.write_html(output_path, include_plotlyjs="cdn")


def generate_lifecycle_report(
    df: pd.DataFrame,
    output_dir_path: str | Path,
    top_n: int = 16,
    min_count: int = 5,
) -> Dict[str, Any]:
    """
    Main entry point to compute tag lifecycles and generate all visual assets.
    """
    out_dir = Path(output_dir_path).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    tag_stats_df, monthly_counts = compute_tag_lifecycles(df, min_count=min_count)

    if tag_stats_df.empty:
        raise ValueError("No tags found meeting the minimum count criteria.")

    # 1. Streamgraph (PNG)
    streamgraph_png = out_dir / "tag_streamgraph.png"
    plot_tag_streamgraph(monthly_counts, tag_stats_df, streamgraph_png, top_n=top_n)

    # 2. Lifespan Gantt Chart (PNG)
    gantt_png = out_dir / "tag_lifespans_gantt.png"
    plot_tag_lifespan_gantt(tag_stats_df, gantt_png, top_n=min(25, len(tag_stats_df)))

    # 3. Monthly Turnover Heatmap (PNG)
    heatmap_png = out_dir / "tag_monthly_heatmap.png"
    plot_tag_turnover_heatmap(monthly_counts, tag_stats_df, heatmap_png, top_n=min(22, len(tag_stats_df)))

    # 4. Interactive Plotly Explorer (HTML)
    interactive_html = out_dir / "tag_lifecycle_report.html"
    generate_interactive_lifecycle_html(monthly_counts, tag_stats_df, interactive_html, top_n=top_n)

    # Summary metrics
    evergreens = tag_stats_df[tag_stats_df["category"] == "Evergreen Passion"]["tag"].tolist()
    bursts = tag_stats_df[tag_stats_df["category"] == "Seasonal Burst"]["tag"].tolist()
    emerging = tag_stats_df[tag_stats_df["category"] == "Emerging Era"]["tag"].tolist()

    return {
        "total_tags_analyzed": len(tag_stats_df),
        "evergreens": evergreens,
        "bursts": bursts,
        "emerging": emerging,
        "top_tag": tag_stats_df.sort_values("total_count", ascending=False).iloc[0]["tag"],
        "top_tag_count": int(tag_stats_df.sort_values("total_count", ascending=False).iloc[0]["total_count"]),
    }
