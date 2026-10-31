@echo off
title Enable Auto-Start for LyricVibe
cd /d "%~dp0.."

echo ========================================================
echo           Enable Auto-Start for LyricVibe
echo ========================================================
echo.

set "TARGET_EXE=%cd%\dist\LyricVibe.exe"
set "TARGET_ARGS=--autostart"
set "TARGET_DIR=%cd%\dist"

if not exist "%TARGET_EXE%" (
    if exist "%cd%\LyricVibe.exe" (
        set "TARGET_EXE=%cd%\LyricVibe.exe"
        set "TARGET_DIR=%cd%"
    ) else (
        set "TARGET_EXE=pythonw.exe"
        set "TARGET_ARGS=\"%cd%\main.py\" --autostart"
        set "TARGET_DIR=%cd%"
    )
)

powershell -NoProfile -Command "$wsh = New-Object -ComObject WScript.Shell; $sc = $wsh.CreateShortcut([Environment]::GetFolderPath('Startup') + '\LyricVibe.lnk'); $sc.TargetPath = '%TARGET_EXE%'; $sc.Arguments = '%TARGET_ARGS%'; $sc.WorkingDirectory = '%TARGET_DIR%'; $sc.IconLocation = '%cd%\icon.ico'; $sc.Description = 'LyricVibe Floating Lyrics Overlay'; $sc.Save(); Set-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Run' -Name 'LyricVibe' -Value '\"%TARGET_EXE%\" %TARGET_ARGS%'"

if errorlevel 0 (
    echo [OK] Auto-Start enabled!
    echo.
    echo LyricVibe will now run silently in the background on Windows startup.
) else (
    echo [ERROR] Failed to create shortcut.
)

echo.
pause
