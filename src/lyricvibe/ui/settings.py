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

from __future__ import annotations

import logging
import os
import sys
from typing import ClassVar

logger = logging.getLogger(__name__)

from PyQt6.QtCore import (
    QEasingCurve,
    QPointF,
    QPropertyAnimation,
    QRectF,
    Qt,
    QTimer,
    pyqtProperty,
    pyqtSignal,
)
from PyQt6.QtGui import (
    QColor,
    QFont,
    QFontDatabase,
    QFontMetrics,
    QIcon,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)
from PyQt6.QtWidgets import (
    QApplication,
    QColorDialog,
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSlider,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

try:
    import lyricvibe.utils.settings as settings_manager
    from lyricvibe.core.animation import (
        ANIMATION_CATALOG,
        ANIMATION_CATEGORIES,
        FADE_ANIMS,
        PER_CHAR_ANIMS,
        AnimationEngine,
    )
    from lyricvibe.core.paths import get_asset_path
    from lyricvibe.utils.settings import (
        BRIGHT_HIGHLIGHT_HEX_LIST,
        BRIGHT_HIGHLIGHT_PALETTE,
        ensure_bright_hex,
        is_autostart_enabled,
        set_autostart_enabled,
    )
except ImportError:
    import settings_manager
    from animation_engine import (
        ANIMATION_CATALOG,
        ANIMATION_CATEGORIES,
        FADE_ANIMS,
        PER_CHAR_ANIMS,
        AnimationEngine,
    )
    from settings_manager import (
        BRIGHT_HIGHLIGHT_HEX_LIST,
        BRIGHT_HIGHLIGHT_PALETTE,
        ensure_bright_hex,
        is_autostart_enabled,
        set_autostart_enabled,
    )

    get_asset_path = lambda p: p


# ─── Material Design 3 Dark Theme Palette ─────────────────────────────
class MD3:
    # ── Luxury Monochrome Canvas & Surfaces ──
    SURFACE = "#0A0A0C"                 # Deepest obsidian black canvas
    SURFACE_DIM = "#050507"             # Pure pitch black
    SURFACE_CONTAINER_LOW = "#101013"   # Low-elevation surface
    SURFACE_CONTAINER = "#141417"       # Clean monochrome card surface
    SURFACE_CONTAINER_HIGH = "#1E1E22"  # Elevated monochrome card
    SURFACE_CONTAINER_MAX = "#28282E"   # Highest card / slider groove

    # ── High-Contrast Black & White Accents ──
    PRIMARY = "#FFFFFF"                 # Pure crisp white
    ON_PRIMARY = "#000000"              # Pure black on primary
    PRIMARY_CONTAINER = "#222226"       # Dark graphite container
    ON_PRIMARY_CONTAINER = "#FFFFFF"    # Crisp white text

    ACCENT_GREEN = "#FFFFFF"            # Clean monochrome
    ACCENT_GREEN_BG = "#1A1A1E"

    ERROR = "#EF4444"
    ERROR_CONTAINER = "#1F1214"
    ON_ERROR_CONTAINER = "#FCA5A5"

    ON_SURFACE = "#FFFFFF"              # Crisp primary white
    ON_SURFACE_VARIANT = "#A1A1AA"      # Muted silver secondary text
    OUTLINE = "#52525B"                 # Medium zinc border
    OUTLINE_VARIANT = "#222226"         # Subtle 1px zinc divider

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
        self.title_label.setStyleSheet(
            f"color: {MD3.ON_SURFACE}; font-size: 14px; font-weight: 500; background: transparent; border: none;"
        )
        text_col.addWidget(self.title_label)

        if subtitle:
            self.subtitle_label = QLabel(subtitle)
            self.subtitle_label.setStyleSheet(
                f"color: {MD3.ON_SURFACE_VARIANT}; font-size: 12px; background: transparent; border: none;"
            )
            self.subtitle_label.setWordWrap(True)
            text_col.addWidget(self.subtitle_label)

        layout.addLayout(text_col, 1)

        self._control_layout = QHBoxLayout()
        self._control_layout.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        layout.addLayout(self._control_layout)

    def add_control(self, widget: QWidget):
        self._control_layout.addWidget(widget)


# ─── Material Slider Row with Live Value Badge ────────────────────────
class SliderRow(QWidget):
    value_changed = pyqtSignal(int)

    def __init__(
        self,
        title: str,
        subtitle: str,
        min_val: int,
        max_val: int,
        value: int,
        suffix: str = "",
        parent=None,
    ):
        super().__init__(parent)
        self.suffix = suffix
        self.setMinimumHeight(82)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 12, 20, 12)
        layout.setSpacing(8)

        header = QHBoxLayout()
        title_label = QLabel(title)
        title_label.setStyleSheet(
            f"color: {MD3.ON_SURFACE}; font-size: 14px; font-weight: 500; background: transparent; border: none;"
        )
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
            sub.setStyleSheet(
                f"color: {MD3.ON_SURFACE_VARIANT}; font-size: 12px; background: transparent; border: none;"
            )
            layout.addWidget(sub)

        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.slider.wheelEvent = lambda event: event.ignore()
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
        sep.setStyleSheet(
            f"background-color: {MD3.OUTLINE_VARIANT}; margin-left: 20px; margin-right: 20px;"
        )
        self._layout.addWidget(sep)


# ─── Live Interactive Preview Canvas ──────────────────────────────────
class LivePreview(QWidget):
    """
    Renders sharp floating lyrics with actual 7clouds font,
    55+ animations, smooth soft color highlight, and focal underlines.
    """

    PREVIEW_LINES: ClassVar[list[str]] = [
        "Magar phir aarzoon ka bikharna bhi zaroori tha",
        "Cause you knew that I'd be at one",
        "Saari jannatein mere paas ho",
        "I fell in love with a girl I met in hell",
        "Patta chanaron ka jaise havaon mein",
        "Dancing under neon city lights tonight",
        "Tere vaaste falak se main chaand laaunga",
        "We found love in a hopeless place",
    ]

    def __init__(self, settings: dict, parent=None):
        super().__init__(parent)
        self.settings = settings.copy()
        self.setFixedHeight(180)

        self.engine = AnimationEngine()
        self.engine.anim_style = str(self.settings.get("animation_style", "all"))
        self._line_idx = 0
        self._current_anim_choice = ""
        self._color_idx = 0
        self._word_span_cache: dict[str, list[tuple[str, int, int]]] = {}

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
        self.engine.trigger_line(
            text, 3.8, anim_name, anim_style=self.engine.anim_style
        )
        self.update()

    def next_line(self):
        self._line_idx = (self._line_idx + 1) % len(self.PREVIEW_LINES)
        text = self.PREVIEW_LINES[self._line_idx]
        # Simulate new song change by picking next distinct ultra-bright color
        self._color_idx = (self._color_idx + 1) % len(BRIGHT_HIGHLIGHT_HEX_LIST)
        self.engine.trigger_line(
            text, 3.8, self._current_anim_choice, anim_style=self.engine.anim_style
        )

    def update_settings(self, settings: dict):
        self.settings.update(settings)
        self.engine.anim_style = str(self.settings.get("animation_style", "all"))
        self._word_span_cache.clear()
        self.update()

    def _get_word_spans(self, text: str) -> list[tuple[str, int, int]]:
        cached = self._word_span_cache.get(text)
        if cached is not None:
            return cached

        words = []
        idx = 0
        length = len(text)
        while idx < length:
            if text[idx].isspace():
                idx += 1
                continue
            w_start = idx
            while idx < length and not text[idx].isspace():
                idx += 1
            w_end = idx
            words.append((text[w_start:w_end], w_start, w_end))

        if len(self._word_span_cache) > 50:
            self._word_span_cache.clear()

        self._word_span_cache[text] = words
        return words

    def showEvent(self, event):
        super().showEvent(event)
        if hasattr(self, "_render_timer") and not self._render_timer.isActive():
            self._render_timer.start(16)
        if hasattr(self, "_cycle_timer") and not self._cycle_timer.isActive():
            self._cycle_timer.start(3800)

    def hideEvent(self, event):
        super().hideEvent(event)
        if hasattr(self, "_render_timer") and self._render_timer.isActive():
            self._render_timer.stop()
        if hasattr(self, "_cycle_timer") and self._cycle_timer.isActive():
            self._cycle_timer.stop()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        w, h = self.width(), self.height()

        # Canvas gradient background
        bg_grad = QLinearGradient(0, 0, 0, h)
        bg_grad.setColorAt(0.0, QColor("#08080A"))
        bg_grad.setColorAt(0.5, QColor("#0D0D10"))
        bg_grad.setColorAt(1.0, QColor("#08080A"))
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
        elif "Bahnschrift" in font_choice:
            fam = "Bahnschrift"
            weight = QFont.Weight.Bold
        elif "Impact" in font_choice:
            fam = "Impact"
            weight = QFont.Weight.Bold
        elif "Franklin" in font_choice:
            fam = "Franklin Gothic Medium"
            weight = QFont.Weight.Bold
        elif "Trebuchet" in font_choice:
            fam = "Trebuchet MS"
            weight = QFont.Weight.Bold
        elif "Georgia" in font_choice:
            fam = "Georgia"
            weight = QFont.Weight.Bold
        elif "Segoe" in font_choice:
            fam = "Segoe UI"
            weight = QFont.Weight.Bold
        else:
            fam = "Montserrat"
            weight = QFont.Weight.Black

        size = min(int(self.settings.get("font_size", 42)), 30)
        font = QFont(fam, size, weight)
        font.setStyleStrategy(
            QFont.StyleStrategy.PreferAntialias
            | QFont.StyleStrategy.NoSubpixelAntialias
        )
        metrics = QFontMetrics(font)

        while metrics.horizontalAdvance(curr_text) > (w - 60) and size > 15:
            size -= 1
            font.setPointSize(size)
            metrics = QFontMetrics(font)

        p.setFont(font)

        hl_enabled = self.settings.get("highlight_enabled", True)
        # Highlight color (supports darker and vivid shades)
        if self.settings.get("highlight_mode", "per_song") == "per_song":
            hl_hex = ensure_bright_hex(BRIGHT_HIGHLIGHT_HEX_LIST[self._color_idx])
            hl_color = QColor(hl_hex)
        else:
            hl_hex = ensure_bright_hex(
                self.settings.get("highlight_color", BRIGHT_HIGHLIGHT_HEX_LIST[0])
            )
            hl_color = QColor(hl_hex)
        hl_idx = data.get("highlight_word_idx", -1)

        # ── 1. Outgoing Line Cross-Transition (Anti-Overlap: lifts cleanly away) ──
        if prev_data and prev_data["alpha"] > 0.02:
            p_text = prev_data["text"]
            p_alpha = int(prev_data["alpha"] * 255)
            p_w = metrics.horizontalAdvance(p_text)
            p_baseline = (metrics.ascent() - metrics.descent()) / 2.0

            # Outgoing motion blur streak (subtle upward optical softening)
            if (
                self.settings.get("motion_blur_enabled", True)
                and prev_data.get("blur_dy", 0.0) != 0.0
            ):
                p_blur_dy = max(-4.0, min(0.0, prev_data["blur_dy"]))
                blur_int = float(self.settings.get("motion_blur_intensity", 1.4))
                for step in range(1, 3):
                    frac = step / 2.0
                    out_blur_a = int(p_alpha * 0.18 * (1.0 - frac * 0.5))
                    if out_blur_a > 2:
                        p.save()
                        p.translate(
                            cx, cy + prev_data["offset_y"] - p_blur_dy * frac * blur_int
                        )
                        p.setPen(QColor(255, 255, 255, out_blur_a))
                        p.drawText(QPointF(-p_w / 2.0, p_baseline), p_text)
                        p.restore()

            p.save()
            # Smooth upward lift starting strictly at 0.0 (zero jump!)
            p.translate(cx, cy + prev_data["offset_y"])
            if prev_data["scale"] != 1.0:
                p.scale(prev_data["scale"], prev_data["scale"])
            p.setPen(QColor(255, 255, 255, p_alpha))
            p.drawText(QPointF(-p_w / 2.0, p_baseline), p_text)
            p.restore()

        # ── 2. Incoming Line ──
        if curr_text and data["curr_alpha"] > 0.02:
            in_alpha = int(data["curr_alpha"] * 255)
            total_w = metrics.horizontalAdvance(curr_text)
            start_x = -total_w / 2.0
            baseline_y = (metrics.ascent() - metrics.descent()) / 2.0

            # Incoming directional motion blur (subtle optical softness on physical motion only)
            anim_type = data.get("anim_type", "")
            blur_enabled = self.settings.get("motion_blur_enabled", True)
            blur_dx = data.get("blur_dx", 0.0)
            blur_dy = data.get("blur_dy", 0.0)
            blur_dist = data.get("blur_dist", 0.0)
            blur_intensity = float(self.settings.get("motion_blur_intensity", 1.4))

            if blur_enabled and blur_dist > 0.4 and anim_type not in FADE_ANIMS:
                clamped_dx = max(-3.5, min(3.5, blur_dx))
                clamped_dy = max(-3.5, min(3.5, blur_dy))
                for step in range(1, 3):
                    frac = step / 2.0
                    trail_x = -clamped_dx * frac * blur_intensity
                    trail_y = -clamped_dy * frac * blur_intensity
                    step_a = int(
                        in_alpha * data.get("blur_alpha", 0.25) * (1.0 - frac * 0.5)
                    )
                    if step_a > 2:
                        p.save()
                        p.translate(
                            cx + data.get("curr_offset_x", 0.0) + trail_x,
                            cy + data["curr_offset_y"] + trail_y,
                        )
                        if data.get("rotation", 0.0) != 0.0:
                            p.rotate(data["rotation"])
                        if data["curr_scale"] != 1.0:
                            p.scale(data["curr_scale"], data["curr_scale"])
                        p.setPen(QColor(255, 255, 255, step_a))
                        p.drawText(QPointF(start_x, baseline_y), curr_text)
                        p.restore()

            p.save()
            p.translate(cx + data.get("curr_offset_x", 0.0), cy + data["curr_offset_y"])

            if data.get("rotation", 0.0) != 0.0:
                p.rotate(data["rotation"])
            if data["curr_scale"] != 1.0:
                p.scale(data["curr_scale"], data["curr_scale"])

            anim_type = data.get("anim_type", "")
            words = self._get_word_spans(curr_text)
            hl_start = -1
            hl_end = -1
            if hl_enabled and 0 <= hl_idx < len(words):
                hl_start = words[hl_idx][1]
                hl_end = words[hl_idx][2]

            if (
                anim_type in PER_CHAR_ANIMS
                and data.get("char_alphas")
                and (
                    any(oy != 0.0 for oy in data.get("char_offsets_y", []))
                    or any(ox != 0.0 for ox in data.get("char_offsets_x", []))
                    or any(rot != 0.0 for rot in data.get("char_rotations", []))
                )
            ):
                offsets_x = data.get("char_offsets_x", [])
                offsets_y = data.get("char_offsets_y", [])
                char_alphas = data.get("char_alphas", [])
                char_scales = data.get("char_scales", [])
                char_rotations = data.get("char_rotations", [])

                char_x_starts = [start_x]
                for ch in curr_text[:-1]:
                    char_x_starts.append(char_x_starts[-1] + metrics.horizontalAdvance(ch))

                for i, ch in enumerate(curr_text):
                    ch_w = metrics.horizontalAdvance(ch)
                    ch_x = char_x_starts[i]
                    ca = char_alphas[i] if i < len(char_alphas) else 1.0
                    ox = offsets_x[i] if i < len(offsets_x) else 0.0
                    oy = offsets_y[i] if i < len(offsets_y) else 0.0
                    cs = char_scales[i] if i < len(char_scales) else 1.0
                    rot = char_rotations[i] if (char_rotations and i < len(char_rotations)) else 0.0
                    final_a = max(0, min(255, int(in_alpha * ca)))

                    if hl_start <= i < hl_end:
                        p.setPen(
                            QColor(hl_color.red(), hl_color.green(), hl_color.blue(), final_a)
                        )
                    else:
                        p.setPen(QColor(255, 255, 255, final_a))

                    if cs != 1.0 or rot != 0.0:
                        p.save()
                        p.translate(ch_x + ch_w / 2.0 + ox, baseline_y + oy)
                        if rot != 0.0:
                            p.rotate(rot)
                        if cs != 1.0:
                            p.scale(cs, cs)
                        p.drawText(QPointF(-ch_w / 2.0, 0), ch)
                        p.restore()
                    else:
                        p.drawText(QPointF(ch_x + ox, baseline_y + oy), ch)
            elif not hl_enabled or hl_idx < 0 or hl_idx >= len(words):
                p.setPen(QColor(255, 255, 255, in_alpha))
                p.drawText(QPointF(start_x, baseline_y), curr_text)
            else:
                w_str, w_start, w_end = words[hl_idx]
                prefix = curr_text[:w_start]
                if prefix:
                    p.setPen(QColor(255, 255, 255, in_alpha))
                    p.drawText(QPointF(start_x, baseline_y), prefix)

                # Draw active word exclusively in highlight color (zero white border bleed)
                w_x = start_x + metrics.horizontalAdvance(prefix)
                p.setPen(
                    QColor(hl_color.red(), hl_color.green(), hl_color.blue(), in_alpha)
                )
                p.drawText(QPointF(w_x, baseline_y), w_str)

                suffix = curr_text[w_end:]
                if suffix:
                    suffix_x = start_x + metrics.horizontalAdvance(curr_text[:w_end])
                    p.setPen(QColor(255, 255, 255, in_alpha))
                    p.drawText(QPointF(suffix_x, baseline_y), suffix)

            # Focal underline
            if (
                self.settings.get("hand_drawn_underline_enabled", True)
                and data.get("underline_active")
                and data.get("underline_progress", 0.0) > 0.02
                and data.get("focal_word_idx", -1) >= 0
            ):
                focal_idx = data["focal_word_idx"]
                if 0 <= focal_idx < len(words):
                    w_str, w_start, _ = words[focal_idx]
                    w_start_x = start_x + metrics.horizontalAdvance(curr_text[:w_start])
                    target_w = metrics.horizontalAdvance(w_str)
                    draw_w = target_w * data["underline_progress"]

                    if draw_w > 6:
                        y_line = baseline_y + 8.0
                        p.setPen(
                            QPen(
                                QColor(255, 255, 255, int(data["curr_alpha"] * 75)),
                                1.2,
                                Qt.PenStyle.SolidLine,
                                Qt.PenCapStyle.RoundCap,
                            )
                        )
                        path1 = QPainterPath()
                        path1.moveTo(w_start_x - 2, y_line)
                        path1.quadTo(
                            w_start_x + draw_w * 0.5,
                            y_line + 3,
                            w_start_x + draw_w + 2,
                            y_line + 1,
                        )
                        p.drawPath(path1)

                        p.setPen(
                            QPen(
                                QColor(255, 255, 255, int(data["curr_alpha"] * 225)),
                                2.6,
                                Qt.PenStyle.SolidLine,
                                Qt.PenCapStyle.RoundCap,
                            )
                        )
                        path2 = QPainterPath()
                        path2.moveTo(w_start_x, y_line)
                        path2.quadTo(
                            w_start_x + draw_w * 0.5,
                            y_line + 3.5,
                            w_start_x + draw_w,
                            y_line + 0.5,
                        )
                        p.drawPath(path2)

            p.restore()

        # Header badge
        p.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
        p.setPen(QColor(MD3.PRIMARY))
        p.drawText(
            QRectF(0, 10, w - 16, 20), Qt.AlignmentFlag.AlignRight, "● LIVE PREVIEW"
        )

        p.end()


# ─── Aesthetic Ultra-Bright Color Swatch Button ─────────────────────────
class ColorSwatch(QPushButton):
    color_changed = pyqtSignal(str)

    PALETTE = BRIGHT_HIGHLIGHT_HEX_LIST

    def __init__(self, current_hex: str = "#26FF7C", parent=None):
        super().__init__(parent)
        self._color = ensure_bright_hex(current_hex)
        self._idx = 0
        for i, c in enumerate(self.PALETTE):
            if c.upper() == self._color.upper():
                self._idx = i
                break
        self.setFixedSize(36, 36)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clicked.connect(self._cycle_color)
        self._apply_style()

    def _apply_style(self):
        color_name = "Highlight Color"
        for item in BRIGHT_HIGHLIGHT_PALETTE:
            if item["hex"].upper() == self._color.upper():
                color_name = item["name"]
                break
        self.setToolTip(
            f"{color_name} ({self._color})\nLeft-click: cycle colors | Right-click: custom color picker"
        )
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

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            self._pick_custom_color()
            event.accept()
        else:
            super().mousePressEvent(event)

    def _pick_custom_color(self):
        initial = QColor(self._color)
        chosen = QColorDialog.getColor(
            initial,
            self,
            "Select Custom Highlight Color",
            QColorDialog.ColorDialogOption.ShowAlphaChannel,
        )
        if chosen.isValid():
            hex_val = ensure_bright_hex(chosen.name())
            self.setColor(hex_val)
            self.color_changed.emit(self._color)

    def _cycle_color(self):
        self._idx = (self._idx + 1) % len(self.PALETTE)
        self._color = ensure_bright_hex(self.PALETTE[self._idx])
        self._apply_style()
        self.color_changed.emit(self._color)

    def color(self) -> str:
        return self._color

    def setColor(self, hex_color: str):
        bright_hex = ensure_bright_hex(hex_color)
        self._color = bright_hex
        for i, c in enumerate(self.PALETTE):
            if c.upper() == bright_hex.upper():
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
        self.setWindowTitle("LyricVibe — Settings")
        self.setFixedSize(580, 790)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowStaysOnTopHint)

        self._load_icon()
        self._load_fonts()
        self._apply_theme()
        self._build_ui()

    def _load_fonts(self):
        for f in (
            "EdoSZ.ttf",
            "Montserrat-Black.ttf",
            "Montserrat.ttf",
            "Poppins-Bold.ttf",
        ):
            fp = get_asset_path(os.path.join("fonts", f))
            if os.path.exists(fp):
                QFontDatabase.addApplicationFont(fp)

    def _load_icon(self):
        for icon_name in ("icon.ico", "icon.png"):
            fp = get_asset_path(icon_name)
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
                padding: 12px 20px;
                border: none;
                border-bottom: 2px solid transparent;
                min-width: 72px;
            }}
            QTabBar::tab:selected {{
                color: #FFFFFF;
                border-bottom: 2px solid #FFFFFF;
            }}
            QTabBar::tab:hover:!selected {{
                color: #FFFFFF;
                background: {MD3.SURFACE_CONTAINER_LOW};
                border-radius: 6px 6px 0 0;
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
                background: #E4E4E7;
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

        # Header bar (High-Contrast Black & White Branding)
        header = QWidget()
        header.setFixedHeight(74)
        header.setStyleSheet(f"""
            QWidget {{
                background: {MD3.SURFACE};
                border-bottom: 1px solid {MD3.OUTLINE_VARIANT};
            }}
        """)
        h_lay = QHBoxLayout(header)
        h_lay.setContentsMargins(24, 0, 24, 0)
        h_lay.setSpacing(14)

        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.png")
        if os.path.exists(icon_path):
            icon_box = QFrame()
            icon_box.setFixedSize(40, 40)
            icon_box.setStyleSheet(f"""
                QFrame {{
                    background: {MD3.SURFACE_CONTAINER};
                    border: 1px solid {MD3.OUTLINE_VARIANT};
                    border-radius: 10px;
                }}
            """)
            box_lay = QVBoxLayout(icon_box)
            box_lay.setContentsMargins(0, 0, 0, 0)
            box_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
            icon_label = QLabel()
            pix = QPixmap(icon_path).scaled(
                26,
                26,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            icon_label.setPixmap(pix)
            box_lay.addWidget(icon_label)
            h_lay.addWidget(icon_box)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        title = QLabel("LyricVibe")
        title.setStyleSheet("""
            color: #FFFFFF;
            font-size: 19px;
            font-weight: 700;
            letter-spacing: 0.4px;
            background: transparent;
            border: none;
        """)
        title_col.addWidget(title)
        subtitle = QLabel("165Hz Desktop Lyrics Customizer")
        subtitle.setStyleSheet(f"""
            color: {MD3.ON_SURFACE_VARIANT};
            font-size: 11px;
            font-weight: 500;
            letter-spacing: 0.2px;
            background: transparent;
            border: none;
        """)
        title_col.addWidget(subtitle)
        h_lay.addLayout(title_col)

        h_lay.addStretch()

        ver_pill = QLabel("v1.1.0")
        ver_pill.setStyleSheet(f"""
            color: #FFFFFF;
            background-color: {MD3.SURFACE_CONTAINER_HIGH};
            font-size: 11px;
            font-weight: 600;
            letter-spacing: 0.5px;
            padding: 5px 12px;
            border-radius: 12px;
            border: 1px solid {MD3.OUTLINE};
        """)
        h_lay.addWidget(ver_pill)

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
                background: #241417;
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
                background: #E4E4E7;
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
        self.combo_test_anim.wheelEvent = lambda event: event.ignore()
        self.combo_test_anim.addItem("Random 72+ Animations", "")
        for name, _ in ANIMATION_CATALOG:
            clean_name = name.replace("_", " ").title()
            self.combo_test_anim.addItem(f"Test: {clean_name}", name)
        self.combo_test_anim.currentIndexChanged.connect(
            lambda: self.preview_widget.trigger_animation(
                self.combo_test_anim.currentData()
            )
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
                background: #2E2E34;
            }}
        """)
        btn_test.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_test.clicked.connect(
            lambda: self.preview_widget.trigger_animation(
                self.combo_test_anim.currentData()
            )
        )
        p_c_lay.addWidget(btn_test)

        btn_next = QPushButton("Next Line →")
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

        row_font = SettingRow(
            "Font Style", "Choose between 7clouds signature brush and clean bold"
        )
        self.combo_font = QComboBox()
        self.combo_font.wheelEvent = lambda event: event.ignore()
        self.combo_font.addItems(
            [
                "7clouds Signature (Edo SZ)",
                "7clouds Modern (Montserrat Black)",
                "Poppins Bold (Modern Geometric)",
                "Bahnschrift Bold (DIN Geometric)",
                "Impact Classic (Bold Poster)",
                "Franklin Gothic (Vintage Headline)",
                "Trebuchet Bold (Dynamic Modern)",
                "Georgia Bold (Editorial Serif)",
                "System Clean (Segoe UI)",
            ]
        )
        cur_font = self.settings.get("font_family", "7clouds Signature (Edo SZ)")
        self.combo_font.setCurrentIndex(self._find_font_combo_index(cur_font))
        self.combo_font.currentIndexChanged.connect(self._on_font_changed)
        row_font.add_control(self.combo_font)
        typo_card.add_row(row_font)
        typo_card.add_separator()

        self.slider_size = SliderRow(
            "Font Size",
            "Automatically scales down on long lines to prevent clipping",
            28,
            64,
            int(self.settings.get("font_size", 42)),
            "px",
        )
        self.slider_size.value_changed.connect(self._on_slider_size_changed)
        typo_card.add_row(self.slider_size)
        typo_card.add_separator()

        self.slider_y = SliderRow(
            "Top Screen Margin",
            "Distance from the top edge of your monitor",
            10,
            350,
            int(self.settings.get("overlay_y", 55)),
            "px",
        )
        self.slider_y.value_changed.connect(self._on_slider_y_changed)
        typo_card.add_row(self.slider_y)

        layout.addWidget(typo_card)

        # 3. Performance Card
        perf_card = SectionCard("Performance & Refresh Rate")

        row_fps = SettingRow(
            "Target Refresh Rate",
            "Hardware-accelerated timer for high-refresh monitors",
        )
        self.combo_fps = QComboBox()
        self.combo_fps.wheelEvent = lambda event: event.ignore()
        self.combo_fps.addItems(
            ["60 Hz", "120 Hz", "144 Hz", "165 Hz (Recommended)", "240 Hz"]
        )
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

        # Live Effects Studio Preview
        preview_card = SectionCard("Live Effects Studio")
        self.effects_preview = LivePreview(self.settings)
        preview_card.add_row(self.effects_preview)

        # Interactive Animation Explorer
        p_ctrls = QWidget()
        p_c_lay = QHBoxLayout(p_ctrls)
        p_c_lay.setContentsMargins(18, 6, 18, 12)
        p_c_lay.setSpacing(10)

        self.combo_cat_filter = QComboBox()
        self.combo_cat_filter.wheelEvent = lambda event: event.ignore()
        self.combo_cat_filter.addItem("Category: All (72+)", "all")
        self.combo_cat_filter.addItem("Category: Smooth (14)", "smooth")
        self.combo_cat_filter.addItem("Category: Kinetic (18)", "kinetic")
        self.combo_cat_filter.addItem("Category: Vocal (12)", "vocal")
        self.combo_cat_filter.addItem("Category: Cinematic (16)", "cinematic")
        self.combo_cat_filter.addItem("Category: Per-Character (12)", "per_char")
        self.combo_cat_filter.addItem("Category: Rare & Experimental (6)", "rare")

        self.combo_fx_anim = QComboBox()
        self.combo_fx_anim.wheelEvent = lambda event: event.ignore()

        self._populate_anim_combo("all")

        def _on_cat_filter_changed(idx):
            cat = self.combo_cat_filter.currentData()
            self._populate_anim_combo(cat)
            self.effects_preview.trigger_animation(self.combo_fx_anim.currentData())

        self.combo_cat_filter.currentIndexChanged.connect(_on_cat_filter_changed)
        self.combo_fx_anim.currentIndexChanged.connect(
            lambda: self.effects_preview.trigger_animation(
                self.combo_fx_anim.currentData()
            )
        )

        p_c_lay.addWidget(self.combo_cat_filter)
        p_c_lay.addWidget(self.combo_fx_anim, 1)

        btn_replay = QPushButton("▶ Replay")
        btn_replay.setStyleSheet(f"""
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
                background: #2E2E34;
            }}
        """)
        btn_replay.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_replay.clicked.connect(
            lambda: self.effects_preview.trigger_animation(
                self.combo_fx_anim.currentData()
            )
        )
        p_c_lay.addWidget(btn_replay)

        preview_card.add_row(p_ctrls)
        layout.addWidget(preview_card)

        fx_card = SectionCard("Visual Effects & Motion Blur Physics")

        # 1. Active Word Highlight Enabled
        row_hl = SettingRow(
            "Word Timing Highlight",
            "Illuminates the active spoken word with high-contrast bright color",
        )
        self.toggle_highlight = PillToggle(self.settings.get("highlight_enabled", True))
        self.toggle_highlight.toggled.connect(
            lambda v: self._update_and_sync("highlight_enabled", v)
        )
        row_hl.add_control(self.toggle_highlight)
        fx_card.add_row(row_hl)
        fx_card.add_separator()

        # 2. Highlight Color Mode & Swatch (Supports darker & vivid palettes)
        row_color = SettingRow(
            "Highlight Color Palette",
            "Rotates a distinct color each song, or pin your favorite shade",
        )
        self.combo_hl_mode = QComboBox()
        self.combo_hl_mode.wheelEvent = lambda event: event.ignore()
        self.combo_hl_mode.addItem("Auto: Different Color Each Song", "per_song")
        for item in BRIGHT_HIGHLIGHT_PALETTE:
            self.combo_hl_mode.addItem(f"● {item['name']}", item["hex"])
        self.combo_hl_mode.addItem("Custom Color...", "custom")

        cur_mode = self.settings.get("highlight_mode", "per_song")
        cur_color = self.settings.get("highlight_color", BRIGHT_HIGHLIGHT_HEX_LIST[0])
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
            elif mode_data == "custom":
                self.color_swatch._pick_custom_color()
            else:
                self._update_and_sync("highlight_mode", "fixed")
                self._update_and_sync("highlight_color", mode_data)
                self.color_swatch.setColor(mode_data)

        def _on_swatch_changed(hex_val):
            self._update_and_sync("highlight_mode", "fixed")
            self._update_and_sync("highlight_color", hex_val)
            matched = False
            for i in range(1, self.combo_hl_mode.count()):
                if self.combo_hl_mode.itemData(i).upper() == hex_val.upper():
                    self.combo_hl_mode.blockSignals(True)
                    self.combo_hl_mode.setCurrentIndex(i)
                    self.combo_hl_mode.blockSignals(False)
                    matched = True
                    break
            if not matched:
                custom_idx = self.combo_hl_mode.findData("custom")
                if custom_idx >= 0:
                    self.combo_hl_mode.blockSignals(True)
                    self.combo_hl_mode.setCurrentIndex(custom_idx)
                    self.combo_hl_mode.blockSignals(False)

        self.combo_hl_mode.currentIndexChanged.connect(_on_color_combo_changed)
        self.color_swatch.color_changed.connect(_on_swatch_changed)

        row_color.add_control(self.combo_hl_mode)
        row_color.add_control(self.color_swatch)
        fx_card.add_row(row_color)
        fx_card.add_separator()

        # 3. Cinematic Motion Blur Toggle & Slider
        row_blur = SettingRow(
            "Cinematic Motion Blur",
            "Hardware-accelerated sub-frame shutter streaks on fast entrances and exits",
        )
        self.toggle_motion_blur = PillToggle(
            self.settings.get("motion_blur_enabled", True)
        )
        self.toggle_motion_blur.toggled.connect(
            lambda v: self._update_and_sync("motion_blur_enabled", v)
        )
        row_blur.add_control(self.toggle_motion_blur)
        fx_card.add_row(row_blur)
        fx_card.add_separator()

        cur_blur = float(self.settings.get("motion_blur_intensity", 1.4))
        self.slider_blur = SliderRow(
            "Motion Blur Streak Length",
            "Controls the intensity of camera shutter motion trails",
            5,
            25,
            int(cur_blur * 10),
            "×0.1",
        )
        self.slider_blur.value_changed.connect(self._on_slider_blur_changed)
        fx_card.add_row(self.slider_blur)
        fx_card.add_separator()

        # Hand-Drawn Underline
        row_line = SettingRow(
            "Hand-Drawn Focal Underlines",
            "Sketched marker stroke under 1 or 2 key focal words (not the whole sentence)",
        )
        self.toggle_underline = PillToggle(
            self.settings.get("hand_drawn_underline_enabled", True)
        )
        self.toggle_underline.toggled.connect(
            lambda v: self._update_and_sync("hand_drawn_underline_enabled", v)
        )
        row_line.add_control(self.toggle_underline)
        fx_card.add_row(row_line)
        fx_card.add_separator()

        # Auto-Hide When Idle
        row_hide = SettingRow(
            "Auto-Hide When Idle",
            "Instantly vanish when music is paused or Spotify closes",
        )
        self.toggle_hide = PillToggle(self.settings.get("auto_hide_idle", True))
        self.toggle_hide.toggled.connect(
            lambda v: self._update_and_sync("auto_hide_idle", v)
        )
        row_hide.add_control(self.toggle_hide)
        fx_card.add_row(row_hide)
        fx_card.add_separator()

        # Auto-Start with Windows & Spotify
        row_autostart = SettingRow(
            "Start with Windows (Auto-Start)",
            "Launch silently in background so lyrics show whenever Spotify starts",
        )
        self.toggle_autostart = PillToggle(is_autostart_enabled())
        self.toggle_autostart.toggled.connect(self._on_autostart_toggled)
        row_autostart.add_control(self.toggle_autostart)
        fx_card.add_row(row_autostart)
        fx_card.add_separator()

        # Animation Motion Style Preference
        row_anim_style = SettingRow(
            "Animation Motion Style",
            "Choose your preferred easing physics and visual movement personality",
        )
        self.combo_anim_style = QComboBox()
        self.combo_anim_style.wheelEvent = lambda event: event.ignore()
        self.combo_anim_style.addItem("Dynamic Mix (All 72+ Animations)", "all")
        self.combo_anim_style.addItem("Silky Smooth Fades & Dissolves", "smooth")
        self.combo_anim_style.addItem("Kinetic & Snappy Motion", "kinetic")
        self.combo_anim_style.addItem("Cinematic & Expressive 3D", "cinematic")
        self.combo_anim_style.addItem("Vocal & Lyric Flow", "vocal")
        self.combo_anim_style.addItem("Rare & Experimental (Burst, Fall, Vortex)", "rare")

        cur_style = self.settings.get("animation_style", "all")
        for i in range(self.combo_anim_style.count()):
            if self.combo_anim_style.itemData(i) == cur_style:
                self.combo_anim_style.setCurrentIndex(i)
                break

        def _on_anim_style_changed(idx):
            val = self.combo_anim_style.itemData(idx)
            self._update_and_sync("animation_style", val)

        self.combo_anim_style.currentIndexChanged.connect(_on_anim_style_changed)
        row_anim_style.add_control(self.combo_anim_style)
        fx_card.add_row(row_anim_style)

        layout.addWidget(fx_card)

        # 72+ Animations Showcase Card
        anim_card = SectionCard("72+ Dynamic Animations & Smooth Physics")
        anim_info = QLabel(
            "<b>Smooth Fade & Continuous 165Hz Physics:</b><br>"
            "Whisper dissolve, silky crossfades, aurora shimmer, nebula bloom, horizon dawn, "
            "whip pans, bass drop shake, hyper zoom, prism refract, 3D card flips, "
            "and gentle elastic springs interpolating continuously at 165Hz sub-millisecond precision.<br><br>"
            "<b>Aesthetic Smooth Soft Colors (Per-Song Rotation):</b><br>"
            "Every song is automatically assigned a distinct, vibrant, smooth soft color (Mint Emerald, "
            "Electric Cyan, Lavender Lilac, Coral Rose, Golden Canary, Sky Azure, Bubblegum Pink, etc.) "
            "with ultra-crisp word highlights.<br><br>"
            "<b>Anti-Overlap Architecture:</b><br>"
            "Outgoing lyrics lift cleanly away, guaranteeing zero clashing or text collision with incoming lines."
        )
        anim_info.setWordWrap(True)
        anim_info.setStyleSheet(
            f"color: {MD3.ON_SURFACE_VARIANT}; font-size: 13px; line-height: 1.6; padding: 16px 20px; background: transparent; border: none;"
        )
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
            "Sync Calibration",
            "Shift lyrics earlier (−) or later (+) relative to the audio",
            -20,
            20,
            int(cur_offset * 10),
            "×0.1s",
        )
        self.slider_sync.value_changed.connect(self._on_slider_sync_changed)
        sync_card.add_row(self.slider_sync)

        quick_row = QWidget()
        q_lay = QHBoxLayout(quick_row)
        q_lay.setContentsMargins(20, 4, 20, 14)
        q_lay.setSpacing(8)

        for label, val in [
            ("−0.5s", -5),
            ("Exact 0.0s", 0),
            ("+0.2s (Vocal Lead)", 2),
            ("+0.5s", 5),
        ]:
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
            "While listening to music, you can fine-tune timing on the fly:\n\n"
            "• Press [  to shift lyrics 0.5s earlier\n"
            "• Press ]  to shift lyrics 0.5s later\n"
            "• Press Ctrl+Alt+L to lock overlay so clicks pass straight through"
        )
        tip_lbl.setWordWrap(True)
        tip_lbl.setStyleSheet(
            f"color: {MD3.ON_SURFACE_VARIANT}; font-size: 13px; line-height: 1.6; padding: 16px 20px; background: transparent; border: none;"
        )
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

        # Preset Studio Live Preview
        preview_card = SectionCard("Preset Studio Live Preview")
        self.preset_preview = LivePreview(self.settings)
        preview_card.add_row(self.preset_preview)

        banner = QLabel(
            "Click 'Preview' on any preset to test it live on the canvas, or 'Apply' to save."
        )
        banner.setStyleSheet(f"""
            color: {MD3.ON_SURFACE_VARIANT};
            font-size: 12px;
            font-style: italic;
            padding: 4px 20px 10px 20px;
            background: transparent;
        """)
        preview_card.add_row(banner)
        layout.addWidget(preview_card)

        card = SectionCard("Curated Aesthetic Presets (16 Styles)")

        presets = [
            (
                "7clouds Signature",
                "Iconic brush style (Edo SZ) with dynamic smooth soft highlights and anti-overlap physics",
                {
                    "font_family": "7clouds Signature (Edo SZ)",
                    "font_size": 42,
                    "hand_drawn_underline_enabled": True,
                    "highlight_enabled": True,
                    "highlight_block_enabled": False,
                    "highlight_mode": "per_song",
                    "highlight_color": "#1DB954",
                    "animation_style": "all",
                    "motion_blur_enabled": True,
                    "motion_blur_intensity": 1.4,
                    "target_fps": 165,
                    "sync_offset_sec": 0.20,
                },
            ),
            (
                "Cyberpunk Neon",
                "Modern sans-serif (Montserrat Black) with electric cyan, kinetic whip pans, and motion blur",
                {
                    "font_family": "7clouds Modern (Montserrat Black)",
                    "font_size": 42,
                    "hand_drawn_underline_enabled": True,
                    "highlight_enabled": True,
                    "highlight_block_enabled": False,
                    "highlight_mode": "fixed",
                    "highlight_color": "#00E5FF",
                    "animation_style": "kinetic",
                    "motion_blur_enabled": True,
                    "motion_blur_intensity": 1.8,
                    "target_fps": 165,
                    "sync_offset_sec": 0.20,
                },
            ),
            (
                "Midnight Emerald",
                "Signature brush typography paired with Spotify deep emerald tones and smooth dissolves",
                {
                    "font_family": "7clouds Signature (Edo SZ)",
                    "font_size": 42,
                    "hand_drawn_underline_enabled": True,
                    "highlight_enabled": True,
                    "highlight_block_enabled": False,
                    "highlight_mode": "fixed",
                    "highlight_color": "#0E8A42",
                    "animation_style": "smooth",
                    "motion_blur_enabled": False,
                    "target_fps": 165,
                    "sync_offset_sec": 0.20,
                },
            ),
            (
                "Aesthetic Dream",
                "Lush cinematic crossfades with soft lavender and rose highlights and subtle underlines",
                {
                    "font_family": "7clouds Signature (Edo SZ)",
                    "font_size": 40,
                    "hand_drawn_underline_enabled": True,
                    "highlight_enabled": True,
                    "highlight_block_enabled": False,
                    "highlight_mode": "fixed",
                    "highlight_color": "#C084FC",
                    "animation_style": "smooth",
                    "motion_blur_enabled": False,
                    "target_fps": 165,
                    "sync_offset_sec": 0.20,
                },
            ),
            (
                "Crimson Bass",
                "Geometric Poppins typography with crimson punch, bass drop shake, and high-impact momentum",
                {
                    "font_family": "Poppins Bold (Modern Geometric)",
                    "font_size": 42,
                    "hand_drawn_underline_enabled": True,
                    "highlight_enabled": True,
                    "highlight_block_enabled": False,
                    "highlight_mode": "fixed",
                    "highlight_color": "#D32F2F",
                    "animation_style": "kinetic",
                    "motion_blur_enabled": True,
                    "motion_blur_intensity": 2.0,
                    "target_fps": 165,
                    "sync_offset_sec": 0.20,
                },
            ),
            (
                "Golden Hour",
                "Luminous golden canary typography with aurora shimmers, gentle rises, and warm glowing ambiance",
                {
                    "font_family": "7clouds Signature (Edo SZ)",
                    "font_size": 42,
                    "hand_drawn_underline_enabled": True,
                    "highlight_enabled": True,
                    "highlight_block_enabled": False,
                    "highlight_mode": "fixed",
                    "highlight_color": "#FFD600",
                    "animation_style": "cinematic",
                    "motion_blur_enabled": True,
                    "motion_blur_intensity": 1.2,
                    "target_fps": 165,
                    "sync_offset_sec": 0.20,
                },
            ),
            (
                "Tokyo Drift",
                "Stylized Japanese street brush aesthetics with royal purple highlights and parabolic arc streaks",
                {
                    "font_family": "7clouds Signature (Edo SZ)",
                    "font_size": 44,
                    "hand_drawn_underline_enabled": True,
                    "highlight_enabled": True,
                    "highlight_block_enabled": False,
                    "highlight_mode": "fixed",
                    "highlight_color": "#A855F7",
                    "animation_style": "cinematic",
                    "motion_blur_enabled": True,
                    "motion_blur_intensity": 1.6,
                    "target_fps": 165,
                    "sync_offset_sec": 0.20,
                },
            ),
            (
                "Minimalist Pure",
                "Clean white distraction-free typography with soft whisper fades and zero highlights",
                {
                    "font_family": "7clouds Modern (Montserrat Black)",
                    "font_size": 38,
                    "hand_drawn_underline_enabled": False,
                    "highlight_enabled": False,
                    "highlight_block_enabled": False,
                    "highlight_mode": "fixed",
                    "highlight_color": "#FFFFFF",
                    "animation_style": "smooth",
                    "motion_blur_enabled": False,
                    "target_fps": 120,
                    "sync_offset_sec": 0.20,
                },
            ),
            (
                "Synthwave Sunset",
                "Industrial DIN geometry (Bahnschrift) with neon hot magenta highlights and kinetic pulse",
                {
                    "font_family": "Bahnschrift Bold (DIN Geometric)",
                    "font_size": 42,
                    "hand_drawn_underline_enabled": True,
                    "highlight_enabled": True,
                    "highlight_block_enabled": False,
                    "highlight_mode": "fixed",
                    "highlight_color": "#FF2A85",
                    "animation_style": "kinetic",
                    "motion_blur_enabled": True,
                    "motion_blur_intensity": 1.7,
                    "target_fps": 165,
                    "sync_offset_sec": 0.20,
                },
            ),
            (
                "Nordic Frost",
                "Crisp high-contrast sans (Montserrat Black) with glacial ice cyan highlights and crystal float",
                {
                    "font_family": "7clouds Modern (Montserrat Black)",
                    "font_size": 42,
                    "hand_drawn_underline_enabled": False,
                    "highlight_enabled": True,
                    "highlight_block_enabled": False,
                    "highlight_mode": "fixed",
                    "highlight_color": "#38BDF8",
                    "animation_style": "smooth",
                    "motion_blur_enabled": True,
                    "motion_blur_intensity": 1.2,
                    "target_fps": 165,
                    "sync_offset_sec": 0.20,
                },
            ),
            (
                "Obsidian Gold",
                "Heavyweight poster typography (Impact) paired with radiant champagne gold and slow cinematic entrance",
                {
                    "font_family": "Impact Classic (Bold Poster)",
                    "font_size": 44,
                    "hand_drawn_underline_enabled": True,
                    "highlight_enabled": True,
                    "highlight_block_enabled": False,
                    "highlight_mode": "fixed",
                    "highlight_color": "#FBBF24",
                    "animation_style": "cinematic",
                    "motion_blur_enabled": True,
                    "motion_blur_intensity": 1.4,
                    "target_fps": 165,
                    "sync_offset_sec": 0.20,
                },
            ),
            (
                "Hyperpop Glitch",
                "Vintage American headline typography (Franklin Gothic) with radioactive lime and high-speed energy",
                {
                    "font_family": "Franklin Gothic (Vintage Headline)",
                    "font_size": 42,
                    "hand_drawn_underline_enabled": True,
                    "highlight_enabled": True,
                    "highlight_block_enabled": False,
                    "highlight_mode": "fixed",
                    "highlight_color": "#A3E635",
                    "animation_style": "kinetic",
                    "motion_blur_enabled": True,
                    "motion_blur_intensity": 2.2,
                    "target_fps": 165,
                    "sync_offset_sec": 0.20,
                },
            ),
            (
                "Lo-Fi Cafe",
                "Warm humanist typography (Trebuchet) with toasted caramel amber highlights and gentle rises",
                {
                    "font_family": "Trebuchet Bold (Dynamic Modern)",
                    "font_size": 40,
                    "hand_drawn_underline_enabled": True,
                    "highlight_enabled": True,
                    "highlight_block_enabled": False,
                    "highlight_mode": "fixed",
                    "highlight_color": "#FB923C",
                    "animation_style": "smooth",
                    "motion_blur_enabled": False,
                    "target_fps": 144,
                    "sync_offset_sec": 0.20,
                },
            ),
            (
                "Deep Amethyst",
                "Modern round sans (Poppins Bold) with royal velvet violet highlights and nebula bloom",
                {
                    "font_family": "Poppins Bold (Modern Geometric)",
                    "font_size": 42,
                    "hand_drawn_underline_enabled": True,
                    "highlight_enabled": True,
                    "highlight_block_enabled": False,
                    "highlight_mode": "fixed",
                    "highlight_color": "#8B5CF6",
                    "animation_style": "cinematic",
                    "motion_blur_enabled": True,
                    "motion_blur_intensity": 1.5,
                    "target_fps": 165,
                    "sync_offset_sec": 0.20,
                },
            ),
            (
                "Sakura Blossom",
                "Classical editorial serif (Georgia) with gentle cherry blossom pink highlights and subtle drift",
                {
                    "font_family": "Georgia Bold (Editorial Serif)",
                    "font_size": 40,
                    "hand_drawn_underline_enabled": True,
                    "highlight_enabled": True,
                    "highlight_block_enabled": False,
                    "highlight_mode": "fixed",
                    "highlight_color": "#F472B6",
                    "animation_style": "smooth",
                    "motion_blur_enabled": False,
                    "target_fps": 144,
                    "sync_offset_sec": 0.20,
                },
            ),
            (
                "Electric Oceanic",
                "DIN precision typography (Bahnschrift) with deep seafoam turquoise highlights and wave physics",
                {
                    "font_family": "Bahnschrift Bold (DIN Geometric)",
                    "font_size": 42,
                    "hand_drawn_underline_enabled": True,
                    "highlight_enabled": True,
                    "highlight_block_enabled": False,
                    "highlight_mode": "fixed",
                    "highlight_color": "#2DD4BF",
                    "animation_style": "cinematic",
                    "motion_blur_enabled": True,
                    "motion_blur_intensity": 1.7,
                    "target_fps": 165,
                    "sync_offset_sec": 0.20,
                },
            ),
        ]

        for title, desc, preset_dict in presets:
            row = QWidget()
            r_lay = QHBoxLayout(row)
            r_lay.setContentsMargins(20, 12, 20, 12)
            r_lay.setSpacing(14)

            preset_hl = preset_dict.get("highlight_color", "#1DB954")
            color_dot = QLabel()
            color_dot.setFixedSize(14, 14)
            color_dot.setStyleSheet(f"""
                background-color: {preset_hl};
                border-radius: 7px;
                border: 1px solid rgba(255, 255, 255, 0.3);
            """)

            text_box = QVBoxLayout()
            text_box.setSpacing(2)

            t_row = QHBoxLayout()
            t_row.setSpacing(8)
            t_row.addWidget(color_dot)

            p_title = QLabel(title)
            p_title.setStyleSheet(
                f"color: {MD3.ON_SURFACE}; font-size: 14px; font-weight: 600; background: transparent; border: none;"
            )
            t_row.addWidget(p_title)
            t_row.addStretch()
            text_box.addLayout(t_row)

            p_desc = QLabel(desc)
            p_desc.setStyleSheet(
                f"color: {MD3.ON_SURFACE_VARIANT}; font-size: 12px; background: transparent; border: none;"
            )
            p_desc.setWordWrap(True)
            text_box.addWidget(p_desc)
            r_lay.addLayout(text_box, 1)

            btn_prev = QPushButton("Preview")
            btn_prev.setStyleSheet(f"""
                QPushButton {{
                    background: {MD3.SURFACE_CONTAINER_HIGH};
                    color: {MD3.ON_SURFACE};
                    font-weight: 500;
                    font-size: 12px;
                    border-radius: 14px;
                    padding: 6px 14px;
                    border: 1px solid {MD3.OUTLINE_VARIANT};
                }}
                QPushButton:hover {{
                    background: {MD3.SURFACE_CONTAINER_MAX};
                }}
            """)
            btn_prev.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_prev.clicked.connect(lambda _, d=preset_dict: self._preview_preset(d))
            r_lay.addWidget(btn_prev)

            btn_apply = QPushButton("Apply")
            btn_apply.setStyleSheet(f"""
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
                    background: #2E2E34;
                }}
            """)
            btn_apply.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_apply.clicked.connect(lambda _, d=preset_dict: self._apply_preset(d))
            r_lay.addWidget(btn_apply)

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
            pix = QPixmap(icon_path).scaled(
                64,
                64,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            icon_label.setPixmap(pix)
        ab_lay.addWidget(icon_label)

        info_col = QVBoxLayout()
        info_col.setSpacing(4)
        app_name = QLabel("LyricVibe")
        app_name.setStyleSheet(
            f"color: {MD3.ON_SURFACE}; font-size: 22px; font-weight: 600; background: transparent; border: none;"
        )
        info_col.addWidget(app_name)

        app_ver = QLabel("Cinematic 165Hz Desktop Overlay")
        app_ver.setStyleSheet(
            f"color: {MD3.PRIMARY}; font-size: 13px; font-weight: 500; background: transparent; border: none;"
        )
        info_col.addWidget(app_ver)

        app_desc = QLabel(
            "Hardware-accelerated desktop lyrics overlay with 55+ animations, "
            "smooth fade transitions, dynamic aesthetic smooth soft color highlights, "
            "anti-overlap typography, and universal Hinglish transliteration."
        )
        app_desc.setWordWrap(True)
        app_desc.setStyleSheet(
            f"color: {MD3.ON_SURFACE_VARIANT}; font-size: 12px; line-height: 1.5; background: transparent; border: none;"
        )
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
            lbl_k.setStyleSheet(
                f"color: {MD3.ON_SURFACE}; font-size: 13px; background: transparent; border: none;"
            )
            rl.addWidget(lbl_k)
            rl.addStretch()

            lbl_v = QLabel(val)
            lbl_v.setStyleSheet(
                f"color: {MD3.PRIMARY}; font-size: 12px; font-weight: 500; background: transparent; border: none;"
            )
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
            ("Ctrl + Alt + S", "Settings", "Open customization window"),
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
            t_act.setStyleSheet(
                f"color: {MD3.ON_SURFACE}; font-size: 13px; font-weight: 500; background: transparent; border: none;"
            )
            text_col.addWidget(t_act)
            t_desc = QLabel(desc)
            t_desc.setStyleSheet(
                f"color: {MD3.ON_SURFACE_VARIANT}; font-size: 11px; background: transparent; border: none;"
            )
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
            if hasattr(self, "preview_widget"):
                self.preview_widget.update_settings(self.settings)
            if hasattr(self, "preset_preview"):
                self.preset_preview.update_settings(self.settings)
            if hasattr(self, "effects_preview"):
                self.effects_preview.update_settings(self.settings)
            self.settings_changed.emit(self.settings)
        except (KeyError, ValueError, TypeError, AttributeError, OSError) as e:
            logger.debug("[settings] _update_and_sync error: %s", e)

    def _on_font_changed(self, idx):
        choice = self.combo_font.currentText()
        self._update_and_sync("font_family", choice)
        if hasattr(self, "preview_widget"):
            self.preview_widget.trigger_animation()
        if hasattr(self, "preset_preview"):
            self.preset_preview.trigger_animation()
        if hasattr(self, "effects_preview"):
            self.effects_preview.trigger_animation()

    def _on_slider_size_changed(self, val: int):
        self._update_and_sync("font_size", val)

    def _on_slider_y_changed(self, val: int):
        self._update_and_sync("overlay_y", val)

    def _on_slider_sync_changed(self, val: int):
        offset = round(val / 10.0, 2)
        self._update_and_sync("sync_offset_sec", offset)

    def _on_slider_blur_changed(self, val: int):
        strength = round(val / 10.0, 1)
        self._update_and_sync("motion_blur_intensity", strength)

    def _on_fps_changed(self, idx):
        fps_values = [60, 120, 144, 165, 240]
        chosen = fps_values[self.combo_fps.currentIndex()]
        self._update_and_sync("target_fps", chosen)

    def _on_autostart_toggled(self, checked: bool):
        set_autostart_enabled(checked)
        self._update_and_sync("autostart_enabled", checked)

    def _find_font_combo_index(self, target: str) -> int:
        target_clean = (target or "").lower().strip()
        for i in range(self.combo_font.count()):
            if self.combo_font.itemText(i).lower().strip() == target_clean:
                return i
        font_identifiers = [
            "edo",
            "montserrat",
            "poppins",
            "bahnschrift",
            "impact",
            "franklin",
            "trebuchet",
            "georgia",
            "segoe",
        ]
        for ident in font_identifiers:
            if ident in target_clean:
                for i in range(self.combo_font.count()):
                    if ident in self.combo_font.itemText(i).lower():
                        return i
        for i in range(self.combo_font.count()):
            txt = self.combo_font.itemText(i).lower()
            if target_clean in txt or txt in target_clean:
                return i
        return 0

    def _populate_anim_combo(self, category="all"):
        if not hasattr(self, "combo_fx_anim"):
            return
        self.combo_fx_anim.blockSignals(True)
        self.combo_fx_anim.clear()
        self.combo_fx_anim.addItem("Random Pick from Category", "")
        cat = (category or "all").lower()
        if cat == "all":
            anims = [name for name, _ in ANIMATION_CATALOG]
        else:
            anims = ANIMATION_CATEGORIES.get(
                cat, [name for name, _ in ANIMATION_CATALOG]
            )
        for name in anims:
            clean_name = name.replace("_", " ").title()
            self.combo_fx_anim.addItem(clean_name, name)
        self.combo_fx_anim.blockSignals(False)

    def _filter_animation_category(self, category: str):
        cat = (category or "all").lower()
        if hasattr(self, "combo_cat_filter"):
            for i in range(self.combo_cat_filter.count()):
                if self.combo_cat_filter.itemData(i).lower() == cat:
                    self.combo_cat_filter.setCurrentIndex(i)
                    return
        self._populate_anim_combo(cat)

    def _preview_preset(self, preset: dict):
        """Immediately displays preset styles and animations on all active preview canvases."""
        if hasattr(self, "preset_preview"):
            self.preset_preview.update_settings(preset)
            self.preset_preview.trigger_animation(preset.get("animation_style", "all"))
        if hasattr(self, "preview_widget"):
            self.preview_widget.update_settings(preset)
            self.preview_widget.trigger_animation(preset.get("animation_style", "all"))
        if hasattr(self, "effects_preview"):
            self.effects_preview.update_settings(preset)
            self.effects_preview.trigger_animation(preset.get("animation_style", "all"))

    def _apply_preset(self, preset: dict):
        try:
            self.settings.update(preset)
            settings_manager.save_settings(self.settings)

            if "font_size" in preset and hasattr(self, "slider_size"):
                self.slider_size.setValue(preset["font_size"])
            if "overlay_y" in preset and hasattr(self, "slider_y"):
                self.slider_y.setValue(preset["overlay_y"])
            if "font_family" in preset and hasattr(self, "combo_font"):
                idx = self._find_font_combo_index(preset["font_family"])
                self.combo_font.setCurrentIndex(idx)
            if "hand_drawn_underline_enabled" in preset and hasattr(
                self, "toggle_underline"
            ):
                self.toggle_underline.setChecked(preset["hand_drawn_underline_enabled"])
            if "highlight_enabled" in preset and hasattr(self, "toggle_highlight"):
                self.toggle_highlight.setChecked(preset["highlight_enabled"])
            if "motion_blur_enabled" in preset and hasattr(self, "toggle_motion_blur"):
                self.toggle_motion_blur.setChecked(preset["motion_blur_enabled"])
            if "motion_blur_intensity" in preset and hasattr(self, "slider_blur"):
                self.slider_blur.setValue(
                    int(float(preset["motion_blur_intensity"]) * 10)
                )
            if "highlight_color" in preset and hasattr(self, "color_swatch"):
                self.color_swatch.setColor(preset["highlight_color"])
            if "highlight_mode" in preset and hasattr(self, "combo_hl_mode"):
                if preset["highlight_mode"] == "per_song":
                    self.combo_hl_mode.setCurrentIndex(0)
                elif "highlight_color" in preset:
                    for i in range(1, self.combo_hl_mode.count()):
                        if (
                            self.combo_hl_mode.itemData(i).upper()
                            == preset["highlight_color"].upper()
                        ):
                            self.combo_hl_mode.setCurrentIndex(i)
                            break
            if "target_fps" in preset and hasattr(self, "combo_fps"):
                fps_map = {60: 0, 120: 1, 144: 2, 165: 3, 240: 4}
                self.combo_fps.setCurrentIndex(fps_map.get(preset["target_fps"], 3))
            if "animation_style" in preset and hasattr(self, "combo_anim_style"):
                style_val = preset["animation_style"]
                for i in range(self.combo_anim_style.count()):
                    if self.combo_anim_style.itemData(i) == style_val:
                        self.combo_anim_style.setCurrentIndex(i)
                        break

            if hasattr(self, "preview_widget"):
                self.preview_widget.update_settings(self.settings)
                self.preview_widget.trigger_animation()
            if hasattr(self, "preset_preview"):
                self.preset_preview.update_settings(self.settings)
                self.preset_preview.trigger_animation()
            if hasattr(self, "effects_preview"):
                self.effects_preview.update_settings(self.settings)
                self.effects_preview.trigger_animation()
            self.settings_changed.emit(self.settings)
        except (KeyError, ValueError, TypeError, AttributeError, OSError) as e:
            logger.debug("[settings] _apply_preset error: %s", e)

    def _reset_to_defaults(self):
        defaults = settings_manager.DEFAULT_SETTINGS.copy()
        self._apply_preset(defaults)
        sync_offset = float(defaults.get("sync_offset_sec", 0.20))
        self.slider_sync.setValue(int(sync_offset * 10))
        if hasattr(self, "slider_blur"):
            blur_int = float(defaults.get("motion_blur_intensity", 1.4))
            self.slider_blur.setValue(int(blur_int * 10))
        self.toggle_hide.setChecked(bool(defaults.get("auto_hide_idle", True)))
        if hasattr(self, "toggle_autostart"):
            self.toggle_autostart.setChecked(is_autostart_enabled())

    def _on_done_clicked(self):
        """Only hides the settings dialog. Does NOT quit the overlay app."""
        settings_manager.save_settings(self.settings)
        self.hide()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self._on_done_clicked()
            event.accept()
        else:
            super().keyPressEvent(event)

    def reject(self):
        """Standard dialog reject (Esc) cleanly hides without quitting overlay."""
        self._on_done_clicked()

    def closeEvent(self, event):
        """Closing via window X cleanly saves settings and hides."""
        self._on_done_clicked()
        event.accept()

    def _on_quit_clicked(self):
        self.quit_requested.emit()
        self.close()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    settings = settings_manager.load_settings()
    dlg = SettingsDialog(settings)
    dlg.show()
    sys.exit(app.exec())
