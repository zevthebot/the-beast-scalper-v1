@echo off
cd /d C:\Users\Claw\.openclaw\workspace\mt5_trader
echo Starting THE BEAST 4.0 - Optimized Version...
echo New settings: 6 pairs, 09-17 UTC, 1.8x volume, 1:2.5 RR, fixed 0.2 lot
echo.
python -u the_beast_v4_price_action.py
echo.
echo Bot stopped. Restarting in 10 seconds...
timeout /t 10 /nobreak >nul
start_restart_v4.bat
