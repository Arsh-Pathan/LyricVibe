"""
LyricVibe — Cinematic 165Hz Floating Lyrics Overlay for Spotify.

Clean entry point for the modular LyricVibe application.
"""

import os
import sys

# Ensure src/ is on sys.path
root_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(root_dir, "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from lyricvibe.ui.overlay import run_app

if __name__ == "__main__":
    sys.exit(run_app())
