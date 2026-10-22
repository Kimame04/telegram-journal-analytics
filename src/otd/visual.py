"""
On This Day (OTD) - Visual Generation.

Formats flashback memory cards with tag badges, media icons, time badges,
and renders the interactive HTML memory cards dashboard via Jinja2 templates.
"""

from __future__ import annotations

import html
from pathlib import Path
from typing import Any, Dict, List

from src.lifecycle import TAG_PALETTE
from src.renderer import render_to_file
from .logic import OTDResult


def format_otd_year_cards(result: OTDResult) -> List[Dict[str, Any]]:
    """
    Format year groups and entries into visual card data structures.
    Applies tag color highlighting, HTML escaping, and sun/moon badges.
    """
    tag_to_color = {t: TAG_PALETTE[i % len(TAG_PALETTE)] for i, t in enumerate(result.all_tags)}

    year_cards = []
    for g in result.year_groups:
        tag_badges = [
            {"tag": t, "count": cnt, "color": tag_to_color.get(t, "#444")}
            for t, cnt in g.tags_summary
        ]

        entries_data = []
        for e in g.entries:
            text_clean = e.text.strip()
            highlighted_text = html.escape(text_clean)
            for t in e.tags:
                escaped_tag = html.escape(f"[{t}]")
                c = tag_to_color.get(t, "#4A5568")
                badge = f"<span class='entry-tag' style='background:{c};'>[{html.escape(t)}]</span>"
                highlighted_text = highlighted_text.replace(escaped_tag, badge)

            highlighted_text = highlighted_text.replace("\r\n", "\n")
            while "\n\n\n" in highlighted_text:
                highlighted_text = highlighted_text.replace("\n\n\n", "\n\n")
            highlighted_text = highlighted_text.replace("\n", "<br>")
            time_icon = "🌙" if e.timestamp.hour >= 22 or e.timestamp.hour < 5 else "☀️"

            entries_data.append({
                "time_icon": time_icon,
                "time_str": e.time_str,
                "has_photo": e.has_photo,
                "highlighted_text": highlighted_text if highlighted_text else "<i>(media attachment)</i>",
            })

        year_cards.append({
            "label": g.label,
            "total_messages": g.total_messages,
            "tag_badges": tag_badges,
            "entries": entries_data,
        })

    return year_cards


def generate_otd_html(
    result: OTDResult,
    output_path: Path | str,
) -> Path:
    """
    Generate an interactive, standalone HTML card showcasing past memories for this day.
    Decoupled via Jinja2 template.
    """
    out_file = Path(output_path).expanduser().resolve()
    year_cards = format_otd_year_cards(result)

    context = {
        "result": result,
        "total_years_active": len(result.year_groups),
        "year_cards": year_cards,
    }
    return render_to_file("on_this_day.html", context, out_file)
