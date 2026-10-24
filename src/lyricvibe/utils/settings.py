"""
Configuration and persistent settings for Spotify Floating Lyrics Overlay.
Supports runtime updates via the Settings Window.
"""

import os
import json

try:
    from lyricvibe.core.paths import get_settings_file_path
    SETTINGS_FILE = get_settings_file_path()
except ImportError:
    SETTINGS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings.json")

# Ultra-bright, vivid, luminous neon/electric highlight color palette
BRIGHT_HIGHLIGHT_PALETTE = [
    {"name": "Laser Neon Green",   "hex": "#00FF66"},  # Ultra-bright electric green
    {"name": "Electric Cyan",       "hex": "#00FFFF"},  # Pure luminous bright cyan
    {"name": "Vivid Neon Yellow",   "hex": "#FFE600"},  # Ultra-bright golden canary
    {"name": "Neon Hot Pink",       "hex": "#FF1493"},  # Brilliant electric pink
    {"name": "Electric Violet",     "hex": "#B026FF"},  # High-chroma glowing purple
    {"name": "Neon Tangerine",      "hex": "#FF6600"},  # Ultra-vivid bright orange
    {"name": "Luminous Aqua",       "hex": "#00F5D4"},  # Super-bright mint turquoise
    {"name": "Neon Strawberry",     "hex": "#FF2D55"},  # Intense bright coral red
    {"name": "Electric Sky",        "hex": "#00C8FF"},  # Deep vivid radiant sky blue
    {"name": "Neon Lime",           "hex": "#A6FF00"},  # Electric chartreuse
    {"name": "Electric Magenta",    "hex": "#FF00A0"},  # Radiant high-contrast magenta
    {"name": "Neon Amber",          "hex": "#FFB800"},  # Bright warm electric amber
    {"name": "Electric Lilac",      "hex": "#C75CFF"},  # Bright electric violet lilac
    {"name": "Neon Seafoam",        "hex": "#14FFB2"},  # Brilliant glowing teal
    {"name": "Electric Rose",       "hex": "#FF3B81"},  # Bright vibrant punch rose
    {"name": "Spotify High-Neon",   "hex": "#1ED760"},  # Official high-vibrancy Spotify green
]

BRIGHT_HIGHLIGHT_HEX_LIST = [c["hex"] for c in BRIGHT_HIGHLIGHT_PALETTE]
# Aliases for compatibility
SMOOTH_SOFT_PALETTE = BRIGHT_HIGHLIGHT_PALETTE
SMOOTH_SOFT_HEX_LIST = BRIGHT_HIGHLIGHT_HEX_LIST

DEFAULT_SETTINGS = {
    "target_fps": 165,             # 165 Hz smooth motion
    "font_size": 42,
    "font_family": "7clouds Signature (Edo SZ)",
    "font_weight": "bold",
    "text_color": "#FFFFFF",
    "highlight_mode": "per_song",  # "per_song" (changes each song) or "fixed"
    "highlight_color": "#00FF66",  # Active / default ultra-bright laser green
    "highlight_block_enabled": False, # Box removed per user preference
    "highlight_enabled": True,
    "motion_blur_enabled": True,   # Multi-pass directional motion blur
    "motion_blur_intensity": 1.4,  # Motion blur streak intensity (0.5 to 2.5)
    "glow_enabled": True,
    "hand_drawn_underline_enabled": True,
    "word_reveal_enabled": True,
    "overlay_y": 55,               # Distance from top of screen
    "sync_offset_sec": 0.20,       # 200ms audio lead time for perfect vocal sync
    "auto_hide_idle": True,
    "animation_intensity": 1.0,    # 0.5 (subtle) to 1.5 (dynamic)
}


def load_settings() -> dict:
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
                res = DEFAULT_SETTINGS.copy()
                res.update(saved)
                return res
        except Exception:
            pass
    return DEFAULT_SETTINGS.copy()


def save_settings(settings: dict):
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=4)
    except Exception as e:
        print(f"[config] Error saving settings: {e}")
