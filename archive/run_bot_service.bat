@echo off
setlocal enabledelayedexpansion

set BOTDIR=C:\Users\Claw\.openclaw\workspace\mt5_trader
set LOGFILE=%BOTDIR%\bot_console.log

echo ========================================== >> "%LOGFILE%"
echo FTMO Bot Service - Started at %date% %time% >> "%LOGFILE%"
echo ========================================== >> "%LOGFILE%"
echo. >> "%LOGFILE%"

cd /d "%BOTDIR%"

echo [INFO] Bot starting... >> "%LOGFILE%"
echo [INFO] Working directory: %CD% >> "%LOGFILE%"
echo [INFO] Logging to: %LOGFILE% >> "%LOGFILE%"
echo. >> "%LOGFILE%"

:LOOP
echo [%date% %time%] Running bot cycle... >> "%LOGFILE%"

python.exe bot_controller.py --trade >> "%LOGFILE%" 2>&1

echo. >> "%LOGFILE%"
echo [%date% %time%] Cycle complete. Waiting 5 minutes... >> "%LOGFILE%"
echo. >> "%LOGFILE%"

timeout /t 300 /nobreak >nul

goto LOOP
