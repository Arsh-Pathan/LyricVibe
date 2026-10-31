"""
LyricVibe - Cinematic 165Hz Floating Lyrics Overlay for Spotify.
"""

__version__ = "1.1.0"
__author__ = "Arsh Pathan"

from lyricvibe.lyrics.fetcher import LyricLine, fetch_lyrics_smart
from lyricvibe.media.client import PlaybackState, SpotifyClient
from lyricvibe.ui.overlay import FloatingLyricsWidget, run_app
from lyricvibe.ui.settings import SettingsDialog

__all__ = [
    "FloatingLyricsWidget",
    "LyricLine",
    "PlaybackState",
    "SettingsDialog",
    "SpotifyClient",
    "fetch_lyrics_smart",
    "run_app",
]
