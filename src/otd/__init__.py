"""
On This Day (OTD) Time Capsule Package.

Exports calendar query logic, dataclasses, and visual HTML card generators.
"""

from .logic import (
    OTDEntry,
    OTDYearGroup,
    OTDResult,
    parse_query_date,
    query_on_this_day,
    get_random_active_day,
)
from .visual import (
    format_otd_year_cards,
    generate_otd_html,
)

__all__ = [
    "OTDEntry",
    "OTDYearGroup",
    "OTDResult",
    "parse_query_date",
    "query_on_this_day",
    "get_random_active_day",
    "format_otd_year_cards",
    "generate_otd_html",
]
