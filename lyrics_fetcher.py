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


def _try_search(query: str, duration_sec: float = 0) -> list[LyricLine] | None:
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
                # Score results to find the EXACT version matching playback duration
                def score_item(item):
                    score = 0
                    synced = item.get("syncedLyrics")
                    if not synced:
                        return -1000
                    score += 100
                    # Duration match (+/- 3 seconds is ideal)
                    item_dur = float(item.get("duration", 0))
                    if duration_sec > 0 and item_dur > 0:
                        diff = abs(item_dur - duration_sec)
                        if diff <= 1.5:
                            score += 80
                        elif diff <= 3.5:
                            score += 50
                        elif diff <= 8.0:
                            score += 10
                        else:
                            score -= min(int(diff * 5), 100)
                    # Romanized preference
                    if is_romanized(synced):
                        score += 30
                    return score

                scored = [(score_item(it), it) for it in results]
                scored.sort(key=lambda x: x[0], reverse=True)

                for sc, best_item in scored:
                    if sc > 0:
                        synced = best_item.get("syncedLyrics")
                        if synced:
                            return parse_lrc(synced)

                # Fallback to any synced
                for it in results:
                    synced = it.get("syncedLyrics")
                    if synced:
                        return parse_lrc(synced)

                # Fallback to plain
                for it in results:
                    plain = it.get("plainLyrics")
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

    # 1. First try exact GET by title, artist and duration (highest accuracy)
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

    # 2. Try duration-aware search
    queries = [
        f"{primary_artist} {clean_title}",
        f"{artist_name} {clean_title}",
        f"{clean_title}",
    ]
    for q in queries:
        lyrics = _try_search(q, duration_sec)
        if lyrics:
            return lyrics

    # 3. Fallback GET without duration constraint
    for p in exact_params:
        p_no_dur = {k: v for k, v in p.items() if k != "duration"}
        lyrics = _try_get(p_no_dur)
        if lyrics:
            return lyrics

    return None
