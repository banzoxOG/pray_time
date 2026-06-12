@echo off
:: ============================================================
::  Salat App — installer + launcher
::  Double-click once. After that it runs automatically
::  every time Windows starts.
:: ============================================================

setlocal EnableDelayedExpansion

:: ── 1. Choose install folder (no admin needed) ───────────────
set "INSTALL_DIR=%APPDATA%\SalatApp"
set "SCRIPT=%INSTALL_DIR%\salat.py"
set "GITHUB_URL=https://raw.githubusercontent.com/banzoxOG/pray_time/refs/heads/main/salat.py"

:: ── 2. Create folder if missing ──────────────────────────────
if not exist "%INSTALL_DIR%" (
    mkdir "%INSTALL_DIR%"
)

:: ── 3. Download latest salat.py from GitHub ──────────────────
echo Downloading latest salat.py from GitHub...
powershell -NoProfile -Command ^
  "try { Invoke-WebRequest -Uri '%GITHUB_URL%' -OutFile '%SCRIPT%' -UseBasicParsing; Write-Host 'OK' } catch { Write-Host 'FAILED: ' + $_.Exception.Message; exit 1 }"

if not exist "%SCRIPT%" (
    echo.
    echo ERROR: Could not download salat.py
    echo Make sure you are connected to the internet.
    pause
    exit /b 1
)

echo Download complete.

:: ── 4. Check Python is installed ─────────────────────────────
where pythonw >nul 2>&1
if errorlevel 1 (
    echo.
    echo ERROR: Python not found.
    echo Please install Python from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during install.
    pause
    exit /b 1
)

:: ── 5. Register in Windows startup registry (no admin) ───────
::    HKCU\Software\Microsoft\Windows\CurrentVersion\Run
::    Value name: SalatApp
::    Value data: this .bat file path (so it re-downloads on each boot)
set "THIS_BAT=%~f0"

:: Copy this bat to install dir so it works even if original is deleted
set "LAUNCHER=%INSTALL_DIR%\salat_launcher.bat"
copy /Y "%THIS_BAT%" "%LAUNCHER%" >nul 2>&1

reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" ^
    /v "SalatApp" ^
    /t REG_SZ ^
    /d "\"%LAUNCHER%\"" ^
    /f >nul 2>&1

if errorlevel 1 (
    echo WARNING: Could not add to startup registry. App will not auto-start.
) else (
    echo Startup registry entry added. App will launch on every login.
)

:: ── 6. Launch salat.py silently (no console window) ──────────
echo Launching Salat App...
start "" pythonw "%SCRIPT%"

echo.
echo ============================================================
echo  Done! Salat App is now running and will start automatically
echo  every time you turn on your PC.
echo  
echo  To UNINSTALL: run salat_uninstall.bat (in %INSTALL_DIR%)
echo ============================================================

:: Create uninstaller in same folder
(
echo @echo off
echo reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "SalatApp" /f ^>nul 2^>^&1
echo taskkill /f /im pythonw.exe ^>nul 2^>^&1
echo rmdir /s /q "%INSTALL_DIR%"
echo echo SalatApp uninstalled.
echo pause
) > "%INSTALL_DIR%\salat_uninstall.bat"

timeout /t 3 >nul
exit /b 0
