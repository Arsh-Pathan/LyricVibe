"""
Settings Window for Spotify Floating Lyrics Overlay.
Material Design 3 dark theme with live preview, interactive animation tester,
preset quick-selectors, and pill switches.
"""

import sys
import os
import time
import math
import random

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QSlider,
    QCheckBox, QComboBox, QPushButton, QGroupBox, QWidget,
    QTabWidget, QFrame, QScrollArea, QSizePolicy, QGraphicsOpacityEffect,
    QSpacerItem, QLineEdit
)
from PyQt6.QtCore import (
    Qt, pyqtSignal, QTimer, QPropertyAnimation, QEasingCurve,
    QPoint, QPointF, QRectF, QSize, pyqtProperty
)
from PyQt6.QtGui import (
    QFont, QColor, QPainter, QPen, QBrush, QPainterPath,
    QFontDatabase, QLinearGradient, QRadialGradient, QIcon, QPixmap
)

import settings_manager


# ─── Material Design 3 Dark Theme Palette ─────────────────────────────
class MD3:
    """Material Design 3 Dark Theme tokens."""
    # Surfaces
    SURFACE               = "#101318"  # Deep canvas
    SURFACE_DIM           = "#0B0E12"
    SURFACE_CONTAINER_LOW = "#181C22"  # Low elevation
    SURFACE_CONTAINER     = "#1E2228"  # Standard card
    SURFACE_CONTAINER_HIGH= "#262B33"  # Highlighted card
    SURFACE_CONTAINER_MAX = "#313640"
    SURFACE_BRIGHT        = "#373C46"

    # Primary (Material Sky / Blue Accent)
    PRIMARY               = "#A8C7FA"
    ON_PRIMARY            = "#062E6F"
    PRIMARY_CONTAINER     = "#0842A0"
    ON_PRIMARY_CONTAINER  = "#D3E3FD"

    # Secondary (Slate / Sage)
    SECONDARY             = "#BEC6DC"
    ON_SECONDARY          = "#283042"
    SECONDARY_CONTAINER   = "#3E4759"
    ON_SECONDARY_CONTAINER= "#DAE2F9"

    # Accent / Green (Media Playing status)
    ACCENT_GREEN          = "#1DB954"
    ACCENT_GREEN_CONTAINER= "#0A3E1D"
    ON_ACCENT_GREEN       = "#A7F3D0"

    # Error
    ERROR                 = "#FFB4AB"
    ERROR_CONTAINER       = "#690005"
    ON_ERROR_CONTAINER    = "#FFDAD6"

    # Typography
    ON_SURFACE            = "#E2E2E9"
    ON_SURFACE_VARIANT    = "#C4C6D0"
    OUTLINE               = "#8E9099"
    OUTLINE_VARIANT       = "#363B44"

    # Radii
    RADIUS_SM = 8
    RADIUS_MD = 12
    RADIUS_LG = 16
    RADIUS_PILL = 28


# ─── Material Pill Toggle Switch ──────────────────────────────────────
class PillToggle(QWidget):
    """Material Design 3 animated pill toggle switch."""
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

        # Track background
        if t > 0.5:
            track_color = QColor(MD3.PRIMARY)
            track_border = QColor(MD3.PRIMARY)
        else:
            track_color = QColor(MD3.SURFACE_CONTAINER_MAX)
            track_border = QColor(MD3.OUTLINE_VARIANT)

        p.setPen(QPen(track_border, 1.5))
        p.setBrush(track_color)
        p.drawRoundedRect(QRectF(1, 1, w - 2, h - 2), h / 2.0, h / 2.0)

        # Handle thumb (shrinks slightly when off, expands when on)
        thumb_r = 8.5 + t * 2.5
        thumb_x = 16.0 + t * (w - 32.0)
        thumb_y = h / 2.0

        if t > 0.5:
            thumb_color = QColor(MD3.ON_PRIMARY)
        else:
            thumb_color = QColor(MD3.OUTLINE)

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(thumb_color)
        p.drawEllipse(QPointF(thumb_x, thumb_y), thumb_r, thumb_r)
        p.end()


# ─── Setting Item Row ─────────────────────────────────────────────────
class SettingRow(QWidget):
    """A single Material preference row with title, description, and control widget."""

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


# ─── Material Slider Row ──────────────────────────────────────────────
class SliderRow(QWidget):
    """A preference row with a Material styled slider and value badge."""
    value_changed = pyqtSignal(int)

    def __init__(self, title: str, subtitle: str, min_val: int, max_val: int,
                 value: int, suffix: str = "", parent=None):
        super().__init__(parent)
        self.suffix = suffix
        self.setMinimumHeight(82)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 12, 20, 12)
        layout.setSpacing(8)

        # Header
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

        # Slider
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


# ─── Material Surface Card ────────────────────────────────────────────
class SectionCard(QFrame):
    """A Material Design 3 surface card container."""

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


# ─── Live Animated Lyrics Preview ─────────────────────────────────────
class LivePreview(QWidget):
    """Interactive preview canvas with real-time typography & animation rendering."""

    PREVIEW_LINES = [
        "Mere haath mein tera haath ho",
        "Cause you knew that I'd be at one",
        "Saari jannatein mere paas ho",
        "I fell in love with a girl I met in hell",
        "Tu jo paas ho phir kya yeh jahaan",
    ]

    ANIMATION_OPTIONS = [
        ("Scale & Fade (Classic)", "scale_fade"),
        ("Slide Up (Smooth)", "slide_up"),
        ("Word by Word Reveal", "word_reveal"),
        ("Kinetic Snap (Punchy)", "kinetic_snap"),
        ("Glow Bloom (Luminous)", "glow_bloom"),
        ("Hand-Drawn Underline", "hand_drawn_underline"),
        ("Chromatic Split (Rare)", "chromatic_split"),
        ("Elastic Bounce", "elastic_slingshot"),
        ("Velocity Blur Streak", "horizontal_blur_streak"),
    ]

    def __init__(self, settings: dict, parent=None):
        super().__init__(parent)
        self.settings = settings.copy()
        self.setFixedHeight(170)

        self._current_line_idx = 0
        self._current_text = self.PREVIEW_LINES[0]
        self._current_anim_type = "scale_fade"

        self._anim_start = time.time()
        self._anim_dur = 0.45

        # Word reveal words
        self._words = self._current_text.split()
        self._word_alphas = [1.0] * len(self._words)

        # 60 FPS animation timer for preview
        self._render_timer = QTimer(self)
        self._render_timer.timeout.connect(self.update)
        self._render_timer.start(16)

        # Auto line cycler
        self._cycle_timer = QTimer(self)
        self._cycle_timer.timeout.connect(self.next_line)
        self._cycle_timer.start(3500)

    def trigger_animation(self, anim_type: str = None):
        if anim_type:
            self._current_anim_type = anim_type
        self._anim_start = time.time()
        self._words = self._current_text.split()
        self._word_alphas = [0.0] * len(self._words)
        self.update()

    def next_line(self):
        self._current_line_idx = (self._current_line_idx + 1) % len(self.PREVIEW_LINES)
        self._current_text = self.PREVIEW_LINES[self._current_line_idx]
        self.trigger_animation()

    def set_custom_text(self, text: str):
        if text.strip():
            self._current_text = text.strip()
            self.trigger_animation()

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
        for x in range(16, w, 32):
            for y in range(16, h, 32):
                p.drawEllipse(QPointF(x, y), 1.2, 1.2)

        # Easing computation
        now = time.time()
        elapsed = now - self._anim_start
        t = min(elapsed / self._anim_dur, 1.0)
        ease_out = 1.0 - math.pow(1.0 - t, 3)

        scale = 1.0
        alpha = ease_out
        offset_y = 0.0
        offset_x = 0.0
        chroma = 0.0
        blur_alpha = 0.0
        underline_prog = 0.0

        if self._current_anim_type == "scale_fade":
            scale = 0.92 + 0.08 * ease_out
            blur_alpha = (1.0 - ease_out) * 0.3
        elif self._current_anim_type == "slide_up":
            offset_y = (1.0 - ease_out) * 22.0
            blur_alpha = (1.0 - ease_out) * 0.35
        elif self._current_anim_type == "kinetic_snap":
            scale = 1.15 - (0.15 * ease_out) if t > 0.3 else (0.85 + 0.3 * (t / 0.3))
        elif self._current_anim_type == "chromatic_split":
            chroma = (1.0 - ease_out) * 6.0
        elif self._current_anim_type == "elastic_slingshot":
            elastic = 1.0 - math.pow(2.0, -10 * t) * math.cos((t * 10 - 0.75) * ((2 * math.pi) / 3)) if t < 1.0 else 1.0
            scale = max(0.5, elastic)
        elif self._current_anim_type == "horizontal_blur_streak":
            offset_x = (1.0 - ease_out) * 35.0
            blur_alpha = (1.0 - ease_out) * 0.5
        elif self._current_anim_type == "hand_drawn_underline":
            underline_prog = min(max(elapsed / 0.45, 0.0), 1.0)
        elif self._current_anim_type == "word_reveal":
            num_w = len(self._words)
            if num_w > 0:
                step = self._anim_dur / num_w
                for i in range(num_w):
                    wt = (elapsed - i * step) / max(step, 0.1)
                    self._word_alphas[i] = min(max(wt, 0.2), 1.0)

        # Typography configuration
        font_size = min(self.settings.get("font_size", 42), 34)
        font = QFont("Montserrat", font_size, QFont.Weight.Bold)
        font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
        p.setFont(font)

        cx = w / 2.0 + offset_x
        cy = h / 2.0 + offset_y

        # Motion Blur layer
        if self.settings.get("motion_blur_enabled", True) and blur_alpha > 0.05:
            b_col = QColor(255, 255, 255, int(blur_alpha * 120))
            p.setPen(b_col)
            for mult in (0.5, 1.0):
                p.drawText(QRectF(cx - 300, cy - 30 + mult * 4, 600, 60),
                           Qt.AlignmentFlag.AlignCenter, self._current_text)

        # Vocal Glow bloom halo
        if self.settings.get("glow_enabled", True) and alpha > 0.1:
            glow_col = QColor(255, 255, 255, int(alpha * 45))
            p.setPen(glow_col)
            for r in (2, 4):
                for dx, dy in ((-r, 0), (r, 0), (0, -r), (0, r)):
                    p.drawText(QRectF(cx + dx - 300, cy + dy - 30, 600, 60),
                               Qt.AlignmentFlag.AlignCenter, self._current_text)

        # Chromatic split
        if chroma > 0.5:
            p.setPen(QColor(100, 220, 255, int(alpha * 130)))
            p.drawText(QRectF(cx - chroma - 300, cy - 30, 600, 60),
                       Qt.AlignmentFlag.AlignCenter, self._current_text)
            p.setPen(QColor(255, 120, 140, int(alpha * 130)))
            p.drawText(QRectF(cx + chroma - 300, cy - 30, 600, 60),
                       Qt.AlignmentFlag.AlignCenter, self._current_text)

        # Main pure white text
        main_a = max(0, min(255, int(alpha * 255)))
        p.setPen(QColor(255, 255, 255, main_a))

        p.save()
        p.translate(cx, cy)
        if scale != 1.0:
            p.scale(scale, scale)

        if self._current_anim_type == "word_reveal" and self.settings.get("word_reveal_enabled", True):
            metrics = p.fontMetrics()
            space_w = metrics.horizontalAdvance(" ")
            w_widths = [metrics.horizontalAdvance(w) for w in self._words]
            total_w = sum(w_widths) + (len(self._words) - 1) * space_w
            start_x = -total_w / 2.0
            curr_x = start_x
            text_y = metrics.ascent() - metrics.height() / 2.0
            for idx, word in enumerate(self._words):
                w_a = self._word_alphas[idx] if idx < len(self._word_alphas) else 1.0
                p.setPen(QColor(255, 255, 255, int(w_a * 255)))
                p.drawText(QPointF(curr_x, text_y), word)
                curr_x += w_widths[idx] + space_w
        else:
            p.drawText(QRectF(-300, -30, 600, 60), Qt.AlignmentFlag.AlignCenter, self._current_text)

        p.restore()

        # Hand-drawn underline
        if underline_prog > 0.0 and self.settings.get("hand_drawn_underline_enabled", True):
            metrics = p.fontMetrics()
            t_w = min(metrics.horizontalAdvance(self._current_text), 500)
            u_start = cx - t_w / 2.0
            u_target = t_w * underline_prog
            if u_target > 4:
                u_pen = QPen(QColor(255, 255, 255, int(alpha * 200)), 2.5)
                u_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
                p.setPen(u_pen)
                u_path = QPainterPath()
                u_path.moveTo(u_start, cy + 24)
                u_path.quadTo(u_start + u_target / 2.0, cy + 26, u_start + u_target, cy + 25)
                p.drawPath(u_path)

        # Corner badge: LIVE PREVIEW
        p.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
        p.setPen(QColor(MD3.PRIMARY))
        p.drawText(QRectF(0, 10, w - 16, 20), Qt.AlignmentFlag.AlignRight, "● LIVE PREVIEW")

        p.end()


# ─── Main Settings Window ─────────────────────────────────────────────
class SettingsDialog(QDialog):
    settings_changed = pyqtSignal(dict)
    quit_requested = pyqtSignal()

    def __init__(self, current_settings: dict, parent=None):
        super().__init__(parent)
        self.settings = current_settings.copy()
        self.setWindowTitle("Lyric Flow — Settings")
        self.setFixedSize(580, 780)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowStaysOnTopHint)

        # Set Window Icon
        self._load_icon()

        self._apply_theme()
        self._build_ui()

    def _load_icon(self):
        icon_dir = os.path.dirname(os.path.abspath(__file__))
        for icon_name in ("icon.ico", "icon.png"):
            p = os.path.join(icon_dir, icon_name)
            if os.path.exists(p):
                self.setWindowIcon(QIcon(p))
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
                min-width: 130px;
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
            QLineEdit {{
                background: {MD3.SURFACE_CONTAINER_HIGH};
                border: 1px solid {MD3.OUTLINE_VARIANT};
                border-radius: 8px;
                padding: 6px 12px;
                color: {MD3.ON_SURFACE};
                font-size: 13px;
            }}
            QLineEdit:focus {{
                border-color: {MD3.PRIMARY};
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

        # ── Top Bar with Icon & Title ──
        header = QWidget()
        header.setFixedHeight(68)
        header.setStyleSheet(f"background: {MD3.SURFACE};")
        h_lay = QHBoxLayout(header)
        h_lay.setContentsMargins(24, 0, 20, 0)
        h_lay.setSpacing(14)

        # App Icon in header
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

        # Active status pill
        status_pill = QLabel("● Active")
        status_pill.setStyleSheet(f"""
            color: {MD3.ACCENT_GREEN};
            background-color: {MD3.ACCENT_GREEN_CONTAINER};
            font-size: 12px;
            font-weight: 600;
            padding: 4px 12px;
            border-radius: 12px;
        """)
        h_lay.addWidget(status_pill)

        root.addWidget(header)

        # ── Material Tabs ──
        tabs = QTabWidget()
        tabs.setDocumentMode(True)

        tabs.addTab(self._build_display_tab(), "Display")
        tabs.addTab(self._build_animations_tab(), "Effects")
        tabs.addTab(self._build_timing_tab(), "Sync")
        tabs.addTab(self._build_presets_tab(), "Presets")
        tabs.addTab(self._build_about_tab(), "About")

        root.addWidget(tabs, 1)

        # ── Bottom Floating Action Bar ──
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

        # Quit button (Error Tonal)
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

        # Reset button (Tonal)
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

        # Save button (Filled Primary Pill)
        btn_save = QPushButton("Save & Apply")
        btn_save.setStyleSheet(f"""
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
        btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save.clicked.connect(self._on_apply_clicked)
        b_lay.addWidget(btn_save)

        root.addWidget(bottom_bar)

    # ── Tab 1: Display & Preview ──
    def _build_display_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(16)

        # 1. Interactive Preview Card
        preview_card = SectionCard("Live Preview")
        self.preview_widget = LivePreview(self.settings)
        preview_card.add_row(self.preview_widget)

        # Preview Controls sub-row (test dropdown + replay button)
        p_ctrls = QWidget()
        p_c_lay = QHBoxLayout(p_ctrls)
        p_c_lay.setContentsMargins(18, 8, 18, 12)
        p_c_lay.setSpacing(10)

        self.combo_preview_anim = QComboBox()
        for label, anim_key in LivePreview.ANIMATION_OPTIONS:
            self.combo_preview_anim.addItem(label, anim_key)
        self.combo_preview_anim.currentIndexChanged.connect(self._on_preview_anim_changed)
        p_c_lay.addWidget(self.combo_preview_anim, 1)

        btn_test_anim = QPushButton("▶ Replay")
        btn_test_anim.setStyleSheet(f"""
            QPushButton {{
                background: {MD3.PRIMARY_CONTAINER};
                color: {MD3.ON_PRIMARY_CONTAINER};
                font-weight: 600;
                font-size: 12px;
                border-radius: 16px;
                padding: 6px 16px;
                border: none;
            }}
            QPushButton:hover {{
                background: #255BB3;
            }}
        """)
        btn_test_anim.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_test_anim.clicked.connect(lambda: self.preview_widget.trigger_animation(self.combo_preview_anim.currentData()))
        p_c_lay.addWidget(btn_test_anim)

        btn_next_lyric = QPushButton("Next Line ⏭")
        btn_next_lyric.setStyleSheet(f"""
            QPushButton {{
                background: {MD3.SURFACE_CONTAINER_HIGH};
                color: {MD3.ON_SURFACE};
                font-size: 12px;
                border-radius: 16px;
                padding: 6px 14px;
                border: 1px solid {MD3.OUTLINE_VARIANT};
            }}
            QPushButton:hover {{
                background: {MD3.SURFACE_CONTAINER_MAX};
            }}
        """)
        btn_next_lyric.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_next_lyric.clicked.connect(self.preview_widget.next_line)
        p_c_lay.addWidget(btn_next_lyric)

        preview_card.add_row(p_ctrls)
        layout.addWidget(preview_card)

        # 2. Performance Card
        perf_card = SectionCard("Performance & Refresh Rate")

        row_fps = SettingRow("Target Refresh Rate", "Hardware-accelerated timer for high-refresh monitors")
        self.combo_fps = QComboBox()
        self.combo_fps.addItems(["60 Hz", "120 Hz", "144 Hz", "165 Hz (Recommended)", "240 Hz"])
        cur_fps = self.settings.get("target_fps", 165)
        fps_map = {60: 0, 120: 1, 144: 2, 165: 3, 240: 4}
        self.combo_fps.setCurrentIndex(fps_map.get(cur_fps, 3))
        row_fps.add_control(self.combo_fps)
        perf_card.add_row(row_fps)

        layout.addWidget(perf_card)

        # 3. Typography & Position Card
        typo_card = SectionCard("Typography & Screen Position")

        self.slider_size = SliderRow(
            "Font Size", "Controls lyrics scale across all animations",
            28, 64, self.settings.get("font_size", 42), "px"
        )
        self.slider_size.value_changed.connect(self._sync_preview)
        typo_card.add_row(self.slider_size)
        typo_card.add_separator()

        self.slider_y = SliderRow(
            "Top Screen Margin", "Distance from the top edge of your monitor",
            10, 350, self.settings.get("overlay_y", 55), "px"
        )
        typo_card.add_row(self.slider_y)

        layout.addWidget(typo_card)

        layout.addStretch()
        scroll.setWidget(content)
        return scroll

    # ── Tab 2: Animations & Effects ──
    def _build_animations_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(16)

        fx_card = SectionCard("Cinematic Visual Effects")

        # Motion Blur
        row_blur = SettingRow("Motion Blur Streaks", "Velocity-based ghost frames for liquid high-framerate transitions")
        self.toggle_blur = PillToggle(self.settings.get("motion_blur_enabled", True))
        self.toggle_blur.toggled.connect(self._sync_preview)
        row_blur.add_control(self.toggle_blur)
        fx_card.add_row(row_blur)
        fx_card.add_separator()

        # Vocal Glow Bloom
        row_glow = SettingRow("Luminous Vocal Glow", "Soft multi-pass white bloom halo that breathes with singing")
        self.toggle_glow = PillToggle(self.settings.get("glow_enabled", True))
        self.toggle_glow.toggled.connect(self._sync_preview)
        row_glow.add_control(self.toggle_glow)
        fx_card.add_row(row_glow)
        fx_card.add_separator()

        # Hand-Drawn Underline
        row_line = SettingRow("Hand-Drawn Brush Underlines", "Organic curved underlines drawn dynamically under key phrases")
        self.toggle_underline = PillToggle(self.settings.get("hand_drawn_underline_enabled", True))
        self.toggle_underline.toggled.connect(self._sync_preview)
        row_line.add_control(self.toggle_underline)
        fx_card.add_row(row_line)
        fx_card.add_separator()

        # Word Reveal
        row_word = SettingRow("Word-by-Word Vocal Reveal", "Progressive syllable illumination for slow, soulful vocal lines")
        self.toggle_word_reveal = PillToggle(self.settings.get("word_reveal_enabled", True))
        self.toggle_word_reveal.toggled.connect(self._sync_preview)
        row_word.add_control(self.toggle_word_reveal)
        fx_card.add_row(row_word)

        layout.addWidget(fx_card)

        # Smart Behavior Card
        beh_card = SectionCard("Overlay Behavior")

        row_hide = SettingRow("Auto-Hide When Idle", "Seamlessly vanish when music is paused or Spotify closes")
        self.toggle_auto_hide = PillToggle(self.settings.get("auto_hide_idle", True))
        row_hide.add_control(self.toggle_auto_hide)
        beh_card.add_row(row_hide)

        layout.addWidget(beh_card)

        layout.addStretch()
        scroll.setWidget(content)
        return scroll

    # ── Tab 3: Timing & Sync ──
    def _build_timing_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(16)

        sync_card = SectionCard("Playback Synchronization")

        cur_offset = self.settings.get("sync_offset_sec", 0.0)
        self.slider_sync = SliderRow(
            "Sync Calibration", "Shift lyrics earlier (−) or later (+) relative to the audio",
            -20, 20, int(cur_offset * 10), "×0.1s"
        )
        sync_card.add_row(self.slider_sync)

        # Quick calibration pill buttons
        quick_row = QWidget()
        q_lay = QHBoxLayout(quick_row)
        q_lay.setContentsMargins(20, 4, 20, 14)
        q_lay.setSpacing(8)

        for label, val in [("−0.5s", -5), ("Exact 0.0s", 0), ("+0.5s", 5)]:
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

        # Hotkeys reminder card
        tip_card = SectionCard("Live Adjustments")
        tip_lbl = QLabel(
            "⚡  While listening to music, you can fine-tune timing on the fly:\n\n"
            "• Press [  to shift lyrics 0.5s earlier\n"
            "• Press ]  to shift lyrics 0.5s later\n"
            "• Press Ctrl+Alt+L to lock the overlay so clicks pass straight through"
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
            ("🎬 Cinematic 165Hz", "Full visual suite: 165Hz, motion blur, bloom glow, and dynamic word reveal", {
                "target_fps": 165, "font_size": 42, "motion_blur_enabled": True,
                "glow_enabled": True, "hand_drawn_underline_enabled": True, "word_reveal_enabled": True
            }),
            ("✨ Minimalist Pure", "Clean floating white typography without blur or bloom for distraction-free focus", {
                "target_fps": 120, "font_size": 40, "motion_blur_enabled": False,
                "glow_enabled": False, "hand_drawn_underline_enabled": False, "word_reveal_enabled": False
            }),
            ("⚡ High Velocity Gaming", "Ultra responsive 240Hz, snappy kinetic transitions with motion blur", {
                "target_fps": 240, "font_size": 38, "motion_blur_enabled": True,
                "glow_enabled": True, "hand_drawn_underline_enabled": False, "word_reveal_enabled": True
            }),
            ("🎙 Vocal Focus", "Large bold text with luminous vocal bloom and word-by-word reveal", {
                "target_fps": 165, "font_size": 48, "motion_blur_enabled": False,
                "glow_enabled": True, "hand_drawn_underline_enabled": True, "word_reveal_enabled": True
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

            btn_apply_preset = QPushButton("Apply")
            btn_apply_preset.setStyleSheet(f"""
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
            btn_apply_preset.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_apply_preset.clicked.connect(lambda _, d=preset_dict: self._apply_preset(d))
            r_lay.addWidget(btn_apply_preset)

            card.add_row(row)
            card.add_separator()

        layout.addWidget(card)
        layout.addStretch()
        scroll.setWidget(content)
        return scroll

    # ── Tab 5: About & Shortcuts ──
    def _build_about_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(16)

        # App Identity Card
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
            "Hardware-accelerated lyrics overlay for Spotify with 18 weighted animations, "
            "automatic Hindi → Hinglish transliteration, and zero-configuration setup."
        )
        app_desc.setWordWrap(True)
        app_desc.setStyleSheet(f"color: {MD3.ON_SURFACE_VARIANT}; font-size: 12px; line-height: 1.5; background: transparent; border: none;")
        info_col.addWidget(app_desc)

        ab_lay.addLayout(info_col, 1)
        app_card.add_row(app_box)
        layout.addWidget(app_card)

        # Shortcuts list
        sc_card = SectionCard("Keyboard Shortcuts")
        shortcuts = [
            ("Ctrl + Alt + L", "Lock Overlay", "Clicks pass through to windows below"),
            ("Ctrl + Alt + H", "Hide / Unhide", "Quick toggle lyrics visibility"),
            ("Ctrl + Alt + Q", "Quit App", "Exit the overlay immediately"),
            ("Ctrl + S", "Settings", "Open this customization window"),
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

    # ── Helpers ──
    def _on_preview_anim_changed(self, idx):
        anim_key = self.combo_preview_anim.currentData()
        self.preview_widget.trigger_animation(anim_key)

    def _sync_preview(self, *args):
        if hasattr(self, 'preview_widget'):
            p_settings = self.settings.copy()
            p_settings["font_size"] = self.slider_size.value()
            p_settings["glow_enabled"] = self.toggle_glow.isChecked()
            p_settings["motion_blur_enabled"] = self.toggle_blur.isChecked()
            p_settings["hand_drawn_underline_enabled"] = self.toggle_underline.isChecked()
            p_settings["word_reveal_enabled"] = self.toggle_word_reveal.isChecked()
            self.preview_widget.update_settings(p_settings)

    def _apply_preset(self, preset: dict):
        if "font_size" in preset:
            self.slider_size.setValue(preset["font_size"])
        if "motion_blur_enabled" in preset:
            self.toggle_blur.setChecked(preset["motion_blur_enabled"])
        if "glow_enabled" in preset:
            self.toggle_glow.setChecked(preset["glow_enabled"])
        if "hand_drawn_underline_enabled" in preset:
            self.toggle_underline.setChecked(preset["hand_drawn_underline_enabled"])
        if "word_reveal_enabled" in preset:
            self.toggle_word_reveal.setChecked(preset["word_reveal_enabled"])
        if "target_fps" in preset:
            fps_map = {60: 0, 120: 1, 144: 2, 165: 3, 240: 4}
            self.combo_fps.setCurrentIndex(fps_map.get(preset["target_fps"], 3))
        self._sync_preview()

    def _reset_to_defaults(self):
        defaults = settings_manager.DEFAULT_SETTINGS
        self._apply_preset(defaults)
        self.slider_y.setValue(defaults.get("overlay_y", 55))
        self.slider_sync.setValue(0)
        self.toggle_auto_hide.setChecked(defaults.get("auto_hide_idle", True))

    def _on_apply_clicked(self):
        fps_values = [60, 120, 144, 165, 240]
        chosen_fps = fps_values[self.combo_fps.currentIndex()]

        updated = {
            "target_fps": chosen_fps,
            "font_size": self.slider_size.value(),
            "overlay_y": self.slider_y.value(),
            "motion_blur_enabled": self.toggle_blur.isChecked(),
            "glow_enabled": self.toggle_glow.isChecked(),
            "hand_drawn_underline_enabled": self.toggle_underline.isChecked(),
            "word_reveal_enabled": self.toggle_word_reveal.isChecked(),
            "auto_hide_idle": self.toggle_auto_hide.isChecked(),
            "sync_offset_sec": round(self.slider_sync.value() / 10.0, 2),
        }
        self.settings.update(updated)
        settings_manager.save_settings(self.settings)
        self.settings_changed.emit(self.settings)
        self.accept()

    def _on_quit_clicked(self):
        self.quit_requested.emit()
        self.close()


# ─── Standalone Runner ────────────────────────────────────────────────
if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Load 7clouds fonts
    font_dir = os.path.join(os.path.dirname(__file__), "fonts")
    for f in ("Montserrat.ttf", "Poppins-Bold.ttf"):
        fp = os.path.join(font_dir, f)
        if os.path.exists(fp):
            QFontDatabase.addApplicationFont(fp)

    settings = settings_manager.load_settings()
    dlg = SettingsDialog(settings)
    dlg.show()
    sys.exit(app.exec())
