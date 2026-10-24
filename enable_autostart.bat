@echo off
title Enable Auto-Start with Spotify / Windows
cd /d "%~dp0"

echo ========================================================
echo        Enable Auto-Start for Spotify Floating Lyrics
echo ========================================================
echo.

set "TARGET_EXE=%~dp0dist\SpotifyLyrics.exe"
if not exist "%TARGET_EXE%" (
    set "TARGET_EXE=%~dp0main.py"
)

powershell -NoProfile -Command "$wsh = New-Object -ComObject WScript.Shell; $sc = $wsh.CreateShortcut([Environment]::GetFolderPath('Startup') + '\SpotifyLyrics.lnk'); $sc.TargetPath = '%TARGET_EXE%'; $sc.WorkingDirectory = '%~dp0dist'; $sc.Description = 'Spotify Floating Lyrics Overlay'; $sc.Save()"

if errorlevel 0 (
    echo [OK] Auto-Start enabled!
    echo.
    echo SpotifyLyrics will now run in the background.
    echo It stays 100%% invisible until you open Spotify and play music,
    echo then automatically appears at the top of your screen!
) else (
    echo [ERROR] Could not create startup shortcut.
)

echo.
pause
