# FTMO Trading Bot Service Wrapper
# This script runs the bot continuously and logs everything

$BotDir = "C:\Users\Claw\.openclaw\workspace\mt5_trader"
$LogFile = "$BotDir\service_log.txt"
$StatusFile = "$BotDir\live_trading_status.json"

function Write-Log {
    param($Message)
    $Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "$Timestamp - $Message" | Out-File -FilePath $LogFile -Append -Encoding UTF8
    Write-Host "$Timestamp - $Message"
}

function Update-Status {
    param($Data)
    $Data | ConvertTo-Json -Depth 10 | Out-File -FilePath $StatusFile -Encoding UTF8
}

Write-Log "=== FTMO Bot Service Starting ==="
Write-Log "Working Directory: $BotDir"

# Check if MT5 is running
$MT5Process = Get-Process | Where-Object {$_.ProcessName -like "*terminal*" -or $_.ProcessName -like "*mt5*"}
if (-not $MT5Process) {
    Write-Log "ERROR: MT5 not running. Please start MT5 and login to FTMO account."
    exit 1
}

Write-Log "MT5 detected - proceeding with trading"

# Change to bot directory
Set-Location $BotDir

# Run bot in continuous mode with output capture
while ($true) {
    try {
        Write-Log "Starting bot cycle..."
        
        # Run Python bot and capture output
        $Output = & python.exe bot_controller.py --trade 2>&1
        
        # Log output
        $Output | ForEach-Object { Write-Log "BOT: $_" }
        
        # Parse and update status
        $Status = @{
            timestamp = Get-Date -Format "yyyy-MM-ddTHH:mm:ss"
            status = "running"
            last_output = ($Output -join "`n")
        }
        Update-Status -Data $Status
        
        Write-Log "Cycle complete. Waiting 5 minutes..."
        Start-Sleep -Seconds 300
        
    } catch {
        Write-Log "ERROR: $($_.Exception.Message)"
        Start-Sleep -Seconds 60
    }
}
