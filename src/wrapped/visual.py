"""
Channel-Wrapped Retrospective - Visual Generation.

Formats terminal retrospective story deck and renders the interactive,
standalone Spotify Wrapped-style dark-mode HTML deck via Jinja2 templates.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from src.renderer import render_to_file
from .logic import WrappedData


def render_wrapped_terminal(data: WrappedData) -> str:
    """
    Render a clean, structured CLI summary deck of Channel-Wrapped.
    """
    lines = []

    lines.append("")
    lines.append(f" ✨ CHANNEL-WRAPPED RETROSPECTIVE: {data.period_label} ✨ ".center(64, "═"))
    lines.append("")

    # Card 1: Volume & Dedication
    lines.append(" 📖  SLIDE 1: VOLUME & DEDICATION ".center(64, "─"))
    lines.append(f"  • Total Entries:       {data.total_messages:,} messages")
    lines.append(f"  • Words Inscribed:     {data.total_words:,} words ({data.total_chars:,} characters)")
    lines.append(f"  • Average Depth:       {data.avg_words_per_message:.1f} words/entry")
    lines.append(f"  • Real-World Metaphor: ~{data.book_pages_equivalent:.1f} book pages (~{data.reading_time_minutes} min read)")
    lines.append(f"  • Consistency:         {data.active_days}/{data.total_period_days} active days ({data.active_days_pct}%)")
    lines.append(f"  • Peak Journal Day:    {data.busiest_date} ({data.busiest_date_count} entries)")
    lines.append("")

    # Card 2: Streaks & Cadence
    lines.append(" ⚡  SLIDE 2: CADENCE & STREAKS ".center(64, "─"))
    if data.longest_streak_days > 1:
        lines.append(f"  • Longest Streak:      {data.longest_streak_days} consecutive days ({data.longest_streak_start} → {data.longest_streak_end})")
    else:
        lines.append(f"  • Longest Streak:      {data.longest_streak_days} day")
    if data.longest_gap_days > 0:
        lines.append(f"  • Longest Hiatus:      {data.longest_gap_days} days pause ({data.longest_gap_start} → {data.longest_gap_end})")
    lines.append(f"  • Top Reflection Month:{data.busiest_month} ({data.busiest_month_count} entries)")
    lines.append(f"  • Favorite Weekday:    {data.favorite_day_of_week} ({data.favorite_day_count} entries)")
    lines.append("")

    # Card 3: Circadian Persona
    p = data.persona
    lines.append(f" {p.emoji}  SLIDE 3: CIRCADIAN PERSONA ".center(64, "─"))
    lines.append(f"  • Archetype:           {p.name} {p.emoji}")
    lines.append(f"  • Persona Vibe:        \"{p.tagline}\"")
    lines.append(f"  • Peak Reflection Hour:{p.peak_hour_formatted} (24h: {p.peak_hour:02d}:00)")
    lines.append(f"  • Night Owl Index:     {p.night_owl_pct}% logged between 10 PM and 4 AM")
    lines.append(f"  • Morning Share:       {p.morning_pct}% logged between 5 AM and 9 AM")
    lines.append("")

    # Card 4: Top Fixations & Tag Eras
    lines.append(" 🏷️  SLIDE 4: TOP FIXATIONS & ERAS ".center(64, "─"))
    if data.top_tags:
        for idx, (tag, count, pct) in enumerate(data.top_tags, start=1):
            bar = "█" * int(min(20, max(1, count / (data.top_tags[0][1] or 1) * 20)))
            lines.append(f"  #{idx} [{tag:<14}] {bar:<20} {count:>3} mentions ({pct:>4.1f}%)")
        if data.top_tag_pairs:
            pair_strs = [f"[{p[0]}] + [{p[1]}] ({p[2]}x)" for p in data.top_tag_pairs]
            lines.append(f"  • Companion Topics:    {', '.join(pair_strs)}")
    else:
        lines.append("  • No bracket tags detected in this period.")
    lines.append("")

    # Card 5: Expressiveness & Reactions
    lines.append(" 🎭  SLIDE 5: EXPRESSIVENESS & MEDIA ".center(64, "─"))
    if data.top_reactions:
        rx_str = " ".join([f"{emoji} ({cnt})" for emoji, cnt in data.top_reactions])
        lines.append(f"  • Total Reactions:     {data.total_reactions:,} recorded")
        lines.append(f"  • Top Reactions:       {rx_str}")
    else:
        lines.append("  • Total Reactions:     0 recorded")
    lines.append(f"  • Visual Archive:      {data.photo_count} photos, {data.media_count} total media files")
    lines.append(f"  • Thought Monologues:  {data.self_reply_count} self-replies / follow-up updates")
    lines.append("")

    # Card 6: The Magnum Opus & Memory
    lines.append(" 🏆  SLIDE 6: THE MAGNUM OPUS & STANDOUTS ".center(64, "─"))
    if data.magnum_opus_words > 0:
        lines.append(f"  • Longest Reflection:  {data.magnum_opus_words:,} words on {data.magnum_opus_date}")
        lines.append(f"    Excerpt: \"{data.magnum_opus_snippet}\"")
    if data.most_reacted_count > 0:
        rx_icons = " ".join([f"{k}x{int(v) if v is not None else 1}" for k, v in data.most_reacted_reactions.items()])
        lines.append(f"  • Most Reacted Entry:  {data.most_reacted_count} reactions ({rx_icons}) on {data.most_reacted_date}")
        lines.append(f"    Excerpt: \"{data.most_reacted_snippet}\"")
    lines.append("")
    lines.append("═" * 64)
    lines.append("")

    return "\n".join(lines)


def generate_wrapped_html(data: WrappedData, output_path: Path) -> Path:
    """
    Generate an interactive, standalone Spotify Wrapped-style dark-mode HTML deck.
    100% offline, zero external CDN or trackers. Decoupled via Jinja2 template.
    """
    rx_summary = " ".join([f"{k}{int(v) if v is not None else ''}" for k, v in data.most_reacted_reactions.items()])
    context = {
        "data": data,
        "p": data.persona,
        "rx_summary": rx_summary,
    }
    return render_to_file("wrapped.html", context, output_path)
