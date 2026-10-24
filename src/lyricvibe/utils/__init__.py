"""Settings management, JSON persistence, and highlight palette utilities."""
from .settings import (
    load_settings,
    save_settings,
    BRIGHT_HIGHLIGHT_PALETTE,
    BRIGHT_HIGHLIGHT_HEX_LIST,
    DEFAULT_SETTINGS,
)

__all__ = [
    "load_settings",
    "save_settings",
    "BRIGHT_HIGHLIGHT_PALETTE",
    "BRIGHT_HIGHLIGHT_HEX_LIST",
    "DEFAULT_SETTINGS",
]
