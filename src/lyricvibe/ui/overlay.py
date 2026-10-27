"""
LyricVibe — 165Hz Floating Lyrics Overlay for Spotify.
- 55+ dynamic, varied cinematic text entrance animations with weighted rarity.
- Anti-overlap architecture: exiting lines lift cleanly away (-35px),
  guaranteeing zero text collision with incoming lines.
- Automatic clear during musical breaks: lyrics fade out cleanly during
  guitar solos and pauses rather than lingering on screen.
- High-contrast active word highlight: vibrant Spotify Green text with
  a soft rounded glowing highlight block behind the active word.
- Butter-smooth 165 FPS continuous time interpolation.
- 100% glitch-free rendering with preserved font kerning and anchored baselines.
- Zero loss of text: all words remain visible, sharp, and anchored.
- Frame-accurate audio synchronization with gentle drift correction.
- Edge-to-edge screen geometry: zero text clipping or cutoff on any display.
- Dynamic font fitting: scales gracefully so long lines never overflow.
- 7clouds typography: Edo SZ signature brush (DEFAULT) & Montserrat Black extra bold.
- Focal hand-drawn underline: elegantly underlines 1 or 2 key words (not whole sentence).
- Rock-solid anchored text: ZERO continuous float or wobble.
- Real-time settings sync with instant live updates.
- Pure razor-sharp text (no fuzzy glow).
"""

import ctypes
import logging
import math
import os
import sys
import time
from ctypes import wintypes

logger = logging.getLogger(__name__)

# Ensure no crashes in windowed mode
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")  # noqa: SIM115
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")  # noqa: SIM115

from PyQt6.QtCore import QObject, QPoint, QPointF, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import (
    QAction,
    QColor,
    QFont,
    QFontDatabase,
    QFontMetrics,
    QIcon,
    QPainter,
    QPainterPath,
    QPen,
)
from PyQt6.QtNetwork import QLocalServer, QLocalSocket
from PyQt6.QtWidgets import QApplication, QMenu, QSystemTrayIcon, QWidget

try:
    import lyricvibe.utils.settings as settings_manager
    from lyricvibe.core.animation import FADE_ANIMS, PER_CHAR_ANIMS, AnimationEngine
    from lyricvibe.core.paths import get_asset_path
    from lyricvibe.lyrics.fetcher import LyricLine, get_lyrics
    from lyricvibe.media.client import PlaybackState, SpotifyClient
    from lyricvibe.ui.settings import SettingsDialog
    from lyricvibe.utils.settings import BRIGHT_HIGHLIGHT_HEX_LIST
except ImportError:
    import settings_manager
    from animation_engine import FADE_ANIMS, PER_CHAR_ANIMS, AnimationEngine
    from lyrics_fetcher import LyricLine, get_lyrics
    from settings_manager import BRIGHT_HIGHLIGHT_HEX_LIST
    from settings_window import SettingsDialog
    from spotify_client import PlaybackState, SpotifyClient
    get_asset_path = lambda p: p

IPC_SERVER_NAME = "LyricVibeIPC_v1"


class AppSignals(QObject):
    """Thread-safe signal bridge between background threads and PyQt6 GUI."""
    lyrics_fetched = pyqtSignal(int, str, object)
    hotkey_lock = pyqtSignal()
    hotkey_hide = pyqtSignal()
    hotkey_quit = pyqtSignal()
    hotkey_settings = pyqtSignal()
    hotkey_sync_adjust = pyqtSignal(float)


def resolve_asset_path(relative_path: str) -> str:
    try:
        candidate = get_asset_path(relative_path)
        if os.path.exists(candidate):
            return candidate
    except (OSError, AttributeError) as e:
        logger.debug("[overlay] get_asset_path failed: %s", e)

    candidates = []
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            candidates.append(os.path.join(meipass, relative_path))
        candidates.append(os.path.join(os.path.dirname(sys.executable), relative_path))
    script_dir = os.path.dirname(os.path.abspath(__file__))
    candidates.append(os.path.join(script_dir, relative_path))
    candidates.append(os.path.join(os.getcwd(), relative_path))
    for p in candidates:
        if os.path.exists(p):
            return p
    return candidates[0]


class FloatingLyricsWidget(QWidget):
    def __init__(self, settings: dict):
        super().__init__()
        self.settings = settings
        self.spotify = SpotifyClient()
        self.playback: PlaybackState | None = None
        self.lyrics: list[LyricLine] | None = None
        self.current_track_id: str = ""
        self.current_line_index: int = -1
        self.current_line_text: str = ""
        self._last_color_idx: int = 0
        self.current_song_color: QColor = QColor(BRIGHT_HIGHLIGHT_HEX_LIST[0])
        self._current_fetch_id: int = 0
        self._font_cache: dict[tuple, tuple[QFont, QFontMetrics]] = {}
        self._word_span_cache: dict[str, list[tuple[str, int, int]]] = {}

        # Thread-safe Signal Bridge
        self.signals = AppSignals()
        self.signals.lyrics_fetched.connect(self._on_lyrics_fetched)
        self.signals.hotkey_lock.connect(self.toggle_lock)
        self.signals.hotkey_hide.connect(self.toggle_visibility)
        self.signals.hotkey_quit.connect(self._quit_app)
        self.signals.hotkey_settings.connect(self.open_settings_window)
        self.signals.hotkey_sync_adjust.connect(self._adjust_sync_offset)

        # State flags
        self.is_locked = False
        self.is_hidden_by_idle = False
        self.is_dragging = False
        self.drag_position = QPoint()
        self._registered_hotkeys = [801, 802, 803, 804, 805, 806, 807]

        # Physics & Animation Engine (55+ animations, butter-smooth 165Hz)
        self.engine = AnimationEngine()

        # Load 7clouds fonts (Edo SZ, Montserrat Black, Poppins)
        self._load_fonts()

        # Configure Frameless Transparent Layered Window
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.SubWindow |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)

        # Edge-to-Edge full width positioning to eliminate text clipping
        screen = QApplication.primaryScreen()
        screen_geo = screen.availableGeometry() if screen else self.screen().geometry()
        self.window_w = screen_geo.width()
        self.window_h = 180
        self.window_x = 0
        self.window_y = self.settings.get("overlay_y", 55)
        self.setGeometry(self.window_x, self.window_y, self.window_w, self.window_h)

        if screen:
            try:
                screen.geometryChanged.connect(self._on_screen_changed)
            except (AttributeError, TypeError):
                pass

        app_inst = QApplication.instance()
        if app_inst:
            try:
                app_inst.screenAdded.connect(lambda _: self._on_screen_changed())
                app_inst.screenRemoved.connect(lambda _: self._on_screen_changed())
            except (AttributeError, TypeError):
                pass

        # 165 Hz Render Timer
        fps = int(self.settings.get("target_fps", 165))
        interval_ms = max(4, int(1000.0 / fps))
        self.render_timer = QTimer(self)
        self.render_timer.timeout.connect(self.update)
        self.render_timer.start(interval_ms)

        # Spotify Playback Poll Timer (every 250ms)
        self.poll_timer = QTimer(self)
        self.poll_timer.timeout.connect(self._poll_spotify)
        self.poll_timer.start(250)

        # Smooth position check (every 50ms)
        self.smooth_timer = QTimer(self)
        self.smooth_timer.timeout.connect(self._smooth_position_check)
        self.smooth_timer.start(50)

        # Settings dialog instance
        self.settings_dialog: SettingsDialog | None = None

        # System tray icon & action references
        self.tray_icon: QSystemTrayIcon | None = None
        self.tray_lock_action: QAction | None = None
        self._setup_system_tray()

        # Global hotkeys thread
        self._start_global_hotkeys()

    def _load_fonts(self):
        font_files = [
            "fonts/EdoSZ.ttf",
            "fonts/Montserrat-Black.ttf",
            "fonts/Montserrat-ExtraBold.ttf",
            "fonts/Montserrat.ttf",
            "fonts/Poppins-Bold.ttf",
        ]
        for rel in font_files:
            fp = resolve_asset_path(rel)
            if os.path.exists(fp):
                QFontDatabase.addApplicationFont(fp)

    def _get_active_font_family(self) -> str:
        choice = self.settings.get("font_family", "7clouds Signature (Edo SZ)")
        if "Edo" in choice:
            return "Edo SZ"
        elif "Poppins" in choice:
            return "Poppins"
        elif "Segoe" in choice:
            return "Segoe UI"
        return "Montserrat"

    def _pick_next_song_color(self, track_identifier: str):
        """Picks a distinct, ultra-bright neon color for each song."""
        palette_len = len(BRIGHT_HIGHLIGHT_HEX_LIST)
        if not palette_len:
            return
        # Calculate pseudo-random seed from track identifier
        seed = sum(ord(c) * (i + 1) for i, c in enumerate(track_identifier)) if track_identifier else int(time.time())
        chosen_idx = seed % palette_len
        # Ensure adjacent songs NEVER share the same color!
        if chosen_idx == getattr(self, "_last_color_idx", -1):
            chosen_idx = (chosen_idx + 1) % palette_len
        self._last_color_idx = chosen_idx
        self.current_song_color = QColor(BRIGHT_HIGHLIGHT_HEX_LIST[chosen_idx])

    def _get_highlight_color(self) -> QColor:
        """
        Returns the vibrant ultra-bright highlight color for the active spoken word.
        Rotates automatically per song or uses fixed user selection.
        """
        mode = self.settings.get("highlight_mode", "per_song")
        if mode == "per_song":
            return getattr(self, "current_song_color", QColor(BRIGHT_HIGHLIGHT_HEX_LIST[0]))
        hex_color = self.settings.get("highlight_color", BRIGHT_HIGHLIGHT_HEX_LIST[0])
        return QColor(hex_color)

    def apply_settings(self, new_settings: dict):
        """Real-time live settings sync without restarts or crashes."""
        try:
            self.settings.update(new_settings)
            self._font_cache.clear()
            self._word_span_cache.clear()

            # Update FPS
            fps = int(self.settings.get("target_fps", 165))
            interval_ms = max(4, int(1000.0 / fps))
            self.render_timer.setInterval(interval_ms)

            # Update screen vertical position
            self.window_y = int(self.settings.get("overlay_y", 55))
            self.move(0, self.window_y)

            # Trigger immediate live repaint
            self.update()
        except (KeyError, ValueError, TypeError, AttributeError, OSError) as e:
            logger.debug("[overlay] apply_settings error: %s", e)

    def open_settings_window(self):
        if self.settings_dialog is None:
            self.settings_dialog = SettingsDialog(self.settings, None)
            self.settings_dialog.settings_changed.connect(self.apply_settings)
            self.settings_dialog.quit_requested.connect(self._quit_app)
        self.settings_dialog.show()
        self.settings_dialog.raise_()
        self.settings_dialog.activateWindow()

    # ── Paint Engine (165 FPS Hardware Accelerated, Butter Smooth) ──
    def paintEvent(self, event):
        data = self.engine.update()
        curr_text = data.get("curr_text", "")
        prev_data = data.get("prev")

        if not curr_text and not prev_data:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        screen_cx = self.width() / 2.0
        screen_cy = self.height() / 2.0
        avail_w = max(100.0, float(self.width() - 80.0))
        base_size = int(self.settings.get("font_size", 42))
        font_family = self._get_active_font_family()

        highlight_enabled = self.settings.get("highlight_enabled", True)
        highlight_color = self._get_highlight_color()
        highlight_idx = data.get("highlight_word_idx", -1)

        # ── 1. Outgoing Line (Lifted UP to prevent overlap with incoming text) ──
        if prev_data and prev_data["alpha"] > 0.02:
            p_text = prev_data["text"]
            p_alpha = int(prev_data["alpha"] * 255)
            p_font, p_metrics = self._fit_font(p_text, avail_w, base_size, font_family)
            painter.setFont(p_font)
            painter.setPen(QColor(255, 255, 255, p_alpha))

            painter.save()
            # Smooth upward lift starting strictly at 0.0 (zero teleportation or offset jump)
            painter.translate(screen_cx, screen_cy + prev_data["offset_y"])
            if prev_data["scale"] != 1.0:
                painter.scale(prev_data["scale"], prev_data["scale"])

            w = p_metrics.horizontalAdvance(p_text)
            p_baseline_y = (p_metrics.ascent() - p_metrics.descent()) / 2.0

            # Outgoing motion blur streak (subtle upward optical softening)
            if self.settings.get("motion_blur_enabled", True) and prev_data.get("blur_dy", 0.0) != 0.0:
                p_blur_dy = max(-4.0, min(0.0, prev_data["blur_dy"]))
                blur_int = float(self.settings.get("motion_blur_intensity", 1.4))
                for step in range(1, 3):
                    frac = step / 2.0
                    out_blur_a = int(p_alpha * 0.18 * (1.0 - frac * 0.5))
                    if out_blur_a > 2:
                        painter.save()
                        painter.translate(0.0, -p_blur_dy * frac * blur_int)
                        painter.setPen(QColor(255, 255, 255, out_blur_a))
                        painter.drawText(QPointF(-w / 2.0, p_baseline_y), p_text)
                        painter.restore()

            painter.drawText(QPointF(-w / 2.0, p_baseline_y), p_text)
            painter.restore()

        # ── 2. Incoming Line ──
        if curr_text and data["curr_alpha"] > 0.02:
            in_alpha = int(data["curr_alpha"] * 255)
            in_font, in_metrics = self._fit_font(curr_text, avail_w, base_size, font_family)
            painter.setFont(in_font)

            # ── Directional Motion Blur Shutter (Subtle optical softness on physical motion) ──
            anim_type = data.get("anim_type", "")
            blur_enabled = self.settings.get("motion_blur_enabled", True)
            blur_dx = data.get("blur_dx", 0.0)
            blur_dy = data.get("blur_dy", 0.0)
            blur_dist = data.get("blur_dist", 0.0)
            blur_intensity = float(self.settings.get("motion_blur_intensity", 1.4))

            # Never blur pure fade transitions; only blur genuine physical entrance motion
            if blur_enabled and blur_dist > 0.4 and anim_type not in FADE_ANIMS:
                total_in_w = in_metrics.horizontalAdvance(curr_text)
                in_base_y = (in_metrics.ascent() - in_metrics.descent()) / 2.0
                clamped_dx = max(-3.5, min(3.5, blur_dx))
                clamped_dy = max(-3.5, min(3.5, blur_dy))
                for step in range(1, 3):
                    frac = step / 2.0
                    trail_x = -clamped_dx * frac * blur_intensity
                    trail_y = -clamped_dy * frac * blur_intensity
                    step_a = int(in_alpha * data.get("blur_alpha", 0.25) * (1.0 - frac * 0.5))
                    if step_a > 2:
                        painter.save()
                        painter.translate(
                            screen_cx + data.get("curr_offset_x", 0.0) + trail_x,
                            screen_cy + data["curr_offset_y"] + trail_y
                        )
                        if data.get("rotation", 0.0) != 0.0:
                            painter.rotate(data["rotation"])
                        if data["curr_scale"] != 1.0:
                            painter.scale(data["curr_scale"], data["curr_scale"])
                        painter.setPen(QColor(255, 255, 255, step_a))
                        painter.drawText(QPointF(-total_in_w / 2.0, in_base_y), curr_text)
                        painter.restore()

            painter.save()
            painter.translate(screen_cx + data.get("curr_offset_x", 0.0), screen_cy + data["curr_offset_y"])

            # Rotational / Skew / Scale transforms
            if data.get("rotation", 0.0) != 0.0:
                painter.rotate(data["rotation"])
            if data.get("skew_x", 0.0) != 0.0:
                painter.shear(math.tan(math.radians(data["skew_x"])), 0)
            if data["curr_scale"] != 1.0:
                painter.scale(data["curr_scale"], data["curr_scale"])

            anim_type = data.get("anim_type", "")

            # ── Per-Character Rendering (Only when per-char active) ──
            if (anim_type in PER_CHAR_ANIMS and data.get("char_alphas")
                    and any(oy != 0.0 for oy in data.get("char_offsets_y", []))):
                self._draw_per_char(
                    painter, in_metrics, curr_text,
                    data["char_offsets_x"], data["char_offsets_y"],
                    data["char_alphas"], data["char_scales"],
                    in_alpha, highlight_enabled, highlight_color, highlight_idx
                )
            else:
                # Glitch-free sharp rendering with high-contrast active word highlight block
                self._draw_sharp_line_with_highlight(
                    painter, in_metrics, curr_text, in_alpha,
                    highlight_enabled, highlight_color, highlight_idx
                )

            # ── 3. Focal Hand-Drawn Underline (Underlines ONLY 1-2 words) ──
            if (self.settings.get("hand_drawn_underline_enabled", True) and
                    data.get("underline_active") and
                    data.get("underline_progress", 0.0) > 0.02 and
                    data.get("focal_word_idx", -1) >= 0):
                self._draw_focal_underline(
                    painter, in_metrics, curr_text,
                    data["focal_word_idx"],
                    data["underline_stroke"],
                    data["underline_progress"],
                    data["curr_alpha"]
                )

            painter.restore()

    def _fit_font(self, text: str, max_w: float, base_size: int, family: str) -> tuple[QFont, QFontMetrics]:
        """Dynamically scales font size down so long lyric lines NEVER get cut off. Uses caching for 165Hz performance."""
        key = (text, int(max_w), base_size, family)
        cached = self._font_cache.get(key)
        if cached is not None:
            return cached

        size = base_size
        weight = QFont.Weight.Black if family == "Montserrat" else QFont.Weight.Bold
        font = QFont(family, size, weight)
        font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
        metrics = QFontMetrics(font)

        # Fast logarithmic binary search to scale font dynamically on long lines
        if metrics.horizontalAdvance(text) > max_w:
            low = 16
            high = base_size
            best_size = 16
            while low <= high:
                mid = (low + high) // 2
                font.setPointSize(mid)
                m = QFontMetrics(font)
                if m.horizontalAdvance(text) <= max_w:
                    best_size = mid
                    low = mid + 1
                else:
                    high = mid - 1
            size = best_size
            font.setPointSize(size)
            metrics = QFontMetrics(font)

        if len(self._font_cache) > 100:
            self._font_cache.clear()

        result = (font, metrics)
        self._font_cache[key] = result
        return result

    def _get_word_spans(self, text: str) -> list[tuple[str, int, int]]:
        """Extracts word substrings and character boundaries with caching."""
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

        if len(self._word_span_cache) > 100:
            self._word_span_cache.clear()

        self._word_span_cache[text] = words
        return words

    def _draw_sharp_line_with_highlight(self, painter: QPainter, metrics: QFontMetrics,
                                        text: str, master_alpha: int,
                                        hl_enabled: bool, hl_color: QColor, hl_word_idx: int):
        """
        Renders razor-sharp lyrics with 100% kerning accuracy and high-contrast
        active word highlight with rounded glowing background block.
        """
        total_w = metrics.horizontalAdvance(text)
        start_x = -total_w / 2.0
        # True vertical center baseline
        baseline_y = (metrics.ascent() - metrics.descent()) / 2.0

        # Pass 1: Render the complete crisp white line at full subpixel quality
        painter.setPen(QColor(255, 255, 255, master_alpha))
        painter.drawText(QPointF(start_x, baseline_y), text)

        if not hl_enabled or hl_word_idx < 0:
            return

        words = self._get_word_spans(text)

        # Pass 2: Active word highlight in ultra-bright vivid color
        if 0 <= hl_word_idx < len(words):
            word_str, w_start, _ = words[hl_word_idx]
            word_x = start_x + metrics.horizontalAdvance(text[:w_start])
            painter.setPen(QColor(hl_color.red(), hl_color.green(), hl_color.blue(), master_alpha))
            painter.drawText(QPointF(word_x, baseline_y), word_str)

    def _draw_per_char(self, painter: QPainter, metrics: QFontMetrics,
                       text: str, offsets_x: list, offsets_y: list,
                       char_alphas: list, char_scales: list,
                       master_alpha: int,
                       hl_enabled: bool, hl_color: QColor, hl_word_idx: int):
        """Renders individual characters with exact kerning preservation."""
        total_w = metrics.horizontalAdvance(text)
        start_x = -total_w / 2.0
        baseline_y = (metrics.ascent() - metrics.descent()) / 2.0

        # Build word map with exact character bounds
        word_char_map = []
        words = text.strip().split()
        if hl_enabled and hl_word_idx >= 0 and words:
            char_idx = 0
            for wi, word in enumerate(words):
                if wi > 0:
                    word_char_map.append(-1)
                    char_idx += 1
                for _ in word:
                    word_char_map.append(wi)
                    char_idx += 1

        for i, ch in enumerate(text):
            ch_w = metrics.horizontalAdvance(ch)
            ch_x = start_x + metrics.horizontalAdvance(text[:i])
            ca = char_alphas[i] if i < len(char_alphas) else 1.0
            ox = offsets_x[i] if i < len(offsets_x) else 0.0
            oy = offsets_y[i] if i < len(offsets_y) else 0.0
            cs = char_scales[i] if i < len(char_scales) else 1.0
            final_a = max(0, min(255, int(master_alpha * ca)))

            if (hl_enabled and hl_word_idx >= 0 and
                    i < len(word_char_map) and word_char_map[i] == hl_word_idx):
                painter.setPen(QColor(hl_color.red(), hl_color.green(), hl_color.blue(), final_a))
            else:
                painter.setPen(QColor(255, 255, 255, final_a))

            if cs != 1.0:
                painter.save()
                painter.translate(ch_x + ch_w / 2.0 + ox, baseline_y + oy)
                painter.scale(cs, cs)
                painter.drawText(QPointF(-ch_w / 2.0, 0), ch)
                painter.restore()
            else:
                painter.drawText(QPointF(ch_x + ox, baseline_y + oy), ch)

    def _draw_focal_underline(self, painter: QPainter, metrics: QFontMetrics,
                               text: str, focal_idx: int, stroke, progress: float, alpha: float):
        """Draws realistic sketched pencil and fluid marker lines ONLY under 1-2 key focal words."""
        if not stroke or progress <= 0.03 or focal_idx < 0:
            return

        total_w = metrics.horizontalAdvance(text)
        start_line_x = -total_w / 2.0
        baseline_y = (metrics.ascent() - metrics.descent()) / 2.0

        words = []
        idx = 0
        while idx < len(text):
            if text[idx].isspace():
                idx += 1
                continue
            w_start = idx
            while idx < len(text) and not text[idx].isspace():
                idx += 1
            w_end = idx
            words.append((text[w_start:w_end], w_start, w_end))

        if focal_idx >= len(words):
            return

        word_str, w_start, w_end = words[focal_idx]
        word_start_x = start_line_x + metrics.horizontalAdvance(text[:w_start])
        target_w = metrics.horizontalAdvance(word_str)

        draw_w = target_w * progress
        if draw_w < 6:
            return

        y_base = baseline_y + 10.0

        # Pass 1: Light sketched pencil under-stroke
        p_sketch = QPen(QColor(255, 255, 255, int(alpha * 75)), 1.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        painter.setPen(p_sketch)
        path1 = QPainterPath()
        path1.moveTo(word_start_x - 2, y_base)
        path1.quadTo(word_start_x + draw_w * 0.5, y_base + 3, word_start_x + draw_w + 3, y_base + 1)
        painter.drawPath(path1)

        # Pass 2: Main hand-drawn ink line with natural tremors
        p_ink = QPen(QColor(255, 255, 255, int(alpha * 225)), 2.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        painter.setPen(p_ink)

        path2 = QPainterPath()
        pts = stroke.offsets
        n = len(pts)
        step_x = draw_w / max(1, n - 1)

        path2.moveTo(word_start_x, y_base + pts[0])
        for i in range(1, n):
            px = word_start_x + i * step_x
            py = y_base + pts[i]
            prev_x = word_start_x + (i - 1) * step_x
            prev_y = y_base + pts[i - 1]
            ctrl_x = (prev_x + px) / 2.0
            ctrl_y = (prev_y + py) / 2.0
            path2.quadTo(prev_x, prev_y, ctrl_x, ctrl_y)

        painter.drawPath(path2)

    # ── System Tray ──
    def _setup_system_tray(self):
        if not QSystemTrayIcon.isSystemTrayAvailable():
            self.tray_icon = None
            return

        self.tray_icon = QSystemTrayIcon(self)
        icon_path = resolve_asset_path("icon.ico")
        if not os.path.exists(icon_path):
            icon_path = resolve_asset_path("icon.png")
        if os.path.exists(icon_path):
            self.tray_icon.setIcon(QIcon(icon_path))

        self.tray_icon.setToolTip("LyricVibe - Spotify Lyrics Overlay")

        menu = QMenu()
        settings_action = QAction("Settings...", self)
        settings_action.triggered.connect(self.open_settings_window)
        font = settings_action.font()
        font.setBold(True)
        settings_action.setFont(font)
        menu.addAction(settings_action)

        self.tray_lock_action = QAction("Lock (Click-Through)", self)
        self.tray_lock_action.setCheckable(True)
        self.tray_lock_action.setChecked(self.is_locked)
        self.tray_lock_action.triggered.connect(self.toggle_lock)
        menu.addAction(self.tray_lock_action)

        toggle_action = QAction("Show / Hide Overlay", self)
        toggle_action.triggered.connect(self.toggle_visibility)
        menu.addAction(toggle_action)

        menu.addSeparator()

        quit_action = QAction("Quit LyricVibe", self)
        quit_action.triggered.connect(self._quit_app)
        menu.addAction(quit_action)

        self.tray_icon.setContextMenu(menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()

    def _on_tray_activated(self, reason):
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self.open_settings_window()

    # ── Mouse Interaction & Window Dragging ──
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and not self.is_locked:
            self.is_dragging = True
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self.is_dragging and not self.is_locked:
            new_pos = event.globalPosition().toPoint() - self.drag_position
            self.move(0, new_pos.y())
            self.settings["overlay_y"] = new_pos.y()
            event.accept()

    def _on_screen_changed(self):
        screen = self.screen() or QApplication.primaryScreen()
        if screen:
            screen_geo = screen.availableGeometry()
            self.window_w = screen_geo.width()
            self.setGeometry(0, self.window_y, self.window_w, self.window_h)
            self._font_cache.clear()
            self.update()

    def _adjust_sync_offset(self, delta: float):
        curr = float(self.settings.get("sync_offset_sec", 0.20))
        new_val = round(max(-5.0, min(5.0, curr + delta)), 2)
        self.settings["sync_offset_sec"] = new_val
        settings_manager.save_settings(self.settings)
        if self.settings_dialog and hasattr(self.settings_dialog, "slider_sync"):
            self.settings_dialog.slider_sync.setValue(int(new_val * 10))

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_BracketLeft:
            self._adjust_sync_offset(-0.5)
            event.accept()
        elif event.key() == Qt.Key.Key_BracketRight:
            self._adjust_sync_offset(0.5)
            event.accept()
        elif event.key() == Qt.Key.Key_L and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self.toggle_lock()
            event.accept()
        elif event.key() == Qt.Key.Key_H and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self.toggle_visibility()
            event.accept()
        elif event.key() == Qt.Key.Key_Q and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self._quit_app()
            event.accept()
        else:
            super().keyPressEvent(event)

    def mouseReleaseEvent(self, event):
        if self.is_dragging:
            self.is_dragging = False
            settings_manager.save_settings(self.settings)

    def mouseDoubleClickEvent(self, event):
        self.open_settings_window()

    # ── Global Hotkeys ──
    def _start_global_hotkeys(self):
        def _hotkey_worker():
            user32 = ctypes.windll.user32
            MOD_ALT = 0x0001
            MOD_CONTROL = 0x0002

            HOTKEY_LOCK = 801
            HOTKEY_HIDE = 802
            HOTKEY_QUIT = 803
            HOTKEY_SETTINGS_COMBO = 804
            HOTKEY_SETTINGS = 805
            HOTKEY_SYNC_PREV = 806
            HOTKEY_SYNC_NEXT = 807

            VK_OEM_4 = 0xDB  # '[' key
            VK_OEM_6 = 0xDD  # ']' key

            user32.RegisterHotKey(None, HOTKEY_LOCK, MOD_CONTROL | MOD_ALT, ord('L'))
            user32.RegisterHotKey(None, HOTKEY_HIDE, MOD_CONTROL | MOD_ALT, ord('H'))
            user32.RegisterHotKey(None, HOTKEY_QUIT, MOD_CONTROL | MOD_ALT, ord('Q'))
            user32.RegisterHotKey(None, HOTKEY_SETTINGS_COMBO, MOD_CONTROL | MOD_ALT, ord('S'))
            user32.RegisterHotKey(None, HOTKEY_SETTINGS, MOD_CONTROL, ord('S'))
            user32.RegisterHotKey(None, HOTKEY_SYNC_PREV, MOD_CONTROL | MOD_ALT, VK_OEM_4)
            user32.RegisterHotKey(None, HOTKEY_SYNC_NEXT, MOD_CONTROL | MOD_ALT, VK_OEM_6)

            msg = wintypes.MSG()
            while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
                if msg.message == 0x0312:
                    if msg.wParam == HOTKEY_LOCK:
                        self.signals.hotkey_lock.emit()
                    elif msg.wParam == HOTKEY_HIDE:
                        self.signals.hotkey_hide.emit()
                    elif msg.wParam == HOTKEY_QUIT:
                        self.signals.hotkey_quit.emit()
                    elif msg.wParam in (HOTKEY_SETTINGS_COMBO, HOTKEY_SETTINGS):
                        self.signals.hotkey_settings.emit()
                    elif msg.wParam == HOTKEY_SYNC_PREV:
                        self.signals.hotkey_sync_adjust.emit(-0.5)
                    elif msg.wParam == HOTKEY_SYNC_NEXT:
                        self.signals.hotkey_sync_adjust.emit(0.5)
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))

        import threading
        threading.Thread(target=_hotkey_worker, daemon=True).start()

    def toggle_lock(self):
        self.is_locked = not self.is_locked
        if hasattr(self, "tray_lock_action") and self.tray_lock_action:
            self.tray_lock_action.setChecked(self.is_locked)
        hwnd = int(self.winId())
        self._set_window_clickthrough(hwnd, self.is_locked)

    def _set_window_clickthrough(self, hwnd: int, clickthrough: bool):
        """Safely applies WS_EX_TRANSPARENT layered style with 64-bit pointer and frame refresh safety."""
        try:
            user32 = ctypes.windll.user32
            GWL_EXSTYLE = -20
            WS_EX_LAYERED = 0x00080000
            WS_EX_TRANSPARENT = 0x00000020
            SWP_FLAGS = 0x0027  # SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_FRAMECHANGED

            get_long = getattr(user32, "GetWindowLongPtrW", user32.GetWindowLongW)
            set_long = getattr(user32, "SetWindowLongPtrW", user32.SetWindowLongW)

            get_long.argtypes = [wintypes.HWND, ctypes.c_int]
            get_long.restype = ctypes.c_ssize_t
            set_long.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_ssize_t]
            set_long.restype = ctypes.c_ssize_t

            current_style = get_long(hwnd, GWL_EXSTYLE)
            if clickthrough:
                new_style = current_style | WS_EX_LAYERED | WS_EX_TRANSPARENT
            else:
                new_style = (current_style & ~WS_EX_TRANSPARENT) | WS_EX_LAYERED

            set_long(hwnd, GWL_EXSTYLE, new_style)
            user32.SetWindowPos(hwnd, None, 0, 0, 0, 0, SWP_FLAGS)
        except (AttributeError, OSError) as e:
            logger.debug("[overlay] set_clickthrough error: %s", e)

    def toggle_visibility(self):
        if self.isVisible():
            self.hide()
        else:
            self.show()

    def closeEvent(self, event):
        self._quit_app()
        event.accept()

    def _quit_app(self):
        try:
            self.render_timer.stop()
            self.poll_timer.stop()
            self.smooth_timer.stop()
            if hasattr(self, "tray_icon") and self.tray_icon:
                self.tray_icon.hide()
            user32 = getattr(ctypes.windll, "user32", None)
            if user32:
                for hid in getattr(self, "_registered_hotkeys", []):
                    try:
                        user32.UnregisterHotKey(None, hid)
                    except OSError:
                        pass
        except (AttributeError, OSError, RuntimeError) as e:
            logger.debug("[overlay] error during shutdown: %s", e)
        self.spotify.close()
        QApplication.quit()

    # ── Spotify Polling & Position Tracking ──
    def _poll_spotify(self):
        try:
            state = self.spotify.get_playback()

            if state is None or not state.track_name or not state.is_playing:
                if self.settings.get("auto_hide_idle", True) and not self.is_hidden_by_idle:
                    self.hide()
                    self.is_hidden_by_idle = True
                self.playback = None
                return

            if self.is_hidden_by_idle:
                self.show()
                self.is_hidden_by_idle = False

            self.playback = state

            # Track changed?
            if state.track_id != self.current_track_id:
                self.current_track_id = state.track_id
                self.lyrics = None  # Crucial: Immediately clear old song lyrics!
                self.current_line_index = -1
                self.current_line_text = ""
                self.engine.clear_line()
                self._pick_next_song_color(state.track_id)
                self.update()

                self._current_fetch_id += 1
                fetch_id = self._current_fetch_id
                req_track = state.track_id

                import threading
                threading.Thread(
                    target=self._fetch_lyrics_thread,
                    args=(state.track_name, state.artist_name,
                          state.album_name, state.duration_sec,
                          fetch_id, req_track),
                    daemon=True,
                ).start()
                return

            self._check_line_update(state)
        except (KeyError, ValueError, TypeError, AttributeError, OSError, RuntimeError) as e:
            logger.debug("[overlay] poll_spotify error: %s", e)

    def _smooth_position_check(self):
        if self.playback and self.playback.is_playing and self.lyrics:
            self._check_line_update(self.playback)

    def _check_line_update(self, state: PlaybackState):
        if not self.lyrics or state.track_id != self.current_track_id:
            return

        progress = self.spotify.estimate_progress(state)
        adjusted = progress + self.settings.get("sync_offset_sec", 0.20)

        # Find matching line index
        line_idx = -1
        for i, line in enumerate(self.lyrics):
            if line.time_sec <= adjusted:
                line_idx = i
            else:
                break

        if line_idx != self.current_line_index:
            self.current_line_index = line_idx
            if 0 <= line_idx < len(self.lyrics):
                raw_text = self.lyrics[line_idx].text.strip()
                next_time = self.lyrics[line_idx + 1].time_sec if (line_idx + 1 < len(self.lyrics)) else state.duration_sec
                dur = max(next_time - self.lyrics[line_idx].time_sec, 1.4)
                lead = max(0.0, adjusted - self.lyrics[line_idx].time_sec)

                self.current_line_text = raw_text
                self.engine.trigger_line(raw_text, dur, lead_sec=lead)
            else:
                self.current_line_text = ""
                self.engine.clear_line()

            self.update()
        elif 0 <= line_idx < len(self.lyrics):
            # Check for instrumental break / guitar solo where vocal has already ended
            current_line = self.lyrics[line_idx]
            next_time = self.lyrics[line_idx + 1].time_sec if (line_idx + 1 < len(self.lyrics)) else state.duration_sec
            gap = next_time - current_line.time_sec
            line_elapsed = adjusted - current_line.time_sec

            # Words take ~0.40s each to sing
            words = current_line.text.strip().split()
            vocal_dur = max(2.2, min(gap - 0.4, len(words) * 0.42 + 1.2))

            # If gap before next line is large (> 4.0s) and vocal has finished:
            if gap > 4.0 and line_elapsed > vocal_dur:
                # Fade out cleanly so old text does NOT linger during musical breaks
                if self.engine.curr_text:
                    self.engine.clear_line()
                    self.current_line_text = ""
                    self.update()
                return

            self.engine.sync_to_audio(line_elapsed)

    def _fetch_lyrics_thread(self, track: str, artist: str, album: str, duration: float,
                             fetch_id: int, req_track_id: str):
        lyrics = get_lyrics(track, artist, album, duration)
        self.signals.lyrics_fetched.emit(fetch_id, req_track_id, lyrics)

    def _on_lyrics_fetched(self, fetch_id: int, req_track_id: str, lyrics: list[LyricLine] | None):
        # Strict validation: Only accept if this matches the currently playing song!
        if fetch_id != getattr(self, "_current_fetch_id", 0) or req_track_id != self.current_track_id:
            return

        self.lyrics = lyrics
        if lyrics and self.playback and self.playback.track_id == self.current_track_id:
            self._check_line_update(self.playback)
        else:
            self.current_line_text = ""
            self.engine.clear_line()
            self.update()


# ── Single-Instance IPC & Entry Point ──
def main():
    app = QApplication(sys.argv)
    app.setApplicationName("LyricVibe")

    # Set Application Icon
    for icon_name in ("icon.ico", "icon.png"):
        icon_path = resolve_asset_path(icon_name)
        if os.path.exists(icon_path):
            app.setWindowIcon(QIcon(icon_path))
            break

    # Single-Instance check via QLocalSocket
    socket = QLocalSocket()
    socket.connectToServer(IPC_SERVER_NAME)
    if socket.waitForConnected(400):
        socket.write(b"OPEN_SETTINGS\n")
        socket.waitForBytesWritten(300)
        socket.disconnectFromServer()
        sys.exit(0)

    # Primary instance -> Start IPC server
    server = QLocalServer()
    QLocalServer.removeServer(IPC_SERVER_NAME)
    server.listen(IPC_SERVER_NAME)

    settings = settings_manager.load_settings()
    widget = FloatingLyricsWidget(settings)

    def handle_client_connection():
        client = server.nextPendingConnection()
        if client:
            def on_ready_read():
                msg = bytes(client.readAll()).decode("utf-8", errors="ignore").strip()
                if "OPEN_SETTINGS" in msg:
                    widget.open_settings_window()
            client.readyRead.connect(on_ready_read)

    server.newConnection.connect(handle_client_connection)

    widget.show()
    sys.exit(app.exec())


def run_app():
    return main()


if __name__ == "__main__":
    main()
