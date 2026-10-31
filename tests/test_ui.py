"""Tests for PyQt6 UI components, settings dialog, and signal bridges."""

import sys
from unittest.mock import MagicMock, patch

from PyQt6.QtNetwork import QLocalServer, QLocalSocket
from PyQt6.QtWidgets import QApplication

from lyricvibe.lyrics.fetcher import LyricLine
from lyricvibe.ui.overlay import IPC_SERVER_NAME, AppSignals, FloatingLyricsWidget
from lyricvibe.ui.settings import SettingsDialog
from lyricvibe.utils.settings import DEFAULT_SETTINGS


def test_app_signals():
    signals = AppSignals()
    received = []

    def on_sync(delta):
        received.append(delta)

    signals.hotkey_sync_adjust.connect(on_sync)
    signals.hotkey_sync_adjust.emit(-0.5)
    signals.hotkey_sync_adjust.emit(0.5)

    assert received == [-0.5, 0.5]


def test_settings_dialog_lifecycle():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    dlg = SettingsDialog(DEFAULT_SETTINGS)
    assert dlg.windowTitle() == "LyricVibe — Settings"
    assert dlg.settings["target_fps"] == 165
    assert dlg.settings["font_size"] == 42

    # Test preset application
    dlg._apply_preset(
        {
            "font_size": 48,
            "target_fps": 120,
        }
    )
    assert dlg.settings["font_size"] == 48
    assert dlg.settings["target_fps"] == 120

    dlg.close()


def test_floating_overlay_clickthrough_logic():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    with patch("lyricvibe.ui.overlay.SpotifyClient"):
        widget = FloatingLyricsWidget(DEFAULT_SETTINGS)
        assert widget.is_locked is False
        assert len(widget._registered_hotkeys) == 6

        with patch.object(widget, "_set_window_clickthrough") as mock_set:
            widget.toggle_lock()
            assert widget.is_locked is True
            mock_set.assert_called_once()

            widget.toggle_lock()
            assert widget.is_locked is False

        # Clean shutdown without calling QApplication.quit
        widget.render_timer.stop()
        widget.poll_timer.stop()
        widget.smooth_timer.stop()
        if widget.tray_icon:
            widget.tray_icon.hide()
        widget.close()


def test_fit_font_dynamic_scaling():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    with patch("lyricvibe.ui.overlay.SpotifyClient"):
        widget = FloatingLyricsWidget(DEFAULT_SETTINGS)
        font_short, _ = widget._fit_font(
            "Short line", max_w=800, base_size=42, family="Montserrat"
        )
        assert font_short.pointSize() == 42

        long_line = "This is an extraordinarily long sentence with numerous words that exceeds width"
        font_long, _ = widget._fit_font(
            long_line, max_w=200, base_size=42, family="Montserrat"
        )
        assert font_long.pointSize() < 42
        assert font_long.pointSize() >= 16

        widget.render_timer.stop()
        widget.poll_timer.stop()
        widget.smooth_timer.stop()
        if widget.tray_icon:
            widget.tray_icon.hide()
        widget.close()


def test_single_instance_ipc_server():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    test_server_name = f"{IPC_SERVER_NAME}_test_uniq"
    QLocalServer.removeServer(test_server_name)

    server = QLocalServer()
    assert server.listen(test_server_name) is True

    client = QLocalSocket()
    client.connectToServer(test_server_name)
    assert client.waitForConnected(500) is True

    client.write(b"PING\n")
    client.waitForBytesWritten(200)

    server.close()
    client.disconnectFromServer()
    QLocalServer.removeServer(test_server_name)


def test_settings_dialog_escape_key_and_close():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    dlg = SettingsDialog(DEFAULT_SETTINGS)
    dlg.show()
    assert dlg.isVisible() is True

    # Pressing Escape invokes reject()
    dlg.reject()
    assert dlg.isVisible() is False

    dlg.close()


def test_overlay_visibility_pauses_render_timer():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    with patch("lyricvibe.ui.overlay.SpotifyClient"):
        widget = FloatingLyricsWidget(DEFAULT_SETTINGS)
        widget.show()
        assert widget.render_timer.isActive() is True

        widget.hide()
        assert widget.render_timer.isActive() is False

        widget.show()
        assert widget.render_timer.isActive() is True

        widget.render_timer.stop()
        widget.poll_timer.stop()
        widget.smooth_timer.stop()
        if widget.tray_icon:
            widget.tray_icon.hide()
        widget.close()


def test_track_switch_race_condition_protection():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    with patch("lyricvibe.ui.overlay.SpotifyClient"):
        widget = FloatingLyricsWidget(DEFAULT_SETTINGS)
        widget.current_track_id = "Artist B - Song B"
        widget._current_fetch_id = 5

        stale_lyrics = [LyricLine(1.0, "Stale song lyrics")]
        valid_lyrics = [LyricLine(1.0, "Valid song lyrics")]

        # Case 1: Out-of-order response with stale fetch_id
        widget._on_lyrics_fetched(
            fetch_id=4, req_track_id="Artist B - Song B", lyrics=stale_lyrics
        )
        assert widget.lyrics is None

        # Case 2: Out-of-order response with mismatched track_id
        widget._on_lyrics_fetched(
            fetch_id=5, req_track_id="Artist A - Song A", lyrics=stale_lyrics
        )
        assert widget.lyrics is None

        # Case 3: Matching response
        widget._on_lyrics_fetched(
            fetch_id=5, req_track_id="Artist B - Song B", lyrics=valid_lyrics
        )
        assert widget.lyrics == valid_lyrics

        widget.render_timer.stop()
        widget.poll_timer.stop()
        widget.smooth_timer.stop()
        if widget.tray_icon:
            widget.tray_icon.hide()
        widget.close()


def test_multi_monitor_coordinate_preservation():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    with patch("lyricvibe.ui.overlay.SpotifyClient"):
        widget = FloatingLyricsWidget(DEFAULT_SETTINGS)

        # Simulate secondary monitor located at x = 1920
        mock_screen = MagicMock()
        mock_geo = MagicMock()
        mock_geo.x.return_value = 1920
        mock_geo.width.return_value = 2560
        mock_screen.availableGeometry.return_value = mock_geo

        with patch.object(widget, "screen", return_value=mock_screen):
            widget._on_screen_changed()
            assert widget.window_x == 1920
            assert widget.window_w == 2560
            assert widget.geometry().x() == 1920

        widget.render_timer.stop()
        widget.poll_timer.stop()
        widget.smooth_timer.stop()
        if widget.tray_icon:
            widget.tray_icon.hide()
        widget.close()


def test_word_span_cache_and_irregular_spaces():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    with patch("lyricvibe.ui.overlay.SpotifyClient"):
        widget = FloatingLyricsWidget(DEFAULT_SETTINGS)

        text_with_spaces = "  Multiple   spaces   between words  "
        spans = widget._get_word_spans(text_with_spaces)
        assert len(spans) == 4
        assert [s[0] for s in spans] == ["Multiple", "spaces", "between", "words"]

        # Verify spans match actual substring indices exactly
        for word, start, end in spans:
            assert text_with_spaces[start:end] == word

        widget.render_timer.stop()
        widget.poll_timer.stop()
        widget.smooth_timer.stop()
        if widget.tray_icon:
            widget.tray_icon.hide()
        widget.close()


def test_empty_lyric_line_clears_gracefully():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    with patch("lyricvibe.ui.overlay.SpotifyClient"):
        widget = FloatingLyricsWidget(DEFAULT_SETTINGS)
        widget.current_track_id = "Artist - Song"
        widget.lyrics = [
            LyricLine(10.0, "Real lyric"),
            LyricLine(20.0, "   "),
        ]

        from lyricvibe.media.client import PlaybackState

        state = PlaybackState(
            is_playing=True,
            track_name="Song",
            artist_name="Artist",
            album_name="Album",
            album_art_url="",
            progress_sec=20.0,
            duration_sec=200.0,
            track_id="Artist - Song",
            updated_at=0.0,
            local_received_at=0.0,
        )

        with patch.object(widget.spotify, "estimate_progress", return_value=20.0):
            widget._check_line_update(state)
            assert widget.current_line_text == ""
            assert widget.engine.curr_text == ""

        widget.render_timer.stop()
        widget.poll_timer.stop()
        widget.smooth_timer.stop()
        if widget.tray_icon:
            widget.tray_icon.hide()
        widget.close()


def test_instrumental_gap_and_scrub_revival():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    with patch("lyricvibe.ui.overlay.SpotifyClient"):
        widget = FloatingLyricsWidget(DEFAULT_SETTINGS)
        widget.current_track_id = "Artist - Song"
        widget.lyrics = [
            LyricLine(10.0, "Hello vocal line"),
            LyricLine(40.0, "Next line after 30s guitar solo"),
        ]

        from lyricvibe.media.client import PlaybackState

        state = PlaybackState(
            is_playing=True,
            track_name="Song",
            artist_name="Artist",
            album_name="Album",
            album_art_url="",
            progress_sec=11.0,
            duration_sec=200.0,
            track_id="Artist - Song",
            updated_at=0.0,
            local_received_at=0.0,
        )

        # 1. Active singing at 11s (adjusted ~11.2s)
        with patch.object(widget.spotify, "estimate_progress", return_value=11.0):
            widget._check_line_update(state)
            assert widget.current_line_text == "Hello vocal line"
            assert widget.engine.curr_text == "Hello vocal line"

        # 2. Reached instrumental break at 25s (line_elapsed = 15s > vocal_dur ~2.5s)
        with patch.object(widget.spotify, "estimate_progress", return_value=25.0):
            widget._check_line_update(state)
            # Text should be cleared during instrumental solo
            assert widget.engine.curr_text == ""
            assert widget.current_line_text == ""

        # 3. User rewinds back to 11.5s inside the same line's vocal window
        with patch.object(widget.spotify, "estimate_progress", return_value=11.5):
            widget._check_line_update(state)
            # Line must be revived smoothly!
            assert widget.current_line_text == "Hello vocal line"
            assert widget.engine.curr_text == "Hello vocal line"

        widget.render_timer.stop()
        widget.poll_timer.stop()
        widget.smooth_timer.stop()
        if widget.tray_icon:
            widget.tray_icon.hide()
        widget.close()


def test_color_swatch_custom_color_dialog():
    from PyQt6.QtGui import QColor

    from lyricvibe.ui.settings import ColorSwatch

    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    swatch = ColorSwatch("#1DB954")
    assert swatch.color() == "#1DB954"

    emitted_colors = []
    swatch.color_changed.connect(emitted_colors.append)

    # 1. Simulate user selecting a custom darker color (#4A148C)
    with patch(
        "lyricvibe.ui.settings.QColorDialog.getColor",
        return_value=QColor("#4A148C"),
    ):
        swatch._pick_custom_color()
        assert swatch.color() == "#4A148C"
        assert emitted_colors == ["#4A148C"]

    # 2. Simulate user canceling the color dialog
    invalid_color = QColor()
    with patch(
        "lyricvibe.ui.settings.QColorDialog.getColor",
        return_value=invalid_color,
    ):
        swatch._pick_custom_color()
        assert swatch.color() == "#4A148C"
        assert len(emitted_colors) == 1
