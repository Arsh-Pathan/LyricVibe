"""
Advanced 165Hz Physics & Animation Engine for Spotify Lyrics.
- Spring-damper gravity physics with organic momentum and natural settling.
- Seamless dual-buffer cross-transitions between lyric lines (no abrupt cuts).
- Realistic multi-stroke hand-drawn brush/marker underlines with pressure variation.
- Razor-sharp word-by-word reveal (high-contrast active illumination, no blurry glow).
- Organic zero-gravity continuous breathing float.
"""

import math
import random
import time


class HandDrawnStroke:
    """Generates an organic, sketched hand-drawn underline path with natural tremors and pressure."""

    def __init__(self, width: float):
        self.width = max(width, 40.0)
        # Generate random organic hand tremors along the stroke
        num_points = 8
        self.offsets = []
        for i in range(num_points):
            # Slight natural hand jitter (±1.5px) with subtle downward arc
            arc = math.sin((i / (num_points - 1)) * math.pi) * 2.8
            jitter = (random.random() - 0.5) * 1.2
            self.offsets.append(arc + jitter)
        # End flourish: slight expressive upward flick
        self.offsets[-1] -= 2.0


class AnimationEngine:
    """
    Manages 165Hz physics, dual-buffer cross-transitions, gravity damping,
    and hand-drawn flourishes.
    """

    def __init__(self):
        # Current (incoming) line
        self.curr_text = ""
        self.curr_start_time = 0.0
        self.curr_duration = 3.0
        self.curr_anim_type = "gravity_float"

        # Previous (outgoing) line for seamless cross-transition
        self.prev_text = ""
        self.prev_exit_start = 0.0
        self.transition_dur = 0.42  # Cross-fade / transition overlap duration

        # Word reveal tracking
        self.words = []
        self.word_alphas = []

        # Hand-drawn underline state
        self.underline_stroke = None
        self.underline_progress = 0.0
        self.underline_active = False

        # Spring-damper physics variables (Gravity mode)
        self.gravity_offset_y = 0.0
        self.gravity_scale = 1.0

    def trigger_line(self, new_text: str, duration: float, anim_type: str = "gravity_float"):
        """Called when a new lyric line is activated."""
        now = time.time()

        # Archive previous line for cross-transition
        if self.curr_text and self.curr_text != new_text:
            self.prev_text = self.curr_text
            self.prev_exit_start = now

        self.curr_text = new_text
        self.curr_start_time = now
        self.curr_duration = max(duration, 1.2)
        self.curr_anim_type = anim_type

        # Word reveal initialization
        self.words = new_text.strip().split()
        self.word_alphas = [0.35] * len(self.words)

        # Underline trigger (randomly flourishes on key lines or when requested)
        self.underline_active = (anim_type == "hand_drawn_underline") or (len(self.words) >= 3 and random.random() < 0.35)
        self.underline_progress = 0.0
        self.underline_stroke = HandDrawnStroke(400)

    def update(self) -> dict:
        """
        Calculates per-frame 165Hz physics transformations for both
        incoming and outgoing lines.
        """
        now = time.time()
        elapsed_in = now - self.curr_start_time
        t_in = min(elapsed_in / self.transition_dur, 1.0) if self.transition_dur > 0 else 1.0

        # ── 1. Gravity Spring-Damper Physics (Entrance) ──
        # Formula: y(t) = A * e^(-damping * t) * cos(freq * t)
        damping = 5.2
        freq = 9.5
        spring_y = -24.0 * math.exp(-damping * t_in) * math.cos(freq * t_in)
        spring_scale = 1.0 - 0.08 * math.exp(-damping * t_in) * math.cos(freq * t_in)

        # Continuous gentle buoyancy float during singing
        float_y = math.sin(now * 2.2) * 1.8

        in_alpha = min(t_in * 1.6, 1.0)
        in_offset_y = spring_y + float_y
        in_scale = spring_scale

        # ── 2. Outgoing Line Physics (Cross-transition Exit) ──
        prev_data = None
        if self.prev_text:
            elapsed_out = now - self.prev_exit_start
            t_out = min(elapsed_out / self.transition_dur, 1.0) if self.transition_dur > 0 else 1.0
            if t_out < 1.0:
                # Outgoing line gently floats upward and smoothly fades out
                out_ease = t_out * t_out  # Quadratic acceleration out
                prev_data = {
                    "text": self.prev_text,
                    "alpha": max(0.0, 1.0 - out_ease),
                    "offset_y": -out_ease * 20.0 + float_y,
                    "scale": 1.0 - out_ease * 0.04,
                }
            else:
                self.prev_text = ""

        # ── 3. Word-by-Word Reveal Illumination ──
        num_words = len(self.words)
        if num_words > 0:
            # Reveal words progressively across 75% of the line duration
            active_window = min(self.curr_duration * 0.75, 4.0)
            step_dur = active_window / num_words
            for i in range(num_words):
                w_elapsed = elapsed_in - (i * step_dur)
                if w_elapsed < 0:
                    self.word_alphas[i] = 0.35  # Clean muted white for upcoming words
                else:
                    progress = min(w_elapsed / max(step_dur * 0.8, 0.15), 1.0)
                    # Smooth ease from 0.35 to 1.0
                    self.word_alphas[i] = 0.35 + 0.65 * (1.0 - math.pow(1.0 - progress, 2))

        # ── 4. Hand-Drawn Underline Sweep ──
        if self.underline_active:
            # Starts drawing after words land (0.15s in)
            u_elapsed = elapsed_in - 0.15
            u_dur = min(self.curr_duration * 0.6, 1.8)
            if u_elapsed > 0:
                u_t = min(u_elapsed / u_dur, 1.0)
                # Cubic ease for natural pen speed
                self.underline_progress = 1.0 - math.pow(1.0 - u_t, 3)

        return {
            "curr_text": self.curr_text,
            "curr_alpha": in_alpha,
            "curr_offset_y": in_offset_y,
            "curr_scale": in_scale,
            "prev": prev_data,
            "word_alphas": self.word_alphas,
            "underline_progress": self.underline_progress,
            "underline_active": self.underline_active,
            "underline_stroke": self.underline_stroke,
            "anim_type": self.curr_anim_type,
        }
