# Controls & Customization Reference

LyricVibe provides full keyboard and mouse control over the overlay, allowing on-the-fly adjustment without leaving your active game or application.

---

## Global Hotkeys

These keyboard shortcuts work system-wide regardless of which window is in focus:

| Shortcut | Action | Description |
|:---|:---|:---|
| **`Ctrl + S`** | Open Settings | Opens the dark-themed customization panel. |
| **`Ctrl + Alt + L`** | Lock Overlay | Toggles click-through mode. When locked, mouse clicks pass directly through lyrics to the window behind. |
| **`Ctrl + Alt + H`** | Hide / Show | Instantly hides or restores lyrics overlay visibility. |
| **`Ctrl + Alt + Q`** | Quit | Terminates LyricVibe and the background listener cleanly. |
| **`[`** | Advance Audio (-0.5s) | Shifts lyrics earlier in time for faster synchronization. |
| **`]`** | Delay Audio (+0.5s) | Delays lyrics later in time if lyrics appear too early. |

---

## Interactive Mouse Controls

When the overlay is in unlocked mode (default):

- **Drag to Move**: Click and hold anywhere on the text to drag the overlay to any position on your screen.
- **Double-Click**: Double-clicking active lyrics opens the Settings Customizer window.
- **Hover**: Lyrics subtly react to cursor presence without stealing focus from your foreground window.

---

## Customization Panel Walkthrough

Press `Ctrl + S` or run `LyricVibe.exe` a second time to open the Settings Dialog.

### 1. Display Tab
- **Font Family**: Choose between Montserrat, Poppins, Segoe UI, Arial, or any installed Windows font.
- **Font Size**: Adjustable from 24px to 64px (default: 40px).
- **Font Weight**: Normal, Medium, Semi-Bold, Bold, or Extra-Bold.
- **Vertical Position (Offset Y)**: Fine-tune the resting vertical distance from the top of the monitor.
- **Letter Spacing**: Adjust typographical tracking for modern aesthetics.

### 2. Effects Tab
- **Bright Highlight Palette**: Choose between automatic per-song color rotation or pin your favorite neon hue (Mint Emerald, Electric Cyan, Golden Canary, Hot Magenta, Neon Violet, Blaze Orange, etc.).
- **Motion Blur Streak Length**: Adjust sub-frame directional motion blur shutter intensity (0.5x to 3.0x).
- **Procedural Accents**: Toggle glowing focal blooms, chromatic dispersion, and hand-drawn underlines.

### 3. Sync Tab
- **Manual Millisecond Offset**: Set persistent timing offsets (`-5000ms` to `+5000ms`) saved permanently in `settings.json`.
- **Quick-Shift Buttons**: Preset `-1.0s`, `-0.5s`, `0.0s`, `+0.5s`, and `+1.0s` buttons for one-tap calibration.

### 4. Presets Tab
- **Cinematic (Default)**: Dynamic multi-color rotation, 165Hz physics, scale-fade transitions.
- **Minimalist**: Clean pure white text, whisper dissolve, motion blur disabled.
- **Vibrant / Cyberpunk**: High-intensity neon glow, kinetic snaps, chromatic split enabled.
- **Studio Lyricist**: Word-by-word reveal, focal underline, Montserrat typography.
