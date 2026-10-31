"""
Path and asset resolution utilities for LyricVibe.
Supports execution from source, development environments, and frozen PyInstaller bundles.
"""

import os
import sys


def get_base_dir() -> str:
    """Returns the base runtime directory (supports PyInstaller bundle & source)."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return sys._MEIPASS
    
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
    """Returns absolute path to the settings.json file.
    Prefers portable settings next to executable if writable, falling back to %APPDATA%/LyricVibe.
    """
    if getattr(sys, "frozen", False):
        exe_dir = os.path.dirname(sys.executable)
        portable_path = os.path.join(exe_dir, "settings.json")
        if os.path.exists(portable_path) or os.access(exe_dir, os.W_OK):
            return portable_path
        appdata = os.environ.get("APPDATA", os.path.expanduser("~"))
        return os.path.join(appdata, "LyricVibe", "settings.json")

    base = get_base_dir()
    return os.path.join(base, "settings.json")


def get_executable_command() -> str:
    """Returns the executable command line for auto-start (handling frozen and script modes)."""
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'

    base = get_base_dir()
    dist_exe = os.path.join(base, "dist", "LyricVibe.exe")
    if os.path.exists(dist_exe):
        return f'"{dist_exe}"'

    main_py = os.path.join(base, "main.py")
    python_dir = os.path.dirname(sys.executable)
    pythonw = os.path.join(python_dir, "pythonw.exe")
    if not os.path.exists(pythonw):
        pythonw = sys.executable
    return f'"{pythonw}" "{main_py}"'
