"""Tests for PyQt6 UI components, settings dialog, and signal bridges."""

import sys

from PyQt6.QtWidgets import QApplication

from lyricvibe.ui.overlay import AppSignals
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
