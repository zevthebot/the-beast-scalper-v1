@echo off
cd /d "C:\Users\Claw\.openclaw\workspace\mt5_trader"
echo Current directory: %CD%
dir
echo.
echo Running Python check...
python --version
echo.
echo Running bot...
python bot_controller.py --trade > bot_run.log 2>&1
echo Bot exit code: %ERRORLEVEL%
