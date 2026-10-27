"""Tests for PyQt6 UI components, settings dialog, and signal bridges."""

import sys
from unittest.mock import patch

from PyQt6.QtWidgets import QApplication

from lyricvibe.ui.overlay import AppSignals, FloatingLyricsWidget
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
