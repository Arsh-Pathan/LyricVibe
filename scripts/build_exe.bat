@echo off
title Build LyricVibe Standalone Executable
cd /d "%~dp0.."

echo ===================================================
echo     Building LyricVibe.exe with PyInstaller
echo ===================================================
echo.

pyinstaller --noconfirm LyricVibe.spec

if exist "dist\LyricVibe.exe" (
    copy /y "src\lyricvibe\media\spotify_listener.ps1" "dist\" >nul 2>&1
    copy /y "icon.ico" "dist\" >nul 2>&1
    copy /y "icon.png" "dist\" >nul 2>&1
    if exist "fonts" (
        xcopy /e /i /y "fonts" "dist\fonts\" >nul 2>&1
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
