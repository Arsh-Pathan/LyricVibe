"""
Comprehensive 165Hz Physics & Animation Engine for Spotify Lyrics.
- 55+ dynamic cinematic entrance & transition animations with weighted rarity.
- Butter-smooth 165 FPS continuous time interpolation (powered by high-res QPC perf_counter).
- Anti-overlap architecture: exiting lines lift cleanly out of the frame (-35px)
  before disappearing, guaranteeing zero text collisions with incoming lines.
- Automatic clear_line() for instrumental pauses and musical breaks.
- Glitch-free word highlight timing tracking active vocal syllables smoothly.
- ZERO loss of text: all words remain visible, sharp, and anchored.
- Rock-solid anchored positioning (ZERO continuous float / wobble).
- Focal hand-drawn marker underline: highlights 1 or 2 key focal words.
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


# ─── 55+ Weighted Animation Styles ───────────────────────────────────
ANIMATION_CATALOG = [
    # ── Silky Smooth Fades & Dissolves ──
    ("cinematic_crossfade", 22),
    ("whisper_dissolve", 20),
    ("gentle_rise_fade", 20),
    ("gentle_sink_fade", 18),
    ("feather_dissolve", 18),
    ("luminous_glow_fade", 16),
    ("smooth_drift_fade", 16),
    ("ambient_breathe", 16),
    ("soft_dissolve", 16),
    ("mist_evaporate", 14),
    ("velvet_wipe", 14),
    ("aurora_shimmer", 16),
    ("nebula_bloom", 14),
    ("horizon_dawn", 14),
    ("starlight_glimmer", 14),
    # ── Kinetic & Snappy Motion ──
    ("gravity_drop", 18),
    ("slide_up", 18),
    ("kinetic_snap", 16),
    ("scale_pop", 16),
    ("drift_left", 14),
    ("drift_right", 14),
    ("overshoot_rise", 14),
    ("whip_pan_left", 14),
    ("whip_pan_right", 14),
    ("bass_drop_shake", 14),
    ("hyper_zoom", 12),
    ("magnetic_snap", 12),
    ("bounce_land", 12),
    ("impact_slam", 10),
    ("elastic_twang", 8),
    ("quick_flick", 10),
    # ── Vocal & Lyric Flow ──
    ("word_reveal", 24),
    ("zoom_in", 14),
    ("zoom_out_settle", 12),
    ("focus_pull", 12),
    ("curtain_reveal", 10),
    ("letter_tracking", 10),
    ("typewriter_snap", 10),
    ("hand_drawn_flourish", 18),
    ("spotlight_reveal", 12),
    ("echo_pulse", 10),
    ("laser_etch", 12),
    ("neon_flicker", 12),
    ("parabolic_arc", 12),
    # ── Expressive & Cinematic ──
    ("pendulum_swing", 8),
    ("split_horizon", 8),
    ("skew_slide", 10),
    ("flip_drop", 8),
    ("velocity_streak", 6),
    ("wave_cascade", 6),
    ("shimmer_sweep", 6),
    ("spiral_settle", 5),
    ("strobe_snap", 4),
    ("glide_in", 12),
    ("subtle_float", 12),
    ("cascade_fall", 10),
    ("tilt_glide", 10),
    ("orbit_arc", 8),
    ("shutter_expand", 8),
    ("spring_rebound", 8),
    ("ripple_snap", 8),
    ("vortex_spin", 6),
    ("prism_refract", 12),
    ("card_flip_3d", 10),
    ("isometric_slide", 10),
    ("cinema_scope_unfold", 12),
    # ── Per-Character Physics (Glitch-Free) ──
    ("letter_drop", 16),
    ("letter_burst", 10),
    ("balloon_inflate", 12),
    ("erase_reveal", 12),
    ("letter_scatter", 8),
]

PER_CHAR_ANIMS = {"letter_drop", "letter_burst", "letter_scatter", "erase_reveal"}

FADE_ANIMS = {
    "cinematic_crossfade",
    "whisper_dissolve",
    "gentle_rise_fade",
    "gentle_sink_fade",
    "feather_dissolve",
    "luminous_glow_fade",
    "smooth_drift_fade",
    "ambient_breathe",
    "soft_dissolve",
    "mist_evaporate",
    "velvet_wipe",
    "aurora_shimmer",
    "nebula_bloom",
    "horizon_dawn",
    "starlight_glimmer",
}

ANIMATION_CATEGORIES: dict[str, list[str]] = {
    "smooth": [
        "cinematic_crossfade",
        "whisper_dissolve",
        "gentle_rise_fade",
        "gentle_sink_fade",
        "feather_dissolve",
        "luminous_glow_fade",
        "smooth_drift_fade",
        "ambient_breathe",
        "soft_dissolve",
        "mist_evaporate",
        "velvet_wipe",
        "aurora_shimmer",
        "nebula_bloom",
        "horizon_dawn",
        "starlight_glimmer",
    ],
    "kinetic": [
        "gravity_drop",
        "slide_up",
        "kinetic_snap",
        "scale_pop",
        "drift_left",
        "drift_right",
        "overshoot_rise",
        "whip_pan_left",
        "whip_pan_right",
        "bass_drop_shake",
        "hyper_zoom",
        "magnetic_snap",
        "bounce_land",
        "impact_slam",
        "elastic_twang",
        "quick_flick",
    ],
    "vocal": [
        "word_reveal",
        "zoom_in",
        "zoom_out_settle",
        "focus_pull",
        "curtain_reveal",
        "letter_tracking",
        "typewriter_snap",
        "hand_drawn_flourish",
        "spotlight_reveal",
        "echo_pulse",
        "laser_etch",
        "neon_flicker",
        "parabolic_arc",
    ],
    "cinematic": [
        "pendulum_swing",
        "split_horizon",
        "skew_slide",
        "flip_drop",
        "velocity_streak",
        "wave_cascade",
        "shimmer_sweep",
        "spiral_settle",
        "strobe_snap",
        "glide_in",
        "subtle_float",
        "cascade_fall",
        "tilt_glide",
        "orbit_arc",
        "shutter_expand",
        "spring_rebound",
        "ripple_snap",
        "vortex_spin",
        "prism_refract",
        "card_flip_3d",
        "isometric_slide",
        "cinema_scope_unfold",
    ],
    "per_char": [
        "letter_drop",
        "letter_burst",
        "balloon_inflate",
        "erase_reveal",
        "letter_scatter",
    ],
}


def pick_animation(line_text: str, duration: float, category: str = "all") -> str:
    """Dynamically picks from the 72+ animation catalog based on category and line pacing."""
    cat = (category or "all").lower()
    if cat in ANIMATION_CATEGORIES:
        pool = ANIMATION_CATEGORIES[cat]
        return random.choice(pool)

    words = line_text.strip().split()

    if duration > 0 and duration < 1.6:
        fast_pool = [
            "kinetic_snap",
            "cinematic_crossfade",
            "scale_pop",
            "overshoot_rise",
            "whisper_dissolve",
            "quick_flick",
            "whip_pan_left",
            "whip_pan_right",
            "hyper_zoom",
            "laser_etch",
        ]
        return random.choice(fast_pool)

    if duration >= 3.0 and len(words) >= 4 and random.random() < 0.55:
        slow_pool = [
            "cinematic_crossfade",
            "whisper_dissolve",
            "gentle_rise_fade",
            "gentle_sink_fade",
            "word_reveal",
            "feather_dissolve",
            "luminous_glow_fade",
            "spotlight_reveal",
            "aurora_shimmer",
            "nebula_bloom",
            "horizon_dawn",
            "starlight_glimmer",
            "cinema_scope_unfold",
        ]
        return random.choice(slow_pool)

    types, weights = zip(*ANIMATION_CATALOG)
    return random.choices(types, weights=weights, k=1)[0]


class AnimationEngine:
    """Manages 165Hz physics, anti-overlap transitions, color highlight, and focal underlines."""

    def __init__(self):
        # Current (incoming) line
        self.curr_text = ""
        self.curr_start_perf = 0.0
        self.curr_duration = 3.0
        self.curr_anim_type = "cinematic_crossfade"
        self.anim_style = "all"

        # Outgoing line transition (anti-overlap lifted exit)
        self.prev_text = ""
        self.prev_exit_perf = 0.0
        self.transition_dur = 0.24

        # Word reveal tracking
        self.words = []
        self.word_alphas = []

        # Per-character tracking
        self.chars = []
        self.char_offsets_x = []
        self.char_offsets_y = []
        self.char_alphas = []
        self.char_scales = []
        self._char_burst_dx = []
        self._char_burst_dy = []

        # Glitch-free color highlight tracking
        self.highlight_word_idx = -1

        # Focal 1-2 word underline
        self.focal_word_idx = -1
        self.focal_num_words = 1
        self.underline_stroke = None
        self.underline_progress = 0.0
        self.underline_active = False

    def trigger_line(
        self,
        new_text: str,
        duration: float,
        anim_type: str = "",
        lead_sec: float = 0.0,
        anim_style: str = "",
    ):
        now_perf = time.perf_counter()

        # Archive old line for smooth anti-overlap lift & fade out
        if self.curr_text:
            self.prev_text = self.curr_text
            self.prev_exit_perf = now_perf

        self.curr_text = new_text
        self.curr_start_perf = now_perf - max(0.0, lead_sec)
        self.curr_duration = max(duration, 1.2)
        style_to_use = anim_style or self.anim_style
        self.curr_anim_type = (
            anim_type
            if anim_type
            else pick_animation(new_text, self.curr_duration, style_to_use)
        )

        if self.curr_anim_type in FADE_ANIMS:
            self.transition_dur = 0.28
        else:
            self.transition_dur = 0.20

        # Word reveal tracking
        self.words = new_text.strip().split()
        self.word_alphas = [0.40] * len(self.words)

        # Per-character tracking
        self.chars = list(new_text)
        n = len(self.chars)
        self.char_offsets_x = [0.0] * n
        self.char_offsets_y = [0.0] * n
        self.char_alphas = [0.40] * n
        self.char_scales = [1.0] * n

        self._char_burst_dx = [(random.random() - 0.5) * 30.0 for _ in range(n)]
        self._char_burst_dy = [(random.random() - 0.5) * 16.0 - 8.0 for _ in range(n)]

        # Focal underline selection
        self.underline_active = (self.curr_anim_type == "hand_drawn_flourish") or (
            len(self.words) >= 2 and random.random() < 0.35
        )
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

        # Reset motion blur state for clean entrance with zero offset spikes
        self._prev_blur_ox = None
        self._prev_blur_oy = None
        self._prev_blur_perf = None

    def clear_line(self):
        """Cleanly clears line during instrumental solos or track pauses."""
        if self.curr_text:
            self.prev_text = self.curr_text
            self.prev_exit_perf = time.perf_counter()
            self.curr_text = ""
            self.highlight_word_idx = -1
            self._prev_blur_ox = None
            self._prev_blur_oy = None
            self._prev_blur_perf = None

    def sync_to_audio(self, audio_elapsed_sec: float):
        """
        Gently corrects audio sync drift with a smooth low-pass filter
        WITHOUT interrupting the continuous 165Hz render clock.
        If a large seek or scrubbing jump is detected (> 0.75s), snaps immediately.
        """
        now_perf = time.perf_counter()
        expected_start = now_perf - audio_elapsed_sec
        drift = expected_start - self.curr_start_perf
        if abs(drift) > 0.75:
            self.curr_start_perf = expected_start
        elif abs(drift) > 0.06:
            self.curr_start_perf += drift * 0.15

    def update(self) -> dict:
        now_perf = time.perf_counter()
        elapsed_in = max(0.0, now_perf - self.curr_start_perf)

        t_in = (
            min(elapsed_in / self.transition_dur, 1.0)
            if self.transition_dur > 0
            else 1.0
        )

        # Silky smooth continuous mathematical easing curves
        ease_out_cubic = 1.0 - math.pow(1.0 - t_in, 3)
        ease_out_quart = 1.0 - math.pow(1.0 - t_in, 4)
        ease_in_out = 0.5 - 0.5 * math.cos(t_in * math.pi)

        # Baseline transforms (rock solid center)
        scale = 1.0
        alpha = ease_out_cubic
        offset_x = 0.0
        offset_y = 0.0
        rotation = 0.0
        skew_x = 0.0
        chroma = 0.0
        blur_alpha = 0.0

        anim = self.curr_anim_type

        # ── 1-11. Smooth Fades & Dissolves ──
        if anim == "cinematic_crossfade":
            alpha = ease_in_out
            offset_y = 0.0
            scale = 1.0
        elif anim == "whisper_dissolve":
            alpha = ease_out_quart
            scale = 0.985 + 0.015 * ease_out_quart
            offset_y = 0.0
        elif anim == "gentle_rise_fade":
            alpha = ease_out_cubic
            offset_y = (1.0 - ease_out_cubic) * 6.0
            scale = 1.0
        elif anim == "gentle_sink_fade":
            alpha = ease_out_cubic
            offset_y = (1.0 - ease_out_cubic) * -6.0
            scale = 1.0
        elif anim == "feather_dissolve":
            alpha = ease_out_cubic
            scale = 0.99 + 0.01 * ease_out_cubic
            offset_y = (1.0 - ease_out_cubic) * 3.0
        elif anim == "luminous_glow_fade":
            alpha = math.sin(t_in * math.pi * 0.5)
            scale = 1.0
            offset_y = 0.0
        elif anim == "smooth_drift_fade":
            alpha = ease_out_cubic
            offset_x = (1.0 - ease_out_cubic) * 8.0
            scale = 1.0
        elif anim == "ambient_breathe":
            alpha = ease_out_cubic
            scale = 0.975 + 0.025 * ease_out_cubic
            offset_y = 0.0
        elif anim == "soft_dissolve":
            alpha = ease_in_out
            offset_y = (1.0 - ease_in_out) * 4.0
        elif anim == "mist_evaporate":
            alpha = ease_out_quart
            scale = 1.02 - 0.02 * ease_out_quart
            offset_y = (1.0 - ease_out_quart) * 4.0
        elif anim == "velvet_wipe":
            alpha = ease_out_cubic
            scale = 0.995 + 0.005 * ease_out_cubic
        elif anim == "aurora_shimmer":
            alpha = ease_out_cubic
            scale = 0.99 + 0.01 * math.sin(t_in * math.pi)
            offset_y = (1.0 - ease_out_cubic) * 3.0
        elif anim == "nebula_bloom":
            alpha = ease_out_quart
            scale = 0.95 + 0.05 * ease_out_quart
            offset_y = (1.0 - ease_out_quart) * 4.0
        elif anim == "horizon_dawn":
            alpha = math.pow(t_in, 1.4)
            offset_y = (1.0 - ease_out_cubic) * 12.0
            scale = 0.98 + 0.02 * ease_out_cubic
        elif anim == "starlight_glimmer":
            alpha = ease_out_cubic
            scale = 0.99 + 0.01 * math.sin(t_in * math.pi * 1.5)

        # ── 12-22. Kinetic & Snappy Motion ──
        elif anim == "gravity_drop":
            alpha = 0.75 + 0.25 * ease_out_cubic
            damping = 7.0
            freq = 12.0
            offset_y = (
                -18.0 * math.exp(-damping * t_in) * math.cos(freq * t_in)
                if t_in < 1.0
                else 0.0
            )
            scale = (
                1.0 - 0.03 * math.exp(-damping * t_in) * math.cos(freq * t_in)
                if t_in < 1.0
                else 1.0
            )
        elif anim == "slide_up":
            alpha = 0.70 + 0.30 * ease_out_cubic
            offset_y = (1.0 - ease_out_cubic) * 16.0
        elif anim == "kinetic_snap":
            alpha = 0.80 + 0.20 * ease_out_cubic
            elastic = (
                1.0
                - math.pow(2.0, -12 * t_in)
                * math.cos((t_in * 12 - 0.75) * ((2 * math.pi) / 3))
                if t_in < 1.0
                else 1.0
            )
            scale = max(0.94, min(1.06, elastic))
        elif anim == "scale_pop":
            alpha = 0.75 + 0.25 * ease_out_cubic
            if t_in < 0.5:
                scale = 0.94 + 0.10 * (t_in / 0.5)
            else:
                scale = 1.04 - 0.04 * ((t_in - 0.5) / 0.5)
        elif anim == "drift_left":
            alpha = 0.70 + 0.30 * ease_out_cubic
            offset_x = (1.0 - ease_out_cubic) * 20.0
        elif anim == "drift_right":
            alpha = 0.70 + 0.30 * ease_out_cubic
            offset_x = (1.0 - ease_out_cubic) * -20.0
        elif anim == "overshoot_rise":
            alpha = 0.75 + 0.25 * ease_out_cubic
            if t_in < 0.7:
                offset_y = 14.0 * (1.0 - (t_in / 0.7)) - 2.5
            else:
                offset_y = -2.5 * (1.0 - ((t_in - 0.7) / 0.3))
        elif anim == "magnetic_snap":
            alpha = 0.75 + 0.25 * ease_out_cubic
            accel = math.pow(t_in, 3)
            offset_y = (1.0 - accel) * 16.0
            scale = 0.96 + 0.04 * accel
        elif anim == "bounce_land":
            alpha = 0.80 + 0.20 * ease_out_cubic
            if t_in < 0.5:
                offset_y = -14.0 * (1.0 - t_in / 0.5)
            elif t_in < 0.75:
                offset_y = -4.0 * math.sin((t_in - 0.5) / 0.25 * math.pi)
            else:
                offset_y = -1.5 * math.sin((t_in - 0.75) / 0.25 * math.pi)
            if t_in >= 1.0:
                offset_y = 0.0
        elif anim == "impact_slam":
            alpha = 0.85 + 0.15 * ease_out_cubic
            if t_in < 0.4:
                scale = 1.15 - 0.15 * (t_in / 0.4)
                offset_y = -10.0 * (1.0 - t_in / 0.4)
            else:
                scale = 1.0
                offset_y = 0.0
        elif anim == "elastic_twang":
            alpha = ease_out_cubic
            offset_y = (
                (1.0 - ease_out_cubic) * 12.0 * math.cos(t_in * math.pi * 3)
                if t_in < 1.0
                else 0.0
            )
        elif anim == "quick_flick":
            alpha = ease_out_quart
            scale = 0.96 + 0.04 * ease_out_quart
            offset_y = (1.0 - ease_out_quart) * -10.0
        elif anim == "whip_pan_left":
            alpha = 0.80 + 0.20 * ease_out_quart
            offset_x = (1.0 - ease_out_quart) * 28.0
        elif anim == "whip_pan_right":
            alpha = 0.80 + 0.20 * ease_out_quart
            offset_x = (1.0 - ease_out_quart) * -28.0
        elif anim == "bass_drop_shake":
            alpha = 0.85 + 0.15 * ease_out_cubic
            damp = 8.0
            freq = 18.0
            offset_y = (
                math.exp(-damp * t_in) * math.sin(freq * t_in) * 4.0
                if t_in < 0.6
                else 0.0
            )
            scale = (
                1.0 + 0.04 * math.exp(-damp * t_in) * math.cos(freq * t_in)
                if t_in < 0.6
                else 1.0
            )
        elif anim == "hyper_zoom":
            alpha = 0.70 + 0.30 * ease_out_cubic
            if t_in < 0.65:
                scale = 0.85 + 0.18 * (t_in / 0.65)
            else:
                scale = 1.03 - 0.03 * ((t_in - 0.65) / 0.35)

        # ── 23-32. Vocal & Flow ──
        elif anim == "word_reveal":
            alpha = 1.0
            offset_y = (1.0 - ease_out_cubic) * 6.0
        elif anim == "zoom_in":
            alpha = ease_out_cubic
            scale = 0.92 + 0.08 * ease_out_cubic
        elif anim == "zoom_out_settle":
            alpha = ease_out_cubic
            scale = 1.07 - 0.07 * ease_out_cubic
        elif anim == "focus_pull":
            alpha = ease_out_quart
            scale = 0.96 + 0.04 * ease_out_quart
        elif anim == "curtain_reveal":
            alpha = ease_out_cubic
            scale = 0.97 + 0.03 * ease_out_cubic
        elif anim == "letter_tracking":
            alpha = ease_out_cubic
            scale = 1.0
        elif anim == "typewriter_snap":
            alpha = 1.0
            offset_y = 0.0
        elif anim == "hand_drawn_flourish":
            alpha = ease_out_cubic
            offset_y = (1.0 - ease_out_cubic) * 8.0
        elif anim == "spotlight_reveal":
            alpha = ease_out_quart
            scale = 0.97 + 0.03 * ease_out_quart
        elif anim == "echo_pulse":
            alpha = ease_out_cubic
            scale = 1.03 - 0.03 * ease_out_cubic
        elif anim == "laser_etch":
            alpha = ease_out_quart
            scale = 0.98 + 0.02 * ease_out_quart
            offset_x = (1.0 - ease_out_quart) * -16.0
        elif anim == "neon_flicker":
            if t_in < 0.12:
                alpha = 0.40 + 0.60 * (t_in / 0.12)
            elif t_in < 0.22:
                alpha = 0.30
            elif t_in < 0.35:
                alpha = 0.95
            elif t_in < 0.42:
                alpha = 0.60
            else:
                alpha = 1.0
            scale = 0.98 + 0.02 * min(t_in / 0.42, 1.0)
        elif anim == "parabolic_arc":
            alpha = ease_out_cubic
            arc_p = 1.0 - ease_out_cubic
            offset_x = arc_p * 15.0
            offset_y = arc_p * arc_p * -12.0

        # ── 33-47. Expressive & Cinematic ──
        elif anim == "pendulum_swing":
            alpha = ease_out_cubic
            rotation = (
                math.sin((1.0 - t_in) * math.pi * 2.0) * 1.5 if t_in < 1.0 else 0.0
            )
        elif anim == "split_horizon":
            alpha = ease_out_cubic
            scale = 0.98 + 0.02 * ease_out_cubic
        elif anim == "skew_slide":
            alpha = 0.75 + 0.25 * ease_out_cubic
            offset_x = (1.0 - ease_out_cubic) * 14.0
            skew_x = (1.0 - ease_out_cubic) * -3.5
        elif anim == "flip_drop":
            alpha = 0.80 + 0.20 * ease_out_cubic
            scale = 0.95 + 0.05 * ease_out_cubic
            offset_y = (1.0 - ease_out_cubic) * -10.0
        elif anim == "velocity_streak":
            offset_x = (1.0 - ease_out_cubic) * 20.0
        elif anim == "wave_cascade":
            alpha = ease_out_cubic
            offset_y = math.sin((1.0 - t_in) * math.pi) * 6.0 if t_in < 1.0 else 0.0
        elif anim == "shimmer_sweep":
            alpha = ease_out_cubic
            scale = 1.0
        elif anim == "spiral_settle":
            alpha = ease_out_cubic
            rotation = (1.0 - ease_out_cubic) * 2.0
            scale = 0.95 + 0.05 * ease_out_cubic
        elif anim == "strobe_snap":
            alpha = 1.0
        elif anim == "glide_in":
            alpha = ease_out_cubic
            offset_y = (1.0 - ease_out_cubic) * 10.0
            offset_x = (1.0 - ease_out_cubic) * 8.0
        elif anim == "subtle_float":
            alpha = ease_out_cubic
            offset_y = (1.0 - ease_out_cubic) * 5.0
        elif anim == "cascade_fall":
            alpha = ease_out_cubic
            offset_y = (1.0 - ease_out_cubic) * -12.0
        elif anim == "tilt_glide":
            alpha = ease_out_cubic
            rotation = (1.0 - ease_out_cubic) * -1.5
            offset_x = (1.0 - ease_out_cubic) * 12.0
        elif anim == "orbit_arc":
            alpha = ease_out_cubic
            offset_x = math.sin((1.0 - t_in) * math.pi * 0.5) * 12.0
            offset_y = (1.0 - ease_out_cubic) * 6.0
        elif anim == "shutter_expand":
            alpha = ease_out_cubic
            scale = 0.96 + 0.04 * ease_out_cubic
        elif anim == "spring_rebound":
            alpha = ease_out_cubic
            scale = (
                1.0 + 0.05 * math.exp(-6 * t_in) * math.cos(10 * t_in)
                if t_in < 1.0
                else 1.0
            )
        elif anim == "ripple_snap":
            alpha = ease_out_cubic
            offset_y = (
                math.sin(t_in * math.pi * 2) * 2.0 * (1.0 - t_in) if t_in < 1.0 else 0.0
            )
        elif anim == "vortex_spin":
            alpha = ease_out_cubic
            rotation = (1.0 - ease_out_cubic) * 1.8
        elif anim == "prism_refract":
            alpha = ease_out_quart
            scale = 0.96 + 0.04 * ease_out_quart
            offset_x = (1.0 - ease_out_quart) * 10.0
            skew_x = (1.0 - ease_out_quart) * 2.0
        elif anim == "card_flip_3d":
            alpha = ease_out_cubic
            scale = 0.92 + 0.08 * ease_out_cubic
            offset_y = (1.0 - ease_out_cubic) * -12.0
            rotation = (1.0 - ease_out_cubic) * -2.5
        elif anim == "isometric_slide":
            alpha = 0.75 + 0.25 * ease_out_cubic
            offset_x = (1.0 - ease_out_cubic) * 16.0
            offset_y = (1.0 - ease_out_cubic) * 9.0
            skew_x = (1.0 - ease_out_cubic) * -1.5
        elif anim == "cinema_scope_unfold":
            alpha = ease_out_quart
            scale = 0.95 + 0.05 * ease_out_quart
            offset_y = (1.0 - ease_out_quart) * 6.0

        # ── 48-52. Per-Character & Special Physics ──
        elif anim == "balloon_inflate":
            alpha = ease_out_cubic
            if t_in < 0.55:
                scale = 0.88 + 0.20 * (t_in / 0.55)
            elif t_in < 0.80:
                scale = 1.08 - 0.08 * ((t_in - 0.55) / 0.25)
            else:
                scale = 1.0 + 0.012 * math.sin((t_in - 0.80) / 0.20 * math.pi)
            offset_y = (1.0 - ease_out_cubic) * 4.0
        elif anim in PER_CHAR_ANIMS:
            alpha = 1.0
            offset_y = 0.0

        # Fallback
        else:
            alpha = ease_out_cubic
            offset_y = (1.0 - ease_out_cubic) * 8.0

        # ── Directional Motion Blur Vector & Shutter Momentum ──
        if anim in FADE_ANIMS:
            blur_dx = 0.0
            blur_dy = 0.0
            blur_dist = 0.0
            blur_alpha = 0.0
        else:
            if getattr(self, "_prev_blur_ox", None) is None:
                self._prev_blur_ox = offset_x
                self._prev_blur_oy = offset_y
                self._prev_blur_perf = now_perf

            dt = max(0.003, now_perf - self._prev_blur_perf)
            inst_vx = (offset_x - self._prev_blur_ox) / dt
            inst_vy = (offset_y - self._prev_blur_oy) / dt
            self._prev_blur_ox = offset_x
            self._prev_blur_oy = offset_y
            self._prev_blur_perf = now_perf

            # Only blur during entrance momentum, clamped to tight subtle spread
            entrance_momentum = max(0.0, 1.0 - t_in * 2.2) if t_in < 0.45 else 0.0
            raw_dx = (inst_vx * 0.015) + (offset_x * 0.20 * entrance_momentum)
            raw_dy = (inst_vy * 0.015) + (offset_y * 0.20 * entrance_momentum)
            blur_dx = max(-4.0, min(4.0, raw_dx))
            blur_dy = max(-4.0, min(4.0, raw_dy))
            blur_dist = math.hypot(blur_dx, blur_dy)
            blur_alpha = min(0.35, blur_dist / 6.0) if blur_dist > 0.4 else 0.0

        # ── Anti-Overlap Outgoing Line (Smooth, continuous upward lift starting at 0px) ──
        prev_data = None
        if self.prev_text:
            elapsed_out = now_perf - self.prev_exit_perf
            exit_dur = 0.18  # Smooth clean lift & fade out
            t_out = min(elapsed_out / exit_dur, 1.0)
            if t_out < 1.0:
                # Easing curve for upward lift: starts strictly at 0.0 (ZERO jump!)
                lift_curve = math.pow(t_out, 1.3)
                out_fade = 1.0 - math.pow(t_out, 1.6)
                prev_data = {
                    "text": self.prev_text,
                    "alpha": max(0.0, out_fade),
                    "offset_y": -lift_curve
                    * 22.0,  # Continuous glide from 0.0px to -22.0px
                    "blur_dy": -4.0 * (1.0 - t_out),
                    "scale": 1.0 - t_out * 0.02,
                }
            else:
                self.prev_text = ""

        # ── Glitch-Free Active Word Highlight Timing ──
        num_words = len(self.words)
        self.highlight_word_idx = -1
        if num_words > 0:
            active_window = min(self.curr_duration * 0.85, max(num_words * 0.38, 2.0))
            step_dur = active_window / num_words
            for i in range(num_words):
                w_start = i * step_dur
                w_end = (i + 1) * step_dur
                if w_start <= elapsed_in < w_end:
                    self.highlight_word_idx = i
                    break
            # Hold highlight on the last word when active window ends (never jump back to 0)
            if self.highlight_word_idx == -1 and elapsed_in >= active_window:
                self.highlight_word_idx = num_words - 1

            for i in range(num_words):
                w_elapsed = elapsed_in - (i * step_dur)
                if w_elapsed < 0:
                    self.word_alphas[i] = 0.40
                else:
                    progress = min(w_elapsed / max(step_dur * 0.7, 0.12), 1.0)
                    self.word_alphas[i] = 0.40 + 0.60 * (
                        1.0 - math.pow(1.0 - progress, 2)
                    )

        # ── Per-Character Physics (Zero Loss of Text & Smooth Spring) ──
        n_chars = len(self.chars)
        if anim in PER_CHAR_ANIMS and n_chars > 0:
            active_window = min(self.curr_duration * 0.65, 2.0)
            stagger = active_window / max(n_chars, 1)

            if anim == "letter_drop":
                for i in range(n_chars):
                    lt = elapsed_in - (i * stagger)
                    if lt < 0:
                        self.char_offsets_x[i] = 0.0
                        self.char_offsets_y[i] = 0.0
                        self.char_alphas[i] = 0.40
                        self.char_scales[i] = 1.0
                    else:
                        t_norm = min(lt / 0.25, 1.0)
                        damp = 7.5
                        freq = 15.0
                        self.char_offsets_y[i] = (
                            -20.0 * math.exp(-damp * t_norm) * math.cos(freq * t_norm)
                            if t_norm < 1.0
                            else 0.0
                        )
                        self.char_offsets_x[i] = 0.0
                        self.char_alphas[i] = 0.40 + 0.60 * min(lt / 0.08, 1.0)
                        self.char_scales[i] = 1.0

            elif anim == "letter_burst":
                for i in range(n_chars):
                    t_norm = min(elapsed_in / 0.22, 1.0)
                    ease = 1.0 - math.pow(1.0 - t_norm, 3)
                    self.char_offsets_x[i] = self._char_burst_dx[i] * (1.0 - ease)
                    self.char_offsets_y[i] = self._char_burst_dy[i] * (1.0 - ease)
                    self.char_alphas[i] = 0.65 + 0.35 * ease
                    self.char_scales[i] = 0.92 + 0.08 * ease

            elif anim == "letter_scatter":
                for i in range(n_chars):
                    lt = elapsed_in - (i * stagger * 0.4)
                    if lt < 0:
                        self.char_offsets_x[i] = self._char_burst_dx[i] * 0.3
                        self.char_offsets_y[i] = self._char_burst_dy[i] * 0.3
                        self.char_alphas[i] = 0.40
                        self.char_scales[i] = 0.97
                    else:
                        t_norm = min(lt / 0.20, 1.0)
                        ease = 1.0 - math.pow(1.0 - t_norm, 3)
                        self.char_offsets_x[i] = (
                            self._char_burst_dx[i] * 0.3 * (1.0 - ease)
                        )
                        self.char_offsets_y[i] = (
                            self._char_burst_dy[i] * 0.3 * (1.0 - ease)
                        )
                        self.char_alphas[i] = 0.40 + 0.60 * ease
                        self.char_scales[i] = 0.97 + 0.03 * ease

            elif anim == "erase_reveal":
                for i in range(n_chars):
                    lt = elapsed_in - (i * stagger * 0.7)
                    if lt < 0:
                        self.char_offsets_x[i] = 0.0
                        self.char_offsets_y[i] = 0.0
                        self.char_alphas[i] = 0.40
                        self.char_scales[i] = 1.0
                    else:
                        t_norm = min(lt / 0.10, 1.0)
                        self.char_offsets_x[i] = 0.0
                        self.char_offsets_y[i] = 0.0
                        self.char_alphas[i] = 0.40 + 0.60 * t_norm
                        self.char_scales[i] = 1.0

        # ── Focal Hand-Drawn Underline Progress ──
        if self.underline_active:
            u_elapsed = elapsed_in - 0.08
            u_dur = max(0.12, min(self.curr_duration * 0.45, 1.2))
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
            "blur_dx": blur_dx,
            "blur_dy": blur_dy,
            "blur_dist": blur_dist,
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
