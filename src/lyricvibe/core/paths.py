"""
Path and asset resolution utilities for LyricVibe.
Supports execution from source, development environments, and frozen PyInstaller bundles.
"""

import os
import sys


def get_base_dir() -> str:
    """Returns the base runtime directory (supports PyInstaller bundle & source)."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return getattr(sys, "_MEIPASS")
    
    # 3 levels up: src/lyricvibe/core -> src/lyricvibe -> src -> root
    core_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(os.path.dirname(os.path.dirname(core_dir)))
    return root_dir


def get_asset_path(relative_path: str) -> str:
    """Returns the absolute path to an asset, checking base dir and cwd."""
    base = get_base_dir()
    candidate = os.path.join(base, relative_path)
    if os.path.exists(candidate):
        return candidate
    
    candidate_cwd = os.path.join(os.getcwd(), relative_path)
    if os.path.exists(candidate_cwd):
        return candidate_cwd
    
    return candidate


def get_settings_file_path() -> str:
    """Returns absolute path to the settings.json file."""
    base = get_base_dir()
    # In frozen mode, write settings.json next to the executable
    if getattr(sys, "frozen", False):
        exe_dir = os.path.dirname(sys.executable)
        return os.path.join(exe_dir, "settings.json")
    return os.path.join(base, "settings.json")
