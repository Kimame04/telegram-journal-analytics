"""
Telegram Message Formatters.
Converts OTDResult, streaks, and retrospective metrics into rich Telegram HTML messages.
Includes automatic HTML escaping and message chunking for Telegram's 4,096 char limit.
"""

from __future__ import annotations

import html
from typing import Any, Dict, List, Optional

from src.otd.logic import OTDEntry, OTDResult, OTDYearGroup


MAX_TELEGRAM_MESSAGE_LEN = 4000  # Leave buffer below hard 4,096 limit
MAX_ENTRY_SNIPPET_LEN = 500       # Cap overly long journal entries for mobile readability


def escape_html(text: str) -> str:
    """Escapes HTML special characters for safe Telegram HTML parsing."""
    return html.escape(text, quote=False)


def format_entry_snippet(entry: OTDEntry, max_len: int = MAX_ENTRY_SNIPPET_LEN) -> str:
    """Format a single entry with optional truncation and tag badges."""
    clean_text = entry.text.strip()
    if len(clean_text) > max_len:
        clean_text = clean_text[:max_len].rstrip() + "..."

    escaped = escape_html(clean_text)
    time_badge = f"<i>({escape_html(entry.time_str)})</i>" if entry.time_str else ""
    snippet = f"<blockquote>{escaped}</blockquote>"

    extras = []
    if entry.tags:
        tags_str = " ".join(f"<code>#{escape_html(t)}</code>" for t in entry.tags[:5])
        extras.append(tags_str)

    if entry.reactions:
        reactions_str = " ".join(f"{emoji}{count}" for emoji, count in entry.reactions.items())
        extras.append(f"<i>{reactions_str}</i>")

    meta_line = (" • ".join(extras)) if extras else ""
    if meta_line:
        return f"{time_badge} {snippet}\n{meta_line}"
    return f"{time_badge} {snippet}"


def format_year_group(group: OTDYearGroup) -> str:
    """Format all entries within a specific past year."""
    header = f"📅 <b>{group.year}</b> <i>({group.label})</i> — {group.total_messages} entries ({group.total_words} words)"
    lines = [header]

    for entry in group.entries:
        lines.append(format_entry_snippet(entry))

    return "\n\n".join(lines)


def format_otd_message(otd: OTDResult) -> List[str]:
    """
    Format complete OTDResult into one or more Telegram HTML messages.
    Splits content across multiple messages if it exceeds MAX_TELEGRAM_MESSAGE_LEN.
    """
    if otd.total_matches == 0:
        return [
            f"🕰️ <b>On This Day — {escape_html(otd.date_title)}</b>\n\n"
            "<i>No journal entries recorded on this calendar day in past years.</i>\n"
            "✨ <i>Write a reflection today to give your future self something to look back on!</i>"
        ]

    intro = (
        f"🕰️ <b>On This Day — {escape_html(otd.date_title)}</b>\n"
        f"<i>{otd.total_matches} {'memories' if otd.total_matches != 1 else 'memory'} "
        f"across {len(otd.year_groups)} past {'years' if len(otd.year_groups) != 1 else 'year'}</i>"
    )

    messages: List[str] = []
    current_chunk = intro

    for group in otd.year_groups:
        group_text = format_year_group(group)
        # Check if adding this group exceeds Telegram max length
        if len(current_chunk) + len(group_text) + 4 > MAX_TELEGRAM_MESSAGE_LEN:
            messages.append(current_chunk.strip())
            current_chunk = group_text
        else:
            current_chunk += f"\n\n{group_text}"

    if current_chunk.strip():
        # Append subtle sign-off on the final chunk
        footer = "\n\n✨ <i>Keep reflecting. Your thoughts build history.</i>"
        if len(current_chunk) + len(footer) <= MAX_TELEGRAM_MESSAGE_LEN:
            current_chunk += footer
        messages.append(current_chunk.strip())

    return messages


def format_stats_message(stats: Dict[str, Any]) -> str:
    """Format high-level journal metrics into a concise Telegram intelligence card."""
    lines = [
        "📊 <b>Telegram Journal Intelligence</b>",
        "",
        f"👤 <b>Persona:</b> <i>{escape_html(stats.get('persona', 'The Introspective Chronicler'))}</i>",
        f"🌙 <b>Night Owl Index:</b> <code>{stats.get('night_owl_pct', 0.0):.1f}%</code> (peak: {stats.get('peak_hour', 'N/A')}:00)",
        f"📖 <b>Total Volume:</b> <code>{stats.get('total_messages', 0):,}</code> entries • <code>{stats.get('total_words', 0):,}</code> words",
        f"📚 <b>Book Equivalent:</b> ~<code>{stats.get('pages', 0)}</code> reading pages",
        f"🔥 <b>Consistency:</b> <code>{stats.get('consistency_pct', 0.0):.1f}%</code> active days (streak: {stats.get('streak', 0)} days)",
    ]

    top_tags = stats.get("top_tags", [])
    if top_tags:
        tags_str = " ".join(f"<code>[{escape_html(t)}]</code>" for t in top_tags[:5])
        lines.append(f"🏷️ <b>Top Tags:</b> {tags_str}")

    lines.append("")
    lines.append("<i>Use /otd to view memories from this day, or /random to roll a past entry.</i>")
    return "\n".join(lines)


def format_tag_message(tag: str, count: int, first_seen: Optional[str], last_seen: Optional[str], sample_text: Optional[str] = None) -> str:
    """Format tag lookup result into a concise report."""
    tag_clean = tag.strip().lstrip("#[").rstrip("]")
    lines = [
        f"🏷️ <b>Tag Dossier: [{escape_html(tag_clean)}]</b>",
        "",
        f"📝 <b>Total Mentions:</b> <code>{count}</code> entries",
        f"⏳ <b>Active Span:</b> <code>{first_seen or 'Unknown'}</code> → <code>{last_seen or 'Present'}</code>",
    ]

    if sample_text:
        snippet = escape_html(sample_text[:300].strip())
        lines.append(f"\n💡 <i>Sample entry:</i>\n<blockquote>{snippet}</blockquote>")

    return "\n".join(lines)
