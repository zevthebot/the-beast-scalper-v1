@echo off
REM Run MT5 monitor with error checking
REM Returns error code only if critical error found

cd %USERPROFILE%\.openclaw\workspace\mt5_trader

REM Run error monitor first
python error_monitor.py > error_output.txt 2>&1
set ERRORLEVEL_CHECK=%ERRORLEVEL%

REM Check if there's a critical error
findstr "CRITICAL" error_output.txt > nul
if %ERRORLEVEL% == 0 (
    type error_output.txt
    exit /b 1
) else (
    echo OK - No critical errors
    exit /b 0
)
