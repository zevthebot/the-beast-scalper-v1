@echo off
echo ==========================================
echo FTMO Trading Bot - TEST MODE
echo ==========================================
echo.

cd /d "C:\Users\Claw\.openclaw\workspace\mt5_trader"

echo [INFO] Running TEST TRADES on EURUSD and XAUUSD
echo.

python bot_controller.py --test

echo.
echo [INFO] Test complete. Check output above for results.
echo ==========================================

pause
