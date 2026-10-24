@echo off
title Launch Spotify + Floating Lyrics
cd /d "%~dp0"

echo Launching Spotify and Lyrics Overlay...

:: Launch Spotify
start "" "spotify:"

:: Launch Overlay (prefers compiled EXE if present)
if exist "dist\SpotifyLyrics.exe" (
    start "" "dist\SpotifyLyrics.exe"
) else (
    start "" pythonw main.py
)

exit
