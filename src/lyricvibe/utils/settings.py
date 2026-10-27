"""
Configuration and persistent settings for LyricVibe.
Provides atomic file writing, schema validation, and default palettes.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile

logger = logging.getLogger(__name__)

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

DEFAULT_SETTINGS: dict[str, object] = {
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


def _validate_settings(raw_data: dict) -> dict:
    """Validates types and clamps numerical ranges to prevent crashes."""
    res = DEFAULT_SETTINGS.copy()
    if not isinstance(raw_data, dict):
        return res

    for key, default_val in DEFAULT_SETTINGS.items():
        if key not in raw_data:
            continue
        val = raw_data[key]
        if isinstance(default_val, bool):
            res[key] = bool(val)
        elif isinstance(default_val, int):
            try:
                res[key] = int(val)
            except (ValueError, TypeError):
                res[key] = default_val
        elif isinstance(default_val, float):
            try:
                res[key] = float(val)
            except (ValueError, TypeError):
                res[key] = default_val
        elif isinstance(default_val, str):
            res[key] = str(val) if val else default_val

    # Sanity bounds
    res["target_fps"] = max(30, min(int(res["target_fps"]), 360))
    res["font_size"] = max(18, min(int(res["font_size"]), 96))
    res["overlay_y"] = max(0, min(int(res["overlay_y"]), 2000))
    res["sync_offset_sec"] = max(-5.0, min(float(res["sync_offset_sec"]), 5.0))
    res["motion_blur_intensity"] = max(0.0, min(float(res["motion_blur_intensity"]), 5.0))

    return res


def load_settings() -> dict:
    """Loads and validates settings from disk. Returns defaults on error."""
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
                return _validate_settings(saved)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("[settings] Could not read %s, using defaults: %s", SETTINGS_FILE, e)

    return DEFAULT_SETTINGS.copy()


def save_settings(settings: dict):
    """Atomically writes settings to disk via temporary file rename to prevent corruption."""
    try:
        dir_name = os.path.dirname(os.path.abspath(SETTINGS_FILE))
        os.makedirs(dir_name, exist_ok=True)

        with tempfile.NamedTemporaryFile("w", dir=dir_name, delete=False, encoding="utf-8") as tf:
            json.dump(settings, tf, indent=4)
            tf.flush()
            os.fsync(tf.fileno())
            temp_name = tf.name

        os.replace(temp_name, SETTINGS_FILE)
    except OSError as e:
        logger.error("[settings] Error saving settings to %s: %s", SETTINGS_FILE, e)
        if "temp_name" in locals() and os.path.exists(temp_name):
            try:
                os.remove(temp_name)
            except OSError:
                pass
