Set WshShell = CreateObject("WScript.Shell") 
WshShell.Run chr(34) & "C:\Python314\python.exe" & chr(34) & " -u C:\Users\Claw\.openclaw\workspace\mt5_trader\bot_watchdog.py", 0
Set WshShell = Nothing
