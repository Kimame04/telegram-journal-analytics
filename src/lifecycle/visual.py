"""
Tag & Hobby Lifecycles - Visual Generation.

Generates high-contrast streamgraphs, horizontal lifespan Gantt charts,
chronological turnover heatmaps, and dark-mode Plotly dashboards.
Renders the standalone HTML report via Jinja2 templates.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import seaborn as sns

from .logic import compute_tag_lifecycles


# Curated 16-color high-contrast, visually distinct qualitative palette
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

    x_dates = [datetime.strptime(m, "%Y-%m") for m in data.index]

    plt.figure(figsize=(15, 7), dpi=300)
    sns.set_theme(style="whitegrid")

    colors = [TAG_PALETTE[i % len(TAG_PALETTE)] for i in range(len(top_tags))]
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
    df_top = tag_stats_df.sort_values("total_count", ascending=False).head(top_n)
    df_sorted = df_top.sort_values(["first_month", "total_count"], ascending=[False, False])

    y_pos = np.arange(len(df_sorted))
    fig, ax = plt.subplots(figsize=(15, max(8, len(df_sorted) * 0.38)), dpi=300)
    sns.set_theme(style="whitegrid")

    category_colors = {
        "Evergreen Passion": "#2E5B88",
        "Seasonal Burst": "#E65100",
        "Emerging Era": "#2E7D32",
    }

    for idx, (_, row) in enumerate(df_sorted.iterrows()):
        dt_start = datetime.strptime(row["first_month"], "%Y-%m")
        dt_end = datetime.strptime(row["last_month"], "%Y-%m")
        dt_peak = datetime.strptime(row["peak_month"], "%Y-%m")

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

        ax.scatter(
            mdates.date2num(dt_peak),
            idx,
            marker="*",
            s=95,
            color="#D32F2F",
            zorder=5,
        )

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

    dt_max_lim = datetime(2027, 4, 1)
    ax.set_xlim(right=mdates.date2num(dt_max_lim))

    plt.xticks(rotation=45, ha="right")

    ax.set_title("Interest Lifespans & Peak Eras (Gantt View - Top 25 Hobbies)", fontsize=16, fontweight="bold", pad=15)
    ax.set_xlabel("Timeline (Dec 2023 – Sep 2026)", fontsize=12, labelpad=10)

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


def build_lifecycle_figures(
    monthly_counts: pd.DataFrame,
    tag_stats_df: pd.DataFrame,
    top_n: int = 16,
) -> Dict[str, go.Figure]:
    """
    Build interactive Plotly figures in dark mode for tag and hobby lifecycles.

    Returns:
        Dictionary mapping figure keys ('streamgraph', 'ranked_bars') to Plotly go.Figure objects.
    """
    top_stats = tag_stats_df.sort_values("total_count", ascending=False).head(top_n).reset_index(drop=True)
    top_tags = top_stats["tag"].tolist()
    data = monthly_counts[top_tags]

    palette = [TAG_PALETTE[i % len(TAG_PALETTE)] for i in range(len(top_tags))]
    tag_to_color = {row["tag"]: palette[idx] for idx, row in top_stats.iterrows()}

    # 1. Streamgraph figure
    fig_stream = go.Figure()
    for idx, row in top_stats.iterrows():
        rank = idx + 1
        tag = row["tag"]
        total_cnt = row["total_count"]
        color = tag_to_color[tag]

        fig_stream.add_trace(
            go.Scatter(
                x=list(data.index),
                y=data[tag],
                mode="lines",
                line=dict(width=0.8, color=color),
                fillcolor=color,
                name=f"#{rank} [{tag}] ({total_cnt} msgs)",
                stackgroup="one",
                hoverinfo="skip",
            )
        )

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

            outside = (
                all_month_series[all_month_series > 0]
                .drop(index=data.columns, errors="ignore")
                .sort_values(ascending=False)
            )
            if not outside.empty:
                other_items = [f"[{t}] ({int(c)})" for t, c in outside.head(3).items()]
                other_str = " · ".join(other_items)
                lines.append(
                    f"<span style='font-size:11px; color:#8b949e;'><i>Also active:</i> {other_str}</span>"
                )

            card = "<br>".join(lines)
        hover_cards.append(card)

    fig_stream.add_trace(
        go.Bar(
            x=list(data.index),
            y=[upper_limit] * len(data.index),
            hovertext=hover_cards,
            hoverinfo="text",
            marker=dict(color="rgba(0,0,0,0)"),
            showlegend=False,
            name="Top 5 Monthly",
        )
    )

    fig_stream.update_layout(
        height=520,
        barmode="overlay",
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        hovermode="closest",
        font=dict(family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif", color="#c9d1d9"),
        hoverlabel=dict(
            bgcolor="rgba(22, 27, 34, 0.96)",
            font_size=13,
            font_family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif",
            font_color="#f0f6fc",
            bordercolor="#30363d",
        ),
        legend=dict(
            title=dict(text="<b>Ranked Interests</b>", font=dict(color="#c9d1d9")),
            orientation="h",
            y=-0.22,
            x=0.5,
            xanchor="center",
        ),
        margin=dict(l=55, r=30, t=25, b=65),
    )
    fig_stream.update_xaxes(tickangle=-45, gridcolor="rgba(255,255,255,0.06)")
    fig_stream.update_yaxes(range=[0, upper_limit], gridcolor="rgba(255,255,255,0.06)", title=dict(text="Monthly Mentions", font=dict(color="#8b949e", size=12)))

    # 2. Ranked horizontal bar chart
    top_stats_bars = top_stats.sort_values("total_count", ascending=True).reset_index(drop=True)
    bar_colors = [tag_to_color[row["tag"]] for _, row in top_stats_bars.iterrows()]
    bar_labels = [
        f"#{top_stats[top_stats['tag'] == row['tag']].index[0] + 1} [{row['tag']}]"
        for _, row in top_stats_bars.iterrows()
    ]

    fig_bars = go.Figure(
        data=go.Bar(
            x=top_stats_bars["total_count"],
            y=bar_labels,
            orientation="h",
            marker_color=bar_colors,
            name="Total Messages",
            customdata=top_stats_bars[["category", "first_month", "last_month", "peak_month", "peak_count"]].values,
            hovertemplate="<b>%{y}</b><br>Total Messages: <b>%{x:,}</b><br>Category: <b>%{customdata[0]}</b><br>Span: %{customdata[1]} to %{customdata[2]}<br>Peak: %{customdata[3]} (%{customdata[4]} msgs)<extra></extra>",
        )
    )
    fig_bars.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif", color="#c9d1d9"),
        margin=dict(l=140, r=35, t=25, b=45),
        height=max(380, len(top_stats_bars) * 26),
        showlegend=False,
    )
    fig_bars.update_xaxes(
        title=dict(text="Total Messages", font=dict(color="#8b949e", size=12)),
        gridcolor="rgba(255,255,255,0.06)",
    )
    fig_bars.update_yaxes(
        gridcolor="rgba(255,255,255,0.06)",
        tickfont=dict(color="#c9d1d9"),
    )

    return {
        "streamgraph": fig_stream,
        "ranked_bars": fig_bars,
    }


def build_lifecycle_chart_divs(figures: Dict[str, go.Figure]) -> Dict[str, str]:
    """Convert Plotly figures to embeddable HTML div strings."""
    return {
        name: fig.to_html(full_html=False, include_plotlyjs=False)
        for name, fig in figures.items()
    }


def generate_interactive_lifecycle_html(
    monthly_counts: pd.DataFrame,
    tag_stats_df: pd.DataFrame,
    output_path: Path,
    top_n: int = 16,
    summary: Optional[Dict[str, Any]] = None,
) -> None:
    """Generate an interactive Plotly HTML dashboard with interest stream and lifespan Gantt via Jinja2."""
    from src.renderer import render_to_file

    figures = build_lifecycle_figures(monthly_counts, tag_stats_df, top_n=top_n)
    chart_divs = build_lifecycle_chart_divs(figures)

    if summary is None:
        evergreens = tag_stats_df[tag_stats_df["category"] == "Evergreen Passion"]["tag"].tolist()
        bursts = tag_stats_df[tag_stats_df["category"] == "Seasonal Burst"]["tag"].tolist()
        emerging = tag_stats_df[tag_stats_df["category"] == "Emerging Era"]["tag"].tolist()
        top_row = tag_stats_df.sort_values("total_count", ascending=False).iloc[0]
        summary = {
            "total_tags_analyzed": len(tag_stats_df),
            "evergreens": evergreens,
            "bursts": bursts,
            "emerging": emerging,
            "top_tag": top_row["tag"],
            "top_tag_count": int(top_row["total_count"]),
        }

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

    date_span = ""
    if not monthly_counts.empty and len(monthly_counts.index) >= 2:
        try:
            d_start = datetime.strptime(monthly_counts.index[0], "%Y-%m").strftime("%b %Y")
            d_end = datetime.strptime(monthly_counts.index[-1], "%Y-%m").strftime("%b %Y")
            date_span = f"{d_start} – {d_end}"
        except Exception:
            pass

    context = {
        "summary": summary,
        "charts": chart_divs,
        "evergreen_records": evergreen_records,
        "burst_records": burst_records,
        "emerging_records": emerging_records,
        "date_span": date_span,
    }
    render_to_file("tag_lifecycle.html", context, output_path)


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

    # Summary metrics
    evergreens = tag_stats_df[tag_stats_df["category"] == "Evergreen Passion"]["tag"].tolist()
    bursts = tag_stats_df[tag_stats_df["category"] == "Seasonal Burst"]["tag"].tolist()
    emerging = tag_stats_df[tag_stats_df["category"] == "Emerging Era"]["tag"].tolist()

    summary = {
        "total_tags_analyzed": len(tag_stats_df),
        "evergreens": evergreens,
        "bursts": bursts,
        "emerging": emerging,
        "top_tag": tag_stats_df.sort_values("total_count", ascending=False).iloc[0]["tag"],
        "top_tag_count": int(tag_stats_df.sort_values("total_count", ascending=False).iloc[0]["total_count"]),
    }

    # 4. Interactive Plotly Explorer (HTML)
    interactive_html = out_dir / "tag_lifecycle_report.html"
    generate_interactive_lifecycle_html(monthly_counts, tag_stats_df, interactive_html, top_n=top_n, summary=summary)

    return summary
