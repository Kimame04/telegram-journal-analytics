"""
Telegram Bot integration package for telegram-journal-analytics.
Provides decoupled bot API client, message formatters, and interactive handlers.
"""

from src.bot.client import TelegramClient
from src.bot.config import BotConfig, load_config
from src.bot.formatter import format_otd_message, format_stats_message
from src.bot.live_sync import (
    get_live_delta_path,
    ingest_channel_post,
    load_unified_journal,
    parse_channel_post,
)

__all__ = [
    "TelegramClient",
    "BotConfig",
    "load_config",
    "format_otd_message",
    "format_stats_message",
    "get_live_delta_path",
    "ingest_channel_post",
    "load_unified_journal",
    "parse_channel_post",
]
