"""
Lyrics fetcher — uses LRCLIB (free, no API key) for synced lyrics.
Automatically cleans track/artist names (stripping Spotify tags like 'From Dabangg')
and converts Hindi/Urdu to clean Roman Hinglish.
Provides connection pooling, retry resilience, multi-timestamp LRC parsing, and bounded caching.
"""

from __future__ import annotations

import collections
import logging
import re
from dataclasses import dataclass

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

try:
    from lyricvibe.core.transliteration import to_hinglish
except ImportError:
    from hinglish_converter import to_hinglish


@dataclass
class LyricLine:
    """A single line of lyrics with its timestamp in seconds."""

    time_sec: float
    text: str


# Bounded in-memory cache to prevent unbounded growth during long playback sessions (max 250 songs)
_MAX_CACHE_SIZE = 250
_LYRICS_CACHE: collections.OrderedDict[str, list[LyricLine] | None] = collections.OrderedDict()


def _get_http_session() -> requests.Session:
    """Creates a shared HTTP session with connection pooling and retries."""
    session = requests.Session()
    retries = Retry(
        total=2,
        backoff_factor=0.3,
        status_forcelist=[500, 502, 503, 504],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retries, pool_connections=5, pool_maxsize=10)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


_HTTP_SESSION = _get_http_session()


def clean_track_title(title: str) -> str:
    """
    Cleans Spotify track titles by stripping movie tags like (From "Dabangg"),
    featured artists, remaster notes, audio/video markers, and visualizer tags
    to dramatically improve exact and fuzzy search match rates on LRCLIB.
    """
    if not title:
        return ""

    t = title

    # Strip (From "...") or [From "..."] or (Soundtrack ...)
    t = re.sub(r'[\(\[]\s*(from|soundtrack)\s+[^)\]]+[\)\]]', '', t, flags=re.IGNORECASE)

    # Strip (feat. ...) or [feat. ...] or (ft. ...)
    t = re.sub(r'[\(\[]\s*(feat|ft|featuring|with)\.?\s+[^)\]]+[\)\]]', '', t, flags=re.IGNORECASE)

    # Strip video and audio markers: (Official Music Video), (Lyric Video), [Visualizer], etc.
    t = re.sub(
        r'[\(\[]\s*(official\s*(music\s*)?(video|audio|lyric\s*video)?|lyric\s*video|audio|visualizer)[^)\]]*[\)\]]',
        '',
        t,
        flags=re.IGNORECASE,
    )

    # Strip remaster / live / deluxe / version / edition / radio edit / acoustic
    t = re.sub(
        r'[\(\[]\s*(remastered|remaster|live|bonus|deluxe|version|edition|original|ost|lofi|slowed|reverb|radio\s*edit|acoustic|instrumental)[^)\]]*[\)\]]',
        '',
        t,
        flags=re.IGNORECASE,
    )

    # Strip trailing " - From ..." or " - Original Motion Picture Soundtrack" or " - 2013 Remaster"
    t = re.sub(
        r'\s*-\s*(?:\d{4}\s+)?(from\s+|original|soundtrack|remaster(?:ed)?|bonus|live|radio\s*edit|anniversary).*$',
        '',
        t,
        flags=re.IGNORECASE,
    )

    # Strip remaining trailing empty brackets
    t = re.sub(r'[\(\[]\s*[\)\]]', '', t)

    # Strip any trailing parenthetical if preceded by a clean title
    t = re.sub(r'\s*\([^)]*\)\s*$', '', t).strip()

    return t.strip() if t.strip() else title.strip()


def get_primary_artist(artist: str) -> str:
    """Extracts first artist if multiple are comma-separated or joined by & / x / feat."""
    if not artist:
        return ""
    # Split by comma, ampersand, slash, 'x', or 'feat'
    parts = re.split(r'[,&/]|\bfeat\.?\b|\bft\.?\b|\bx\b', artist, flags=re.IGNORECASE)
    return parts[0].strip() if parts else artist.strip()


def parse_lrc(lrc_text: str) -> list[LyricLine]:
    """
    Parse standard and multi-tag LRC format lyrics into a sorted list of LyricLine objects.
    Supports formats like:
      [01:23.45] Single line
      [01:23.456] Three-digit millisecond line
      [01:23:45] Colon fractional separator
      [00:10.00][00:25.00] Repeated chorus line
    """
    if not lrc_text or not lrc_text.strip():
        return []

    lines: list[LyricLine] = []
    # Pattern to find all timestamp tags on a line: [mm:ss.xx] or [mm:ss:xx]
    tag_pattern = re.compile(r"\[(\d{1,3}):(\d{2})[\.:](\d{2,3})\]")

    for raw_line in lrc_text.strip().splitlines():
        trimmed = raw_line.strip()
        if not trimmed:
            continue

        matches = list(tag_pattern.finditer(trimmed))
        if not matches:
            continue

        # Extract lyric text by removing all timestamp tags
        lyric_text = tag_pattern.sub("", trimmed).strip()
        if not lyric_text:
            continue

        roman_lyric = to_hinglish(lyric_text)

        for match in matches:
            minutes = int(match.group(1))
            seconds = int(match.group(2))
            frac_str = match.group(3)
            frac = int(frac_str) / (1000.0 if len(frac_str) == 3 else 100.0)
            total_sec = round(minutes * 60 + seconds + frac, 3)
            lines.append(LyricLine(time_sec=total_sec, text=roman_lyric))

    lines.sort(key=lambda item: item.time_sec)
    return lines


def is_romanized(text: str) -> bool:
    """Checks whether the text is already Romanized (Latin characters)."""
    if not text:
        return True
    return not any(('\u0900' <= ch <= '\u097f') or ('\u0600' <= ch <= '\u06ff') for ch in text)


def _cache_put(key: str, lyrics: list[LyricLine] | None):
    """Stores result in bounded cache with LRU eviction."""
    if key in _LYRICS_CACHE:
        _LYRICS_CACHE.move_to_end(key)
    _LYRICS_CACHE[key] = lyrics
    if len(_LYRICS_CACHE) > _MAX_CACHE_SIZE:
        _LYRICS_CACHE.popitem(last=False)


def _try_get(params: dict) -> list[LyricLine] | None:
    try:
        resp = _HTTP_SESSION.get(
            "https://lrclib.net/api/get",
            params=params,
            headers={"User-Agent": "LyricVibe/1.0 (Windows; 165Hz Floating Lyrics)"},
            timeout=5.0,
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
                    cleaned = line_text.strip()
                    if cleaned:
                        lines.append(LyricLine(time_sec=float(i * 4.0), text=to_hinglish(cleaned)))
                return lines
    except requests.RequestException as e:
        logger.debug("[fetcher] Exact GET failed for %s: %s", params, e)
    return None


def _try_search(query: str, duration_sec: float = 0) -> list[LyricLine] | None:
    try:
        resp = _HTTP_SESSION.get(
            "https://lrclib.net/api/search",
            params={"q": query},
            headers={"User-Agent": "LyricVibe/1.0 (Windows; 165Hz Floating Lyrics)"},
            timeout=5.0,
        )
        if resp.status_code == 200:
            results = resp.json()
            if results and isinstance(results, list):
                # Score results to find the EXACT version matching playback duration
                def score_item(item: dict) -> int:
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
                            cleaned = line_text.strip()
                            if cleaned:
                                lines.append(LyricLine(time_sec=float(i * 4.0), text=to_hinglish(cleaned)))
                        return lines
    except requests.RequestException as e:
        logger.debug("[fetcher] Search failed for query %r: %s", query, e)
    return None


def get_lyrics(
    track_name: str,
    artist_name: str,
    album_name: str = "",
    duration_sec: float = 0,
) -> list[LyricLine] | None:
    """
    Fetches synchronized lyrics for the given track using exact LRCLIB lookup,
    falling back to intelligent query search with duration scoring.
    """
    if not track_name or not track_name.strip():
        return None

    cache_key = f"{track_name.strip().lower()}||{artist_name.strip().lower()}"
    if cache_key in _LYRICS_CACHE:
        _LYRICS_CACHE.move_to_end(cache_key)
        return _LYRICS_CACHE[cache_key]

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
            _cache_put(cache_key, lyrics)
            return lyrics

    # 2. Try duration-aware search
    queries = [
        f"{primary_artist} {clean_title}".strip(),
        f"{artist_name} {clean_title}".strip(),
        clean_title,
    ]
    for q in queries:
        lyrics = _try_search(q, duration_sec)
        if lyrics:
            _cache_put(cache_key, lyrics)
            return lyrics

    # 3. Fallback GET without duration constraint
    for p in exact_params:
        p_no_dur = {k: v for k, v in p.items() if k != "duration"}
        lyrics = _try_get(p_no_dur)
        if lyrics:
            _cache_put(cache_key, lyrics)
            return lyrics

    _cache_put(cache_key, None)
    return None


fetch_lyrics_smart = get_lyrics
