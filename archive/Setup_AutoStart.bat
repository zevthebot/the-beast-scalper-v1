@echo off
echo ============================================
echo FTMO Protection Manager - Setup Auto-Start
echo ============================================
echo.
echo Acest script configureaza Protection Manager
echo sa porneasca AUTOMAT la fiecare boot Windows.
echo.
echo REZULTAT:
echo   • Protection Manager porneste automat
echo   • Ruleaza in background (fara fereastra)
echo   • Gestioneaza breakeven si trailing stop
echo   • Restart automat daca se opreste
echo.
echo ============================================
echo.
pause

echo.
echo Se configureaza task-ul...
echo.

powershell -ExecutionPolicy Bypass -File "C:\Users\Claw\.openclaw\workspace\mt5_trader\Setup_Protection_Task.ps1"

echo.
echo ============================================
pause
