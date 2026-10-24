"""
LyricVibe - Cinematic 165Hz Floating Lyrics Overlay for Spotify.
"""

__version__ = "1.0.0"
__author__ = "Arsh Pathan"

from lyricvibe.ui.overlay import FloatingLyricsWidget, run_app
from lyricvibe.ui.settings import SettingsDialog
from lyricvibe.media.client import SpotifyClient, PlaybackState
from lyricvibe.lyrics.fetcher import fetch_lyrics_smart, LyricLine

__all__ = [
    "FloatingLyricsWidget",
    "SettingsDialog",
    "run_app",
    "SpotifyClient",
    "PlaybackState",
    "fetch_lyrics_smart",
    "LyricLine",
]
