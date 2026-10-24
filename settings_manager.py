"""
Configuration and persistent settings for Spotify Floating Lyrics Overlay.
Supports runtime updates via the Settings Window.
"""

import os
import json

SETTINGS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings.json")

# Curated aesthetic smooth soft color palette (rich chroma, soft luminous pastels, high visibility)
SMOOTH_SOFT_PALETTE = [
    {"name": "Mint Emerald",    "hex": "#2EE59D"},  # Fresh soft neon green
    {"name": "Electric Cyan",   "hex": "#00E5FF"},  # Luminous cyber aqua
    {"name": "Lavender Lilac",  "hex": "#C084FC"},  # Dreamy soft purple
    {"name": "Coral Rose",      "hex": "#FF758C"},  # Warm soft strawberry pink
    {"name": "Golden Canary",   "hex": "#FCD34D"},  # Smooth warm amber gold
    {"name": "Sky Azure",       "hex": "#38BDF8"},  # Silky vibrant blue
    {"name": "Candy Bubblegum", "hex": "#FF77A9"},  # Sweet vibrant pastel pink
    {"name": "Electric Lime",   "hex": "#A8FF78"},  # Crisp pastel lime
    {"name": "Sunset Tangerine","hex": "#FF9F43"},  # Warm soft orange
    {"name": "Orchid Violet",   "hex": "#E879F9"},  # Vivid soft magenta
    {"name": "Seafoam Aqua",    "hex": "#20E3B2"},  # Cool smooth mint
    {"name": "Strawberry Melon","hex": "#FB7185"},  # Punchy pastel red
    {"name": "Periwinkle Blue", "hex": "#70A6FF"},  # Soft denim electric
    {"name": "Warm Honey",      "hex": "#FFD166"},  # Mellow sunshine
    {"name": "Jade Neon",       "hex": "#1DD1A1"},  # Luminous sea emerald
    {"name": "Apricot Peach",   "hex": "#FFA07A"},  # Cozy soft coral
    {"name": "Electric Indigo", "hex": "#818CF8"},  # Modern velvet violet
    {"name": "Blossom Pink",    "hex": "#FF6EA7"},  # Vibrant spring petal
    {"name": "Spotify Green",   "hex": "#1DB954"},  # Iconic Spotify vibrant
]

SMOOTH_SOFT_HEX_LIST = [c["hex"] for c in SMOOTH_SOFT_PALETTE]

DEFAULT_SETTINGS = {
    "target_fps": 165,             # 165 Hz smooth motion
    "font_size": 42,
    "font_family": "7clouds Signature (Edo SZ)",
    "font_weight": "bold",
    "text_color": "#FFFFFF",
    "highlight_mode": "per_song",  # "per_song" (changes each song) or "fixed"
    "highlight_color": "#2EE59D",  # Active / default smooth soft highlight
    "highlight_block_enabled": True, # Translucent rounded pill behind active word
    "highlight_enabled": True,
    "motion_blur_enabled": True,
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
