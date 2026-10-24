@echo off
title Build LyricVibe Standalone Executable
cd /d "%~dp0.."

echo ===================================================
echo     Building LyricVibe.exe with PyInstaller
echo ===================================================
echo.

pyinstaller --noconfirm --onefile --windowed ^
    --name "LyricVibe" ^
    --icon "icon.ico" ^
    --add-data "spotify_listener.ps1;." ^
    --add-data "fonts;fonts" ^
    --add-data "icon.ico;." ^
    --add-data "icon.png;." ^
    main.py

if exist "dist\LyricVibe.exe" (
    copy /y "spotify_listener.ps1" "dist\" >nul
    copy /y "icon.ico" "dist\" >nul
    copy /y "icon.png" "dist\" >nul
    if exist "fonts" (
        xcopy /e /i /y "fonts" "dist\fonts\" >nul
    )
    copy /y "dist\LyricVibe.exe" "dist\SpotifyLyrics.exe" >nul 2>&1
    echo.
    echo ===================================================
    echo  Build Successful: dist\LyricVibe.exe
    echo ===================================================
) else (
    echo.
    echo [ERROR] Build failed! Check PyInstaller output above.
)

pause
