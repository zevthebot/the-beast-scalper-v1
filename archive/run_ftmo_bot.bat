@echo off
echo ==========================================
echo FTMO 24/7 Trading Bot - Auto Start
echo ==========================================
echo.

cd /d "C:\Users\Claw\.openclaw\workspace\mt5_trader"

echo [INFO] Starting bot at %date% %time%
echo [INFO] Running: python bot_controller.py --trade
echo.

python bot_controller.py --trade

echo.
echo [INFO] Bot finished at %date% %time%
echo ==========================================

pause
