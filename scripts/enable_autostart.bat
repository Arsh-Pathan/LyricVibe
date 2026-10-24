@echo off
title Enable Auto-Start for LyricVibe
cd /d "%~dp0.."

echo ========================================================
echo           Enable Auto-Start for LyricVibe
echo ========================================================
echo.

set "TARGET_EXE=%cd%\dist\LyricVibe.exe"
if not exist "%TARGET_EXE%" (
    set "TARGET_EXE=%cd%\dist\SpotifyLyrics.exe"
)
if not exist "%TARGET_EXE%" (
    set "TARGET_EXE=%cd%\main.py"
)

powershell -NoProfile -Command "$wsh = New-Object -ComObject WScript.Shell; $sc = $wsh.CreateShortcut([Environment]::GetFolderPath('Startup') + '\LyricVibe.lnk'); $sc.TargetPath = '%TARGET_EXE%'; $sc.WorkingDirectory = '%cd%\dist'; $sc.IconLocation = '%cd%\icon.ico'; $sc.Description = 'LyricVibe Floating Lyrics Overlay'; $sc.Save()"

if errorlevel 0 (
    echo [OK] Auto-Start enabled!
    echo.
    echo LyricVibe will now run silently in the background on Windows startup.
) else (
    echo [ERROR] Failed to create shortcut.
)

echo.
pause
