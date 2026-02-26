# FTMO Phase 1 - Simple Continuous Trading Loop
# Run this to continuously execute trades every 5 minutes

import subprocess
import json
import time
import os
from datetime import datetime

STATUS_FILE = r'C:\Users\Claw\.openclaw\workspace\mt5_trader\mt5_ftmo_status.json'
REPORT_FILE = r'C:\Users\Claw\.openclaw\workspace\mt5_trader\ftmo_live_report.txt'
INITIAL_BALANCE = 10000

def read_status():
    try:
        if os.path.exists(STATUS_FILE):
            with open(STATUS_FILE, 'r') as f:
                return json.load(f)
    except:
        pass
    return None

def run_bot():
    try:
        result = subprocess.run(
            ['python', 'bot_controller.py', '--trade'],
            cwd=r'C:\Users\Claw\.openclaw\workspace\mt5_trader',
            capture_output=True,
            text=True,
            timeout=120
        )
        return result.returncode == 0
    except:
        return False

def format_report(cycle):
    status = read_status()
    if not status:
        return f"[{datetime.now().strftime('%H:%M:%S')}] Cycle #{cycle}: No status available"
    
    balance = status.get('balance', 0)
    equity = status.get('equity', 0)
    profit = equity - INITIAL_BALANCE
    profit_pct = (profit / INITIAL_BALANCE) * 100
    positions = status.get('positions', [])
    pos_count = len(positions)
    
    lines = [
        "=" * 60,
        f"FTMO PHASE 1 MONITOR - Report #{cycle}",
        f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "=" * 60,
        f"Balance: ${balance:,.2f}",
        f"Equity:  ${equity:,.2f}",
        f"P&L:     ${profit:+.2f} ({profit_pct:+.2f}%)",
        f"Target:  +$1,000 (+10%) | Progress: {profit/10:.1f}%",
        "-" * 60,
        f"Positions: {pos_count}/5",
    ]
    
    if positions:
        for p in positions:
            lines.append(f"  - {p.get('symbol')} {p.get('type')}: ${p.get('profit', 0):+.2f}")
    else:
        lines.append("  No open positions")
    
    lines.append("-" * 60)
    
    # FTMO Limits Check
    daily_loss = status.get('daily_loss_pct', 0) * 100
    lines.append(f"Daily Loss: {daily_loss:.2f}% (Limit: 4%)")
    lines.append(f"Total Loss: {abs(profit_pct) if profit < 0 else 0:.2f}% (Limit: 8%)")
    
    # Status
    if profit >= 1000:
        lines.append("STATUS: TARGET REACHED! STOP TRADING")
    elif profit <= -800:
        lines.append("STATUS: TOTAL LOSS LIMIT - STOP")
    elif daily_loss >= 4:
        lines.append("STATUS: DAILY LOSS LIMIT - STOP")
    else:
        lines.append("STATUS: ACTIVE - Within FTMO limits")
    
    lines.append("=" * 60)
    return "\n".join(lines)

def should_stop():
    status = read_status()
    if not status:
        return False
    
    equity = status.get('equity', INITIAL_BALANCE)
    profit = equity - INITIAL_BALANCE
    daily_loss = status.get('daily_loss_pct', 0)
    
    if profit >= 1000:
        return True, f"PROFIT TARGET: ${profit:.2f}"
    if profit <= -800:
        return True, f"TOTAL LOSS LIMIT: ${profit:.2f}"
    if daily_loss >= 0.04:
        return True, f"DAILY LOSS LIMIT: {daily_loss:.1%}"
    
    return False, "OK"

def main():
    print("FTMO PHASE 1 - CONTINUOUS TRADING")
    print("Target: +$1,000 (+10%) to pass Phase 1")
    print("Scanning: EURUSD, GBPUSD, USDJPY, XAUUSD, EURJPY, GBPJPY, AUDJPY, EURGBP")
    print("Strategy: Trend/Range/Breakout (Conf >40%)")
    print("Risk: 0.01 lots, SL 50 pips, TP 100 pips")
    print("=" * 60)
    print()
    
    cycle = 0
    report_counter = 0
    
    while True:
        cycle += 1
        now = datetime.now()
        
        # Check if we should stop
        stop, reason = should_stop()
        if stop:
            print(f"\n*** TRADING HALTED: {reason} ***")
            break
        
        # Run trading cycle
        print(f"[{now.strftime('%H:%M:%S')}] Cycle #{cycle}: Running scan...", end=" ")
        success = run_bot()
        print("OK" if success else "FAILED")
        
        # Generate report every 6 cycles (~30 minutes if 5 min interval)
        report_counter += 1
        if report_counter >= 6 or cycle == 1:
            report = format_report(cycle)
            print("\n" + report + "\n")
            
            # Save to file
            with open(REPORT_FILE, 'w', encoding='utf-8') as f:
                f.write(report)
            
            report_counter = 0
        
        # Wait 5 minutes before next scan
        time.sleep(5 * 60)

if __name__ == "__main__":
    main()
