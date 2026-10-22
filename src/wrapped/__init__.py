"""
Channel-Wrapped Retrospective Package.

Exports retrospective analytical calculation logic and visual deck generators.
"""

from .logic import (
    PersonaInfo,
    WrappedData,
    determine_persona,
    compute_streaks,
    compute_wrapped,
)
from .visual import (
    render_wrapped_terminal,
    generate_wrapped_html,
)

__all__ = [
    "PersonaInfo",
    "WrappedData",
    "determine_persona",
    "compute_streaks",
    "compute_wrapped",
    "render_wrapped_terminal",
    "generate_wrapped_html",
]
