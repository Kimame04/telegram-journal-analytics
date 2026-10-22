"""
Centralized Jinja2 template rendering engine.

Provides resilient template discovery, shared formatting filters, and helper functions
to render standalone HTML reports from analytical domain models.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

import jinja2

# Robust template directory resolution relative to project root
TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"


def _format_commas(value: Any) -> str:
    """Format integers or floats with thousand separator commas."""
    if value is None:
        return "0"
    try:
        num = int(value)
        return f"{num:,}"
    except (ValueError, TypeError):
        return str(value)


def _round_num(value: Any, decimals: int = 1) -> str:
    """Safely round numbers to specified decimal places."""
    if value is None:
        return "0.0"
    try:
        f = float(value)
        return f"{f:.{decimals}f}"
    except (ValueError, TypeError):
        return str(value)


_ENV: Optional[jinja2.Environment] = None


def get_jinja_env() -> jinja2.Environment:
    """
    Get or initialize the shared Jinja2 Environment with project filters.
    """
    global _ENV
    if _ENV is None:
        if not TEMPLATES_DIR.exists():
            raise FileNotFoundError(f"Templates directory not found at: {TEMPLATES_DIR}")

        _ENV = jinja2.Environment(
            loader=jinja2.FileSystemLoader(str(TEMPLATES_DIR)),
            autoescape=jinja2.select_autoescape(["html", "xml"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        _ENV.filters["commas"] = _format_commas
        _ENV.filters["round_num"] = _round_num

    return _ENV


def render_template(template_name: str, context: Dict[str, Any]) -> str:
    """
    Render a Jinja2 template by name with given context dictionary.
    """
    env = get_jinja_env()
    template = env.get_template(template_name)
    return template.render(**context)


def render_to_file(
    template_name: str,
    context: Dict[str, Any],
    output_path: Path,
) -> Path:
    """
    Render a template with context and write the resulting HTML to output_path.
    Creates parent directories if necessary.
    """
    rendered_html = render_template(template_name, context)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(rendered_html)
    return output_path
