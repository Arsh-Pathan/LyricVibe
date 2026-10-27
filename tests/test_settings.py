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
            custom["highlight_color"] = "#FF00FF"

            save_settings(custom)
            assert os.path.exists(test_file)

            loaded = load_settings()
            assert loaded["font_size"] == 54
            assert loaded["target_fps"] == 144
            assert loaded["highlight_color"] == "#FF00FF"


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
