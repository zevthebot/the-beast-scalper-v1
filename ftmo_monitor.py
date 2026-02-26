"""
FTMO Phase 1 - Continuous Trading Monitor
Runs bot in loop, reports every 30 minutes, enforces FTMO limits
"""
import subprocess
import json
import time
import os
from datetime import datetime, timedelta

# FTMO Configuration
INITIAL_BALANCE = 10000
PROFIT_TARGET = 1000  # $1,000 = 10%
MAX_DAILY_LOSS = 400  # $400 = 4%
MAX_TOTAL_LOSS = 800  # $800 = 8%
REPORT_INTERVAL = 30 * 60  # 30 minutes in seconds

def run_bot():
    """Run one trading cycle"""
    try:
        result = subprocess.run(
            ['python', 'bot_controller.py', '--trade'],
            cwd=r'C:\Users\Claw\.openclaw\workspace\mt5_trader',
            capture_output=True,
            text=True,
            timeout=120
        )
        return result.stdout + result.stderr
    except Exception as e:
        return f"Error running bot: {e}"

def read_status():
    """Read status JSON from bot"""
    try:
        status_file = r'C:\Users\Claw\.openclaw\workspace\mt5_trader\mt5_ftmo_status.json'
        if os.path.exists(status_file):
            with open(status_file, 'r') as f:
                return json.load(f)
    except Exception as e:
        return None
    return None

def format_report(status, bot_output, cycle_num):
    """Format status report"""
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    if not status:
        return f"""
╔═══════════════════════════════════════════════════════════╗
║  FTMO PHASE 1 MONITOR - Cycle #{cycle_num}                        ║
║  Time: {now}                              ║
╠═══════════════════════════════════════════════════════════╣
║  Status: Unable to read account data                      ║
║  Bot Output:                                              ║
{bot_output[-500:] if len(bot_output) > 500 else bot_output}
╚═══════════════════════════════════════════════════════════╝
"""
    
    balance = status.get('balance', 0)
    equity = status.get('equity', 0)
    profit = status.get('profit', 0)
    profit_pct = status.get('profit_pct', 0) * 100
    positions = status.get('positions', [])
    
    # Calculate metrics
    daily_pnl = equity - balance + profit  # Approximate
    total_pnl = equity - INITIAL_BALANCE
    total_pnl_pct = (total_pnl / INITIAL_BALANCE) * 100
    
    # Status indicators
    profit_status = "✅ TARGET MET!" if total_pnl >= PROFIT_TARGET else f"${total_pnl:.2f} ({total_pnl_pct:.1f}%)"
    daily_loss_status = "🚨 STOP!" if daily_pnl <= -MAX_DAILY_LOSS else f"${daily_pnl:.2f}"
    total_loss_status = "🚨 STOP!" if total_pnl <= -MAX_TOTAL_LOSS else f"${total_pnl:.2f}"
    
    # Position summary
    pos_summary = ""
    if positions:
        for pos in positions[:3]:  # Show max 3 positions
            pos_summary += f"\n║    • {pos.get('symbol')} {pos.get('type')} | P&L: ${pos.get('profit', 0):.2f}"
    else:
        pos_summary = "\n║    No open positions"
    
    return f"""
╔═══════════════════════════════════════════════════════════╗
║  📊 FTMO PHASE 1 MONITOR - Cycle #{cycle_num}                       ║
║  🕐 {now}                              ║
╠═══════════════════════════════════════════════════════════╣
║  💰 ACCOUNT STATUS                                        ║
║     Balance: ${balance:,.2f}                               ║
║     Equity:  ${equity:,.2f}                               ║
║     Profit:  ${profit:.2f}                                 ║
╠═══════════════════════════════════════════════════════════╣
║  🎯 PROGRESS TO TARGET (+$1,000 = +10%)                   ║
║     {profit_status:<50}    ║
╠═══════════════════════════════════════════════════════════╣
║  🛡️ FTMO LIMITS CHECK                                     ║
║     Daily P&L:  {daily_loss_status:<45}    ║
║     Total P&L:  {total_loss_status:<45}    ║
║     Positions:  {len(positions)}/5                                        ║
╠═══════════════════════════════════════════════════════════╣
║  📈 OPEN POSITIONS{pos_summary}
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
"""

def should_stop_trading(status):
    """Check if we should stop trading due to limits"""
    if not status:
        return False, "No status available"
    
    equity = status.get('equity', INITIAL_BALANCE)
    total_pnl = equity - INITIAL_BALANCE
    
    # Check profit target reached
    if total_pnl >= PROFIT_TARGET:
        return True, f"🎉 PROFIT TARGET REACHED! ${total_pnl:.2f} ({(total_pnl/INITIAL_BALANCE)*100:.1f}%)"
    
    # Check daily loss limit
    if total_pnl <= -MAX_DAILY_LOSS:
        return True, f"🚨 DAILY LOSS LIMIT REACHED: ${total_pnl:.2f}"
    
    # Check total loss limit
    if total_pnl <= -MAX_TOTAL_LOSS:
        return True, f"🚨 TOTAL LOSS LIMIT REACHED: ${total_pnl:.2f}"
    
    return False, "Within limits"

def main():
    """Main monitoring loop"""
    print("""
╔═══════════════════════════════════════════════════════════╗
║     🤖 FTMO PHASE 1 - CONTINUOUS TRADING BOT              ║
║                                                           ║
║  Target:  +$1,000 (+10%) to pass Phase 1                  ║
║  Pairs:   EURUSD, GBPUSD, USDJPY, XAUUSD                  ║
║           EURJPY, GBPJPY, AUDJPY, EURGBP                  ║
║  Strategy: Trend/Range/Breakout (Conf >40%)               ║
║  Risk:    0.01 lots, SL 50 pips, TP 100 pips              ║
║                                                           ║
║  STOP CONDITIONS:                                         ║
║  • Daily loss ≥ $400 (4%)                                 ║
║  • Total loss ≥ $800 (8%)                                 ║
║  • Profit target reached (+$1,000)                        ║
╚═══════════════════════════════════════════════════════════╝
""")
    
    cycle = 0
    next_report_time = datetime.now()
    
    while True:
        cycle += 1
        now = datetime.now()
        
        print(f"\n[Cycle #{cycle}] Running trading scan at {now.strftime('%H:%M:%S')}...")
        
        # Run bot
        output = run_bot()
        
        # Read status
        status = read_status()
        
        # Check if we should stop
        should_stop, stop_reason = should_stop_trading(status)
        
        if should_stop:
            print(f"\n{'='*60}")
            print(f"TRADING HALTED: {stop_reason}")
            print(f"{'='*60}")
            break
        
        # Generate report if it's time
        if now >= next_report_time:
            report = format_report(status, output, cycle)
            print(report)
            
            # Write report to file for external monitoring
            report_file = r'C:\Users\Claw\.openclaw\workspace\mt5_trader\ftmo_report.txt'
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(report)
            
            next_report_time = now + timedelta(seconds=REPORT_INTERVAL)
            print(f"Next report at: {next_report_time.strftime('%H:%M:%S')}")
        else:
            # Minimal output between reports
            if status:
                equity = status.get('equity', 0)
                total_pnl = equity - INITIAL_BALANCE
                positions = len(status.get('positions', []))
                print(f"  Equity: ${equity:.2f} | P&L: ${total_pnl:.2f} | Positions: {positions}")
        
        # Wait before next scan (check every 5 minutes)
        print(f"  Waiting 5 minutes before next scan...")
        time.sleep(5 * 60)

if __name__ == "__main__":
    main()
