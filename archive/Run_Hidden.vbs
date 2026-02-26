' FTMO Trading Bot - Hidden Runner
' This runs the bot without showing a console window

Set WshShell = CreateObject("WScript.Shell")
Set FSO = CreateObject("Scripting.FileSystemObject")

BotDir = "C:\Users\Claw\.openclaw\workspace\mt5_trader"
LogFile = BotDir & "\bot_hidden.log"

' Function to log messages
Sub LogMessage(msg)
    Set logFileObj = FSO.OpenTextFile(LogFile, 8, True)
    logFileObj.WriteLine Now & " - " & msg
    logFileObj.Close
End Sub

LogMessage("=== Bot Hidden Runner Started ===")

' Check if already running
Set WMI = GetObject("winmgmts:")
Set processes = WMI.ExecQuery("SELECT * FROM Win32_Process WHERE Name='python.exe'")
Dim alreadyRunning
alreadyRunning = False
For Each process in processes
    If InStr(process.CommandLine, "bot_controller.py") > 0 Then
        alreadyRunning = True
        Exit For
    End If
Next

If alreadyRunning Then
    LogMessage("Bot already running - exiting")
    WScript.Quit
End If

' Run bot in hidden window
WshShell.CurrentDirectory = BotDir
LogMessage("Starting Python bot...")

' Run with hidden window (0 = hidden)
WshShell.Run "python.exe bot_controller.py --trade", 0, False

LogMessage("Bot started successfully (hidden window)")
LogMessage("Check bot_console.log or ftmo_live_status.json for status")

Set WshShell = Nothing
Set FSO = Nothing
