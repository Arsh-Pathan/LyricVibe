"""
High-Performance 165Hz Animation Engine for Spotify Lyrics.
Supports 18 distinct cinematic animation types with weighted rarity,
motion blur streaks, word-by-word reveals, harmonic ripples, and hand-drawn underlines.
"""

import math
import random
import time

# Animation types with their distribution weights (Common vs Rare)
ANIMATION_WEIGHTS = [
    ("scale_fade", 22),              # Common
    ("slide_up", 20),                # Common
    ("word_reveal", 20),             # Common
    ("kinetic_snap", 18),            # Common for punchy lines
    ("drift_dissolve", 15),          # Common
    ("glow_bloom", 14),              # Uncommon
    ("hand_drawn_underline", 14),    # Uncommon
    ("chromatic_split", 6),          # Rare
    ("shimmer_sweep", 6),            # Rare
    ("wave_ripple", 6),              # Rare
    ("star_glint", 5),               # Rare
    ("elastic_slingshot", 5),        # Rare
    ("horizontal_blur_streak", 5),   # Rare
    ("drop_settle", 4),              # Rare
    ("spotlight_halo", 4),           # Rare
    ("letter_tracking", 4),          # Rare
    ("strobe_pulse", 2),             # Very Rare
    ("smooth_crossfade", 10),        # Classic
]


def pick_animation_type(line_text: str, duration: float) -> str:
    """Selects an animation type dynamically based on line pacing and weighted rarity."""
    words = line_text.strip().split()
    # Fast sudden line -> favor kinetic / snap / blur streak
    if duration > 0 and duration < 1.6:
        fast_choices = ["kinetic_snap", "horizontal_blur_streak", "strobe_pulse", "scale_fade"]
        return random.choice(fast_choices)

    # Slow vocal line with 4+ words -> favor word reveal or smooth float
    if duration >= 3.0 and len(words) >= 4 and random.random() < 0.65:
        return "word_reveal"

    # Weighted random selection across full catalog
    types, weights = zip(*ANIMATION_WEIGHTS)
    return random.choices(types, weights=weights, k=1)[0]


class AnimationState:
    """Tracks state and easing mathematics for the active line at 165 FPS."""

    def __init__(self):
        self.anim_type = "scale_fade"
        self.start_time = 0.0
        self.duration_sec = 0.45       # Transition duration
        self.progress = 1.0            # 0.0 -> 1.0 transition progress
        self.line_duration = 4.0       # Total duration of current lyric line
        self.line_start_time = 0.0

        # Motion Blur vector
        self.blur_offset_x = 0.0
        self.blur_offset_y = 0.0
        self.blur_alpha = 0.0

        # Word Reveal tracking
        self.words = []
        self.word_alphas = []

        # Underline drawing progress (0.0 to 1.0)
        self.underline_progress = 0.0

        # Shimmer position (-1.0 to 2.0 across text width)
        self.shimmer_pos = 0.0

        # Chromatic split distance
        self.chroma_offset = 0.0

        # Glint stars
        self.stars = []

    def trigger(self, anim_type: str, line_text: str, line_duration: float):
        self.anim_type = anim_type
        self.start_time = time.time()
        self.line_start_time = self.start_time
        self.line_duration = max(line_duration, 1.5)
        self.progress = 0.0

        # Transition duration based on anim type
        if anim_type in ("kinetic_snap", "strobe_pulse"):
            self.duration_sec = 0.32
        elif anim_type in ("word_reveal",):
            self.duration_sec = min(self.line_duration * 0.85, 3.5)
        else:
            self.duration_sec = 0.42

        # Initialize word reveal data
        self.words = line_text.strip().split()
        self.word_alphas = [0.0] * len(self.words)

        # Underline
        self.underline_progress = 0.0

        # Star glints (positions across width: 0.1 to 0.9)
        self.stars = [
            {"pos_x": random.uniform(0.15, 0.85), "y_offset": random.uniform(-14, 14), "phase": random.uniform(0, 6.28)}
            for _ in range(3)
        ]

    def update(self) -> dict:
        """Called on every 165Hz frame (every ~6ms). Computes real-time transformations."""
        now = time.time()
        elapsed = now - self.start_time
        t = min(elapsed / self.duration_sec, 1.0) if self.duration_sec > 0 else 1.0
        self.progress = t

        # Cubic Ease-Out curve for ultra-smooth 165Hz deceleration
        # formula: 1 - (1 - t)^3
        ease_out = 1.0 - math.pow(1.0 - t, 3)
        # Elastic Out curve for bounce/snap
        elastic = 1.0 - math.pow(2.0, -10 * t) * math.cos((t * 10 - 0.75) * ((2 * math.pi) / 3)) if t < 1.0 else 1.0

        # Default transforms
        scale = 1.0
        alpha = min(t * 1.8, 1.0)
        offset_x = 0.0
        offset_y = 0.0
        glow_radius = 0.0
        chroma = 0.0
        wave_time = now * 6.0

        # ── 1. Scale & Fade ──
        if self.anim_type == "scale_fade":
            scale = 0.92 + 0.08 * ease_out
            alpha = ease_out
            self.blur_offset_y = (1.0 - ease_out) * -8.0
            self.blur_alpha = (1.0 - ease_out) * 0.35

        # ── 2. Slide Up ──
        elif self.anim_type == "slide_up":
            offset_y = (1.0 - ease_out) * 26.0
            alpha = ease_out
            self.blur_offset_y = offset_y * 0.4
            self.blur_alpha = (1.0 - ease_out) * 0.4

        # ── 3. Kinetic Snap & Bounce ──
        elif self.anim_type == "kinetic_snap":
            scale = 1.15 - (0.15 * ease_out) if t > 0.3 else (0.8 + 0.35 * (t / 0.3))
            alpha = min(t * 3.0, 1.0)
            self.blur_offset_x = math.sin(t * 20.0) * (1.0 - ease_out) * 4.0
            self.blur_alpha = (1.0 - ease_out) * 0.3

        # ── 4. Drift & Dissolve ──
        elif self.anim_type == "drift_dissolve":
            offset_x = (1.0 - ease_out) * -35.0
            alpha = ease_out
            self.blur_offset_x = (1.0 - ease_out) * -12.0
            self.blur_alpha = (1.0 - ease_out) * 0.35

        # ── 5. Glow Bloom ──
        elif self.anim_type == "glow_bloom":
            alpha = ease_out
            scale = 0.96 + 0.04 * ease_out
            # Bloom pulse
            glow_radius = math.sin(t * math.pi) * 22.0 + (math.sin(now * 3.5) * 3.0)

        # ── 6. Hand-Drawn Underline ──
        elif self.anim_type == "hand_drawn_underline":
            alpha = ease_out
            # Underline sweeps smoothly across from left to right
            self.underline_progress = min(max((elapsed - 0.1) / 0.5, 0.0), 1.0)

        # ── 7. Chromatic Split ──
        elif self.anim_type == "chromatic_split":
            alpha = ease_out
            scale = 0.95 + 0.05 * ease_out
            chroma = (1.0 - ease_out) * 7.0  # RGB split distance in pixels

        # ── 8. Shimmer Sweep ──
        elif self.anim_type == "shimmer_sweep":
            alpha = ease_out
            self.shimmer_pos = -0.3 + (now - self.start_time) * 1.8

        # ── 9. Wave Ripple ──
        elif self.anim_type == "wave_ripple":
            alpha = ease_out
            # Handled per character in drawing

        # ── 10. Star Glint ──
        elif self.anim_type == "star_glint":
            alpha = ease_out
            scale = 0.96 + 0.04 * ease_out

        # ── 11. Elastic Slingshot ──
        elif self.anim_type == "elastic_slingshot":
            scale = max(0.5, elastic)
            alpha = min(t * 2.5, 1.0)
            self.blur_offset_y = (1.0 - t) * 15.0
            self.blur_alpha = (1.0 - t) * 0.3

        # ── 12. Horizontal Blur Streak ──
        elif self.anim_type == "horizontal_blur_streak":
            offset_x = (1.0 - ease_out) * 45.0
            alpha = ease_out
            self.blur_offset_x = offset_x * 0.65
            self.blur_alpha = (1.0 - ease_out) * 0.55

        # ── 13. Drop & Settle ──
        elif self.anim_type == "drop_settle":
            offset_y = (1.0 - ease_out) * -28.0
            alpha = ease_out
            self.blur_offset_y = offset_y * 0.4
            self.blur_alpha = (1.0 - ease_out) * 0.3

        # ── 14. Spotlight Halo ──
        elif self.anim_type == "spotlight_halo":
            alpha = ease_out
            glow_radius = 16.0 + math.sin(now * 4.0) * 4.0

        # ── 15. Strobe Pulse ──
        elif self.anim_type == "strobe_pulse":
            if t < 0.12:
                alpha = 0.2 if (int(t * 60) % 2 == 0) else 1.0
                scale = 1.08
            else:
                alpha = 1.0
                scale = 1.0 + (0.08 * (1.0 - t))

        # ── 16. Word Reveal ──
        elif self.anim_type == "word_reveal":
            alpha = 1.0
            num_words = len(self.words)
            if num_words > 0:
                word_step = self.duration_sec / num_words
                for i in range(num_words):
                    w_t = (elapsed - (i * word_step)) / max(word_step, 0.15)
                    self.word_alphas[i] = min(max(w_t, 0.22), 1.0)

        # ── 17. Letter Tracking / Expansion ──
        elif self.anim_type == "letter_tracking":
            alpha = ease_out

        # ── 18. Smooth Crossfade ──
        else:
            alpha = ease_out

        return {
            "scale": scale,
            "alpha": alpha,
            "offset_x": offset_x,
            "offset_y": offset_y,
            "glow_radius": glow_radius,
            "chroma": chroma,
            "wave_time": wave_time,
            "blur_offset_x": self.blur_offset_x,
            "blur_offset_y": self.blur_offset_y,
            "blur_alpha": self.blur_alpha,
            "underline_progress": self.underline_progress,
            "shimmer_pos": self.shimmer_pos,
            "word_alphas": self.word_alphas,
            "anim_type": self.anim_type,
            "stars": self.stars,
            "progress": self.progress,
        }
