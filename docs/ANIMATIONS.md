# Animation System & Physics Engine

LyricVibe features a custom 165Hz physics and procedural animation pipeline built directly on top of PyQt6's `QPainter` and hardware-accelerated Direct2D / OpenGL surfaces.

---

## Physics & Interpolation

### 1. High-Precision Timing
Progress is calculated continuously at sub-millisecond precision:
```python
now = time.perf_counter()
t_in = min((now - self.curr_enter_perf) / self.enter_duration, 1.0)
```
Interpolation curves match native monitor refresh rates (60Hz, 120Hz, 144Hz, 165Hz, and 240Hz) without frame jitter.

### 2. Glitch-Free Continuous Lift-Out Physics
Outgoing lines smoothly lift away from the active resting baseline:
- Starts strictly at `0.0px` vertical offset at $t_{out} = 0.0$.
- Interpolates continuously up to `-22.0px` via an exponential easing curve:
  $$\text{offset\_y} = -t_{out}^{1.3} \times 22.0\text{px}$$
- Guarantees zero teleportation, snapping, or text collisions with incoming lines.

### 3. Clamped Directional Motion Blur
Calculates real-time velocity deltas between successive frames:
```python
dt = max(0.003, now_perf - self._prev_blur_perf)
inst_vx = (offset_x - self._prev_blur_ox) / dt
inst_vy = (offset_y - self._prev_blur_oy) / dt
```
- Directional shutter passes trail opposite the movement vector.
- Vector components are clamped strictly to `[-4.0px, +4.0px]` to maintain typographic sharpness and prevent ghost duplicates.
- Blur is dynamically disabled on static fade animations to ensure pure typographic transparency.

---

## Dynamic Animation Library

Animations are selected by adaptive lyric pacing and weighted rarity tiers:

### Common Tier (High Frequency)
- **Scale Fade**: Elegant subtle scale-up from 96% to 100% paired with a clean alpha fade.
- **Slide Up**: Upward glide with cubic deceleration.
- **Word Reveal**: Progressive left-to-right word unveiling timed to syllables.
- **Kinetic Snap**: High-energy explosive entrance with instant snap settle.
- **Drift Dissolve**: Gentle horizontal float with crossfade dissolve.
- **Whisper Dissolve**: Soft floating text entrance with feathered edge transparency.
- **Silky Crossfade**: Multi-pass interpolation between successive lines.

### Uncommon Tier
- **Glow Bloom**: Atmospheric radiant outer halo that expands and settles into resting typography.
- **Cinematic Rise**: Smooth vertical rise from below the screen baseline.
- **Luminous Drift**: Horizontal drift accompanied by soft perimeter luminescence.
- **Subtle Glide**: Pure linear micro-glide into resting position.
- **Hand-Drawn Underline**: Procedural animated accent underline beneath the active line.

### Rare Tier
- **Chromatic Split**: RGB optical prism dispersion separating during entry and resolving into pure white.
- **Shimmer Sweep**: Light reflection highlight sweeping horizontally across typography.
- **Wave Ripple**: Sine wave undulating ripple across individual word baselines.
- **Star Glint**: Procedural sparkle glints shimmering across key letter accents.
- **Elastic Slingshot**: Spring-tensioned slingshot trajectory with gentle damping.

### Very Rare Tier
- **Horizontal Blur Streak**: Extended cinematic anamorphic blur streak trailing rapid motion.
- **Drop Settle**: Overhead gravity drop with realistic elastic bounce settling.
- **Spotlight Halo**: Concentrated soft spotlight tracking the active line.
- **Letter Tracking**: Dynamic letter spacing expanding outward from center.
- **Strobe Pulse**: Crisp rhythmic brightness pulse synchronized to audio transients.

---

## Vibrant Highlight Suite

Highlighted active words are illuminated using an ultra-bright neon palette with automatic per-song rotation:

| Palette Name | Hex Color | Visual Style |
|:---|:---|:---|
| **Mint Emerald** | `#00FF66` | Vibrant Spotify neon green |
| **Electric Cyan** | `#00FFFF` | High-visibility bright aqua cyan |
| **Golden Canary** | `#FFE600` | Warm brilliant solar yellow |
| **Hot Magenta** | `#FF1493` | High-energy neon pink |
| **Neon Violet** | `#B026FF` | Deep electric ultraviolet |
| **Blaze Orange** | `#FF6600` | Bright incandescent amber-orange |
| **Sky Azure** | `#00BFFF` | Vivid electric blue |
| **Spring Lime** | `#39FF14` | High-contrast neon lime |
| **Plasma Pink** | `#FF007F` | Intense electric rose |
| **Hyper Turquoise** | `#40E0D0` | Crisp tropical turquoise |
| **Electric Coral** | `#FF4040` | Saturated punchy coral red |
| **Laser Lemon** | `#FAFF00` | Intense ultra-bright yellow |

### Highlight Modes
- **Auto (Different Bright Color Each Song)**: The overlay hashes the current track ID to select a distinct neon color for every song.
- **Pinned Color**: Pin any single color permanently via the settings panel.
