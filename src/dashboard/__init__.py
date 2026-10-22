"""
Unified Master Journal Intelligence Dashboard Package.

Orchestrates analytical results from all feature modules and compiles
a comprehensive, interactive, standalone HTML report.
"""

from .logic import DashboardData, build_dashboard_context
from .visual import generate_dashboard

__all__ = [
    "DashboardData",
    "build_dashboard_context",
    "generate_dashboard",
]
