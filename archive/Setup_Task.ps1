# Create Windows Scheduled Task for FTMO Bot
# Run this as Administrator

$TaskName = "FTMO_Trading_Bot_Service"
$BotPath = "C:\Users\Claw\.openclaw\workspace\mt5_trader"
$BatchFile = "$BotPath\run_bot_service.bat"
$User = $env:USERNAME

# Create task action
$Action = New-ScheduledTaskAction -Execute "$BatchFile" -WorkingDirectory "$BotPath"

# Create trigger - run at startup and repeat every 5 minutes if fails
$Trigger = New-ScheduledTaskTrigger -AtStartup

# Create task settings - run whether user is logged on or not, highest privileges
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -RunOnlyIfNetworkAvailable:$false

# Register task
try {
    Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -User $User -RunLevel Highest -Force
    Write-Host "✅ Task '$TaskName' created successfully!" -ForegroundColor Green
    Write-Host "The bot will start automatically when Windows boots." -ForegroundColor Green
    Write-Host ""
    Write-Host "To start now, run: Start-ScheduledTask -TaskName '$TaskName'" -ForegroundColor Yellow
} catch {
    Write-Host "❌ Failed to create task: $_" -ForegroundColor Red
    Write-Host "Make sure you run this script as Administrator!" -ForegroundColor Red
}
