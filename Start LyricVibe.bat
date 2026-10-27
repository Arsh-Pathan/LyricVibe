@echo off
title Launch Spotify + LyricVibe
cd /d "%~dp0"

echo Launching Spotify and LyricVibe...

:: Launch Spotify
start "" "spotify:"

:: Launch Overlay (prefers compiled EXE if present)
if exist "dist\LyricVibe.exe" (
    start "" "dist\LyricVibe.exe"
) else (
    start "" pythonw main.py
)

exit
