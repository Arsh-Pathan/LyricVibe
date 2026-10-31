# Setup & Installation Guide

This guide covers all methods for installing and configuring LyricVibe on Windows.

---

## System Requirements

- **Operating System**: Windows 10 (Build 19041+) or Windows 11
- **Spotify**: Official Spotify Desktop App (Free or Premium)
- **Display**: Any 60Hz, 120Hz, 144Hz, 165Hz, or 240Hz monitor
- **Python (Optional)**: Python 3.10 or higher (only needed if running from source)

---

## Method 1: Windows Setup Installer (Recommended)

The official Windows installer provides a guided setup wizard with Start Menu shortcuts, optional desktop icon, auto-start integration, and clean uninstallation registered in Windows Add/Remove programs.

1. Download `LyricVibe-Setup-v1.1.0.exe` from the [GitHub Releases](https://github.com/Arsh-Pathan/LyricVibe/releases) page.
2. Double-click `LyricVibe-Setup-v1.1.0.exe` and follow the setup wizard instructions.
3. Select optional tasks:
   - Create a desktop shortcut.
   - Launch LyricVibe on Windows startup.
4. Click **Install**.
5. Once installed, launch LyricVibe from your Start Menu or Desktop.
6. Play any song in Spotify Desktop — lyrics will float seamlessly on your screen.

---

## Method 2: Portable Standalone Executable

The standalone executable requires no installer and no Python runtime:

1. Download `LyricVibe.exe` or `LyricVibe-v1.1.0-Windows.zip` from [GitHub Releases](https://github.com/Arsh-Pathan/LyricVibe/releases).
2. Move `LyricVibe.exe` to your preferred folder (e.g., `C:\Tools\LyricVibe`).
3. Double-click `LyricVibe.exe` to run.
4. Play any track in Spotify Desktop — lyrics will appear automatically.

---

## Method 3: Running from Python Source

If you prefer to run or modify the code directly:

### 1. Clone the Repository
```bash
git clone https://github.com/Arsh-Pathan/LyricVibe.git
cd LyricVibe
```

### 2. Create and Activate a Virtual Environment
```bash
python -m venv venv
venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Launch the Overlay
```bash
python main.py
```

---

## Method 4: One-Click Spotify + Overlay Launcher

To launch Spotify and LyricVibe together in a single click:

Run `Start Spotify + Lyrics.bat` included in the root directory:
```bat
@echo off
start "" "%APPDATA%\Spotify\Spotify.exe"
start "" "dist\LyricVibe.exe"
```

---

## Auto-Start with Windows

To have the overlay start automatically with Windows in the background:

### Enable Auto-Start
Run `enable_autostart.bat`. This registers a shortcut in your Windows Startup directory (`%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup`).
The overlay runs silently and only shows text when Spotify is playing.

### Disable Auto-Start
Run `disable_autostart.bat` to remove the shortcut from your Startup folder.

---

## Troubleshooting

### Lyrics are not showing when Spotify plays
1. Ensure you are using the **Spotify Desktop client** from Spotify.com (not the web browser player).
2. Check that Windows Media Transport Controls (SMTC) are enabled in Spotify:
   - Spotify Settings -> Display -> Enable "Show desktop overlay when using media keys".
3. Verify that PowerShell scripts are allowed on your machine:
   ```powershell
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
   ```

### Text position is too high or too low
- Press `Ctrl + Alt + S` or double-click the lyrics text to open the settings window.
- In the **Display** tab, adjust the **Vertical Offset** slider to place lyrics at your preferred position.
- You can also click and drag the text anywhere on your screen.

### Lyrics timing is slightly ahead or behind
- Press `[` to shift lyrics 0.5 seconds earlier.
- Press `]` to shift lyrics 0.5 seconds later.
- Or open Settings (`Ctrl + Alt + S`) -> **Sync** tab to set a permanent millisecond audio offset.
