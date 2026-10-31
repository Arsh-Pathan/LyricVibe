<p align="center">
  <img src="icon.svg" width="100" height="100" alt="LyricVibe Logo" />
</p>

<h1 align="center">LyricVibe</h1>

<p align="center">
  <b>Cinematic 165Hz Floating Lyrics Overlay for Spotify</b><br>
  <i>Real-time synchronized lyrics floating borderless on your screen — no Spotify Premium required.</i>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Platform-Windows%2010%2F11-0078D6?logo=windows&logoColor=white" alt="Windows" />
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/Framerate-165Hz%20Fluid-00C853" alt="165Hz" />
  <img src="https://img.shields.io/badge/Release-v1.0.0-blue" alt="Release" />
  <img src="https://img.shields.io/badge/License-MIT-green" alt="License" />
</p>

---

## Demo Video

<p align="center">
  <a href="https://youtu.be/0j6qynWk0WA" target="_blank" rel="noopener noreferrer">
    <img src="assets/youtube-preview.png" alt="LyricVibe Demo Video on YouTube" width="100%" />
  </a>
</p>

<p align="center">
  <a href="https://youtu.be/0j6qynWk0WA" target="_blank" rel="noopener noreferrer">
    <b>Watch the Full 1080p 60FPS Demonstration on YouTube &rarr;</b>
  </a>
</p>

<p align="center">
  <img src="assets/demo.gif" alt="LyricVibe Live Animation Preview" width="100%" />
</p>

---

## Screenshots

<p align="center">
  <b>Synchronized Floating Overlay</b><br>
  <img src="assets/overlay-preview.png" width="100%" alt="LyricVibe Floating Lyrics Overlay" />
</p>

<p align="center">
  <b>Modern Customizer Panel</b><br>
  <img src="assets/settings-preview.png" width="520" alt="LyricVibe Settings Window" />
</p>

---

## Features

- **Pure Floating Overlay**: Zero window borders, zero background — only clean typography floating seamlessly over games, browsers, and desktop apps.
- **No Spotify Premium Required**: Intercepts Windows SMTC telemetry directly; works out of the box with Spotify Free and Premium.
- **Zero Configuration**: No API keys, developer tokens, or Spotify login credentials required.
- **165Hz Smooth Rendering**: Hardware-accelerated PyQt6 rendering at your monitor's native refresh rate (60–240Hz).
- **55+ Dynamic Animations**: Scale fades, kinetic snaps, word-by-word reveals, soft glows, star glints, and directional motion blur.
- **Vibrant Highlight Palette**: 16 ultra-bright neon colors that rotate automatically per song, or can be pinned in settings.
- **Hindi to Hinglish Transliteration**: Automatically converts Devanagari and Urdu lyrics into natural Roman Hinglish.
- **Smart LRCLIB Matching**: Automatically strips movie tags, featured artists, and remaster suffixes for accurate lyrics retrieval.
- **Settings Customizer**: Double-click or press `Ctrl + Alt + S` to customize fonts, colors, physics, and timing offsets.

---

## Quick Start

### Standalone Executable (Recommended)
Download the latest pre-built binary from [Releases](https://github.com/Arsh-Pathan/LyricVibe/releases):
```
dist\LyricVibe.exe
```
Double-click to run. No Python installation required.

### One-Click Spotify + Overlay Launcher
Run `Start LyricVibe.bat` in the root folder to open Spotify and the overlay together in one click.

### Run from Source
```bash
git clone https://github.com/Arsh-Pathan/LyricVibe.git
cd LyricVibe
pip install -r requirements.txt
python main.py
```

---

## Essential Controls

| Shortcut | Action |
|:---|:---|
| **Click & Drag** | Move lyrics anywhere on screen |
| **`Ctrl + Alt + S`** | Open Settings Customizer (or double-click text / tray icon) |
| **`Ctrl + Alt + L`** | Lock / Click-through mode (clicks pass through text) |
| **`Ctrl + Alt + H`** | Hide / Show overlay |
| **`[` / `]`** | Shift lyrics 0.5s earlier / later |
| **`Ctrl + Alt + Q`** | Quit overlay cleanly |
| **System Tray** | Access settings, lock, visibility, and quit via notification area |

---

## Documentation

Comprehensive guides and architectural specifications are available in the [`docs/`](docs/) directory:

- [**Architecture & Pipeline**](docs/ARCHITECTURE.md) — WinRT SMTC telemetry, LRCLIB API, Hinglish parser, and 165Hz rendering engine.
- [**Setup & Installation Guide**](docs/SETUP.md) — Detailed installation methods, virtual environments, startup automation, and troubleshooting.
- [**Animation System & Physics**](docs/ANIMATIONS.md) — Breakdown of all 55+ animations, cubic easing curves, motion blur, and neon palettes.
- [**Controls & Customization**](docs/CONTROLS.md) — Full hotkey index, mouse gestures, timing calibration, and settings guide.
- [**Building the Executable**](docs/BUILDING.md) — Packaging into a standalone `.exe` using PyInstaller.
- [**Release Notes**](docs/RELEASE_NOTES.md) — Changelog and highlights for v1.0.0.

---

## License

MIT License — see [LICENSE](LICENSE) for details.
