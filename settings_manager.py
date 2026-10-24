"""
Configuration and persistent settings for Spotify Floating Lyrics Overlay.
Supports runtime updates via the Settings Window.
"""

import os
import json

SETTINGS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings.json")

DEFAULT_SETTINGS = {
    "target_fps": 165,             # 165 Hz smooth motion
    "font_size": 42,
    "font_family": "7clouds Signature (Edo SZ)",
    "font_weight": "bold",
    "text_color": "#FFFFFF",
    "highlight_color": "#1DB954",  # Spotify green active word highlight
    "highlight_enabled": True,
    "motion_blur_enabled": True,
    "glow_enabled": True,
    "hand_drawn_underline_enabled": True,
    "word_reveal_enabled": True,
    "overlay_y": 55,               # Distance from top of screen
    "sync_offset_sec": 0.0,
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
