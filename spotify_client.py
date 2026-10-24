"""
Windows Media SMTC Spotify Client.
Reads directly from Windows System Media Transport Controls (SMTC).
- Works with FREE Spotify accounts (NO Premium needed).
- High precision sync: calculates exact audio playback timestamp without drift.
- Supports both Python script and PyInstaller frozen EXE.
"""

import json
import os
import sys
import subprocess
import threading
import time
from dataclasses import dataclass
import requests

import config


@dataclass
class PlaybackState:
    """Current Spotify playback information."""
    is_playing: bool
    track_name: str
    artist_name: str
    album_name: str
    album_art_url: str
    progress_sec: float
    duration_sec: float
    track_id: str
    updated_at: float        # timestamp when Windows SMTC last updated
    local_received_at: float # local clock when we received the update


class SpotifyClient:
    def __init__(self):
        self._state: PlaybackState | None = None
        self._proc: subprocess.Popen | None = None
        self._art_cache: dict[str, str] = {}
        self._lock = threading.Lock()
        self._start_listener()

    def _resolve_ps_script(self) -> str:
        candidates = []
        if getattr(sys, "frozen", False):
            meipass = getattr(sys, "_MEIPASS", None)
            if meipass:
                candidates.append(os.path.join(meipass, "spotify_listener.ps1"))
            candidates.append(os.path.join(os.path.dirname(sys.executable), "spotify_listener.ps1"))

        script_dir = os.path.dirname(os.path.abspath(__file__))
        candidates.append(os.path.join(script_dir, "spotify_listener.ps1"))
        candidates.append(os.path.join(os.getcwd(), "spotify_listener.ps1"))

        for path in candidates:
            if os.path.exists(path):
                return path

        return candidates[0]

    def _start_listener(self):
        ps_script = self._resolve_ps_script()

        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = 0

        try:
            self._proc = subprocess.Popen(
                [
                    "powershell.exe",
                    "-NoProfile",
                    "-ExecutionPolicy", "Bypass",
                    "-File", ps_script,
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                text=True,
                encoding="utf-8",
                bufsize=1,
                startupinfo=startupinfo,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )

            thread = threading.Thread(target=self._reader_thread, daemon=True)
            thread.start()
        except Exception as e:
            print(f"[spotify_client] Failed to start listener: {e}")

    def _fetch_art(self, track: str, artist: str) -> str:
        cache_key = f"{artist}_{track}"
        if cache_key in self._art_cache:
            return self._art_cache[cache_key]
        try:
            query = f"{artist} {track}"
            resp = requests.get(
                "https://itunes.apple.com/search",
                params={"term": query, "entity": "song", "limit": 1},
                timeout=4,
            )
            if resp.status_code == 200:
                results = resp.json().get("results", [])
                if results:
                    art = results[0].get("artworkUrl100", "").replace("100x100bb", "300x300bb")
                    self._art_cache[cache_key] = art
                    return art
        except Exception:
            pass
        self._art_cache[cache_key] = ""
        return ""

    def _reader_thread(self):
        if not self._proc or not self._proc.stdout:
            return

        for raw_line in self._proc.stdout:
            line = raw_line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                track = data.get("track", "").strip()
                artist = data.get("artist", "").strip()
                album = data.get("album", "").strip()
                is_playing = bool(data.get("is_playing", False))
                position = float(data.get("position", 0.0))
                duration = float(data.get("duration", 0.0))
                updated_at = float(data.get("updated_at", 0.0))

                if not track:
                    with self._lock:
                        self._state = None
                    continue

                track_id = f"{artist} - {track}"

                art_url = self._art_cache.get(f"{artist}_{track}", "")
                if not art_url and track_id:
                    threading.Thread(target=self._fetch_art, args=(track, artist), daemon=True).start()

                state = PlaybackState(
                    is_playing=is_playing,
                    track_name=track,
                    artist_name=artist,
                    album_name=album,
                    album_art_url=art_url,
                    progress_sec=position,
                    duration_sec=duration,
                    track_id=track_id,
                    updated_at=updated_at,
                    local_received_at=time.time(),
                )

                with self._lock:
                    self._state = state

            except Exception:
                continue

    def get_playback(self) -> PlaybackState | None:
        with self._lock:
            if not self._state:
                return None
            cache_key = f"{self._state.artist_name}_{self._state.track_name}"
            cached_art = self._art_cache.get(cache_key, "")
            if cached_art and not self._state.album_art_url:
                self._state.album_art_url = cached_art
            return self._state

    def estimate_progress(self, state: PlaybackState) -> float:
        """Calculates exact current position without drift or double-counting."""
        if not state.is_playing:
            return state.progress_sec

        now = time.time()
        # Prefer elapsed time since Windows SMTC timestamp
        if state.updated_at > 0:
            elapsed = now - state.updated_at
            if 0 <= elapsed < 300:
                pos = state.progress_sec + elapsed
                return min(pos, state.duration_sec) if state.duration_sec > 0 else pos

        # Fallback to local receive clock
        elapsed = now - state.local_received_at
        pos = state.progress_sec + elapsed
        return min(pos, state.duration_sec) if state.duration_sec > 0 else pos

    def close(self):
        if self._proc:
            try:
                self._proc.terminate()
            except Exception:
                pass
