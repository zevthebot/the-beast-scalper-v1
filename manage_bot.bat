@echo off
echo ===================================
echo MT5 AI Trading Bot - Launcher
echo ===================================
echo.
cd /d "C:\Users\Claw\.openclaw\workspace\mt5_trader"
echo [1] Check Status
echo [2] View Trading Log
echo [3] Stop Bot
echo [4] Restart Bot
echo.
set /p choice="Select option: "

if "%choice%"=="1" (
    python -c "import MetaTrader5 as mt5; mt5.initialize(); info=mt5.account_info(); print(f'Balance: {info.balance:.2f} EUR | Profit: {info.profit:.2f}'); mt5.shutdown()"
)
if "%choice%"=="2" (
    if exist trading_log.txt (
        type trading_log.txt
    ) else (
        echo No trades yet.
    )
)
if "%choice%"=="3" (
    taskkill /F /IM python.exe 2>nul
    echo Bot stopped.
)
if "%choice%"=="4" (
    taskkill /F /IM python.exe 2>nul
    timeout /t 2 /nobreak >nul
    start python bot_auto.py
    echo Bot restarted.
)
pause
