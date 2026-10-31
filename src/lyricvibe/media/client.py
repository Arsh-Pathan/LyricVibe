"""
Windows Media SMTC Spotify Client.
Reads directly from Windows System Media Transport Controls (SMTC).
- Works with FREE Spotify accounts (NO Premium needed).
- High precision sync: calculates exact audio playback timestamp without drift.
- Supports both Python script and PyInstaller frozen EXE.
- Resilient auto-restarting background listener process with thread-safe telemetry.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import threading
import time
from dataclasses import dataclass

import requests

logger = logging.getLogger(__name__)


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
    """Manages background PowerShell SMTC telemetry streaming and playback state."""

    def __init__(self):
        self._state: PlaybackState | None = None
        self._proc: subprocess.Popen | None = None
        self._art_cache: dict[str, str] = {}
        self._art_pending: set[str] = set()
        self._lock = threading.Lock()
        self._stopped = False
        self._reader_thread_handle = threading.Thread(
            target=self._reader_loop, daemon=True, name="LyricVibe-SMTC-Reader"
        )
        self._reader_thread_handle.start()

    def _resolve_ps_script(self) -> str:
        candidates = []
        try:
            from lyricvibe.core.paths import get_asset_path

            candidates.append(get_asset_path("spotify_listener.ps1"))
            candidates.append(get_asset_path("src/lyricvibe/media/spotify_listener.ps1"))
        except ImportError:
            pass

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

        return candidates[0] if candidates else "spotify_listener.ps1"

    def _spawn_process(self) -> subprocess.Popen | None:
        """Spawns the background PowerShell WinRT listener process."""
        ps_script = self._resolve_ps_script()

        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = 0

        creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0

        try:
            return subprocess.Popen(
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
                creationflags=creationflags,
            )
        except (subprocess.SubprocessError, OSError) as e:
            logger.warning("[spotify_client] Failed to spawn PowerShell listener: %s", e)
            return None

    def _fetch_art(self, track: str, artist: str):
        """Fetches 300x300 album artwork asynchronously from iTunes with deduplication."""
        cache_key = f"{artist}_{track}"
        try:
            query = f"{artist} {track}".strip()
            resp = requests.get(
                "https://itunes.apple.com/search",
                params={"term": query, "entity": "song", "limit": 1},
                timeout=4.0,
            )
            if resp.status_code == 200:
                payload = resp.json()
                results = payload.get("results", []) if isinstance(payload, dict) else []
                if results and isinstance(results[0], dict):
                    art = results[0].get("artworkUrl100", "").replace("100x100bb", "300x300bb")
                    with self._lock:
                        if len(self._art_cache) > 200:
                            self._art_cache.pop(next(iter(self._art_cache)), None)
                        self._art_cache[cache_key] = art
                        if self._state and self._state.track_name == track and not self._state.album_art_url:
                            self._state.album_art_url = art
                    return
        except (requests.RequestException, ValueError, AttributeError) as e:
            logger.debug("[spotify_client] Artwork request failed: %s", e)
        finally:
            with self._lock:
                self._art_pending.discard(cache_key)
                if cache_key not in self._art_cache:
                    if len(self._art_cache) > 200:
                        self._art_cache.pop(next(iter(self._art_cache)), None)
                    self._art_cache[cache_key] = ""

    def _reader_loop(self):
        """Continuous reader loop with automatic reconnection on process termination."""
        backoff_sec = 0.5

        while not self._stopped:
            self._proc = self._spawn_process()
            if not self._proc or not self._proc.stdout:
                time.sleep(backoff_sec)
                backoff_sec = min(backoff_sec * 1.5, 5.0)
                continue

            backoff_sec = 0.5  # Reset backoff after successful connection

            try:
                for raw_line in self._proc.stdout:
                    if self._stopped:
                        break

                    line = raw_line.strip()
                    if not line:
                        continue

                    try:
                        data = json.loads(line)
                        if not isinstance(data, dict):
                            continue
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
                        cache_key = f"{artist}_{track}"

                        with self._lock:
                            art_url = self._art_cache.get(cache_key, "")
                            needs_fetch = cache_key not in self._art_cache and cache_key not in self._art_pending
                            if needs_fetch:
                                self._art_pending.add(cache_key)

                        if needs_fetch:
                            threading.Thread(
                                target=self._fetch_art,
                                args=(track, artist),
                                daemon=True,
                                name=f"LyricVibe-Art-{cache_key[:20]}",
                            ).start()

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

                    except (json.JSONDecodeError, ValueError, AttributeError, TypeError):
                        continue

            except (OSError, ValueError) as e:
                logger.debug("[spotify_client] Reader stream interrupted: %s", e)

            # Clean up dead process before potential restart
            if self._proc:
                try:
                    self._proc.terminate()
                except OSError:
                    pass
                self._proc = None

            if not self._stopped:
                time.sleep(1.0)

    def get_playback(self) -> PlaybackState | None:
        """Returns the latest playback snapshot in a thread-safe manner."""
        with self._lock:
            if not self._state:
                return None
            cache_key = f"{self._state.artist_name}_{self._state.track_name}"
            cached_art = self._art_cache.get(cache_key, "")
            if cached_art and not self._state.album_art_url:
                self._state.album_art_url = cached_art
            return self._state

    def estimate_progress(self, state: PlaybackState) -> float:
        """Calculates exact current position using freshly polled position + local clock delta.

        The PowerShell listener re-reads SMTC position every 250ms and stores it alongside
        a local high-resolution timestamp. We calculate:
            current_pos = recorded_pos + (current_time - recorded_time)
        This completely eliminates timestamp drift while tracking playback seamlessly.
        """
        if not state.is_playing:
            return state.progress_sec

        now = time.time()
        elapsed = now - state.local_received_at
        # Clamp elapsed to a sane range (shouldn't exceed 5.0 seconds between polling frames)
        elapsed = max(0.0, min(elapsed, 5.0))
        pos = max(0.0, state.progress_sec + elapsed)
        return min(pos, state.duration_sec) if state.duration_sec > 0 else pos

    def close(self):
        """Cleanly terminates the client and stops the background PowerShell process."""
        self._stopped = True
        if self._proc:
            try:
                self._proc.terminate()
                self._proc.wait(timeout=0.8)
            except (subprocess.SubprocessError, OSError):
                try:
                    self._proc.kill()
                except OSError:
                    pass
            self._proc = None
