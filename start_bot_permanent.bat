@echo off
title Pepperstone ML Bot Watchdog
cd /d C:\Users\Claw\.openclaw\workspace\mt5_trader

:: Check if already running
tasklist | findstr /i "python.exe" | findstr /i "bot_watchdog" >nul
if %errorlevel% == 0 (
    echo Bot already running!
    exit /b 0
)

echo Starting Pepperstone ML Bot Watchdog...
echo Log file: C:\Users\Claw\.openclaw\workspace\mt5_trader\watchdog.log
echo.

:restart
python -u bot_watchdog.py
echo Bot crashed or stopped. Restarting in 10 seconds...
timeout /t 10 /nobreak >nul
goto restart
