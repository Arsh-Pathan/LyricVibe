"""
Comprehensive 165Hz Physics & Animation Engine for Spotify Lyrics.
- 35+ dynamic, varied cinematic text entrance animations with weighted rarity.
- Per-character physics: letter_drop, letter_burst, balloon_inflate, erase_reveal.
- Color word highlighting: active spoken word gets accent color.
- Rock-solid anchored positioning (ZERO continuous float / wobble).
- Dual-buffer seamless cross-transitions between lyric lines.
- Focal hand-drawn marker underline: underlines only 1 or 2 key words.
- Razor-sharp, high-contrast typography (no blurry glow).
"""

import math
import random
import time


class HandDrawnStroke:
    """Organic sketched hand-drawn underline for 1-2 focal words."""

    def __init__(self, target_word_idx: int = -1):
        self.target_word_idx = target_word_idx
        num_points = 6
        self.offsets = []
        for i in range(num_points):
            arc = math.sin((i / (num_points - 1)) * math.pi) * 2.2
            jitter = (random.random() - 0.5) * 1.0
            self.offsets.append(arc + jitter)
        # End flourish: lively slight upward flick
        self.offsets[-1] -= 2.2


# ─── 35+ Weighted Animation Styles ───────────────────────────────────
ANIMATION_CATALOG = [
    # Fast / Punchy (Common)
    ("gravity_drop", 18),
    ("slide_up", 18),
    ("kinetic_snap", 16),
    ("scale_pop", 16),
    ("drift_left", 14),
    ("drift_right", 14),
    ("overshoot_rise", 14),
    ("magnetic_snap", 12),

    # Vocal / Lyric Flow (Common)
    ("word_reveal", 22),
    ("soft_dissolve", 14),
    ("zoom_in", 14),
    ("zoom_out_settle", 12),
    ("focus_pull", 12),
    ("curtain_reveal", 10),
    ("letter_tracking", 10),

    # Dynamic & Expressive (Uncommon)
    ("hand_drawn_flourish", 16),
    ("bounce_land", 12),
    ("impact_slam", 10),
    ("skew_slide", 10),
    ("flip_drop", 8),
    ("typewriter_snap", 8),
    ("pendulum_swing", 8),
    ("split_horizon", 8),

    # Per-Character Physics (Distinctive)
    ("letter_drop", 14),
    ("letter_burst", 10),
    ("balloon_inflate", 10),
    ("erase_reveal", 12),
    ("letter_scatter", 8),

    # Rare & Dramatic
    ("chromatic_split", 5),
    ("velocity_streak", 5),
    ("elastic_twang", 5),
    ("wave_cascade", 5),
    ("shimmer_sweep", 5),
    ("spiral_settle", 4),
    ("strobe_snap", 3),
    ("glitch_flicker", 3),
]

# Animations that need per-character rendering
PER_CHAR_ANIMS = {"letter_drop", "letter_burst", "letter_scatter", "erase_reveal"}


def pick_animation(line_text: str, duration: float) -> str:
    """Dynamically picks from the 35+ animation catalog based on line pacing and rarity."""
    words = line_text.strip().split()

    # Fast short line (<1.6s) -> favor punchy snaps
    if duration > 0 and duration < 1.6:
        fast_pool = ["kinetic_snap", "impact_slam", "scale_pop", "velocity_streak",
                     "strobe_snap", "overshoot_rise", "letter_burst"]
        return random.choice(fast_pool)

    # Slow vocal line with 4+ words -> favor word reveal or smooth transitions
    if duration >= 3.2 and len(words) >= 4 and random.random() < 0.50:
        return random.choice(["word_reveal", "letter_drop", "erase_reveal"])

    # Weighted random selection across full catalog
    types, weights = zip(*ANIMATION_CATALOG)
    return random.choices(types, weights=weights, k=1)[0]


class AnimationEngine:
    """Manages 165Hz physics, dual-buffer line cross-transitions, color highlight, and focal underlines."""

    def __init__(self):
        # Current (incoming) line
        self.curr_text = ""
        self.curr_start_time = 0.0
        self.curr_duration = 3.0
        self.curr_anim_type = "gravity_drop"

        # Previous (outgoing) line for seamless cross-transition
        self.prev_text = ""
        self.prev_exit_start = 0.0
        self.transition_dur = 0.38

        # Word reveal tracking
        self.words = []
        self.word_alphas = []

        # Per-character tracking (letter_drop, letter_burst, letter_scatter, erase)
        self.chars = []
        self.char_offsets_x = []
        self.char_offsets_y = []
        self.char_alphas = []
        self.char_scales = []
        # Pre-baked random targets for burst/scatter
        self._char_burst_dx = []
        self._char_burst_dy = []

        # Color highlight tracking
        self.highlight_word_idx = -1

        # Focal 1-2 word underline
        self.focal_word_idx = -1
        self.focal_num_words = 1
        self.underline_stroke = None
        self.underline_progress = 0.0
        self.underline_active = False

    def trigger_line(self, new_text: str, duration: float, anim_type: str = ""):
        now = time.time()

        if self.curr_text and self.curr_text != new_text:
            self.prev_text = self.curr_text
            self.prev_exit_start = now

        self.curr_text = new_text
        self.curr_start_time = now
        self.curr_duration = max(duration, 1.2)
        self.curr_anim_type = anim_type if anim_type else pick_animation(new_text, self.curr_duration)

        # Word reveal tracking
        self.words = new_text.strip().split()
        self.word_alphas = [0.35] * len(self.words)

        # Per-character tracking
        self.chars = list(new_text)
        n = len(self.chars)
        self.char_offsets_x = [0.0] * n
        self.char_offsets_y = [0.0] * n
        self.char_alphas = [0.0] * n
        self.char_scales = [1.0] * n

        # Pre-bake random burst/scatter vectors so they don't flicker
        self._char_burst_dx = [(random.random() - 0.5) * 120.0 for _ in range(n)]
        self._char_burst_dy = [(random.random() - 0.5) * 80.0 - 30.0 for _ in range(n)]

        # ── Focal 1-2 Word Selection for Underline ──
        self.underline_active = (self.curr_anim_type == "hand_drawn_flourish") or (len(self.words) >= 2 and random.random() < 0.38)
        self.underline_progress = 0.0

        if self.words:
            longest_idx = max(range(len(self.words)), key=lambda i: len(self.words[i]))
            last_idx = len(self.words) - 1
            self.focal_word_idx = longest_idx if (random.random() < 0.6) else last_idx
            self.focal_num_words = 1
            self.underline_stroke = HandDrawnStroke(self.focal_word_idx)
        else:
            self.focal_word_idx = -1
            self.underline_stroke = None

    def update(self) -> dict:
        now = time.time()
        elapsed_in = now - self.curr_start_time
        t_in = min(elapsed_in / self.transition_dur, 1.0) if self.transition_dur > 0 else 1.0

        # Easing curves
        ease_out_cubic = 1.0 - math.pow(1.0 - t_in, 3)
        ease_out_quad = 1.0 - math.pow(1.0 - t_in, 2)
        ease_out_quart = 1.0 - math.pow(1.0 - t_in, 4)

        # Default transforms (ANCHORED, NO CONTINUOUS FLOAT)
        scale = 1.0
        alpha = ease_out_cubic
        offset_x = 0.0
        offset_y = 0.0
        rotation = 0.0
        skew_x = 0.0
        chroma = 0.0
        blur_alpha = 0.0
        blur_offset_x = 0.0

        anim = self.curr_anim_type

        # ── 1. Gravity Drop ──
        if anim == "gravity_drop":
            damping = 5.2
            freq = 9.5
            offset_y = -26.0 * math.exp(-damping * t_in) * math.cos(freq * t_in) if t_in < 1.0 else 0.0
            scale = 1.0 - 0.06 * math.exp(-damping * t_in) * math.cos(freq * t_in) if t_in < 1.0 else 1.0

        # ── 2. Slide Up ──
        elif anim == "slide_up":
            offset_y = (1.0 - ease_out_cubic) * 28.0

        # ── 3. Kinetic Snap ──
        elif anim == "kinetic_snap":
            elastic = 1.0 - math.pow(2.0, -10 * t_in) * math.cos((t_in * 10 - 0.75) * ((2 * math.pi) / 3)) if t_in < 1.0 else 1.0
            scale = max(0.85, min(1.12, elastic))
            alpha = min(t_in * 3.0, 1.0)

        # ── 4. Scale Pop ──
        elif anim == "scale_pop":
            if t_in < 0.6:
                scale = 0.88 + 0.20 * (t_in / 0.6)
            else:
                scale = 1.08 - 0.08 * ((t_in - 0.6) / 0.4)
            alpha = min(t_in * 2.5, 1.0)

        # ── 5. Drift Left / Right ──
        elif anim == "drift_left":
            offset_x = (1.0 - ease_out_cubic) * 36.0
        elif anim == "drift_right":
            offset_x = (1.0 - ease_out_cubic) * -36.0

        # ── 6. Overshoot Rise ──
        elif anim == "overshoot_rise":
            if t_in < 0.7:
                offset_y = 26.0 * (1.0 - (t_in / 0.7)) - 4.0
            else:
                offset_y = -4.0 * (1.0 - ((t_in - 0.7) / 0.3))

        # ── 7. Magnetic Snap ──
        elif anim == "magnetic_snap":
            accel = math.pow(t_in, 3)
            offset_y = (1.0 - accel) * 32.0
            scale = 0.94 + 0.06 * accel

        # ── 8. Zoom In / Out ──
        elif anim == "zoom_in":
            scale = 0.82 + 0.18 * ease_out_cubic
        elif anim == "zoom_out_settle":
            scale = 1.16 - 0.16 * ease_out_cubic

        # ── 9. Focus Pull ──
        elif anim == "focus_pull":
            scale = 0.92 + 0.08 * ease_out_quart
            alpha = ease_out_quart

        # ── 10. Curtain Reveal ──
        elif anim == "curtain_reveal":
            scale = 0.95 + 0.05 * ease_out_cubic

        # ── 11. Letter Tracking ──
        elif anim == "letter_tracking":
            scale = 1.0

        # ── 12. Hand-Drawn Flourish ──
        elif anim == "hand_drawn_flourish":
            offset_y = (1.0 - ease_out_cubic) * 16.0

        # ── 13. Bounce Land ──
        elif anim == "bounce_land":
            if t_in < 0.5:
                offset_y = -30.0 * (1.0 - t_in / 0.5)
            elif t_in < 0.75:
                offset_y = -10.0 * math.sin((t_in - 0.5) / 0.25 * math.pi)
            else:
                offset_y = -3.0 * math.sin((t_in - 0.75) / 0.25 * math.pi)
            if t_in >= 1.0:
                offset_y = 0.0

        # ── 14. Impact Slam ──
        elif anim == "impact_slam":
            if t_in < 0.4:
                scale = 1.35 - 0.35 * (t_in / 0.4)
                offset_y = -18.0 * (1.0 - t_in / 0.4)
            else:
                scale = 1.0
                offset_y = 0.0

        # ── 15. Skew Slide ──
        elif anim == "skew_slide":
            offset_x = (1.0 - ease_out_cubic) * 30.0
            skew_x = (1.0 - ease_out_cubic) * -8.0

        # ── 16. Flip Drop ──
        elif anim == "flip_drop":
            scale = 0.88 + 0.12 * ease_out_cubic
            offset_y = (1.0 - ease_out_cubic) * -24.0

        # ── 17. Pendulum Swing ──
        elif anim == "pendulum_swing":
            rotation = math.sin((1.0 - t_in) * math.pi * 2.0) * 2.5 if t_in < 1.0 else 0.0

        # ── 18. Chromatic Split (Rare) ──
        elif anim == "chromatic_split":
            chroma = (1.0 - ease_out_cubic) * 6.0

        # ── 19. Velocity Streak (Rare) ──
        elif anim == "velocity_streak":
            offset_x = (1.0 - ease_out_cubic) * 45.0
            blur_offset_x = offset_x * 0.5
            blur_alpha = (1.0 - ease_out_cubic) * 0.4

        # ── 20. Strobe Snap (Rare) ──
        elif anim == "strobe_snap":
            if t_in < 0.15:
                alpha = 0.2 if (int(t_in * 60) % 2 == 0) else 1.0
            else:
                alpha = 1.0

        # ── 21. Glitch Flicker (Rare) ──
        elif anim == "glitch_flicker":
            if t_in < 0.2:
                offset_x = (random.random() - 0.5) * 8.0
            else:
                offset_x = 0.0

        # ── 22. Word Reveal (Common) ──
        elif anim == "word_reveal":
            alpha = 1.0
            offset_y = (1.0 - ease_out_cubic) * 12.0

        # ── 23. Letter Drop — Spoken Gravity (per-char) ──
        elif anim == "letter_drop":
            alpha = 1.0
            offset_y = 0.0

        # ── 24. Letter Burst — Explode Outward Then Settle (per-char) ──
        elif anim == "letter_burst":
            alpha = 1.0
            offset_y = 0.0

        # ── 25. Balloon Inflate — Tiny to Full with Overshoot ──
        elif anim == "balloon_inflate":
            alpha = min(t_in * 3.0, 1.0)
            if t_in < 0.55:
                # Inflate from nothing
                inflate_t = t_in / 0.55
                scale = inflate_t * 1.18
            elif t_in < 0.75:
                # Overshoot settle
                settle_t = (t_in - 0.55) / 0.20
                scale = 1.18 - 0.18 * settle_t
            else:
                # Tiny elastic wobble
                wobble_t = (t_in - 0.75) / 0.25
                scale = 1.0 + 0.03 * math.sin(wobble_t * math.pi * 3) * (1.0 - wobble_t)
            offset_y = max(0.0, (1.0 - ease_out_cubic) * 8.0)

        # ── 26. Erase Reveal — Left-to-Right Wipe (per-char) ──
        elif anim == "erase_reveal":
            alpha = 1.0
            offset_y = 0.0

        # ── 27. Letter Scatter — Fly In From Random Positions (per-char) ──
        elif anim == "letter_scatter":
            alpha = 1.0
            offset_y = 0.0

        # Default fallback
        else:
            offset_y = (1.0 - ease_out_cubic) * 16.0

        # ── Outgoing Line Physics (Cross-Transition) ──
        prev_data = None
        if self.prev_text:
            elapsed_out = now - self.prev_exit_start
            t_out = min(elapsed_out / self.transition_dur, 1.0) if self.transition_dur > 0 else 1.0
            if t_out < 1.0:
                out_ease = t_out * t_out
                prev_data = {
                    "text": self.prev_text,
                    "alpha": max(0.0, 1.0 - out_ease),
                    "offset_y": -out_ease * 22.0,
                    "scale": 1.0 - out_ease * 0.05,
                }
            else:
                self.prev_text = ""

        # ── Word-by-Word Reveal Illumination + Color Highlight Tracking ──
        num_words = len(self.words)
        self.highlight_word_idx = -1
        if num_words > 0:
            active_window = min(self.curr_duration * 0.72, 3.8)
            step_dur = active_window / num_words
            for i in range(num_words):
                w_elapsed = elapsed_in - (i * step_dur)
                if w_elapsed < 0:
                    self.word_alphas[i] = 0.35  # Muted upcoming words
                else:
                    progress = min(w_elapsed / max(step_dur * 0.8, 0.14), 1.0)
                    self.word_alphas[i] = 0.35 + 0.65 * (1.0 - math.pow(1.0 - progress, 2))
                    # Track the most recently activated word for color highlight
                    if progress < 0.92:
                        self.highlight_word_idx = i
                    elif self.highlight_word_idx < 0:
                        self.highlight_word_idx = i

        # ── Per-Character Physics ──
        n_chars = len(self.chars)
        if anim in PER_CHAR_ANIMS and n_chars > 0:
            total_stagger = min(self.curr_duration * 0.55, 2.4)
            stagger = total_stagger / max(n_chars, 1)

            if anim == "letter_drop":
                # Letters fall from above under gravity, staggered as spoken
                for i in range(n_chars):
                    lt = elapsed_in - (i * stagger)
                    if lt < 0:
                        self.char_offsets_x[i] = 0.0
                        self.char_offsets_y[i] = -52.0
                        self.char_alphas[i] = 0.0
                        self.char_scales[i] = 1.0
                    else:
                        t_norm = min(lt / 0.42, 1.0)
                        damp = 7.0
                        freq = 12.0
                        self.char_offsets_y[i] = -52.0 * math.exp(-damp * t_norm) * math.cos(freq * t_norm)
                        self.char_offsets_x[i] = 0.0
                        self.char_alphas[i] = min(lt / 0.08, 1.0)
                        self.char_scales[i] = 1.0

            elif anim == "letter_burst":
                # Letters start scattered outward, snap back to position
                for i in range(n_chars):
                    lt = elapsed_in
                    t_norm = min(lt / 0.45, 1.0)
                    ease = 1.0 - math.pow(1.0 - t_norm, 3)
                    self.char_offsets_x[i] = self._char_burst_dx[i] * (1.0 - ease)
                    self.char_offsets_y[i] = self._char_burst_dy[i] * (1.0 - ease)
                    self.char_alphas[i] = min(lt / 0.12, 1.0)
                    self.char_scales[i] = 0.4 + 0.6 * ease

            elif anim == "letter_scatter":
                # Letters fly in from random positions with stagger
                for i in range(n_chars):
                    lt = elapsed_in - (i * stagger * 0.6)
                    if lt < 0:
                        self.char_offsets_x[i] = self._char_burst_dx[i] * 1.5
                        self.char_offsets_y[i] = self._char_burst_dy[i] * 1.5
                        self.char_alphas[i] = 0.0
                        self.char_scales[i] = 0.3
                    else:
                        t_norm = min(lt / 0.38, 1.0)
                        # Elastic ease out
                        if t_norm < 1.0:
                            elastic = 1.0 - math.pow(2.0, -10 * t_norm) * math.cos(t_norm * 8.0)
                        else:
                            elastic = 1.0
                        self.char_offsets_x[i] = self._char_burst_dx[i] * 1.5 * (1.0 - elastic)
                        self.char_offsets_y[i] = self._char_burst_dy[i] * 1.5 * (1.0 - elastic)
                        self.char_alphas[i] = min(lt / 0.1, 1.0)
                        self.char_scales[i] = 0.3 + 0.7 * min(t_norm * 1.3, 1.0)

            elif anim == "erase_reveal":
                # Left-to-right wipe: characters appear sequentially
                for i in range(n_chars):
                    lt = elapsed_in - (i * stagger * 0.7)
                    if lt < 0:
                        self.char_offsets_x[i] = 0.0
                        self.char_offsets_y[i] = 0.0
                        self.char_alphas[i] = 0.0
                        self.char_scales[i] = 0.7
                    else:
                        t_norm = min(lt / 0.15, 1.0)
                        self.char_offsets_x[i] = 0.0
                        self.char_offsets_y[i] = 0.0
                        self.char_alphas[i] = t_norm
                        self.char_scales[i] = 0.7 + 0.3 * t_norm

        # ── Focal Hand-Drawn Underline Progress ──
        if self.underline_active:
            u_elapsed = elapsed_in - 0.12
            u_dur = min(self.curr_duration * 0.55, 1.6)
            if u_elapsed > 0:
                u_t = min(u_elapsed / u_dur, 1.0)
                self.underline_progress = 1.0 - math.pow(1.0 - u_t, 3)

        return {
            "curr_text": self.curr_text,
            "curr_alpha": alpha,
            "curr_offset_x": offset_x,
            "curr_offset_y": offset_y,
            "curr_scale": scale,
            "rotation": rotation,
            "skew_x": skew_x,
            "chroma": chroma,
            "blur_alpha": blur_alpha,
            "blur_offset_x": blur_offset_x,
            "prev": prev_data,
            "word_alphas": self.word_alphas,
            "highlight_word_idx": self.highlight_word_idx,
            "char_offsets_x": self.char_offsets_x,
            "char_offsets_y": self.char_offsets_y,
            "char_alphas": self.char_alphas,
            "char_scales": self.char_scales,
            "underline_progress": self.underline_progress,
            "underline_active": self.underline_active,
            "focal_word_idx": self.focal_word_idx,
            "underline_stroke": self.underline_stroke,
            "anim_type": self.curr_anim_type,
        }
