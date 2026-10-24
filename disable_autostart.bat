@echo off
title Disable Auto-Start for Spotify Floating Lyrics
cd /d "%~dp0"

powershell -NoProfile -Command "$path = [Environment]::GetFolderPath('Startup') + '\SpotifyLyrics.lnk'; if (Test-Path $path) { Remove-Item $path -Force; Write-Host '[OK] Auto-Start shortcut removed.' } else { Write-Host 'Shortcut was not present.' }"

echo.
pause
