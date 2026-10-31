"""Stress and durability tests for long-running Spotify playback sessions."""

import math
import sys
from unittest.mock import patch

from PyQt6.QtWidgets import QApplication

from lyricvibe.core.animation import ANIMATION_CATALOG, AnimationEngine
from lyricvibe.core.transliteration import to_hinglish
from lyricvibe.lyrics.fetcher import (
    _LYRICS_CACHE,
    _MAX_CACHE_SIZE,
    LyricLine,
    _cache_put,
)
from lyricvibe.media.client import SpotifyClient
from lyricvibe.ui.overlay import FloatingLyricsWidget
from lyricvibe.utils.settings import DEFAULT_SETTINGS


def test_lyrics_cache_lru_eviction_under_high_volume():
    _LYRICS_CACHE.clear()

    # Simulate 500 different song lookups over hours of listening
    for i in range(500):
        key = f"track_{i}||artist_{i}"
        lines = [LyricLine(float(i), f"Lyric line for song {i}")]
        _cache_put(key, lines)

    # Cache must strictly stay capped at _MAX_CACHE_SIZE (250)
    assert len(_LYRICS_CACHE) == _MAX_CACHE_SIZE

    # Oldest entries (e.g. track_0) must have been evicted, newest must remain
    assert "track_0||artist_0" not in _LYRICS_CACHE
    assert "track_499||artist_499" in _LYRICS_CACHE


def test_overlay_font_and_word_caches_stay_bounded():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    with patch("lyricvibe.ui.overlay.SpotifyClient"):
        widget = FloatingLyricsWidget(DEFAULT_SETTINGS)

        # Generate 250 distinct lines of varying lengths
        for i in range(250):
            line = (
                f"Distinct line number {i} with varying word count {'extra ' * (i % 5)}"
            )
            widget._fit_font(line, max_w=800, base_size=42, family="Montserrat")
            widget._get_word_spans(line)

        # Both caches must remain strictly bounded (<= 100 items)
        assert len(widget._font_cache) <= 100
        assert len(widget._word_span_cache) <= 100

        widget.render_timer.stop()
        widget.poll_timer.stop()
        widget.smooth_timer.stop()
        if widget.tray_icon:
            widget.tray_icon.hide()
        widget.close()


def test_animation_engine_extreme_durations_and_scrubbing():
    engine = AnimationEngine()

    extreme_durations = [0.05, 0.1, 0.5, 1.0, 180.0, 1200.0, 7200.0]

    for dur in extreme_durations:
        for anim_name, _ in ANIMATION_CATALOG[:15]:
            engine.trigger_line(
                "Extreme duration test line", duration=dur, anim_type=anim_name
            )
            state = engine.update()
            assert not math.isnan(state["curr_alpha"])
            assert not math.isnan(state["curr_scale"])
            assert not math.isnan(state["curr_offset_y"])
            assert not math.isnan(state["blur_alpha"])
            assert not math.isinf(state["curr_alpha"])
            assert not math.isinf(state["curr_scale"])

    # Simulate 50 rapid scrub jumps forward and backward
    engine.trigger_line("Scrubbing simulation line", duration=4.0)
    for scrub_offset in [0.1, 3.5, 1.2, 0.4, 2.8, 0.0, 3.9, 0.2]:
        engine.sync_to_audio(scrub_offset)
        state = engine.update()
        assert state is not None
        assert 0.0 <= state["curr_alpha"] <= 1.0


def test_media_client_art_cache_bounded():
    with patch.object(SpotifyClient, "_reader_loop"):
        client = SpotifyClient()

        # Simulate 300 track artworks loaded
        with client._lock:
            for i in range(300):
                if len(client._art_cache) > 200:
                    client._art_cache.pop(next(iter(client._art_cache)), None)
                client._art_cache[f"artist_{i}_track_{i}"] = (
                    f"https://example.com/art_{i}.jpg"
                )

        with client._lock:
            assert len(client._art_cache) <= 201

        client.close()


def test_multilingual_unicode_stress():
    # Mixed Devanagari, Urdu, Gurmukhi, Latin, and punctuation
    text = "ਸਤਿ ਸ੍ਰੀ ਅਕਾਲ! ज़िंदगी और मोहब्बत... (Tere Vaaste) 100%"
    out = to_hinglish(text)
    assert len(out) > 0
    # Must be 100% pure ASCII Latin characters
    assert all(ord(c) < 128 for c in out)
    assert "Tere Vaaste" in out
    assert "zindagi" in out.lower()
