"""Settings management, JSON persistence, and highlight palette utilities."""

from .settings import (
    BRIGHT_HIGHLIGHT_HEX_LIST,
    BRIGHT_HIGHLIGHT_PALETTE,
    DEFAULT_SETTINGS,
    load_settings,
    save_settings,
)

__all__ = [
    "BRIGHT_HIGHLIGHT_HEX_LIST",
    "BRIGHT_HIGHLIGHT_PALETTE",
    "DEFAULT_SETTINGS",
    "load_settings",
    "save_settings",
]
