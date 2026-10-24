"""
Dark-themed Settings Window for Spotify Floating Lyrics Overlay.
Appears when the user runs the application a second time or hits Ctrl+S.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QSlider,
    QCheckBox, QComboBox, QPushButton, QGroupBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor

import settings_manager


class SettingsDialog(QDialog):
    settings_changed = pyqtSignal(dict)
    quit_requested = pyqtSignal()

    def __init__(self, current_settings: dict, parent=None):
        super().__init__(parent)
        self.settings = current_settings.copy()
        self.setWindowTitle("Spotify Floating Lyrics — Settings")
        self.setFixedSize(480, 560)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowStaysOnTopHint)

        # Dark sleek styling
        self.setStyleSheet("""
            QDialog {
                background-color: #121218;
                color: #FFFFFF;
                font-family: 'Segoe UI', sans-serif;
            }
            QGroupBox {
                border: 1px solid #28283c;
                border-radius: 8px;
                margin-top: 14px;
                padding-top: 14px;
                color: #8AB4F8;
                font-weight: bold;
                font-size: 13px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 4px;
            }
            QLabel {
                color: #D0D0E0;
                font-size: 12px;
            }
            QCheckBox {
                color: #E0E0F0;
                font-size: 12px;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 4px;
                border: 1px solid #3d3d5c;
                background: #1c1c28;
            }
            QCheckBox::indicator:checked {
                background: #8AB4F8;
                border-color: #8AB4F8;
            }
            QSlider::groove:horizontal {
                height: 5px;
                background: #252538;
                border-radius: 2px;
            }
            QSlider::sub-page:horizontal {
                background: #8AB4F8;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #FFFFFF;
                border: 1px solid #8AB4F8;
                width: 14px;
                margin-top: -5px;
                margin-bottom: -5px;
                border-radius: 7px;
            }
            QComboBox {
                background: #1e1e2d;
                border: 1px solid #33334d;
                border-radius: 6px;
                padding: 4px 10px;
                color: #FFFFFF;
                font-size: 12px;
            }
            QPushButton {
                background: #8AB4F8;
                color: #101018;
                font-weight: bold;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 12px;
            }
            QPushButton:hover {
                background: #A6C8FF;
            }
            QPushButton#btnQuit {
                background: #2d181e;
                color: #F28B82;
                border: 1px solid #4a242c;
            }
            QPushButton#btnQuit:hover {
                background: #421e25;
            }
        """)

        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(20, 20, 20, 20)

        # Title Header
        header = QLabel("✨ Spotify Lyrics Customization")
        header.setStyleSheet("font-size: 16px; font-weight: bold; color: #FFFFFF; margin-bottom: 4px;")
        layout.addWidget(header)

        # ── Group: Display & 165Hz Monitor ──
        grp_display = QGroupBox("Performance & Display")
        lay_display = QVBoxLayout(grp_display)

        # Refresh Rate
        row_fps = QHBoxLayout()
        row_fps.addWidget(QLabel("Target Refresh Rate:"))
        self.combo_fps = QComboBox()
        self.combo_fps.addItems(["60 Hz", "120 Hz", "144 Hz", "165 Hz (Recommended)", "240 Hz"])
        cur_fps = self.settings.get("target_fps", 165)
        fps_map = {60: 0, 120: 1, 144: 2, 165: 3, 240: 4}
        self.combo_fps.setCurrentIndex(fps_map.get(cur_fps, 3))
        row_fps.addWidget(self.combo_fps)
        lay_display.addLayout(row_fps)

        # Font Size
        row_size = QHBoxLayout()
        self.lbl_size = QLabel(f"Font Size: {self.settings.get('font_size', 42)}px")
        row_size.addWidget(self.lbl_size)
        self.slider_size = QSlider(Qt.Orientation.Horizontal)
        self.slider_size.setRange(28, 64)
        self.slider_size.setValue(self.settings.get("font_size", 42))
        self.slider_size.valueChanged.connect(lambda v: self.lbl_size.setText(f"Font Size: {v}px"))
        row_size.addWidget(self.slider_size)
        lay_display.addLayout(row_size)

        # Screen Top Offset
        row_y = QHBoxLayout()
        self.lbl_y = QLabel(f"Position (Top Offset): {self.settings.get('overlay_y', 55)}px")
        row_y.addWidget(self.lbl_y)
        self.slider_y = QSlider(Qt.Orientation.Horizontal)
        self.slider_y.setRange(10, 300)
        self.slider_y.setValue(self.settings.get("overlay_y", 55))
        self.slider_y.valueChanged.connect(lambda v: self.lbl_y.setText(f"Position (Top Offset): {v}px"))
        row_y.addWidget(self.slider_y)
        lay_display.addLayout(row_y)

        layout.addWidget(grp_display)

        # ── Group: Cinematic Animations ──
        grp_anim = QGroupBox("Cinematic Effects")
        lay_anim = QVBoxLayout(grp_anim)

        self.chk_motion_blur = QCheckBox("Motion Blur (Smooth 165Hz Velocity Streaks)")
        self.chk_motion_blur.setChecked(self.settings.get("motion_blur_enabled", True))
        lay_anim.addWidget(self.chk_motion_blur)

        self.chk_glow = QCheckBox("Luminous Vocal Glow / Bloom Halo")
        self.chk_glow.setChecked(self.settings.get("glow_enabled", True))
        lay_anim.addWidget(self.chk_glow)

        self.chk_underline = QCheckBox("Hand-Drawn Animated Brush Underlines")
        self.chk_underline.setChecked(self.settings.get("hand_drawn_underline_enabled", True))
        lay_anim.addWidget(self.chk_underline)

        self.chk_word_reveal = QCheckBox("Dynamic Word-by-Word Reveal on Slow/Legato Lines")
        self.chk_word_reveal.setChecked(self.settings.get("word_reveal_enabled", True))
        lay_anim.addWidget(self.chk_word_reveal)

        layout.addWidget(grp_anim)

        # ── Group: Sync Calibration ──
        grp_sync = QGroupBox("Timing & Sync")
        lay_sync = QVBoxLayout(grp_sync)

        row_sync = QHBoxLayout()
        cur_offset = self.settings.get("sync_offset_sec", 0.0)
        self.lbl_sync = QLabel(f"Sync Offset: {cur_offset:+.1f}s")
        row_sync.addWidget(self.lbl_sync)

        self.slider_sync = QSlider(Qt.Orientation.Horizontal)
        self.slider_sync.setRange(-20, 20)  # -2.0s to +2.0s
        self.slider_sync.setValue(int(cur_offset * 10))
        self.slider_sync.valueChanged.connect(lambda v: self.lbl_sync.setText(f"Sync Offset: {v/10.0:+.1f}s"))
        row_sync.addWidget(self.slider_sync)
        lay_sync.addLayout(row_sync)

        layout.addWidget(grp_sync)

        # ── Bottom Action Buttons ──
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        self.btn_quit = QPushButton("Exit Overlay")
        self.btn_quit.setObjectName("btnQuit")
        self.btn_quit.clicked.connect(self._on_quit_clicked)
        btn_layout.addWidget(self.btn_quit)

        btn_layout.addStretch()

        self.btn_apply = QPushButton("Save & Apply")
        self.btn_apply.clicked.connect(self._on_apply_clicked)
        btn_layout.addWidget(self.btn_apply)

        layout.addLayout(btn_layout)

    def _on_apply_clicked(self):
        fps_values = [60, 120, 144, 165, 240]
        chosen_fps = fps_values[self.combo_fps.currentIndex()]

        updated = {
            "target_fps": chosen_fps,
            "font_size": self.slider_size.value(),
            "overlay_y": self.slider_y.value(),
            "motion_blur_enabled": self.chk_motion_blur.isChecked(),
            "glow_enabled": self.chk_glow.isChecked(),
            "hand_drawn_underline_enabled": self.chk_underline.isChecked(),
            "word_reveal_enabled": self.chk_word_reveal.isChecked(),
            "sync_offset_sec": round(self.slider_sync.value() / 10.0, 2),
        }
        self.settings.update(updated)
        settings_manager.save_settings(self.settings)
        self.settings_changed.emit(self.settings)
        self.accept()

    def _on_quit_clicked(self):
        self.quit_requested.emit()
        self.close()
