"""
Configuration and persistent settings for LyricVibe.
Provides atomic file writing, schema validation, and default palettes.
"""

from __future__ import annotations

import colorsys
import json
import logging
import os
import sys
import tempfile

logger = logging.getLogger(__name__)

try:
    from lyricvibe.core.paths import get_executable_command, get_settings_file_path

    SETTINGS_FILE = get_settings_file_path()
except ImportError:
    SETTINGS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings.json")
    get_executable_command = lambda: sys.executable


def ensure_bright_hex(hex_str: str, min_lum: float = 175.0) -> str:
    """
    Guarantees that a hex color string is never a darker shade.
    If the perceived relative luminance is below min_lum, dynamically adjusts
    saturation in HSV space to lift brightness while strictly preserving hue.
    """
    if not isinstance(hex_str, str):
        return "#26FF7C"

    clean_hex = hex_str.strip().lstrip("#")
    if len(clean_hex) != 6:
        return "#26FF7C"

    try:
        r = int(clean_hex[0:2], 16)
        g = int(clean_hex[2:4], 16)
        b = int(clean_hex[4:6], 16)
    except ValueError:
        return "#26FF7C"

    # Perceived relative luminance (ITU-R BT.601 standard)
    lum = 0.299 * r + 0.587 * g + 0.114 * b
    if lum >= min_lum:
        return f"#{r:02X}{g:02X}{b:02X}"

    h_val, s_val, _ = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
    v_val = 1.0

    # Step down saturation to inject white luminance until threshold met
    for s_step in range(int(s_val * 100), 10, -5):
        s_test = s_step / 100.0
        nr, ng, nb = [int(c * 255) for c in colorsys.hsv_to_rgb(h_val, s_test, v_val)]
        if (0.299 * nr + 0.587 * ng + 0.114 * nb) >= min_lum:
            return f"#{nr:02X}{ng:02X}{nb:02X}"

    nr, ng, nb = [int(c * 255) for c in colorsys.hsv_to_rgb(h_val, 0.15, 1.0)]
    return f"#{nr:02X}{ng:02X}{nb:02X}"


# Ultra-bright, vivid, luminous highlight color palette (guaranteed Lum >= 175.0, NEVER dark)
BRIGHT_HIGHLIGHT_PALETTE = [
    {"name": "Laser Neon Green",   "hex": "#26FF7C"},  # High-luminance electric green (Lum: 175.2)
    {"name": "Electric Cyan",       "hex": "#00FFFF"},  # Pure luminous bright cyan (Lum: 178.8)
    {"name": "Vivid Neon Yellow",   "hex": "#FFE600"},  # Ultra-bright golden canary (Lum: 211.3)
    {"name": "Neon Candy Pink",     "hex": "#FF87C7"},  # Radiant luminous candy pink (Lum: 178.2)
    {"name": "Electric Violet",     "hex": "#D999FF"},  # Luminous glowing violet lilac (Lum: 183.8)
    {"name": "Neon Tangerine",      "hex": "#FF9B59"},  # Ultra-bright neon tangerine (Lum: 177.4)
    {"name": "Luminous Aqua",       "hex": "#33F7DC"},  # Super-bright mint turquoise (Lum: 183.8)
    {"name": "Neon Strawberry",     "hex": "#FF8CA8"},  # Bright luminous coral strawberry (Lum: 177.6)
    {"name": "Electric Sky",        "hex": "#59D7FF"},  # Radiant high-chroma sky azure (Lum: 179.9)
    {"name": "Neon Lime",           "hex": "#A6FF00"},  # Brilliant electric chartreuse (Lum: 199.3)
    {"name": "Electric Magenta",    "hex": "#FF8CD4"},  # Radiant bright magenta orchid (Lum: 182.6)
    {"name": "Neon Amber",          "hex": "#FFB800"},  # Bright warm electric amber (Lum: 184.3)
    {"name": "Electric Lilac",      "hex": "#DF8FFF"},  # Bright electric violet lilac (Lum: 178.4)
    {"name": "Neon Seafoam",        "hex": "#14FFB2"},  # Brilliant glowing teal seafoam (Lum: 176.0)
    {"name": "Electric Rose",       "hex": "#FF8CB8"},  # Bright vibrant punch rose (Lum: 179.4)
    {"name": "Spotify High-Neon",   "hex": "#57E48A"},  # Ultra-bright vibrant Spotify green (Lum: 175.2)
]

BRIGHT_HIGHLIGHT_HEX_LIST = [c["hex"] for c in BRIGHT_HIGHLIGHT_PALETTE]
# Aliases for compatibility
SMOOTH_SOFT_PALETTE = BRIGHT_HIGHLIGHT_PALETTE
SMOOTH_SOFT_HEX_LIST = BRIGHT_HIGHLIGHT_HEX_LIST

WINDOWS_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_REG_NAME = "LyricVibe"


def is_autostart_enabled() -> bool:
    """Checks whether LyricVibe is configured to auto-start with Windows/Spotify."""
    if sys.platform != "win32":
        return False
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, WINDOWS_RUN_KEY, 0, winreg.KEY_READ) as key:
            val, _ = winreg.QueryValueEx(key, APP_REG_NAME)
            if val:
                return True
    except (FileNotFoundError, OSError):
        pass

    startup_dir = os.path.join(os.environ.get("APPDATA", ""), r"Microsoft\Windows\Start Menu\Programs\Startup")
    return os.path.exists(os.path.join(startup_dir, f"{APP_REG_NAME}.lnk"))


def set_autostart_enabled(enabled: bool) -> bool:
    """Configures or removes auto-start in Windows registry and Startup directory."""
    if sys.platform != "win32":
        return False

    success = False
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, WINDOWS_RUN_KEY, 0, winreg.KEY_ALL_ACCESS) as key:
            if enabled:
                cmd_line = f'{get_executable_command()} --autostart'
                winreg.SetValueEx(key, APP_REG_NAME, 0, winreg.REG_SZ, cmd_line)
            else:
                try:
                    winreg.DeleteValue(key, APP_REG_NAME)
                except FileNotFoundError:
                    pass
        success = True
    except OSError as e:
        logger.debug("[settings] winreg autostart modification failed: %s", e)

    # Manage startup folder link cleanup or creation
    startup_dir = os.path.join(os.environ.get("APPDATA", ""), r"Microsoft\Windows\Start Menu\Programs\Startup")
    lnk_path = os.path.join(startup_dir, f"{APP_REG_NAME}.lnk")
    if not enabled and os.path.exists(lnk_path):
        try:
            os.remove(lnk_path)
        except OSError:
            pass

    return success

DEFAULT_SETTINGS: dict[str, object] = {
    "target_fps": 165,             # 165 Hz smooth motion
    "font_size": 42,
    "font_family": "7clouds Signature (Edo SZ)",
    "font_weight": "bold",
    "text_color": "#FFFFFF",
    "highlight_mode": "per_song",  # "per_song" (changes each song) or "fixed"
    "highlight_color": "#26FF7C",  # Active / default ultra-bright laser green (guaranteed never dark)
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
    "autostart_enabled": True,     # Launch with Windows & Spotify in background
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

    # Guarantee highlight color is NEVER a darker shade
    res["highlight_color"] = ensure_bright_hex(str(res.get("highlight_color", "#26FF7C")))

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
