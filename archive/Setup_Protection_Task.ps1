# Create Windows Scheduled Task for FTMO Protection Manager
# Run this as Administrator

$TaskName = "FTMO_Protection_Manager"
$BotPath = "C:\Users\Claw\.openclaw\workspace\mt5_trader"
$PythonScript = "$BotPath\protection_manager.py"
$User = $env:USERNAME

# Create task action - run Python script directly
$Action = New-ScheduledTaskAction -Execute "python.exe" -Argument "$PythonScript" -WorkingDirectory "$BotPath"

# Create triggers
# 1. At startup (with 30 second delay to let MT5 start)
$TriggerStartup = New-ScheduledTaskTrigger -AtStartup
# 2. Also run if missed (every 5 minutes check)
$TriggerLogon = New-ScheduledTaskTrigger -AtLogon

# Create task settings
$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable:$false `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1)

# Register task
try {
    Register-ScheduledTask `
        -TaskName $TaskName `
        -Action $Action `
        -Trigger $TriggerStartup, $TriggerLogon `
        -Settings $Settings `
        -User $User `
        -RunLevel Highest `
        -Force
    
    Write-Host "✅ Task '$TaskName' creat cu succes!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Protection Manager va porni automat:" -ForegroundColor Cyan
    Write-Host "  • La fiecare boot Windows" -ForegroundColor Gray
    Write-Host "  • La fiecare logon" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Să pornească acum?" -ForegroundColor Yellow
    
    $response = Read-Host "Scrie 'da' pentru a porni acum, sau Enter pentru a ieși"
    
    if ($response -eq "da") {
        Start-ScheduledTask -TaskName $TaskName
        Write-Host ""
        Write-Host "🚀 Protection Manager a pornit!" -ForegroundColor Green
        Write-Host "Verifică Task Manager > Details pentru python.exe" -ForegroundColor Gray
    }
    
    Write-Host ""
    Write-Host "Comenzi utile:" -ForegroundColor Cyan
    Write-Host "  Start:  Start-ScheduledTask -TaskName '$TaskName'" -ForegroundColor Gray
    Write-Host "  Stop:   Stop-ScheduledTask -TaskName '$TaskName'" -ForegroundColor Gray
    Write-Host "  Status: Get-ScheduledTask -TaskName '$TaskName'" -ForegroundColor Gray
} catch {
    Write-Host "❌ Eroare la crearea task-ului: $_" -ForegroundColor Red
    Write-Host "Asigură-te că rulezi ca Administrator!" -ForegroundColor Red
}
