"""
Spotify Floating Lyrics Overlay — 165Hz Cinematic Edition.
- Liquid 165 Hz hardware-accelerated rendering.
- 7clouds Montserrat / Poppins typography in pure white (#FFFFFF).
- 18 weighted animation styles (motion blur, word reveals, hand-drawn underlines, glow).
- Single-instance IPC: running the app twice opens the Settings Window.
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
    QPainter, QColor, QFont, QFontDatabase, QPen,
    QPainterPath, QTransform, QIcon
)
from PyQt6.QtNetwork import QLocalServer, QLocalSocket

import settings_manager
from settings_window import SettingsDialog
from spotify_client import SpotifyClient, PlaybackState
from lyrics_fetcher import get_lyrics, LyricLine
from animation_engine import pick_animation_type, AnimationState

IPC_SERVER_NAME = "SpotifyLyricsOverlayIPC_v1"


class AppSignals(QObject):
    """Thread-safe signal bridge between background worker threads and PyQt6 GUI."""
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
        self.line_start_time = 0.0
        self.line_duration = 3.0

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

        # Animation Engine
        self.anim = AnimationState()

        # Load 7clouds Fonts (Montserrat & Poppins)
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

        # Positioning at top of screen
        screen = QApplication.primaryScreen()
        screen_geo = screen.availableGeometry() if screen else self.screen().geometry()
        self.window_w = min(1400, screen_geo.width() - 40)
        self.window_h = 160
        self.window_x = (screen_geo.width() - self.window_w) // 2
        self.window_y = self.settings.get("overlay_y", 55)
        self.setGeometry(self.window_x, self.window_y, self.window_w, self.window_h)

        # 165 Hz Render Timer
        fps = self.settings.get("target_fps", 165)
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
        f1 = resolve_asset_path(os.path.join("fonts", "Montserrat.ttf"))
        f2 = resolve_asset_path(os.path.join("fonts", "Poppins-Bold.ttf"))
        if os.path.exists(f1):
            QFontDatabase.addApplicationFont(f1)
        if os.path.exists(f2):
            QFontDatabase.addApplicationFont(f2)

    def apply_settings(self, new_settings: dict):
        self.settings.update(new_settings)
        # Update FPS
        fps = self.settings.get("target_fps", 165)
        interval_ms = max(4, int(1000.0 / fps))
        self.render_timer.setInterval(interval_ms)
        # Update Y-position
        self.window_y = self.settings.get("overlay_y", 55)
        self.move(self.x(), self.window_y)
        self.update()

    def open_settings_window(self):
        if self.settings_dialog is None:
            self.settings_dialog = SettingsDialog(self.settings, None)
            self.settings_dialog.settings_changed.connect(self.apply_settings)
            self.settings_dialog.quit_requested.connect(self._quit_app)
        self.settings_dialog.show()
        self.settings_dialog.raise_()
        self.settings_dialog.activateWindow()

    # ── Paint Engine (165 FPS Hardware Accelerated) ──
    def paintEvent(self, event):
        if not self.current_line_text:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        # Compute animation frame parameters
        anim_data = self.anim.update()

        center_x = self.width() / 2.0
        center_y = self.height() / 2.0 + anim_data["offset_y"]
        scale = anim_data["scale"]
        alpha = anim_data["alpha"]

        # Font configuration (Montserrat / 7clouds style)
        font_size = self.settings.get("font_size", 42)
        font = QFont("Montserrat", font_size, QFont.Weight.Bold)
        font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
        painter.setFont(font)

        # ── 1. Motion Blur Layer (if enabled) ──
        if self.settings.get("motion_blur_enabled", True) and anim_data["blur_alpha"] > 0.02:
            blur_a = int(anim_data["blur_alpha"] * 180)
            blur_color = QColor(255, 255, 255, blur_a)
            painter.setPen(blur_color)

            # Draw two ghosted sub-frames
            for mult in (0.5, 1.0):
                gx = center_x + anim_data["blur_offset_x"] * mult
                gy = center_y + anim_data["blur_offset_y"] * mult
                rect_ghost = QRectF(gx - 600, gy - 50, 1200, 100)
                painter.drawText(rect_ghost, Qt.AlignmentFlag.AlignCenter, self.current_line_text)

        # ── 2. Vocal Glow / Bloom (if enabled) ──
        if self.settings.get("glow_enabled", True) and alpha > 0.1:
            glow_radius = anim_data["glow_radius"]
            glow_alpha = int(alpha * (50 + min(glow_radius, 40)))
            glow_color = QColor(255, 255, 255, min(glow_alpha, 90))
            painter.setPen(glow_color)

            # Multi-pass soft bloom halo
            for r in (2, 4):
                for dx, dy in ((-r, 0), (r, 0), (0, -r), (0, r)):
                    glow_rect = QRectF(center_x + dx - 600, center_y + dy - 50, 1200, 100)
                    painter.drawText(glow_rect, Qt.AlignmentFlag.AlignCenter, self.current_line_text)

        # ── 3. Chromatic Aberration Split (Rare Animation) ──
        if anim_data["chroma"] > 0.5:
            c = anim_data["chroma"]
            painter.setPen(QColor(100, 220, 255, int(alpha * 140)))
            painter.drawText(QRectF(center_x - c - 600, center_y - 50, 1200, 100),
                             Qt.AlignmentFlag.AlignCenter, self.current_line_text)
            painter.setPen(QColor(255, 120, 140, int(alpha * 140)))
            painter.drawText(QRectF(center_x + c - 600, center_y - 50, 1200, 100),
                             Qt.AlignmentFlag.AlignCenter, self.current_line_text)

        # ── 4. Main Pure White Text Layer ──
        main_alpha = int(alpha * 255)
        text_color = QColor(255, 255, 255, max(0, min(255, main_alpha)))
        painter.setPen(text_color)

        painter.save()
        painter.translate(center_x, center_y)
        if scale != 1.0:
            painter.scale(scale, scale)

        rect_main = QRectF(-600, -50, 1200, 100)

        # Word-by-word reveal rendering
        if (anim_data["anim_type"] == "word_reveal" and
                self.settings.get("word_reveal_enabled", True) and
                anim_data["word_alphas"]):
            self._draw_word_reveal(painter, font, anim_data["word_alphas"])
        else:
            painter.drawText(rect_main, Qt.AlignmentFlag.AlignCenter, self.current_line_text)

        painter.restore()

        # ── 5. Hand-Drawn Underline Effect ──
        if (self.settings.get("hand_drawn_underline_enabled", True) and
                anim_data["underline_progress"] > 0.0):
            self._draw_hand_drawn_underline(painter, center_x, center_y, anim_data["underline_progress"], alpha)

        # ── 6. Star Glints (Rare Animation) ──
        if anim_data["anim_type"] == "star_glint" and anim_data["stars"]:
            self._draw_star_glints(painter, center_x, center_y, anim_data["stars"], alpha)

    def _draw_word_reveal(self, painter: QPainter, font: QFont, word_alphas: list[float]):
        """Renders words with individualized progressive alpha & vocal illumination."""
        metrics = painter.fontMetrics()
        words = self.current_line_text.strip().split()
        space_w = metrics.horizontalAdvance(" ")
        word_widths = [metrics.horizontalAdvance(w) for w in words]
        total_w = sum(word_widths) + (len(words) - 1) * space_w

        curr_x = -total_w / 2.0
        y = metrics.ascent() - metrics.height() / 2.0

        for idx, word in enumerate(words):
            w_alpha = word_alphas[idx] if idx < len(word_alphas) else 1.0
            col = QColor(255, 255, 255, int(w_alpha * 255))
            painter.setPen(col)
            painter.drawText(QPointF(curr_x, y), word)
            curr_x += word_widths[idx] + space_w

    def _draw_hand_drawn_underline(self, painter: QPainter, cx: float, cy: float, progress: float, alpha: float):
        """Draws an organic, curved hand-drawn chalk/brush underline."""
        metrics = painter.fontMetrics()
        text_w = min(metrics.horizontalAdvance(self.current_line_text), 900)
        start_x = cx - text_w / 2.0
        target_w = text_w * progress

        if target_w <= 4:
            return

        pen = QPen(QColor(255, 255, 255, int(alpha * 210)), 2.8)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)

        path = QPainterPath()
        path.moveTo(start_x, cy + 32)
        mid_x = start_x + target_w / 2.0
        end_x = start_x + target_w
        path.quadTo(mid_x, cy + 35, end_x, cy + 33)

        painter.drawPath(path)

    def _draw_star_glints(self, painter: QPainter, cx: float, cy: float, stars: list[dict], alpha: float):
        metrics = painter.fontMetrics()
        text_w = min(metrics.horizontalAdvance(self.current_line_text), 900)
        left = cx - text_w / 2.0

        now = time.time()
        for s in stars:
            glint_x = left + text_w * s["pos_x"]
            glint_y = cy + s["y_offset"]
            sparkle_alpha = int(alpha * (math.sin(now * 8.0 + s["phase"]) * 0.5 + 0.5) * 220)

            if sparkle_alpha > 15:
                painter.setPen(QPen(QColor(255, 255, 255, sparkle_alpha), 1.5))
                painter.drawLine(QPointF(glint_x - 3, glint_y), QPointF(glint_x + 3, glint_y))
                painter.drawLine(QPointF(glint_x, glint_y - 3), QPointF(glint_x, glint_y + 3))

    # ── Mouse Dragging & Double Click for Settings ──
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and not self.is_locked:
            self.is_dragging = True
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self.is_dragging and not self.is_locked:
            self.move(event.globalPosition().toPoint() - self.drag_position)
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

        # Find line
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
                # Compute duration of this line
                next_time = self.lyrics[line_idx + 1].time_sec if (line_idx + 1 < len(self.lyrics)) else state.duration_sec
                dur = max(next_time - self.lyrics[line_idx].time_sec, 1.5)

                self.current_line_text = raw_text
                self.line_duration = dur

                # Trigger dynamic animation
                anim_type = pick_animation_type(raw_text, dur)
                self.anim.trigger(anim_type, raw_text, dur)
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
