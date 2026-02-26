@echo off
REM FTMO Monitor Runner - Save this to run_monitor.bat and double-click it
REM It will save status to ftmo_status.json which I can read

cd /d "C:\Users\Claw\.openclaw\workspace\mt5_trader"

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo Python not found in PATH. Trying python3...
    python3 ftmo_monitor.py > ftmo_status.json 2>&1
) else (
    python ftmo_monitor.py > ftmo_status.json 2>&1
)

echo Status saved to ftmo_status.json
timeout /t 2 >nul
