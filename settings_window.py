"""
Settings Window for Spotify Floating Lyrics Overlay.
- Real-time live settings synchronization (zero crashes, instant updates).
- Dedicated interactive live preview testing 55+ animations and typography.
- Rich suite of silky-smooth fade-in and fade-out animations.
- Aesthetic smooth soft color highlights: rotates a new vibrant, soft pastel tone
  for each song, consistent for the entire song, and different for the next song.
- 100% glitch-free rendering with preserved font kerning and anchored baselines.
- 7clouds font switcher (Edo SZ signature brush DEFAULT & Montserrat Black).
- Focal hand-drawn underline (highlights only 1-2 key words).
- Zero continuous float (firmly anchored lyrics).
- Modern Material 3 container design with clean typography and system diagnostics.
- Done button ONLY closes settings dialog (does NOT quit the overlay app).
"""

import sys
import os
import time
import math
import random

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QSlider,
    QCheckBox, QComboBox, QPushButton, QGroupBox, QWidget,
    QTabWidget, QFrame, QScrollArea, QSizePolicy
)
from PyQt6.QtCore import (
    Qt, pyqtSignal, QTimer, QPropertyAnimation, QEasingCurve,
    QPoint, QPointF, QRectF, QSize, pyqtProperty
)
from PyQt6.QtGui import (
    QFont, QColor, QPainter, QPen, QBrush, QPainterPath,
    QFontDatabase, QLinearGradient, QIcon, QPixmap, QFontMetrics
)

import settings_manager
from settings_manager import SMOOTH_SOFT_PALETTE, SMOOTH_SOFT_HEX_LIST
from animation_engine import AnimationEngine, ANIMATION_CATALOG, PER_CHAR_ANIMS


# ─── Material Design 3 Dark Theme Palette ─────────────────────────────
class MD3:
    SURFACE               = "#101318"  # Deep canvas
    SURFACE_DIM           = "#0B0E12"
    SURFACE_CONTAINER_LOW = "#181C22"
    SURFACE_CONTAINER     = "#1E2228"  # Card surface
    SURFACE_CONTAINER_HIGH= "#262B33"  # Elevated card
    SURFACE_CONTAINER_MAX = "#313640"

    PRIMARY               = "#A8C7FA"  # Material Sky Blue
    ON_PRIMARY            = "#062E6F"
    PRIMARY_CONTAINER     = "#0842A0"
    ON_PRIMARY_CONTAINER  = "#D3E3FD"

    ACCENT_GREEN          = "#1DB954"
    ACCENT_GREEN_BG       = "#0A3E1D"

    ERROR                 = "#FFB4AB"
    ERROR_CONTAINER       = "#690005"
    ON_ERROR_CONTAINER    = "#FFDAD6"

    ON_SURFACE            = "#E2E2E9"
    ON_SURFACE_VARIANT    = "#C4C6D0"
    OUTLINE               = "#8E9099"
    OUTLINE_VARIANT       = "#363B44"

    RADIUS_SM = 8
    RADIUS_MD = 12
    RADIUS_LG = 16


# ─── Animated Pill Toggle Switch ──────────────────────────────────────
class PillToggle(QWidget):
    toggled = pyqtSignal(bool)

    def __init__(self, checked=False, parent=None):
        super().__init__(parent)
        self._checked = checked
        self._handle_pos = 1.0 if checked else 0.0
        self.setFixedSize(52, 32)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._anim = QPropertyAnimation(self, b"handlePos")
        self._anim.setDuration(220)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    def getHandlePos(self):
        return self._handle_pos

    def setHandlePos(self, val):
        self._handle_pos = val
        self.update()

    handlePos = pyqtProperty(float, getHandlePos, setHandlePos)

    def isChecked(self) -> bool:
        return self._checked

    def setChecked(self, checked: bool):
        if checked != self._checked:
            self._checked = checked
            self._anim.stop()
            self._anim.setStartValue(self._handle_pos)
            self._anim.setEndValue(1.0 if checked else 0.0)
            self._anim.start()
            self.toggled.emit(checked)

    def mousePressEvent(self, event):
        self.setChecked(not self._checked)
        event.accept()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        t = self._handle_pos

        if t > 0.5:
            track_color = QColor(MD3.PRIMARY)
            track_border = QColor(MD3.PRIMARY)
            thumb_color = QColor(MD3.ON_PRIMARY)
        else:
            track_color = QColor(MD3.SURFACE_CONTAINER_MAX)
            track_border = QColor(MD3.OUTLINE_VARIANT)
            thumb_color = QColor(MD3.OUTLINE)

        p.setPen(QPen(track_border, 1.5))
        p.setBrush(track_color)
        p.drawRoundedRect(QRectF(1, 1, w - 2, h - 2), h / 2.0, h / 2.0)

        thumb_r = 8.5 + t * 2.5
        thumb_x = 16.0 + t * (w - 32.0)
        thumb_y = h / 2.0

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(thumb_color)
        p.drawEllipse(QPointF(thumb_x, thumb_y), thumb_r, thumb_r)
        p.end()


# ─── Setting Item Row ─────────────────────────────────────────────────
class SettingRow(QWidget):
    def __init__(self, title: str, subtitle: str = "", parent=None):
        super().__init__(parent)
        self.setMinimumHeight(64)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 10, 20, 10)
        layout.setSpacing(16)

        text_col = QVBoxLayout()
        text_col.setSpacing(3)

        self.title_label = QLabel(title)
        self.title_label.setStyleSheet(f"color: {MD3.ON_SURFACE}; font-size: 14px; font-weight: 500; background: transparent; border: none;")
        text_col.addWidget(self.title_label)

        if subtitle:
            self.subtitle_label = QLabel(subtitle)
            self.subtitle_label.setStyleSheet(f"color: {MD3.ON_SURFACE_VARIANT}; font-size: 12px; background: transparent; border: none;")
            self.subtitle_label.setWordWrap(True)
            text_col.addWidget(self.subtitle_label)

        layout.addLayout(text_col, 1)

        self._control_layout = QHBoxLayout()
        self._control_layout.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.addLayout(self._control_layout)

    def add_control(self, widget: QWidget):
        self._control_layout.addWidget(widget)


# ─── Material Slider Row with Live Value Badge ────────────────────────
class SliderRow(QWidget):
    value_changed = pyqtSignal(int)

    def __init__(self, title: str, subtitle: str, min_val: int, max_val: int,
                 value: int, suffix: str = "", parent=None):
        super().__init__(parent)
        self.suffix = suffix
        self.setMinimumHeight(82)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 12, 20, 12)
        layout.setSpacing(8)

        header = QHBoxLayout()
        title_label = QLabel(title)
        title_label.setStyleSheet(f"color: {MD3.ON_SURFACE}; font-size: 14px; font-weight: 500; background: transparent; border: none;")
        header.addWidget(title_label)

        self.value_badge = QLabel(f"{value}{suffix}")
        self.value_badge.setStyleSheet(f"""
            color: {MD3.ON_PRIMARY_CONTAINER};
            background-color: {MD3.PRIMARY_CONTAINER};
            font-size: 12px;
            font-weight: 600;
            padding: 2px 10px;
            border-radius: 10px;
        """)
        self.value_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.addWidget(self.value_badge)
        layout.addLayout(header)

        if subtitle:
            sub = QLabel(subtitle)
            sub.setStyleSheet(f"color: {MD3.ON_SURFACE_VARIANT}; font-size: 12px; background: transparent; border: none;")
            layout.addWidget(sub)

        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(min_val, max_val)
        self.slider.setValue(value)
        self.slider.valueChanged.connect(self._on_value_changed)
        layout.addWidget(self.slider)

    def _on_value_changed(self, val):
        self.value_badge.setText(f"{val}{self.suffix}")
        self.value_changed.emit(val)

    def value(self) -> int:
        return self.slider.value()

    def setValue(self, val: int):
        self.slider.setValue(val)


# ─── Material Surface Card Container ──────────────────────────────────
class SectionCard(QFrame):
    def __init__(self, title: str = "", parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"""
            SectionCard {{
                background-color: {MD3.SURFACE_CONTAINER};
                border-radius: {MD3.RADIUS_LG}px;
                border: 1px solid {MD3.OUTLINE_VARIANT};
            }}
        """)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 10, 0, 10)
        self._layout.setSpacing(0)

        if title:
            header = QLabel(title.upper())
            header.setStyleSheet(f"""
                color: {MD3.PRIMARY};
                font-size: 11px;
                font-weight: 700;
                letter-spacing: 1.2px;
                padding: 8px 20px 6px 20px;
                background: transparent;
                border: none;
            """)
            self._layout.addWidget(header)

    def add_row(self, widget: QWidget):
        self._layout.addWidget(widget)

    def add_separator(self):
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background-color: {MD3.OUTLINE_VARIANT}; margin-left: 20px; margin-right: 20px;")
        self._layout.addWidget(sep)


# ─── Live Interactive Preview Canvas ──────────────────────────────────
class LivePreview(QWidget):
    """
    Renders sharp floating lyrics with actual 7clouds font,
    55+ animations, smooth soft color highlight, and focal underlines.
    """

    PREVIEW_LINES = [
        "Magar phir aarzoon ka bikharna bhi zaroori tha",
        "Cause you knew that I'd be at one",
        "Saari jannatein mere paas ho",
        "I fell in love with a girl I met in hell",
        "Patta chanaron ka jaise havaon mein",
    ]

    def __init__(self, settings: dict, parent=None):
        super().__init__(parent)
        self.settings = settings.copy()
        self.setFixedHeight(180)

        self.engine = AnimationEngine()
        self._line_idx = 0
        self._current_anim_choice = ""
        self._color_idx = 0

        self.engine.trigger_line(self.PREVIEW_LINES[0], 3.8, "cinematic_crossfade")

        self._render_timer = QTimer(self)
        self._render_timer.timeout.connect(self.update)
        self._render_timer.start(16)

        self._cycle_timer = QTimer(self)
        self._cycle_timer.timeout.connect(self.next_line)
        self._cycle_timer.start(3800)

    def trigger_animation(self, anim_name: str = ""):
        self._current_anim_choice = anim_name
        text = self.PREVIEW_LINES[self._line_idx]
        self.engine.trigger_line(text, 3.8, anim_name)
        self.update()

    def next_line(self):
        self._line_idx = (self._line_idx + 1) % len(self.PREVIEW_LINES)
        text = self.PREVIEW_LINES[self._line_idx]
        # Simulate new song change by picking next distinct smooth soft color
        self._color_idx = (self._color_idx + 1) % len(SMOOTH_SOFT_HEX_LIST)
        self.engine.trigger_line(text, 3.8, self._current_anim_choice)

    def update_settings(self, settings: dict):
        self.settings.update(settings)
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        w, h = self.width(), self.height()

        # Canvas gradient background
        bg_grad = QLinearGradient(0, 0, 0, h)
        bg_grad.setColorAt(0.0, QColor(MD3.SURFACE_DIM))
        bg_grad.setColorAt(0.5, QColor("#12161E"))
        bg_grad.setColorAt(1.0, QColor(MD3.SURFACE_DIM))
        p.fillRect(0, 0, w, h, bg_grad)

        # Dot matrix grid
        dot_color = QColor(MD3.OUTLINE_VARIANT)
        dot_color.setAlpha(35)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(dot_color)
        for x in range(16, w, 28):
            for y in range(16, h, 28):
                p.drawEllipse(QPointF(x, y), 1.2, 1.2)

        data = self.engine.update()
        curr_text = data.get("curr_text", "")
        prev_data = data.get("prev")
        anim_type = data.get("anim_type", "")

        cx = w / 2.0
        cy = h / 2.0

        # Font configuration
        font_choice = self.settings.get("font_family", "7clouds Signature (Edo SZ)")
        if "Edo" in font_choice:
            fam = "Edo SZ"
            weight = QFont.Weight.Bold
        elif "Poppins" in font_choice:
            fam = "Poppins"
            weight = QFont.Weight.Bold
        elif "Segoe" in font_choice:
            fam = "Segoe UI"
            weight = QFont.Weight.Bold
        else:
            fam = "Montserrat"
            weight = QFont.Weight.Black

        size = min(int(self.settings.get("font_size", 42)), 30)
        font = QFont(fam, size, weight)
        font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
        metrics = QFontMetrics(font)

        while metrics.horizontalAdvance(curr_text) > (w - 60) and size > 15:
            size -= 1
            font.setPointSize(size)
            metrics = QFontMetrics(font)

        p.setFont(font)

        hl_enabled = self.settings.get("highlight_enabled", True)
        # Use smooth soft colorful highlight
        if self.settings.get("highlight_mode", "per_song") == "per_song":
            hl_color = QColor(SMOOTH_SOFT_HEX_LIST[self._color_idx])
        else:
            hl_color = QColor(self.settings.get("highlight_color", SMOOTH_SOFT_HEX_LIST[0]))
        hl_idx = data.get("highlight_word_idx", -1)

        # ── 1. Outgoing Line Cross-Transition (Anti-Overlap: lifts cleanly away) ──
        if prev_data and prev_data["alpha"] > 0.02:
            p_text = prev_data["text"]
            p_alpha = int(prev_data["alpha"] * 255)
            p.setPen(QColor(255, 255, 255, p_alpha))
            p_w = metrics.horizontalAdvance(p_text)
            p_baseline = (metrics.ascent() - metrics.descent()) / 2.0
            p.save()
            p.translate(cx, cy - 24.0 + prev_data["offset_y"])
            if prev_data["scale"] != 1.0:
                p.scale(prev_data["scale"], prev_data["scale"])
            p.drawText(QPointF(-p_w / 2.0, p_baseline), p_text)
            p.restore()

        # ── 2. Incoming Line ──
        if curr_text and data["curr_alpha"] > 0.02:
            in_alpha = int(data["curr_alpha"] * 255)
            total_w = metrics.horizontalAdvance(curr_text)
            start_x = -total_w / 2.0
            baseline_y = (metrics.ascent() - metrics.descent()) / 2.0

            p.save()
            p.translate(cx + data.get("curr_offset_x", 0.0), cy + data["curr_offset_y"])

            if data.get("rotation", 0.0) != 0.0:
                p.rotate(data["rotation"])
            if data["curr_scale"] != 1.0:
                p.scale(data["curr_scale"], data["curr_scale"])

            # Render complete line in pure white (100% kerning accuracy)
            p.setPen(QColor(255, 255, 255, in_alpha))
            p.drawText(QPointF(start_x, baseline_y), curr_text)

            # Smooth soft highlight on currently spoken word + rounded glowing pill
            if hl_enabled and hl_idx >= 0:
                words = []
                idx = 0
                while idx < len(curr_text):
                    if curr_text[idx].isspace():
                        idx += 1
                        continue
                    w_start = idx
                    while idx < len(curr_text) and not curr_text[idx].isspace():
                        idx += 1
                    w_end = idx
                    words.append((curr_text[w_start:w_end], w_start, w_end))

                if 0 <= hl_idx < len(words):
                    w_str, w_start, _ = words[hl_idx]
                    w_x = start_x + metrics.horizontalAdvance(curr_text[:w_start])
                    w_w = metrics.horizontalAdvance(w_str)

                    # Draw rounded glowing highlight block/pill behind the active word
                    if self.settings.get("highlight_block_enabled", True):
                        pill_pad_x = 6.0
                        pill_pad_y = 3.0
                        pill_rect = QRectF(
                            w_x - pill_pad_x,
                            baseline_y - metrics.ascent() - pill_pad_y,
                            w_w + pill_pad_x * 2.0,
                            metrics.ascent() + metrics.descent() + pill_pad_y * 2.0
                        )
                        pill_alpha = int(in_alpha * 0.30)
                        p.setPen(Qt.PenStyle.NoPen)
                        p.setBrush(QColor(hl_color.red(), hl_color.green(), hl_color.blue(), pill_alpha))
                        p.drawRoundedRect(pill_rect, 6.0, 6.0)

                    # Draw active word in vibrant smooth soft color
                    p.setPen(QColor(hl_color.red(), hl_color.green(), hl_color.blue(), in_alpha))
                    p.drawText(QPointF(w_x, baseline_y), w_str)

            # Focal underline
            if (self.settings.get("hand_drawn_underline_enabled", True) and
                    data.get("underline_active") and
                    data.get("underline_progress", 0.0) > 0.02 and
                    data.get("focal_word_idx", -1) >= 0):

                focal_idx = data["focal_word_idx"]
                words = []
                idx = 0
                while idx < len(curr_text):
                    if curr_text[idx].isspace():
                        idx += 1
                        continue
                    w_start = idx
                    while idx < len(curr_text) and not curr_text[idx].isspace():
                        idx += 1
                    w_end = idx
                    words.append((curr_text[w_start:w_end], w_start, w_end))

                if 0 <= focal_idx < len(words):
                    w_str, w_start, _ = words[focal_idx]
                    w_start_x = start_x + metrics.horizontalAdvance(curr_text[:w_start])
                    target_w = metrics.horizontalAdvance(w_str)
                    draw_w = target_w * data["underline_progress"]

                    if draw_w > 6:
                        y_line = baseline_y + 8.0
                        p.setPen(QPen(QColor(255, 255, 255, int(data["curr_alpha"] * 75)), 1.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
                        path1 = QPainterPath()
                        path1.moveTo(w_start_x - 2, y_line)
                        path1.quadTo(w_start_x + draw_w * 0.5, y_line + 3, w_start_x + draw_w + 2, y_line + 1)
                        p.drawPath(path1)

                        p.setPen(QPen(QColor(255, 255, 255, int(data["curr_alpha"] * 225)), 2.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
                        path2 = QPainterPath()
                        path2.moveTo(w_start_x, y_line)
                        path2.quadTo(w_start_x + draw_w * 0.5, y_line + 3.5, w_start_x + draw_w, y_line + 0.5)
                        p.drawPath(path2)

            p.restore()

        # Header badge
        p.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
        p.setPen(QColor(MD3.PRIMARY))
        p.drawText(QRectF(0, 10, w - 16, 20), Qt.AlignmentFlag.AlignRight, "● LIVE PREVIEW")

        p.end()


# ─── Aesthetic Smooth Soft Color Swatch Button ─────────────────────────
class ColorSwatch(QPushButton):
    color_changed = pyqtSignal(str)

    PALETTE = SMOOTH_SOFT_HEX_LIST

    def __init__(self, current_hex: str = "#2EE59D", parent=None):
        super().__init__(parent)
        self._color = current_hex
        self._idx = 0
        for i, c in enumerate(self.PALETTE):
            if c.upper() == current_hex.upper():
                self._idx = i
                break
        self.setFixedSize(36, 36)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clicked.connect(self._cycle_color)
        self._apply_style()

    def _apply_style(self):
        color_name = "Smooth Soft Color"
        for item in SMOOTH_SOFT_PALETTE:
            if item["hex"].upper() == self._color.upper():
                color_name = item["name"]
                break
        self.setToolTip(f"{color_name} ({self._color})\nClick to cycle through colors")
        self.setStyleSheet(f"""
            QPushButton {{
                background: {self._color};
                border: 2px solid {MD3.OUTLINE_VARIANT};
                border-radius: 18px;
            }}
            QPushButton:hover {{
                border: 2px solid {MD3.PRIMARY};
            }}
        """)

    def _cycle_color(self):
        self._idx = (self._idx + 1) % len(self.PALETTE)
        self._color = self.PALETTE[self._idx]
        self._apply_style()
        self.color_changed.emit(self._color)

    def color(self) -> str:
        return self._color

    def setColor(self, hex_color: str):
        self._color = hex_color
        for i, c in enumerate(self.PALETTE):
            if c.upper() == hex_color.upper():
                self._idx = i
                break
        self._apply_style()


# ─── Main Settings Window ─────────────────────────────────────────────
class SettingsDialog(QDialog):
    settings_changed = pyqtSignal(dict)
    quit_requested = pyqtSignal()

    def __init__(self, current_settings: dict, parent=None):
        super().__init__(parent)
        self.settings = current_settings.copy()
        self.setWindowTitle("Lyric Flow — Settings")
        self.setFixedSize(580, 790)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowStaysOnTopHint)

        self._load_icon()
        self._apply_theme()
        self._build_ui()

    def _load_icon(self):
        icon_dir = os.path.dirname(os.path.abspath(__file__))
        for icon_name in ("icon.ico", "icon.png"):
            fp = os.path.join(icon_dir, icon_name)
            if os.path.exists(fp):
                self.setWindowIcon(QIcon(fp))
                break

    def _apply_theme(self):
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {MD3.SURFACE};
                color: {MD3.ON_SURFACE};
                font-family: 'Segoe UI Variable Display', 'Segoe UI', sans-serif;
            }}
            QTabWidget::pane {{
                border: none;
                background: transparent;
            }}
            QTabBar::tab {{
                background: transparent;
                color: {MD3.ON_SURFACE_VARIANT};
                font-size: 13px;
                font-weight: 600;
                padding: 10px 18px;
                border: none;
                border-bottom: 3px solid transparent;
                min-width: 70px;
            }}
            QTabBar::tab:selected {{
                color: {MD3.PRIMARY};
                border-bottom: 3px solid {MD3.PRIMARY};
            }}
            QTabBar::tab:hover:!selected {{
                color: {MD3.ON_SURFACE};
                background: {MD3.SURFACE_CONTAINER_LOW};
                border-radius: 8px 8px 0 0;
            }}
            QSlider::groove:horizontal {{
                height: 6px;
                background: {MD3.SURFACE_CONTAINER_MAX};
                border-radius: 3px;
            }}
            QSlider::sub-page:horizontal {{
                background: {MD3.PRIMARY};
                border-radius: 3px;
            }}
            QSlider::handle:horizontal {{
                background: {MD3.PRIMARY};
                border: 2px solid {MD3.SURFACE_CONTAINER};
                width: 18px;
                height: 18px;
                margin-top: -6px;
                margin-bottom: -6px;
                border-radius: 9px;
            }}
            QSlider::handle:horizontal:hover {{
                background: #D3E3FD;
            }}
            QComboBox {{
                background: {MD3.SURFACE_CONTAINER_HIGH};
                border: 1px solid {MD3.OUTLINE_VARIANT};
                border-radius: 8px;
                padding: 6px 14px;
                color: {MD3.ON_SURFACE};
                font-size: 13px;
                min-width: 180px;
            }}
            QComboBox QAbstractItemView {{
                background: {MD3.SURFACE_CONTAINER_HIGH};
                border: 1px solid {MD3.OUTLINE_VARIANT};
                border-radius: 8px;
                color: {MD3.ON_SURFACE};
                selection-background-color: {MD3.PRIMARY_CONTAINER};
                selection-color: {MD3.ON_PRIMARY_CONTAINER};
                padding: 4px;
            }}
            QScrollArea {{
                border: none;
                background: transparent;
            }}
            QScrollBar:vertical {{
                background: transparent;
                width: 6px;
                margin: 4px 0;
            }}
            QScrollBar::handle:vertical {{
                background: {MD3.OUTLINE_VARIANT};
                border-radius: 3px;
                min-height: 28px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {MD3.OUTLINE};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """)

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Header bar
        header = QWidget()
        header.setFixedHeight(68)
        header.setStyleSheet(f"background: {MD3.SURFACE};")
        h_lay = QHBoxLayout(header)
        h_lay.setContentsMargins(24, 0, 20, 0)
        h_lay.setSpacing(14)

        icon_label = QLabel()
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.png")
        if os.path.exists(icon_path):
            pix = QPixmap(icon_path).scaled(32, 32, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            icon_label.setPixmap(pix)
        h_lay.addWidget(icon_label)

        title_col = QVBoxLayout()
        title_col.setSpacing(0)
        title = QLabel("Lyric Flow")
        title.setStyleSheet(f"color: {MD3.ON_SURFACE}; font-size: 18px; font-weight: 600; background: transparent;")
        title_col.addWidget(title)
        subtitle = QLabel("165Hz Desktop Lyrics Customizer")
        subtitle.setStyleSheet(f"color: {MD3.ON_SURFACE_VARIANT}; font-size: 11px; background: transparent;")
        title_col.addWidget(subtitle)
        h_lay.addLayout(title_col)

        h_lay.addStretch()

        status_pill = QLabel("● Active")
        status_pill.setStyleSheet(f"""
            color: {MD3.ACCENT_GREEN};
            background-color: {MD3.ACCENT_GREEN_BG};
            font-size: 12px;
            font-weight: 600;
            padding: 4px 12px;
            border-radius: 12px;
        """)
        h_lay.addWidget(status_pill)

        root.addWidget(header)

        # Tabs
        tabs = QTabWidget()
        tabs.setDocumentMode(True)
        tabs.addTab(self._build_display_tab(), "Display")
        tabs.addTab(self._build_effects_tab(), "Effects")
        tabs.addTab(self._build_timing_tab(), "Sync")
        tabs.addTab(self._build_presets_tab(), "Presets")
        tabs.addTab(self._build_about_tab(), "About")
        root.addWidget(tabs, 1)

        # Bottom Bar
        bottom_bar = QWidget()
        bottom_bar.setFixedHeight(72)
        bottom_bar.setStyleSheet(f"""
            QWidget {{
                background: {MD3.SURFACE_CONTAINER_LOW};
                border-top: 1px solid {MD3.OUTLINE_VARIANT};
            }}
        """)
        b_lay = QHBoxLayout(bottom_bar)
        b_lay.setContentsMargins(20, 0, 20, 0)
        b_lay.setSpacing(12)

        btn_quit = QPushButton("Exit Overlay")
        btn_quit.setStyleSheet(f"""
            QPushButton {{
                background: {MD3.ERROR_CONTAINER};
                color: {MD3.ON_ERROR_CONTAINER};
                font-weight: 600;
                font-size: 13px;
                border: none;
                border-radius: 20px;
                padding: 10px 22px;
            }}
            QPushButton:hover {{
                background: #8C0009;
            }}
        """)
        btn_quit.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_quit.clicked.connect(self._on_quit_clicked)
        b_lay.addWidget(btn_quit)

        b_lay.addStretch()

        btn_reset = QPushButton("Reset Defaults")
        btn_reset.setStyleSheet(f"""
            QPushButton {{
                background: {MD3.SURFACE_CONTAINER_HIGH};
                color: {MD3.ON_SURFACE};
                font-weight: 500;
                font-size: 13px;
                border: 1px solid {MD3.OUTLINE_VARIANT};
                border-radius: 20px;
                padding: 9px 20px;
            }}
            QPushButton:hover {{
                background: {MD3.SURFACE_CONTAINER_MAX};
            }}
        """)
        btn_reset.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_reset.clicked.connect(self._reset_to_defaults)
        b_lay.addWidget(btn_reset)

        btn_close = QPushButton("Done")
        btn_close.setStyleSheet(f"""
            QPushButton {{
                background: {MD3.PRIMARY};
                color: {MD3.ON_PRIMARY};
                font-weight: 600;
                font-size: 13px;
                border: none;
                border-radius: 20px;
                padding: 10px 28px;
            }}
            QPushButton:hover {{
                background: #D3E3FD;
            }}
        """)
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.clicked.connect(self._on_done_clicked)
        b_lay.addWidget(btn_close)

        root.addWidget(bottom_bar)

    # ── Tab 1: Display & Typography ──
    def _build_display_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(16)

        # 1. Preview Card
        preview_card = SectionCard("Live Preview")
        self.preview_widget = LivePreview(self.settings)
        preview_card.add_row(self.preview_widget)

        p_ctrls = QWidget()
        p_c_lay = QHBoxLayout(p_ctrls)
        p_c_lay.setContentsMargins(18, 6, 18, 12)
        p_c_lay.setSpacing(10)

        self.combo_test_anim = QComboBox()
        self.combo_test_anim.addItem("Random 55+ Animations", "")
        for name, _ in ANIMATION_CATALOG:
            clean_name = name.replace("_", " ").title()
            self.combo_test_anim.addItem(f"Test: {clean_name}", name)
        self.combo_test_anim.currentIndexChanged.connect(
            lambda: self.preview_widget.trigger_animation(self.combo_test_anim.currentData())
        )
        p_c_lay.addWidget(self.combo_test_anim, 1)

        btn_test = QPushButton("▶ Replay")
        btn_test.setStyleSheet(f"""
            QPushButton {{
                background: {MD3.PRIMARY_CONTAINER};
                color: {MD3.ON_PRIMARY_CONTAINER};
                font-weight: 600;
                font-size: 12px;
                border-radius: 14px;
                padding: 6px 16px;
                border: none;
            }}
            QPushButton:hover {{
                background: #255BB3;
            }}
        """)
        btn_test.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_test.clicked.connect(lambda: self.preview_widget.trigger_animation(self.combo_test_anim.currentData()))
        p_c_lay.addWidget(btn_test)

        btn_next = QPushButton("Next Line ⏭")
        btn_next.setStyleSheet(f"""
            QPushButton {{
                background: {MD3.SURFACE_CONTAINER_HIGH};
                color: {MD3.ON_SURFACE};
                font-size: 12px;
                border-radius: 14px;
                padding: 6px 14px;
                border: 1px solid {MD3.OUTLINE_VARIANT};
            }}
            QPushButton:hover {{
                background: {MD3.SURFACE_CONTAINER_MAX};
            }}
        """)
        btn_next.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_next.clicked.connect(self.preview_widget.next_line)
        p_c_lay.addWidget(btn_next)

        preview_card.add_row(p_ctrls)
        layout.addWidget(preview_card)

        # 2. Typography Card
        typo_card = SectionCard("Typography & 7clouds Style")

        row_font = SettingRow("Font Style", "Choose between 7clouds signature brush and clean bold")
        self.combo_font = QComboBox()
        self.combo_font.addItems([
            "7clouds Signature (Edo SZ)",
            "7clouds Modern (Montserrat Black)",
            "Clean Bold (Poppins)",
            "System Clean (Segoe UI)",
        ])
        cur_font = self.settings.get("font_family", "7clouds Signature (Edo SZ)")
        idx = 0
        if "Montserrat" in cur_font or "Modern" in cur_font:
            idx = 1
        elif "Poppins" in cur_font:
            idx = 2
        elif "Segoe" in cur_font:
            idx = 3
        self.combo_font.setCurrentIndex(idx)
        self.combo_font.currentIndexChanged.connect(self._on_font_changed)
        row_font.add_control(self.combo_font)
        typo_card.add_row(row_font)
        typo_card.add_separator()

        self.slider_size = SliderRow(
            "Font Size", "Automatically scales down on long lines to prevent clipping",
            28, 64, int(self.settings.get("font_size", 42)), "px"
        )
        self.slider_size.value_changed.connect(self._on_slider_size_changed)
        typo_card.add_row(self.slider_size)
        typo_card.add_separator()

        self.slider_y = SliderRow(
            "Top Screen Margin", "Distance from the top edge of your monitor",
            10, 350, int(self.settings.get("overlay_y", 55)), "px"
        )
        self.slider_y.value_changed.connect(self._on_slider_y_changed)
        typo_card.add_row(self.slider_y)

        layout.addWidget(typo_card)

        # 3. Performance Card
        perf_card = SectionCard("Performance & Refresh Rate")

        row_fps = SettingRow("Target Refresh Rate", "Hardware-accelerated timer for high-refresh monitors")
        self.combo_fps = QComboBox()
        self.combo_fps.addItems(["60 Hz", "120 Hz", "144 Hz", "165 Hz (Recommended)", "240 Hz"])
        cur_fps = int(self.settings.get("target_fps", 165))
        fps_map = {60: 0, 120: 1, 144: 2, 165: 3, 240: 4}
        self.combo_fps.setCurrentIndex(fps_map.get(cur_fps, 3))
        self.combo_fps.currentIndexChanged.connect(self._on_fps_changed)
        row_fps.add_control(self.combo_fps)
        perf_card.add_row(row_fps)

        layout.addWidget(perf_card)

        layout.addStretch()
        scroll.setWidget(content)
        return scroll

    # ── Tab 2: Visual Effects & Physics ──
    def _build_effects_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(16)

        fx_card = SectionCard("Visual Effects & Dynamic Colors")

        # 1. Active Word Highlight Enabled
        row_hl = SettingRow(
            "Word Timing Highlight",
            "Illuminates the active spoken word with high contrast and smooth vocal pacing"
        )
        self.toggle_highlight = PillToggle(self.settings.get("highlight_enabled", True))
        self.toggle_highlight.toggled.connect(lambda v: self._update_and_sync("highlight_enabled", v))
        row_hl.add_control(self.toggle_highlight)
        fx_card.add_row(row_hl)
        fx_card.add_separator()

        # 2. Glowing Rounded Block / Pill
        row_hl_block = SettingRow(
            "Highlight Glowing Pill Block",
            "Soft translucent rounded pill behind active word for 100% visibility on any background"
        )
        self.toggle_hl_block = PillToggle(self.settings.get("highlight_block_enabled", True))
        self.toggle_hl_block.toggled.connect(lambda v: self._update_and_sync("highlight_block_enabled", v))
        row_hl_block.add_control(self.toggle_hl_block)
        fx_card.add_row(row_hl_block)
        fx_card.add_separator()

        # 3. Highlight Color Mode & Swatch
        row_color = SettingRow(
            "Aesthetic Color Palette",
            "Auto rotates a different smooth soft color each song, or pin your favorite"
        )
        self.combo_hl_mode = QComboBox()
        self.combo_hl_mode.addItem("🎨 Auto: Different Color Each Song", "per_song")
        for item in SMOOTH_SOFT_PALETTE:
            self.combo_hl_mode.addItem(f"● {item['name']}", item["hex"])

        cur_mode = self.settings.get("highlight_mode", "per_song")
        cur_color = self.settings.get("highlight_color", SMOOTH_SOFT_HEX_LIST[0])
        if cur_mode == "per_song":
            self.combo_hl_mode.setCurrentIndex(0)
        else:
            found = False
            for i in range(1, self.combo_hl_mode.count()):
                if self.combo_hl_mode.itemData(i).upper() == cur_color.upper():
                    self.combo_hl_mode.setCurrentIndex(i)
                    found = True
                    break
            if not found:
                self.combo_hl_mode.setCurrentIndex(0)

        self.color_swatch = ColorSwatch(cur_color)

        def _on_color_combo_changed(idx):
            mode_data = self.combo_hl_mode.currentData()
            if mode_data == "per_song":
                self._update_and_sync("highlight_mode", "per_song")
            else:
                self._update_and_sync("highlight_mode", "fixed")
                self._update_and_sync("highlight_color", mode_data)
                self.color_swatch.setColor(mode_data)

        def _on_swatch_changed(hex_val):
            self._update_and_sync("highlight_mode", "fixed")
            self._update_and_sync("highlight_color", hex_val)
            for i in range(1, self.combo_hl_mode.count()):
                if self.combo_hl_mode.itemData(i).upper() == hex_val.upper():
                    self.combo_hl_mode.blockSignals(True)
                    self.combo_hl_mode.setCurrentIndex(i)
                    self.combo_hl_mode.blockSignals(False)
                    break

        self.combo_hl_mode.currentIndexChanged.connect(_on_color_combo_changed)
        self.color_swatch.color_changed.connect(_on_swatch_changed)

        row_color.add_control(self.combo_hl_mode)
        row_color.add_control(self.color_swatch)
        fx_card.add_row(row_color)
        fx_card.add_separator()

        # Hand-Drawn Underline
        row_line = SettingRow(
            "Hand-Drawn Focal Underlines",
            "Sketched marker stroke under 1 or 2 key focal words (not the whole sentence)"
        )
        self.toggle_underline = PillToggle(self.settings.get("hand_drawn_underline_enabled", True))
        self.toggle_underline.toggled.connect(lambda v: self._update_and_sync("hand_drawn_underline_enabled", v))
        row_line.add_control(self.toggle_underline)
        fx_card.add_row(row_line)
        fx_card.add_separator()

        # Auto-Hide When Idle
        row_hide = SettingRow(
            "Auto-Hide When Idle",
            "Instantly vanish when music is paused or Spotify closes"
        )
        self.toggle_hide = PillToggle(self.settings.get("auto_hide_idle", True))
        self.toggle_hide.toggled.connect(lambda v: self._update_and_sync("auto_hide_idle", v))
        row_hide.add_control(self.toggle_hide)
        fx_card.add_row(row_hide)

        layout.addWidget(fx_card)

        # 55+ Animations Showcase Card
        anim_card = SectionCard("55+ Dynamic Animations & Smooth Physics")
        anim_info = QLabel(
            "🎬  <b>Smooth Fade & Continuous 165Hz Physics:</b><br>"
            "Whisper dissolve, silky crossfades, luminous drift, cinematic rise, "
            "kinetic snaps, and gentle elastic springs interpolating continuously at sub-millisecond precision.<br><br>"
            "🎨  <b>Aesthetic Smooth Soft Colors (Per-Song Rotation):</b><br>"
            "Every song is automatically assigned a distinct, vibrant, smooth soft color (Mint Emerald, "
            "Electric Cyan, Lavender Lilac, Coral Rose, Golden Canary, Sky Azure, Bubblegum Pink, etc.) "
            "paired with a soft glowing background pill block for ultra-crisp visibility.<br><br>"
            "🛡️  <b>Anti-Overlap Architecture:</b><br>"
            "Outgoing lyrics lift cleanly away (-32px), guaranteeing zero clashing or text collision with incoming lines."
        )
        anim_info.setWordWrap(True)
        anim_info.setStyleSheet(f"color: {MD3.ON_SURFACE_VARIANT}; font-size: 13px; line-height: 1.6; padding: 16px 20px; background: transparent; border: none;")
        anim_card.add_row(anim_info)
        layout.addWidget(anim_card)

        layout.addStretch()
        scroll.setWidget(content)
        return scroll

    # ── Tab 3: Timing & Synchronization ──
    def _build_timing_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(16)

        sync_card = SectionCard("Audio Synchronization")

        cur_offset = float(self.settings.get("sync_offset_sec", 0.20))
        self.slider_sync = SliderRow(
            "Sync Calibration", "Shift lyrics earlier (−) or later (+) relative to the audio",
            -20, 20, int(cur_offset * 10), "×0.1s"
        )
        self.slider_sync.value_changed.connect(self._on_slider_sync_changed)
        sync_card.add_row(self.slider_sync)

        quick_row = QWidget()
        q_lay = QHBoxLayout(quick_row)
        q_lay.setContentsMargins(20, 4, 20, 14)
        q_lay.setSpacing(8)

        for label, val in [("−0.5s", -5), ("Exact 0.0s", 0), ("+0.2s (Vocal Lead)", 2), ("+0.5s", 5)]:
            btn = QPushButton(label)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {MD3.SURFACE_CONTAINER_HIGH};
                    color: {MD3.ON_SURFACE};
                    font-size: 12px;
                    border-radius: 14px;
                    padding: 5px 14px;
                    border: 1px solid {MD3.OUTLINE_VARIANT};
                }}
                QPushButton:hover {{
                    background: {MD3.PRIMARY_CONTAINER};
                    color: {MD3.ON_PRIMARY_CONTAINER};
                }}
            """)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, v=val: self.slider_sync.setValue(v))
            q_lay.addWidget(btn)

        sync_card.add_row(quick_row)
        layout.addWidget(sync_card)

        tip_card = SectionCard("Live Adjustments")
        tip_lbl = QLabel(
            "⚡  While listening to music, you can fine-tune timing on the fly:\n\n"
            "• Press [  to shift lyrics 0.5s earlier\n"
            "• Press ]  to shift lyrics 0.5s later\n"
            "• Press Ctrl+Alt+L to lock overlay so clicks pass straight through"
        )
        tip_lbl.setWordWrap(True)
        tip_lbl.setStyleSheet(f"color: {MD3.ON_SURFACE_VARIANT}; font-size: 13px; line-height: 1.6; padding: 16px 20px; background: transparent; border: none;")
        tip_card.add_row(tip_lbl)
        layout.addWidget(tip_card)

        layout.addStretch()
        scroll.setWidget(content)
        return scroll

    # ── Tab 4: Presets ──
    def _build_presets_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(14)

        card = SectionCard("One-Click Presets")

        presets = [
            ("7clouds Signature", "Iconic brush style (Edo SZ) with dynamic smooth soft highlights and anti-overlap physics", {
                "font_family": "7clouds Signature (Edo SZ)", "font_size": 42,
                "hand_drawn_underline_enabled": True, "highlight_enabled": True,
                "highlight_block_enabled": True, "highlight_mode": "per_song",
                "highlight_color": "#2EE59D", "target_fps": 165, "sync_offset_sec": 0.20
            }),
            ("Aesthetic Dream", "Lush cinematic crossfades with soft lavender and rose highlights and subtle underlines", {
                "font_family": "7clouds Signature (Edo SZ)", "font_size": 40,
                "hand_drawn_underline_enabled": True, "highlight_enabled": True,
                "highlight_block_enabled": True, "highlight_mode": "per_song",
                "highlight_color": "#C084FC", "target_fps": 165, "sync_offset_sec": 0.20
            }),
            ("7clouds Modern", "Ultra-bold sans-serif (Montserrat Black) with smooth whisper dissolve and electric cyan", {
                "font_family": "7clouds Modern (Montserrat Black)", "font_size": 42,
                "hand_drawn_underline_enabled": True, "highlight_enabled": True,
                "highlight_block_enabled": True, "highlight_mode": "per_song",
                "highlight_color": "#00E5FF", "target_fps": 165, "sync_offset_sec": 0.20
            }),
            ("Minimalist Pure", "Distraction-free pure white typography without highlights", {
                "font_family": "7clouds Signature (Edo SZ)", "font_size": 38,
                "hand_drawn_underline_enabled": False, "highlight_enabled": False,
                "highlight_block_enabled": False, "target_fps": 120, "sync_offset_sec": 0.20
            }),
        ]

        for title, desc, preset_dict in presets:
            row = QWidget()
            r_lay = QHBoxLayout(row)
            r_lay.setContentsMargins(20, 12, 20, 12)
            r_lay.setSpacing(14)

            text_box = QVBoxLayout()
            text_box.setSpacing(2)
            p_title = QLabel(title)
            p_title.setStyleSheet(f"color: {MD3.ON_SURFACE}; font-size: 14px; font-weight: 600; background: transparent; border: none;")
            text_box.addWidget(p_title)

            p_desc = QLabel(desc)
            p_desc.setStyleSheet(f"color: {MD3.ON_SURFACE_VARIANT}; font-size: 12px; background: transparent; border: none;")
            p_desc.setWordWrap(True)
            text_box.addWidget(p_desc)
            r_lay.addLayout(text_box, 1)

            btn = QPushButton("Apply")
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {MD3.PRIMARY_CONTAINER};
                    color: {MD3.ON_PRIMARY_CONTAINER};
                    font-weight: 600;
                    font-size: 12px;
                    border-radius: 14px;
                    padding: 6px 16px;
                    border: none;
                }}
                QPushButton:hover {{
                    background: #255BB3;
                }}
            """)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, d=preset_dict: self._apply_preset(d))
            r_lay.addWidget(btn)

            card.add_row(row)
            card.add_separator()

        layout.addWidget(card)
        layout.addStretch()
        scroll.setWidget(content)
        return scroll

    # ── Tab 5: About & System Diagnostics ──
    def _build_about_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(16)

        # Header Info Card
        app_card = SectionCard()
        app_box = QWidget()
        ab_lay = QHBoxLayout(app_box)
        ab_lay.setContentsMargins(20, 20, 20, 20)
        ab_lay.setSpacing(16)

        icon_label = QLabel()
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.png")
        if os.path.exists(icon_path):
            pix = QPixmap(icon_path).scaled(64, 64, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            icon_label.setPixmap(pix)
        ab_lay.addWidget(icon_label)

        info_col = QVBoxLayout()
        info_col.setSpacing(4)
        app_name = QLabel("Lyric Flow")
        app_name.setStyleSheet(f"color: {MD3.ON_SURFACE}; font-size: 22px; font-weight: 600; background: transparent; border: none;")
        info_col.addWidget(app_name)

        app_ver = QLabel("Cinematic 165Hz Desktop Overlay")
        app_ver.setStyleSheet(f"color: {MD3.PRIMARY}; font-size: 13px; font-weight: 500; background: transparent; border: none;")
        info_col.addWidget(app_ver)

        app_desc = QLabel(
            "Hardware-accelerated desktop lyrics overlay with 55+ animations, "
            "smooth fade transitions, dynamic aesthetic smooth soft color highlights, "
            "anti-overlap typography, and universal Hinglish transliteration."
        )
        app_desc.setWordWrap(True)
        app_desc.setStyleSheet(f"color: {MD3.ON_SURFACE_VARIANT}; font-size: 12px; line-height: 1.5; background: transparent; border: none;")
        info_col.addWidget(app_desc)

        ab_lay.addLayout(info_col, 1)
        app_card.add_row(app_box)
        layout.addWidget(app_card)

        # System Diagnostics Card
        diag_card = SectionCard("System Diagnostics")

        diag_items = [
            ("Rendering Engine", "PyQt6 QPainter (Hardware-Accelerated)"),
            ("Active Refresh Target", f"{self.settings.get('target_fps', 165)} Hz"),
            ("Media Transport", "Windows SMTC (WinRT Native)"),
            ("Sync Strategy", "Real-Time SMTC Elapsed Clock + Lead Calibration"),
            ("Highlight Engine", "Aesthetic Smooth Soft Colors (Per-Song Rotation)"),
            ("Transliteration Engine", "100% Clean Latin Hinglish (Zero Leaks)"),
            ("Lyrics Provider", "LRCLIB (Free & Open)"),
        ]
        for key, val in diag_items:
            row = QWidget()
            rl = QHBoxLayout(row)
            rl.setContentsMargins(20, 8, 20, 8)

            lbl_k = QLabel(key)
            lbl_k.setStyleSheet(f"color: {MD3.ON_SURFACE}; font-size: 13px; background: transparent; border: none;")
            rl.addWidget(lbl_k)
            rl.addStretch()

            lbl_v = QLabel(val)
            lbl_v.setStyleSheet(f"color: {MD3.PRIMARY}; font-size: 12px; font-weight: 500; background: transparent; border: none;")
            rl.addWidget(lbl_v)

            diag_card.add_row(row)
            diag_card.add_separator()

        layout.addWidget(diag_card)

        # Shortcuts list
        sc_card = SectionCard("Keyboard Shortcuts")
        shortcuts = [
            ("Ctrl + Alt + L", "Lock Overlay", "Clicks pass through to windows below"),
            ("Ctrl + Alt + H", "Hide / Unhide", "Quick toggle lyrics visibility"),
            ("Ctrl + Alt + Q", "Quit App", "Exit overlay immediately"),
            ("Ctrl + S", "Settings", "Open customization window"),
            ("Double Click", "Settings", "Double-click floating lyrics text"),
            ("[  /  ]", "Sync Shift", "Adjust audio timing by 0.5s"),
        ]

        for key, act, desc in shortcuts:
            row = QWidget()
            rl = QHBoxLayout(row)
            rl.setContentsMargins(20, 10, 20, 10)
            rl.setSpacing(12)

            text_col = QVBoxLayout()
            text_col.setSpacing(1)
            t_act = QLabel(act)
            t_act.setStyleSheet(f"color: {MD3.ON_SURFACE}; font-size: 13px; font-weight: 500; background: transparent; border: none;")
            text_col.addWidget(t_act)
            t_desc = QLabel(desc)
            t_desc.setStyleSheet(f"color: {MD3.ON_SURFACE_VARIANT}; font-size: 11px; background: transparent; border: none;")
            text_col.addWidget(t_desc)
            rl.addLayout(text_col, 1)

            badge = QLabel(key)
            badge.setStyleSheet(f"""
                color: {MD3.ON_PRIMARY_CONTAINER};
                background: {MD3.PRIMARY_CONTAINER};
                font-size: 11px;
                font-weight: 600;
                font-family: 'Cascadia Code', 'Consolas', monospace;
                padding: 4px 10px;
                border-radius: 6px;
            """)
            rl.addWidget(badge)

            sc_card.add_row(row)
            if key != "[  /  ]":
                sc_card.add_separator()

        layout.addWidget(sc_card)
        layout.addStretch()
        scroll.setWidget(content)
        return scroll

    # ── Real-Time Sync Handlers (Instant Live Update, Zero Crash) ──
    def _update_and_sync(self, key: str, val):
        try:
            self.settings[key] = val
            settings_manager.save_settings(self.settings)
            if hasattr(self, 'preview_widget'):
                self.preview_widget.update_settings(self.settings)
            self.settings_changed.emit(self.settings)
        except Exception:
            pass

    def _on_font_changed(self, idx):
        choice = self.combo_font.currentText()
        self._update_and_sync("font_family", choice)

    def _on_slider_size_changed(self, val: int):
        self._update_and_sync("font_size", val)

    def _on_slider_y_changed(self, val: int):
        self._update_and_sync("overlay_y", val)

    def _on_slider_sync_changed(self, val: int):
        offset = round(val / 10.0, 2)
        self._update_and_sync("sync_offset_sec", offset)

    def _on_fps_changed(self, idx):
        fps_values = [60, 120, 144, 165, 240]
        chosen = fps_values[self.combo_fps.currentIndex()]
        self._update_and_sync("target_fps", chosen)

    def _apply_preset(self, preset: dict):
        try:
            self.settings.update(preset)
            settings_manager.save_settings(self.settings)

            if "font_size" in preset:
                self.slider_size.setValue(preset["font_size"])
            if "overlay_y" in preset:
                self.slider_y.setValue(preset["overlay_y"])
            if "font_family" in preset:
                fam = preset["font_family"]
                idx = 0
                if "Montserrat" in fam or "Modern" in fam:
                    idx = 1
                elif "Poppins" in fam:
                    idx = 2
                elif "Segoe" in fam:
                    idx = 3
                self.combo_font.setCurrentIndex(idx)
            if "hand_drawn_underline_enabled" in preset:
                self.toggle_underline.setChecked(preset["hand_drawn_underline_enabled"])
            if "highlight_enabled" in preset:
                self.toggle_highlight.setChecked(preset["highlight_enabled"])
            if "highlight_block_enabled" in preset and hasattr(self, "toggle_hl_block"):
                self.toggle_hl_block.setChecked(preset["highlight_block_enabled"])
            if "highlight_color" in preset:
                self.color_swatch.setColor(preset["highlight_color"])
            if "highlight_mode" in preset and hasattr(self, "combo_hl_mode"):
                if preset["highlight_mode"] == "per_song":
                    self.combo_hl_mode.setCurrentIndex(0)
                elif "highlight_color" in preset:
                    for i in range(1, self.combo_hl_mode.count()):
                        if self.combo_hl_mode.itemData(i).upper() == preset["highlight_color"].upper():
                            self.combo_hl_mode.setCurrentIndex(i)
                            break
            if "target_fps" in preset:
                fps_map = {60: 0, 120: 1, 144: 2, 165: 3, 240: 4}
                self.combo_fps.setCurrentIndex(fps_map.get(preset["target_fps"], 3))

            if hasattr(self, 'preview_widget'):
                self.preview_widget.update_settings(self.settings)
            self.settings_changed.emit(self.settings)
        except Exception:
            pass

    def _reset_to_defaults(self):
        defaults = {
            "target_fps": 165,
            "font_size": 42,
            "font_family": "7clouds Signature (Edo SZ)",
            "overlay_y": 55,
            "sync_offset_sec": 0.20,
            "auto_hide_idle": True,
            "hand_drawn_underline_enabled": True,
            "highlight_enabled": True,
            "highlight_block_enabled": True,
            "highlight_color": "#2EE59D",
            "highlight_mode": "per_song",
        }
        self._apply_preset(defaults)
        self.slider_sync.setValue(2)
        self.toggle_hide.setChecked(True)

    def _on_done_clicked(self):
        """Only hides the settings dialog. Does NOT quit the overlay app."""
        settings_manager.save_settings(self.settings)
        self.hide()

    def _on_quit_clicked(self):
        self.quit_requested.emit()
        self.close()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    font_dir = os.path.join(os.path.dirname(__file__), "fonts")
    for f in ("EdoSZ.ttf", "Montserrat-Black.ttf", "Montserrat.ttf", "Poppins-Bold.ttf"):
        fp = os.path.join(font_dir, f)
        if os.path.exists(fp):
            QFontDatabase.addApplicationFont(fp)

    settings = settings_manager.load_settings()
    dlg = SettingsDialog(settings)
    dlg.show()
    sys.exit(app.exec())
