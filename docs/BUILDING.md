# Building the Standalone Executable

LyricVibe can be packaged into a standalone, portable Windows executable (`LyricVibe.exe`) using PyInstaller.

---

## Prerequisites

Ensure you have Python 3.10+ installed and install the required dependencies:

```bash
pip install -r requirements.txt
pip install pyinstaller
```

---

## One-Click Build

Run the build script located in `scripts/build_exe.bat`:

```bash
scripts\build_exe.bat
```

The script automatically:
1. Compiles `main.py` into `dist\LyricVibe.exe`.
2. Embeds `spotify_listener.ps1`, `fonts/`, and `icon.ico` directly into the binary bundle.
3. Copies auxiliary fallback assets into `dist/`.
4. Generates a portable zip archive in `dist/`.

---

## Manual PyInstaller Command

If you prefer building manually via command line:

```bash
pyinstaller --noconfirm --onefile --windowed ^
    --name "LyricVibe" ^
    --icon "icon.ico" ^
    --add-data "spotify_listener.ps1;." ^
    --add-data "fonts;fonts" ^
    --add-data "icon.ico;." ^
    --add-data "icon.png;." ^
    main.py
```

### Build Flags Explained
- `--onefile`: Bundles all dependencies, Qt6 runtime DLLs, and scripts into a single self-extracting `.exe`.
- `--windowed`: Suppresses the Windows command prompt terminal console window on startup.
- `--icon "icon.ico"`: Embeds the application icon into Windows Explorer.
- `--add-data`: Packages auxiliary assets (PowerShell listener, fonts, icon graphics) into PyInstaller's runtime `sys._MEIPASS` directory.

---

## Building the Windows Setup Installer (.exe)

LyricVibe includes an Inno Setup script (`scripts/installer.iss`) to build a professional Windows Setup Installer (`LyricVibe-Setup-v1.1.0.exe`).

### Prerequisites
Install Inno Setup 6:
```powershell
winget install JRSoftware.InnoSetup
```

### One-Click Installer Build
Run `scripts/build_installer.bat`:
```cmd
scripts\build_installer.bat
```

Or compile directly with the Inno Setup CLI compiler:
```powershell
& "C:\Users\ArshPathan\AppData\Local\Programs\Inno Setup 6\ISCC.exe" scripts/installer.iss
```

The resulting setup executable is output to `dist\LyricVibe-Setup-v1.1.0.exe`.

---

## Verification

After building, test the binary from the command line:

```powershell
.\dist\LyricVibe.exe
```

Verify that:
1. The overlay appears without any terminal window opening.
2. Playing music in Spotify immediately streams lyrics.
3. Double-clicking lyrics opens the Settings Customizer.
