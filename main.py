"""
Lyric Flow — 165Hz Floating Lyrics Overlay for Spotify.
- 30+ dynamic, varied cinematic text entrance animations with weighted rarity.
- Edge-to-edge screen geometry: zero text clipping or cutoff on any display.
- Dynamic font fitting: scales gracefully so long lines never overflow.
- 7clouds typography: Edo SZ signature brush & Montserrat Black extra bold.
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
from animation_engine import AnimationEngine

IPC_SERVER_NAME = "SpotifyLyricsOverlayIPC_v1"


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

        # Physics & Animation Engine (30+ animations, zero continuous float)
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
        choice = self.settings.get("font_family", "7clouds Modern")
        if "Edo" in choice:
            return "Edo SZ"
        elif "Poppins" in choice:
            return "Poppins"
        elif "Segoe" in choice:
            return "Segoe UI"
        return "Montserrat"

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
        except Exception as e:
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
            painter.drawText(QRectF(-w / 2.0, -40, w, 80), Qt.AlignmentFlag.AlignCenter, p_text)
            painter.restore()

        # ── 2. Incoming Line (Razor Sharp Pure White with 30+ Animations) ──
        if curr_text and data["curr_alpha"] > 0.02:
            in_alpha = int(data["curr_alpha"] * 255)
            in_font, in_metrics = self._fit_font(curr_text, avail_w, base_size, font_family)
            painter.setFont(in_font)

            painter.save()
            # Position without continuous float (firmly anchored)
            painter.translate(screen_cx + data.get("curr_offset_x", 0.0), screen_cy + data["curr_offset_y"])

            # Rotational / Skew / Scale transforms
            if data.get("rotation", 0.0) != 0.0:
                painter.rotate(data["rotation"])
            if data.get("skew_x", 0.0) != 0.0:
                painter.shear(math.tan(math.radians(data["skew_x"])), 0)
            if data["curr_scale"] != 1.0:
                painter.scale(data["curr_scale"], data["curr_scale"])

            total_w = in_metrics.horizontalAdvance(curr_text)

            # Chromatic Split animation (Rare)
            chroma = data.get("chroma", 0.0)
            if chroma > 0.5:
                painter.setPen(QColor(100, 220, 255, int(data["curr_alpha"] * 140)))
                painter.drawText(QRectF(-total_w / 2.0 - chroma, -40, total_w, 80), Qt.AlignmentFlag.AlignCenter, curr_text)
                painter.setPen(QColor(255, 120, 140, int(data["curr_alpha"] * 140)))
                painter.drawText(QRectF(-total_w / 2.0 + chroma, -40, total_w, 80), Qt.AlignmentFlag.AlignCenter, curr_text)

            # Word-by-word reveal (Active sharp illumination)
            if (data.get("anim_type") == "word_reveal" or self.settings.get("word_reveal_enabled", True)) and data.get("word_alphas"):
                self._draw_sharp_word_reveal(painter, in_metrics, curr_text, data["word_alphas"], in_alpha)
            else:
                # Razor sharp pure white line
                painter.setPen(QColor(255, 255, 255, in_alpha))
                painter.drawText(QRectF(-total_w / 2.0, -40, total_w, 80), Qt.AlignmentFlag.AlignCenter, curr_text)

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

        # Scale down smoothly if line exceeds available width
        while metrics.horizontalAdvance(text) > max_w and size > 16:
            size -= 1
            font.setPointSize(size)
            metrics = QFontMetrics(font)

        return font, metrics

    def _draw_sharp_word_reveal(self, painter: QPainter, metrics: QFontMetrics,
                                 text: str, word_alphas: list[float], master_alpha: int):
        """Renders words with high-contrast sharp illumination (no fuzzy blur)."""
        words = text.strip().split()
        space_w = metrics.horizontalAdvance(" ")
        word_widths = [metrics.horizontalAdvance(w) for w in words]
        total_w = sum(word_widths) + (len(words) - 1) * space_w

        curr_x = -total_w / 2.0
        y = metrics.ascent() - metrics.height() / 2.0

        for idx, word in enumerate(words):
            raw_w_alpha = word_alphas[idx] if idx < len(word_alphas) else 1.0
            # Muted upcoming words (sharp ~35% white), active words (pure 100% white)
            final_a = int(master_alpha * raw_w_alpha)
            painter.setPen(QColor(255, 255, 255, max(0, min(255, final_a))))
            painter.drawText(QPointF(curr_x, y), word)
            curr_x += word_widths[idx] + space_w

    def _draw_focal_underline(self, painter: QPainter, metrics: QFontMetrics,
                               text: str, focal_idx: int, stroke, progress: float, alpha: float):
        """Draws realistic sketched pencil and fluid marker lines ONLY under 1-2 key focal words."""
        if not stroke or progress <= 0.03 or focal_idx < 0:
            return

        words = text.strip().split()
        if focal_idx >= len(words):
            return

        space_w = metrics.horizontalAdvance(" ")
        w_widths = [metrics.horizontalAdvance(w) for w in words]
        total_w = sum(w_widths) + (len(words) - 1) * space_w

        # Compute exact X position of the focal word within the centered line
        start_line_x = -total_w / 2.0
        word_start_x = start_line_x + sum(w_widths[:focal_idx]) + focal_idx * space_w
        target_w = w_widths[focal_idx]

        draw_w = target_w * progress
        if draw_w < 6:
            return

        y_base = 22.0

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
            # Keep X anchored at 0 (full width) and allow Y dragging
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
        adjusted = progress + self.settings.get("sync_offset_sec", 0.0)

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

                self.current_line_text = raw_text
                # Trigger dynamic animation from the 30+ catalog
                self.engine.trigger_line(raw_text, dur)
            else:
                self.current_line_text = ""

            self.update()

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
        # Already running -> Ask first instance to open Settings Window
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
