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
        "target_fps": 9999,  # clamped to 360
        "font_size": 2,  # clamped to 18
        "overlay_y": -500,  # clamped to 0
        "sync_offset_sec": 99.0,  # clamped to 5.0
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
    with (
        patch("sys.frozen", True, create=True),
        patch("sys.executable", "C:\\Program Files\\LyricVibe\\LyricVibe.exe"),
        patch("os.path.exists", return_value=False),
        patch("os.access", return_value=False),
        patch.dict("os.environ", {"APPDATA": "C:\\Users\\Test\\AppData\\Roaming"}),
    ):
        fallback_path = get_settings_file_path()
        assert "AppData\\Roaming\\LyricVibe\\settings.json" in fallback_path


def test_ensure_hex_supports_darker_colors():
    from lyricvibe.utils.settings import HIGHLIGHT_PALETTE, ensure_bright_hex

    # 1. Darker colors are supported and preserved directly
    dark_inputs = [
        ("#1DB954", "#1DB954"),  # Spotify green
        ("#0E8A42", "#0E8A42"),  # Deep emerald
        ("#000080", "#000080"),  # Navy blue
        ("#800000", "#800000"),  # Maroon
        ("#7B1FA2", "#7B1FA2"),  # Royal purple
        ("#D32F2F", "#D32F2F"),  # Crimson
    ]
    for d, expected in dark_inputs:
        res = ensure_bright_hex(d)
        assert res.upper() == expected.upper(), (
            f"Expected {expected}, got {res} for {d}"
        )

    # 2. Shorthand 3-digit hex is expanded
    assert ensure_bright_hex("#fff") == "#FFFFFF"
    assert ensure_bright_hex("#123") == "#112233"

    # 3. Explicit min_lum lifts darker colors when requested
    brightened = ensure_bright_hex("#000080", min_lum=175.0)
    h = brightened.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    lum = 0.299 * r + 0.587 * g + 0.114 * b
    assert lum >= 175.0

    # 4. All palette items are valid 7-character hex colors starting with '#'
    for item in HIGHLIGHT_PALETTE:
        hx = item["hex"]
        assert len(hx) == 7
        assert hx.startswith("#")
        assert int(hx[1:], 16) >= 0

    # 5. Invalid or malformed inputs return default fallback
    assert ensure_bright_hex(None).startswith("#")
    assert ensure_bright_hex("invalid").startswith("#")


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


def test_settings_save_fallback_on_restricted_path():
    with tempfile.TemporaryDirectory() as tmp_dir:
        restricted_file = "Z:\\NonExistentDrive\\settings.json"
        fallback_dir = os.path.join(tmp_dir, "LyricVibe")
        fallback_file = os.path.join(fallback_dir, "settings.json")

        with (
            patch("lyricvibe.utils.settings.SETTINGS_FILE", restricted_file),
            patch.dict("os.environ", {"APPDATA": tmp_dir}),
        ):
            custom = DEFAULT_SETTINGS.copy()
            custom["font_size"] = 50

            save_settings(custom)
            assert os.path.exists(fallback_file)

            loaded = load_settings()
            assert loaded["font_size"] == 50


def test_get_asset_path_frozen_exe_dir_override():
    from lyricvibe.core.paths import get_asset_path

    with tempfile.TemporaryDirectory() as tmp_dir:
        fake_font = os.path.join(tmp_dir, "CustomFont.ttf")
        with open(fake_font, "w") as f:
            f.write("font data")

        fake_exe = os.path.join(tmp_dir, "LyricVibe.exe")

        with patch("sys.frozen", True, create=True), patch("sys.executable", fake_exe):
            resolved = get_asset_path("CustomFont.ttf")
            assert resolved == fake_font
