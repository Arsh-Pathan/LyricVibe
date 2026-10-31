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
    dlg._apply_preset({
        "font_size": 48,
        "target_fps": 120,
    })
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
        assert len(widget._registered_hotkeys) == 7

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
        font_short, _ = widget._fit_font("Short line", max_w=800, base_size=42, family="Montserrat")
        assert font_short.pointSize() == 42

        long_line = "This is an extraordinarily long sentence with numerous words that exceeds width"
        font_long, _ = widget._fit_font(long_line, max_w=200, base_size=42, family="Montserrat")
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
        widget._on_lyrics_fetched(fetch_id=4, req_track_id="Artist B - Song B", lyrics=stale_lyrics)
        assert widget.lyrics is None

        # Case 2: Out-of-order response with mismatched track_id
        widget._on_lyrics_fetched(fetch_id=5, req_track_id="Artist A - Song A", lyrics=stale_lyrics)
        assert widget.lyrics is None

        # Case 3: Matching response
        widget._on_lyrics_fetched(fetch_id=5, req_track_id="Artist B - Song B", lyrics=valid_lyrics)
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
