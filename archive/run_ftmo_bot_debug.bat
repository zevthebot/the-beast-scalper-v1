@echo off
echo ==========================================
echo FTMO 24/7 Trading Bot - Auto Start
echo ==========================================
echo.

cd /d "C:\Users\Claw\.openclaw\workspace\mt5_trader"

echo [INFO] Starting bot at %date% %time%
echo [INFO] Running: python bot_controller.py --trade
echo [INFO] Logging to: bot_run_log.txt
echo.

python bot_controller.py --trade > bot_run_log.txt 2>&1

echo.
echo [INFO] Bot finished at %date% %time%
echo [INFO] Check bot_run_log.txt for details
echo ==========================================

REM Don't close - wait for user
echo.
echo Press any key to close this window...
pause > nul
