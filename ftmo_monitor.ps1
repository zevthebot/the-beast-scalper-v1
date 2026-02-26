# FTMO Phase 1 Continuous Trading Loop
# Run this PowerShell script for continuous monitoring

$INITIAL_BALANCE = 10000
$TARGET_PROFIT = 1000
$MAX_DAILY_LOSS = 400
$MAX_TOTAL_LOSS = 800
$STATUS_FILE = "C:\Users\Claw\.openclaw\workspace\mt5_trader\mt5_ftmo_status.json"
$CYCLE = 0

function Get-Status {
    if (Test-Path $STATUS_FILE) {
        try {
            return Get-Content $STATUS_FILE | ConvertFrom-Json
        } catch {
            return $null
        }
    }
    return $null
}

function Show-Report {
    param($Cycle)
    $status = Get-Status
    if (-not $status) {
        Write-Host "No status available" -ForegroundColor Yellow
        return
    }
    
    $balance = $status.balance
    $equity = $status.equity
    $profit = $equity - $INITIAL_BALANCE
    $profitPct = ($profit / $INITIAL_BALANCE) * 100
    $positions = $status.positions
    
    Write-Host ""
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host "  FTMO PHASE 1 MONITOR - Report #$Cycle" -ForegroundColor Cyan
    Write-Host "  Time: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Cyan
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host "  Balance: `$$("{0:N2}" -f $balance)" -ForegroundColor White
    Write-Host "  Equity:  `$$("{0:N2}" -f $equity)" -ForegroundColor White
    
    if ($profit -ge 0) {
        Write-Host "  P&L:     `$$("{0:N2}" -f $profit) ("("{0:N2}" -f $profitPct)%" -ForegroundColor Green
    } else {
        Write-Host "  P&L:     `$$("{0:N2}" -f $profit) ("("{0:N2}" -f $profitPct)%" -ForegroundColor Red
    }
    
    Write-Host "  Target:  +`$1,000 (+10%) | Progress: $("{0:N1}" -f ($profit/10))%" -ForegroundColor Yellow
    Write-Host "------------------------------------------------------------" -ForegroundColor Gray
    Write-Host "  Positions: $($positions.Count)/5" -ForegroundColor White
    
    foreach ($pos in $positions) {
        $pnl = $pos.profit
        $color = if ($pnl -ge 0) { "Green" } else { "Red" }
        Write-Host "    - $($pos.symbol) $($pos.type): `$$("{0:N2}" -f $pnl)" -ForegroundColor $color
    }
    
    Write-Host "------------------------------------------------------------" -ForegroundColor Gray
    $dailyLoss = $status.daily_loss_pct * 100
    Write-Host "  Daily Loss: $("{0:N2}" -f $dailyLoss)% (Limit: 4%)" -ForegroundColor $(if ($dailyLoss -ge 4) { "Red" } else { "Green" })
    
    $totalLossPct = [Math]::Abs($profitPct)
    Write-Host "  Total Loss: $("{0:N2}" -f $totalLossPct)% (Limit: 8%)" -ForegroundColor $(if ($totalLossPct -ge 8) { "Red" } else { "Green" })
    
    Write-Host "------------------------------------------------------------" -ForegroundColor Gray
    
    if ($profit -ge 1000) {
        Write-Host "  STATUS: TARGET REACHED! STOP TRADING" -ForegroundColor Green -BackgroundColor Black
    } elseif ($profit -le -800) {
        Write-Host "  STATUS: TOTAL LOSS LIMIT REACHED - STOP" -ForegroundColor Red -BackgroundColor Black
    } elseif ($dailyLoss -ge 4) {
        Write-Host "  STATUS: DAILY LOSS LIMIT REACHED - STOP" -ForegroundColor Red -BackgroundColor Black
    } else {
        Write-Host "  STATUS: ACTIVE - Within FTMO limits" -ForegroundColor Green
    }
    
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host ""
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Magenta
Write-Host "  FTMO PHASE 1 - CONTINUOUS TRADING BOT" -ForegroundColor Magenta
Write-Host "============================================================" -ForegroundColor Magenta
Write-Host "  Target:  +`$1,000 (+10%) to pass Phase 1" -ForegroundColor White
Write-Host "  Pairs:   EURUSD, GBPUSD, USDJPY, XAUUSD" -ForegroundColor White
Write-Host "           EURJPY, GBPJPY, AUDJPY, EURGBP" -ForegroundColor White
Write-Host "  Strategy: Trend/Range/Breakout (Conf >40%)" -ForegroundColor White
Write-Host "  Risk:    0.01 lots, SL 50 pips, TP 100 pips" -ForegroundColor White
Write-Host "------------------------------------------------------------" -ForegroundColor Gray
Write-Host "  STOP CONDITIONS:" -ForegroundColor Yellow
Write-Host "    - Daily loss >= `$400 (4%)" -ForegroundColor Yellow
Write-Host "    - Total loss >= `$800 (8%)" -ForegroundColor Yellow
Write-Host "    - Profit target reached (+`$1,000)" -ForegroundColor Yellow
Write-Host "============================================================" -ForegroundColor Magenta
Write-Host ""

# Initial report
Show-Report -Cycle 0

while ($true) {
    $CYCLE++
    $now = Get-Date -Format "HH:mm:ss"
    
    # Check stop conditions
    $status = Get-Status
    if ($status) {
        $profit = $status.equity - $INITIAL_BALANCE
        $dailyLoss = $status.daily_loss_pct * 100
        
        if ($profit -ge 1000) {
            Write-Host "`n*** PROFIT TARGET REACHED: `$$("{0:N2}" -f $profit) ***" -ForegroundColor Green -BackgroundColor Black
            break
        }
        if ($profit -le -800) {
            Write-Host "`n*** TOTAL LOSS LIMIT: `$$("{0:N2}" -f $profit) ***" -ForegroundColor Red -BackgroundColor Black
            break
        }
        if ($dailyLoss -ge 4) {
            Write-Host "`n*** DAILY LOSS LIMIT: $("{0:N2}" -f $dailyLoss)% ***" -ForegroundColor Red -BackgroundColor Black
            break
        }
    }
    
    Write-Host "[$now] Cycle #$CYCLE : Running trading scan..." -NoNewline -ForegroundColor Cyan
    
    # Run the bot
    $output = & python C:\Users\Claw\.openclaw\workspace\mt5_trader\bot_controller.py --trade 2>&1
    $exitCode = $LASTEXITCODE
    
    if ($exitCode -eq 0) {
        Write-Host " OK" -ForegroundColor Green
    } else {
        Write-Host " FAILED" -ForegroundColor Red
    }
    
    # Show report every 6 cycles (~30 min at 5 min intervals)
    if ($CYCLE % 6 -eq 0) {
        Show-Report -Cycle $CYCLE
    }
    
    # Wait 5 minutes
    Write-Host "  Waiting 5 minutes..." -ForegroundColor Gray
    Start-Sleep -Seconds 300
}

Write-Host "`nFTMO Trading Session Ended" -ForegroundColor Magenta
