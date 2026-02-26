@echo off
REM The Beast - FTMO Trading System Launcher
REM Version 1.0 - 2026-02-19
REM Account: 541144102 (FTMO Challenge $10K)

echo ========================================
echo    THE BEAST v1.0
echo    FTMO Trading System
echo ========================================
echo.

REM Check if MT5 is running
tasklist /FI "IMAGENAME eq terminal64.exe" 2>NUL | find /I /N "terminal64.exe">NUL
if "%ERRORLEVEL%"=="0" (
    echo [OK] MetaTrader 5 is running
) else (
    echo [WARN] MetaTrader 5 is NOT running!
    echo Please start MT5 and login to account 541144102 first.
    pause
    exit /b 1
)

echo.
echo Starting The Beast via Runner...
echo This will restart automatically if bot crashes.
echo.
echo Press Ctrl+C to stop (or close this window)
echo.

REM Change to THE_BEAST directory
cd /d "C:\Users\Claw\.openclaw\workspace\mt5_trader\THE_BEAST"

REM Start The Beast Runner
python the_beast_runner.py

echo.
echo The Beast has stopped.
pause
