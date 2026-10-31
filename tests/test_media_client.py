"""Tests for media client, playback state, and monotonic progress tracking."""

import time
from unittest.mock import MagicMock, patch

from lyricvibe.media.client import PlaybackState, SpotifyClient


def test_playback_state_dataclass():
    state = PlaybackState(
        is_playing=True,
        track_name="Starboy",
        artist_name="The Weeknd",
        album_name="Starboy",
        album_art_url="https://example.com/art.jpg",
        progress_sec=30.0,
        duration_sec=230.0,
        track_id="the_weeknd_starboy",
        updated_at=time.time(),
        local_received_at=time.time(),
    )
    assert state.is_playing is True
    assert state.track_name == "Starboy"
    assert state.progress_sec == 30.0
    assert state.duration_sec == 230.0


def test_estimate_progress_paused():
    with patch.object(SpotifyClient, "_reader_loop"):
        client = SpotifyClient()
        now = time.time()
        state = PlaybackState(
            is_playing=False,
            track_name="Song",
            artist_name="Artist",
            album_name="Album",
            album_art_url="",
            progress_sec=45.0,
            duration_sec=200.0,
            track_id="id1",
            updated_at=now - 2.0,
            local_received_at=now - 2.0,
        )
        # When paused, progress must not advance
        assert client.estimate_progress(state) == 45.0
        client.close()


def test_estimate_progress_playing():
    with patch.object(SpotifyClient, "_reader_loop"):
        client = SpotifyClient()
        now = time.time()
        state = PlaybackState(
            is_playing=True,
            track_name="Song",
            artist_name="Artist",
            album_name="Album",
            album_art_url="",
            progress_sec=10.0,
            duration_sec=100.0,
            track_id="id1",
            updated_at=now - 0.5,
            local_received_at=now - 0.5,
        )
        prog = client.estimate_progress(state)
        # Should be roughly 10.5 seconds (progress + elapsed delta)
        assert 10.4 <= prog <= 10.7
        client.close()


def test_estimate_progress_clamped_to_duration():
    with patch.object(SpotifyClient, "_reader_loop"):
        client = SpotifyClient()
        now = time.time()
        state = PlaybackState(
            is_playing=True,
            track_name="Song",
            artist_name="Artist",
            album_name="Album",
            album_art_url="",
            progress_sec=99.5,
            duration_sec=100.0,
            track_id="id1",
            updated_at=now - 2.0,
            local_received_at=now - 2.0,
        )
        prog = client.estimate_progress(state)
        # Must be clamped at duration (100.0)
        assert prog == 100.0
        client.close()


def test_client_close_terminates_proc():
    with patch.object(SpotifyClient, "_reader_loop"):
        client = SpotifyClient()
        mock_proc = MagicMock()
        client._proc = mock_proc

        client.close()
        assert client._stopped is True
        mock_proc.terminate.assert_called_once()
        assert client._proc is None


def test_estimate_progress_negative_progress_clamped_to_zero():
    with patch.object(SpotifyClient, "_reader_loop"):
        client = SpotifyClient()
        now = time.time()
        state = PlaybackState(
            is_playing=True,
            track_name="Song",
            artist_name="Artist",
            album_name="Album",
            album_art_url="",
            progress_sec=-2.0,
            duration_sec=100.0,
            track_id="id1",
            updated_at=now,
            local_received_at=now,
        )
        prog = client.estimate_progress(state)
        assert prog >= 0.0
        client.close()


def test_fetch_art_malformed_payload_safety():
    with patch.object(SpotifyClient, "_reader_loop"):
        client = SpotifyClient()

        # Simulate iTunes returning unexpected non-dict or empty payload
        with patch("lyricvibe.media.client.requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = ["not", "a", "dict"]
            mock_get.return_value = mock_resp

            # Must handle cleanly without raising AttributeError or crashing
            client._fetch_art("Song Title", "Artist Name")
            cache_key = "Artist Name_Song Title"
            assert client._art_cache.get(cache_key) == ""

        client.close()
