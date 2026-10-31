@echo off
title Build LyricVibe Windows Setup Installer
cd /d "%~dp0.."

echo ===================================================
echo     Building LyricVibe Windows Setup Installer
echo ===================================================
echo.

set ISCC=""
if exist "C:\Users\ArshPathan\AppData\Local\Programs\Inno Setup 6\ISCC.exe" (
    set ISCC="C:\Users\ArshPathan\AppData\Local\Programs\Inno Setup 6\ISCC.exe"
) else if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" (
    set ISCC="%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
) else if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" (
    set ISCC="%ProgramFiles%\Inno Setup 6\ISCC.exe"
)

if %ISCC%=="" (
    echo [ERROR] Inno Setup 6 compiler (ISCC.exe) not found.
    echo Please install Inno Setup 6 via: winget install JRSoftware.InnoSetup
    pause
    exit /b 1
)

if not exist "dist\LyricVibe.exe" (
    echo [ERROR] dist\LyricVibe.exe not found!
    echo Please run scripts\build_exe.bat first to build the executable.
    pause
    exit /b 1
)

%ISCC% "scripts\installer.iss"

if exist "dist\LyricVibe-Setup-v1.1.0.exe" (
    echo.
    echo ===================================================
    echo  Installer Built: dist\LyricVibe-Setup-v1.1.0.exe
    echo ===================================================
) else (
    echo.
    echo [ERROR] Inno Setup compilation failed!
)

pause
