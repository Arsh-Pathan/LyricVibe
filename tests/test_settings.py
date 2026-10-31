"""Tests for settings persistence, schema validation, and atomic writes."""

import os
import tempfile
from unittest.mock import patch

from lyricvibe.utils.settings import (
    DEFAULT_SETTINGS,
    _validate_settings,
    load_settings,
    save_settings,
)


def test_default_settings_keys():
    expected_keys = {
        "target_fps",
        "font_size",
        "font_family",
        "overlay_y",
        "sync_offset_sec",
        "auto_hide_idle",
        "hand_drawn_underline_enabled",
        "highlight_enabled",
        "highlight_block_enabled",
        "highlight_color",
        "highlight_mode",
        "motion_blur_enabled",
        "motion_blur_intensity",
    }
    assert expected_keys.issubset(set(DEFAULT_SETTINGS.keys()))


def test_validate_settings_bounds_clamping():
    raw = {
        "target_fps": 9999,      # clamped to 360
        "font_size": 2,          # clamped to 18
        "overlay_y": -500,       # clamped to 0
        "sync_offset_sec": 99.0, # clamped to 5.0
        "motion_blur_intensity": -1.0,  # clamped to 0.0
    }
    validated = _validate_settings(raw)
    assert validated["target_fps"] == 360
    assert validated["font_size"] == 18
    assert validated["overlay_y"] == 0
    assert validated["sync_offset_sec"] == 5.0
    assert validated["motion_blur_intensity"] == 0.0


def test_validate_settings_type_mismatches():
    raw = {
        "target_fps": "not_an_int",
        "font_size": None,
        "auto_hide_idle": "true",
    }
    validated = _validate_settings(raw)
    assert validated["target_fps"] == DEFAULT_SETTINGS["target_fps"]
    assert validated["font_size"] == DEFAULT_SETTINGS["font_size"]
    assert isinstance(validated["auto_hide_idle"], bool)


def test_save_and_load_roundtrip():
    with tempfile.TemporaryDirectory() as tmp_dir:
        test_file = os.path.join(tmp_dir, "test_settings.json")
        with patch("lyricvibe.utils.settings.SETTINGS_FILE", test_file):
            custom = DEFAULT_SETTINGS.copy()
            custom["font_size"] = 54
            custom["target_fps"] = 144
            custom["highlight_color"] = "#26FF7C"

            save_settings(custom)
            assert os.path.exists(test_file)

            loaded = load_settings()
            assert loaded["font_size"] == 54
            assert loaded["target_fps"] == 144
            assert loaded["highlight_color"] == "#26FF7C"


def test_load_settings_corrupted_json_recovery():
    with tempfile.TemporaryDirectory() as tmp_dir:
        corrupted_file = os.path.join(tmp_dir, "corrupt_settings.json")
        with open(corrupted_file, "w", encoding="utf-8") as f:
            f.write("{ invalid json content :::")

        with patch("lyricvibe.utils.settings.SETTINGS_FILE", corrupted_file):
            loaded = load_settings()
            assert loaded == DEFAULT_SETTINGS


def test_load_settings_missing_file_returns_defaults():
    with patch("lyricvibe.utils.settings.SETTINGS_FILE", "non_existent_file_path.json"):
        loaded = load_settings()
        assert loaded == DEFAULT_SETTINGS


def test_get_settings_file_path_fallback():
    from lyricvibe.core.paths import get_settings_file_path

    # Unfrozen mode should return project root / settings.json
    unfrozen_path = get_settings_file_path()
    assert unfrozen_path.endswith("settings.json")

    # Frozen mode with non-writable exe directory should fallback to APPDATA
    with patch("sys.frozen", True, create=True), \
         patch("sys.executable", "C:\\Program Files\\LyricVibe\\LyricVibe.exe"), \
         patch("os.path.exists", return_value=False), \
         patch("os.access", return_value=False), \
         patch.dict("os.environ", {"APPDATA": "C:\\Users\\Test\\AppData\\Roaming"}):
        fallback_path = get_settings_file_path()
        assert "AppData\\Roaming\\LyricVibe\\settings.json" in fallback_path


def test_ensure_bright_hex_never_dark():
    from lyricvibe.utils.settings import BRIGHT_HIGHLIGHT_PALETTE, ensure_bright_hex

    # 1. Dark colors must be boosted to luminance >= 175.0
    dark_inputs = [
        "#000000",  # Pure black
        "#111111",  # Dark grey
        "#000080",  # Navy blue
        "#800000",  # Maroon
        "#004400",  # Dark green
        "#330033",  # Deep purple
        "#FF00A0",  # Darker magenta
        "#B026FF",  # Darker electric violet
    ]
    for d in dark_inputs:
        bright = ensure_bright_hex(d)
        h = bright.lstrip("#")
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        lum = 0.299 * r + 0.587 * g + 0.114 * b
        assert lum >= 175.0, f"Expected {d} to be lifted >= 175.0 lum, got {lum} ({bright})"

    # 2. Already bright colors preserve high luminance
    for bright_in in ["#00FFFF", "#FFE600", "#26FF7C"]:
        res = ensure_bright_hex(bright_in)
        assert res.upper() == bright_in.upper()

    # 3. All colors in BRIGHT_HIGHLIGHT_PALETTE are strictly >= 175.0 lum
    for item in BRIGHT_HIGHLIGHT_PALETTE:
        h = item["hex"].lstrip("#")
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        lum = 0.299 * r + 0.587 * g + 0.114 * b
        assert lum >= 175.0, f"Palette color {item['name']} ({item['hex']}) is below 175.0 lum: {lum}"

    # 4. Invalid or malformed inputs return bright fallback
    assert ensure_bright_hex(None).startswith("#")
    assert ensure_bright_hex("invalid").startswith("#")
    assert ensure_bright_hex("#123").startswith("#")


def test_autostart_toggle():
    from lyricvibe.utils.settings import is_autostart_enabled, set_autostart_enabled

    initial = is_autostart_enabled()

    # Test toggling
    set_autostart_enabled(True)
    assert is_autostart_enabled() is True

    set_autostart_enabled(False)
    assert is_autostart_enabled() is False

    # Restore initial state
    set_autostart_enabled(initial)
