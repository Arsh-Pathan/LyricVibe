@echo off
title Build Spotify Lyrics EXE (165Hz Edition)
cd /d "%~dp0"

echo ===================================================
echo     Building SpotifyLyrics.exe with PyInstaller
echo ===================================================
echo.

pyinstaller --noconfirm --onefile --windowed --name "SpotifyLyrics" --icon "icon.ico" --add-data "spotify_listener.ps1;." --add-data "fonts;fonts" --add-data "icon.ico;." --add-data "icon.png;." main.py

if exist "dist\SpotifyLyrics.exe" (
    copy /y "spotify_listener.ps1" "dist\" >nul
    copy /y "icon.ico" "dist\" >nul
    copy /y "icon.png" "dist\" >nul
    if exist "fonts" (
        xcopy /e /i /y "fonts" "dist\fonts\" >nul
    )
    echo.
    echo ===================================================
    echo  SUCCESS! Built: dist\SpotifyLyrics.exe
    echo ===================================================
) else (
    echo.
    echo [ERROR] Build failed. Check the logs above.
)

pause
