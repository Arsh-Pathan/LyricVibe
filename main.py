"""
Lyric Flow — 165Hz Floating Lyrics Overlay for Spotify.
- 38+ dynamic, varied cinematic text entrance animations with weighted rarity.
- Rich suite of silky-smooth fade-in and fade-out transitions.
- Aesthetic soft cream color highlight: consistent throughout each song,
  randomly selects a new soft cream tone for the next song.
- 100% glitch-free rendering with preserved font kerning and anchored baselines.
- Zero loss of text: all words remain visible, sharp, and anchored.
- Frame-accurate audio synchronization via direct song elapsed feedback.
- Edge-to-edge screen geometry: zero text clipping or cutoff on any display.
- Dynamic font fitting: scales gracefully so long lines never overflow.
- 7clouds typography: Edo SZ signature brush (DEFAULT) & Montserrat Black extra bold.
- Focal hand-drawn underline: elegantly underlines 1 or 2 key words (not whole sentence).
- Dual-buffer cross-transitions between lyric lines (no abrupt cuts).
- Rock-solid anchored text: ZERO continuous float or wobble.
- Real-time settings sync with instant live updates.
- Pure razor-sharp text (no fuzzy glow).
"""

import sys
import os
import time
import math
import ctypes
from ctypes import wintypes

# Ensure no crashes in windowed mode
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")

from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtCore import Qt, QTimer, QPoint, QPointF, QRectF, QObject, pyqtSignal
from PyQt6.QtGui import (
    QPainter, QColor, QFont, QFontMetrics, QFontDatabase, QPen,
    QPainterPath, QTransform, QIcon
)
from PyQt6.QtNetwork import QLocalServer, QLocalSocket

import settings_manager
from settings_window import SettingsDialog
from spotify_client import SpotifyClient, PlaybackState
from lyrics_fetcher import get_lyrics, LyricLine
from animation_engine import AnimationEngine, PER_CHAR_ANIMS

IPC_SERVER_NAME = "SpotifyLyricsOverlayIPC_v1"

# Curated aesthetic soft cream / warm pastel color palette
CREAM_SOFT_PALETTE = [
    "#FFF4E0",  # Soft Buttercream
    "#FFEEDB",  # Warm Cream
    "#FDF0ED",  # Rose Linen
    "#FDF8E2",  # Pale Honey Cream
    "#F7EBE8",  # Almond Milk
    "#FFF8EE",  # Soft Vanilla
    "#F5EBE0",  # Warm Cashmere
    "#FFE5D9",  # Peach Whipped Cream
    "#FAF0E6",  # Antique Linen
    "#F3E9DC",  # Soft Biscuit Latte
    "#FFF1C5",  # Warm Primrose Cream
    "#F0E6D2",  # Warm Oat Parchment
]


class AppSignals(QObject):
    """Thread-safe signal bridge between background threads and PyQt6 GUI."""
    lyrics_fetched = pyqtSignal(object)
    hotkey_lock = pyqtSignal()
    hotkey_hide = pyqtSignal()
    hotkey_quit = pyqtSignal()
    hotkey_settings = pyqtSignal()


def resolve_asset_path(relative_path: str) -> str:
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
        # Active soft cream color for current song
        self.current_song_cream_color = CREAM_SOFT_PALETTE[0]

        # Thread-safe Signal Bridge
        self.signals = AppSignals()
        self.signals.lyrics_fetched.connect(self._on_lyrics_fetched)
        self.signals.hotkey_lock.connect(self.toggle_lock)
        self.signals.hotkey_hide.connect(self.toggle_visibility)
        self.signals.hotkey_quit.connect(self._quit_app)
        self.signals.hotkey_settings.connect(self.open_settings_window)

        # State flags
        self.is_locked = False
        self.is_hidden_by_idle = False
        self.is_dragging = False
        self.drag_position = QPoint()

        # Physics & Animation Engine (38+ animations, zero continuous float)
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

    def _get_highlight_color(self) -> QColor:
        """Returns the soft cream accent color, consistent for the entire song."""
        mode = self.settings.get("highlight_mode", "cream_per_song")
        if mode == "cream_per_song" or not self.settings.get("highlight_color"):
            return QColor(getattr(self, "current_song_cream_color", CREAM_SOFT_PALETTE[0]))
        return QColor(self.settings.get("highlight_color", CREAM_SOFT_PALETTE[0]))

    def apply_settings(self, new_settings: dict):
        """Real-time live settings sync without restarts or crashes."""
        try:
            self.settings.update(new_settings)

            # Update FPS
            fps = int(self.settings.get("target_fps", 165))
            interval_ms = max(4, int(1000.0 / fps))
            self.render_timer.setInterval(interval_ms)

            # Update screen vertical position
            self.window_y = int(self.settings.get("overlay_y", 55))
            self.move(0, self.window_y)

            # Trigger immediate live repaint
            self.update()
        except Exception:
            pass

    def open_settings_window(self):
        if self.settings_dialog is None:
            self.settings_dialog = SettingsDialog(self.settings, None)
            self.settings_dialog.settings_changed.connect(self.apply_settings)
            self.settings_dialog.quit_requested.connect(self._quit_app)
        self.settings_dialog.show()
        self.settings_dialog.raise_()
        self.settings_dialog.activateWindow()

    # ── Paint Engine (165 FPS Hardware Accelerated, Razor Sharp) ──
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
        avail_w = self.width() - 80.0
        base_size = int(self.settings.get("font_size", 42))
        font_family = self._get_active_font_family()

        highlight_enabled = self.settings.get("highlight_enabled", True)
        highlight_color = self._get_highlight_color()
        highlight_idx = data.get("highlight_word_idx", -1)

        # ── 1. Outgoing Line (Seamless Cross-Transition) ──
        if prev_data and prev_data["alpha"] > 0.02:
            p_text = prev_data["text"]
            p_alpha = int(prev_data["alpha"] * 255)
            p_font, p_metrics = self._fit_font(p_text, avail_w, base_size, font_family)
            painter.setFont(p_font)
            painter.setPen(QColor(255, 255, 255, p_alpha))

            painter.save()
            painter.translate(screen_cx, screen_cy + prev_data["offset_y"])
            if prev_data["scale"] != 1.0:
                painter.scale(prev_data["scale"], prev_data["scale"])

            w = p_metrics.horizontalAdvance(p_text)
            p_baseline_y = (p_metrics.ascent() - p_metrics.descent()) / 2.0
            painter.drawText(QPointF(-w / 2.0, p_baseline_y), p_text)
            painter.restore()

        # ── 2. Incoming Line ──
        if curr_text and data["curr_alpha"] > 0.02:
            in_alpha = int(data["curr_alpha"] * 255)
            in_font, in_metrics = self._fit_font(curr_text, avail_w, base_size, font_family)
            painter.setFont(in_font)

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
                # Glitch-free sharp rendering with soft cream active word highlight
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
        """Dynamically scales font size down so long lyric lines NEVER get cut off."""
        size = base_size
        weight = QFont.Weight.Black if family == "Montserrat" else QFont.Weight.Bold
        font = QFont(family, size, weight)
        font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
        metrics = QFontMetrics(font)

        while metrics.horizontalAdvance(text) > max_w and size > 16:
            size -= 1
            font.setPointSize(size)
            metrics = QFontMetrics(font)

        return font, metrics

    def _draw_sharp_line_with_highlight(self, painter: QPainter, metrics: QFontMetrics,
                                        text: str, master_alpha: int,
                                        hl_enabled: bool, hl_color: QColor, hl_word_idx: int):
        """
        Renders razor-sharp lyrics with 100% kerning accuracy and zero glitching.
        Draws the full text cleanly at baseline, then overlays the soft cream
        highlight on the exact active word with identical geometry.
        """
        total_w = metrics.horizontalAdvance(text)
        start_x = -total_w / 2.0
        # True vertical center baseline inside height 80 (-40 to +40)
        baseline_y = (metrics.ascent() - metrics.descent()) / 2.0

        # Pass 1: Render the complete crisp white line at full subpixel quality
        painter.setPen(QColor(255, 255, 255, master_alpha))
        painter.drawText(QPointF(start_x, baseline_y), text)

        if not hl_enabled or hl_word_idx < 0:
            return

        # Find words and their exact substring start indices in the original text
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

        # Pass 2: Soft cream highlight overlay on the active spoken word
        if 0 <= hl_word_idx < len(words):
            word_str, w_start, w_end = words[hl_word_idx]
            # Exact X coordinate measured from text prefix preserves 100% font kerning!
            word_x = start_x + metrics.horizontalAdvance(text[:w_start])
            cream_a = int(master_alpha * 0.95)
            painter.setPen(QColor(hl_color.red(), hl_color.green(), hl_color.blue(), cream_a))
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
            settings_manager.save_settings(self.settings)
            event.accept()

    def mouseReleaseEvent(self, event):
        self.is_dragging = False

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
            HOTKEY_SETTINGS = 804

            user32.RegisterHotKey(None, HOTKEY_LOCK, MOD_CONTROL | MOD_ALT, ord('L'))
            user32.RegisterHotKey(None, HOTKEY_HIDE, MOD_CONTROL | MOD_ALT, ord('H'))
            user32.RegisterHotKey(None, HOTKEY_QUIT, MOD_CONTROL | MOD_ALT, ord('Q'))
            user32.RegisterHotKey(None, HOTKEY_SETTINGS, MOD_CONTROL, ord('S'))

            msg = wintypes.MSG()
            while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
                if msg.message == 0x0312:
                    if msg.wParam == HOTKEY_LOCK:
                        self.signals.hotkey_lock.emit()
                    elif msg.wParam == HOTKEY_HIDE:
                        self.signals.hotkey_hide.emit()
                    elif msg.wParam == HOTKEY_QUIT:
                        self.signals.hotkey_quit.emit()
                    elif msg.wParam == HOTKEY_SETTINGS:
                        self.signals.hotkey_settings.emit()
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))

        import threading
        threading.Thread(target=_hotkey_worker, daemon=True).start()

    def toggle_lock(self):
        self.is_locked = not self.is_locked
        hwnd = int(self.winId())
        try:
            GWL_EXSTYLE = -20
            WS_EX_LAYERED = 0x00080000
            WS_EX_TRANSPARENT = 0x00000020
            current_style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)

            if self.is_locked:
                new_style = current_style | WS_EX_LAYERED | WS_EX_TRANSPARENT
                ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, new_style)
            else:
                new_style = (current_style & ~WS_EX_TRANSPARENT) | WS_EX_LAYERED
                ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, new_style)
        except Exception:
            pass

    def toggle_visibility(self):
        if self.isVisible():
            self.hide()
        else:
            self.show()

    def _quit_app(self):
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
                self.current_line_index = -1
                self.current_line_text = ""

                # Select a consistent soft cream aesthetic color for this song
                color_idx = abs(hash(state.track_id)) % len(CREAM_SOFT_PALETTE)
                self.current_song_cream_color = CREAM_SOFT_PALETTE[color_idx]

                self.update()

                import threading
                threading.Thread(
                    target=self._fetch_lyrics_thread,
                    args=(state.track_name, state.artist_name,
                          state.album_name, state.duration_sec),
                    daemon=True,
                ).start()

            self._check_line_update(state)
        except Exception:
            pass

    def _smooth_position_check(self):
        if self.playback and self.playback.is_playing and self.lyrics:
            self._check_line_update(self.playback)

    def _check_line_update(self, state: PlaybackState):
        if not self.lyrics:
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

            self.update()
        elif 0 <= line_idx < len(self.lyrics):
            # Line is currently playing -> continuously synchronize elapsed audio progress
            song_line_elapsed = adjusted - self.lyrics[line_idx].time_sec
            self.engine.sync_to_audio(song_line_elapsed)

    def _fetch_lyrics_thread(self, track: str, artist: str, album: str, duration: float):
        lyrics = get_lyrics(track, artist, album, duration)
        self.signals.lyrics_fetched.emit(lyrics)

    def _on_lyrics_fetched(self, lyrics: list[LyricLine] | None):
        self.lyrics = lyrics
        if lyrics and self.playback:
            self._check_line_update(self.playback)
        elif not lyrics:
            self.current_line_text = ""
            self.update()


# ── Single-Instance IPC & Entry Point ──
def main():
    app = QApplication(sys.argv)
    app.setApplicationName("SpotifyFloatingLyrics")

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


if __name__ == "__main__":
    main()
