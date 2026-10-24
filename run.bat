@echo off
title Spotify Lyrics Overlay
cd /d "%~dp0"

echo ===================================================
echo           Spotify Lyrics Overlay Launcher
echo ===================================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH!
    echo Please install Python from https://www.python.org/
    pause
    exit /b 1
)

echo Checking dependencies...
python -m pip install -r requirements.txt --quiet

echo Starting Spotify Lyrics Overlay...
python main.py

if errorlevel 1 (
    echo.
    echo Overlay closed or encountered an error.
    pause
)
