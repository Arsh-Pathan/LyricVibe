# Release Notes

## LyricVibe v1.1.0 — Windows Setup Installer, 72+ Animations, Multi-Script Transliteration & Custom Color Picker

### New Features & Improvements in v1.1.0
- **Professional Windows Setup Installer**:
  - Added native Windows installer (`LyricVibe-Setup-v1.1.0.exe`) created with Inno Setup 6.
  - Guided setup wizard with options for Desktop shortcut, Start Menu folder, Windows Startup integration, and clean uninstaller registered in Windows Add/Remove programs.
  - Per-user and system-wide installation support without requiring elevation.
- **Expanded 72+ Dynamic Animations Suite & Motion Personality Switcher**:
  - Expanded catalog from 55+ to 72+ animations with custom mathematical easing functions.
  - 15 new animations: `aurora_shimmer`, `nebula_bloom`, `horizon_dawn`, `starlight_glimmer`, `whip_pan_left`, `whip_pan_right`, `bass_drop_shake`, `hyper_zoom`, `laser_etch`, `neon_flicker`, `parabolic_arc`, `prism_refract`, `card_flip_3d`, `isometric_slide`, and `cinema_scope_unfold`.
  - Atmospheric fade animations (`aurora_shimmer`, `nebula_bloom`, `horizon_dawn`, `starlight_glimmer`) integrated into zero-blur transition physics.
  - Added Animation Motion Style preference in Settings (Dynamic Mix, Silky Smooth Fades, Kinetic & Snappy, Cinematic & Expressive 3D, and Vocal & Lyric Flow).
- **8 Curated One-Click Style Presets**:
  - Added dedicated one-click aesthetic style presets in Settings: 7clouds Signature, Cyberpunk Neon, Midnight Emerald, Aesthetic Dream, Crimson Bass, Golden Hour, Tokyo Drift, and Minimalist Pure.
- **Multi-Script Transliteration Suite**:
  - Full native phonetic transliteration for Devanagari (Hindi), Perso-Arabic (Urdu), Gurmukhi (Punjabi), Bengali, Gujarati, Tamil, and Telugu into Latin Roman text.
  - Zero-width character and bidi formatter filtering (ZWNJ, ZWJ, LRM, RLM, BOM) to prevent missing glyph rectangle boxes in brush fonts.
  - Expanded search ranking script detector recognizing all major Indic scripts.
- **Custom Color Picker & Shorthand Hex Formats**:
  - Right-click custom color dialog (`QColorDialog`) and "Custom Color..." dropdown option to pick any color.
  - Shorthand 3-digit (`#RGB`), 6-digit (`#RRGGBB`), and 8-digit (`#AARRGGBB` / `#RRGGBBAA`) hex validation.
  - Added rich darker shades to the palette: Spotify Green (`#1DB954`), Deep Emerald (`#0E8A42`), Crimson (`#D32F2F`), Royal Purple (`#7B1FA2`), Midnight Indigo (`#303F9F`), Midnight Navy (`#1A237E`), Deep Teal (`#00796B`), and Dark Slate (`#263238`).
- **Precision Audio Scrubbing & Snapping**:
  - Instant snap on seek jumps (`|drift| > 0.75s`) with low-pass micro-drift correction.
  - Active line revival when rewinding backward into vocal windows during instrumental pauses.
  - Standard LRC `[offset:+/-ms]` tag parsing and application.
- **Enhanced Metadata Sanitization**:
  - Strips producer tags (`(Prod. ...)`, `[Produced by ...]`), viral modifiers (`(Sped Up)`, `(Nightcore)`, `(Slowed + Reverb)`), and section headers with artist attributions.
  - Split delimiters extended to include `with` and `vs` in artist parsing.
- **Multi-Monitor Screen Coordinate Clamping**:
  - Screen boundary clamping keeps the overlay within viewable display bounds across monitor moves and resolution drops.
  - Dynamic `windowHandle().screenChanged` listener for multi-display setups.
- **Durability & Stress Test Suite**:
  - 93 unit tests validating LRU bounded caches, multi-hour continuous playback, animation categories, easing calculations, and thread safety.

---

## LyricVibe v1.0.0 — Cinematic 165Hz Floating Lyrics Overlay for Spotify

**Real-time synchronized lyrics floating borderless on your screen — no Spotify Premium required.**

---

### Demo Video & Screenshots

<div align="center">
  <a href="https://youtu.be/0j6qynWk0WA" target="_blank" rel="noopener noreferrer">
    <img src="https://raw.githubusercontent.com/Arsh-Pathan/LyricVibe/main/assets/youtube-preview.png" width="100%" alt="Watch LyricVibe Demo on YouTube" />
  </a>
  <p><a href="https://youtu.be/0j6qynWk0WA" target="_blank" rel="noopener noreferrer"><b>Watch Full 1080p 60FPS Video Demonstration on YouTube &rarr;</b></a></p>
</div>

<div align="center">
  <img src="https://raw.githubusercontent.com/Arsh-Pathan/LyricVibe/main/assets/overlay-preview.png" width="100%" alt="Floating Lyrics Overlay" />
  <p><i>Real-time synchronized floating lyrics with active word highlight and smooth continuous physics.</i></p>
</div>

<div align="center">
  <img src="https://raw.githubusercontent.com/Arsh-Pathan/LyricVibe/main/assets/settings-preview.png" width="520" alt="LyricVibe Customization Panel" />
  <p><i>Modern dark-themed customization panel with live preview.</i></p>
</div>

---

### Key Highlights

- **Pure Floating Overlay**: Zero window borders, zero background — only pure typography floating seamlessly on top of your games, browsers, and desktop.
- **No Spotify Premium Required**: Reads playback telemetry via Windows System Media Transport Controls (WinRT SMTC). Works out of the box with Spotify Free and Premium.
- **Zero API Keys & Zero Configuration**: Instant startup without needing Spotify developer tokens or Spotify login credentials.
- **165Hz Fluid Rendering**: Hardware-accelerated PyQt6 rendering at your display's native refresh rate (60Hz–240Hz).
- **Continuous Fade Physics**: 100% glitch-free smooth baseline transitions with zero sudden text snapping or jumps.
- **Versatile Highlight Palette**: Rich darker tones (Spotify Green, Deep Emerald, Crimson, Royal Purple, Midnight Indigo, Deep Teal) and ultra-bright neon colors that rotate automatically per song, or can be chosen via the custom color picker.
- **Universal Multi-Script Transliteration**: Automatically converts Devanagari (Hindi), Perso-Arabic (Urdu), Gurmukhi (Punjabi), Bengali, and Gujarati lyrics into clean Latin Roman text with zero missing glyph boxes.
- **55+ Dynamic Animations**: Scale fades, kinetic snaps, word-by-word reveals, soft glows, and directional motion blur.
- **Smart LRCLIB Matching**: Automatically strips movie suffixes, artist tags, remaster notes, producer credits, and viral modifiers for high-accuracy lyrics lookup.

---

### Installation & Quick Start

#### Standalone Executable (No Python Required)
1. Download `LyricVibe.exe` or `LyricVibe-v1.0.0-Windows.zip` below.
2. Run `LyricVibe.exe`.
3. Play music on Spotify — the lyrics will appear automatically!

#### Global Hotkeys
- **Ctrl + Alt + S** or double-click text: Open Settings Customizer
- **Ctrl + Alt + L**: Lock overlay / click-through mode
- **Ctrl + Alt + H**: Hide / Show overlay
- **Ctrl + Alt + [ / ]**: Adjust audio sync offset (-0.5s / +0.5s)
- **Ctrl + Alt + Q**: Quit overlay
