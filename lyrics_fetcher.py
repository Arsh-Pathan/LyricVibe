"""
Lyrics fetcher — uses LRCLIB (free, no API key) for synced lyrics.
Automatically cleans track/artist names (stripping Spotify tags like 'From Dabangg')
and converts Hindi/Urdu to clean Roman Hinglish.
"""

import re
import requests
from dataclasses import dataclass
from hinglish_converter import to_hinglish


@dataclass
class LyricLine:
    """A single line of lyrics with its timestamp in seconds."""
    time_sec: float
    text: str


def clean_track_title(title: str) -> str:
    """
    Cleans Spotify track titles by stripping movie tags like (From "Dabangg"),
    featured artists, remaster notes, etc., to dramatically improve match rates.
    """
    if not title:
        return ""
    # Strip (From "...") or [From "..."]
    t = re.sub(r'[\(\[]\s*from\s+[^)\]]+[\)\]]', '', title, flags=re.IGNORECASE).strip()
    # Strip (feat. ...) or [feat. ...]
    t = re.sub(r'[\(\[]\s*(feat|ft)\.?\s+[^)\]]+[\)\]]', '', t, flags=re.IGNORECASE).strip()
    # Strip remaster / live / deluxe / version
    t = re.sub(r'[\(\[]\s*(remastered|live|bonus|deluxe|version|edition|original|ost|audio|video|lofi)[^)\]]*[\)\]]', '', t, flags=re.IGNORECASE).strip()
    # Strip " - From ..." or " - Original Motion Picture Soundtrack"
    t = re.sub(r'\s*-\s*(from\s+|original|soundtrack|remastered).*$', '', t, flags=re.IGNORECASE).strip()
    # Strip any trailing parenthetical
    t = re.sub(r'\s*\([^)]*\)\s*$', '', t).strip()
    return t if t else title


def get_primary_artist(artist: str) -> str:
    """Extracts first artist if multiple are comma-separated."""
    if not artist:
        return ""
    parts = re.split(r'[,&/]', artist)
    return parts[0].strip() if parts else artist.strip()


def parse_lrc(lrc_text: str) -> list[LyricLine]:
    """Parse LRC format lyrics into a list of LyricLine objects."""
    lines = []
    pattern = re.compile(r"\[(\d{2}):(\d{2})\.(\d{2,3})\](.*)")
    for raw_line in lrc_text.strip().splitlines():
        match = pattern.match(raw_line.strip())
        if match:
            minutes = int(match.group(1))
            seconds = int(match.group(2))
            centiseconds = match.group(3)
            if len(centiseconds) == 2:
                frac = int(centiseconds) / 100.0
            else:
                frac = int(centiseconds) / 1000.0
            total_sec = minutes * 60 + seconds + frac
            raw_lyric = match.group(4).strip()
            # Convert to Hinglish if Hindi or Urdu
            roman_lyric = to_hinglish(raw_lyric)
            lines.append(LyricLine(time_sec=total_sec, text=roman_lyric))
    lines.sort(key=lambda l: l.time_sec)
    return lines


def is_romanized(text: str) -> bool:
    if not text:
        return True
    return not any(('\u0900' <= ch <= '\u097f') or ('\u0600' <= ch <= '\u06ff') for ch in text)


def _try_get(params: dict) -> list[LyricLine] | None:
    try:
        resp = requests.get(
            "https://lrclib.net/api/get",
            params=params,
            headers={"User-Agent": "SpotifyLyricsOverlay/3.0"},
            timeout=5,
        )
        if resp.status_code == 200:
            data = resp.json()
            synced = data.get("syncedLyrics")
            if synced:
                return parse_lrc(synced)
            plain = data.get("plainLyrics")
            if plain:
                lines = []
                for i, line_text in enumerate(plain.strip().splitlines()):
                    lines.append(LyricLine(time_sec=i * 4.0, text=to_hinglish(line_text.strip())))
                return lines
    except Exception:
        pass
    return None


def _try_search(query: str) -> list[LyricLine] | None:
    try:
        resp = requests.get(
            "https://lrclib.net/api/search",
            params={"q": query},
            headers={"User-Agent": "SpotifyLyricsOverlay/3.0"},
            timeout=5,
        )
        if resp.status_code == 200:
            results = resp.json()
            if results and isinstance(results, list):
                # 1. Prefer Romanized synced lyrics
                for item in results:
                    synced = item.get("syncedLyrics")
                    if synced and is_romanized(synced):
                        return parse_lrc(synced)
                # 2. Prefer any synced lyrics
                for item in results:
                    synced = item.get("syncedLyrics")
                    if synced:
                        return parse_lrc(synced)
                # 3. Plain lyrics fallback
                for item in results:
                    plain = item.get("plainLyrics")
                    if plain:
                        lines = []
                        for i, line_text in enumerate(plain.strip().splitlines()):
                            lines.append(LyricLine(time_sec=i * 4.0, text=to_hinglish(line_text.strip())))
                        return lines
    except Exception:
        pass
    return None


def get_lyrics(track_name: str, artist_name: str, album_name: str = "",
               duration_sec: float = 0) -> list[LyricLine] | None:
    clean_title = clean_track_title(track_name)
    primary_artist = get_primary_artist(artist_name)

    # 1. Try search with clean title and primary artist (highest success for Bollywood)
    queries = [
        f"{primary_artist} {clean_title}",
        f"{artist_name} {clean_title}",
        f"{clean_title}",
    ]
    for q in queries:
        lyrics = _try_search(q)
        if lyrics:
            return lyrics

    # 2. Try exact GET with clean title
    exact_params = [
        {"track_name": clean_title, "artist_name": primary_artist},
        {"track_name": clean_title, "artist_name": artist_name},
        {"track_name": track_name, "artist_name": artist_name},
    ]
    for p in exact_params:
        if duration_sec > 0:
            p["duration"] = int(duration_sec)
        lyrics = _try_get(p)
        if lyrics:
            return lyrics

    return None
