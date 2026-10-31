@echo off
title Disable Auto-Start for LyricVibe
cd /d "%~dp0.."

powershell -NoProfile -Command "$paths = @([Environment]::GetFolderPath('Startup') + '\LyricVibe.lnk', [Environment]::GetFolderPath('Startup') + '\SpotifyLyrics.lnk'); foreach ($p in $paths) { if (Test-Path $p) { Remove-Item $p -Force; Write-Host \"[OK] Removed: $p\" } }; Remove-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Run' -Name 'LyricVibe' -ErrorAction SilentlyContinue; Write-Host '[OK] Removed registry auto-start.'"

echo.
pause
