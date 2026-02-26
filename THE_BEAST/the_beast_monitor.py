#!/usr/bin/env python3
"""
THE BEAST Monitor - Journal Monitor pentru contul 541144102
Verifică trade_journal.jsonl și raportează doar pentru contul target

Usage: python the_beast_monitor.py
"""

import json
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Configuration
TARGET_ACCOUNT = 541144102
JOURNAL_FILE = Path(r"C:\Users\Claw\.openclaw\workspace\mt5_trader\trade_journal.jsonl")
STATE_FILE = Path(r"C:\Users\Claw\.openclaw\workspace\mt5_trader\THE_BEAST\monitor_state_541144102.json")

def load_state():
    """Load previous monitor state"""
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return {
        "last_check": None,
        "last_trade_count": 0,
        "reported_milestones": [],
        "last_alert_time": None
    }

def save_state(state):
    """Save monitor state"""
    try:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        print(f"[ERROR] Could not save state: {e}")

def read_journal():
    """Read journal entries for target account"""
    if not JOURNAL_FILE.exists():
        return []
    
    entries = []
    try:
        with open(JOURNAL_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    # Filter for target account only
                    if str(entry.get('account', '')) == str(TARGET_ACCOUNT):
                        entries.append(entry)
                except json.JSONDecodeError:
                    continue
    except Exception as e:
        print(f"[ERROR] Could not read journal: {e}")
    
    return entries

def check_new_trades(entries, state):
    """Check for new trades since last check"""
    current_count = len(entries)
    last_count = state.get('last_trade_count', 0)
    
    if current_count > last_count:
        # New entries
        new_entries = entries[last_count:]
        
        opens = [e for e in new_entries if e.get('event') == 'TRADE_OPEN']
        closes = [e for e in new_entries if 'close' in e.get('event', '').lower() or e.get('event') == 'TRADE_CLOSE']
        
        return opens, closes, current_count
    
    return [], [], current_count

def check_milestones(entries):
    """Check for profit milestones"""
    if not entries:
        return []
    
    # Calculate total PnL from closed trades
    total_pnl = 0
    for entry in entries:
        if entry.get('event') == 'TRADE_CLOSE':
            total_pnl += entry.get('pnl', 0)
    
    # Calculate profit percentage
    starting_balance = 10000
    profit_pct = (total_pnl / starting_balance) * 100
    
    milestones = [6, 7, 8, 9, 10]
    new_milestones = []
    
    for m in milestones:
        if profit_pct >= m:
            new_milestones.append(m)
    
    return new_milestones, profit_pct, total_pnl

def check_risk_alerts(entries):
    """Check for risk alerts (daily loss approaching limits)"""
    # This would require access to current equity data
    # For now, we'll skip this and rely on the bot's internal checks
    return []

def format_output(opens, closes, milestones, profit_pct, total_pnl, entry_count):
    """Format output for Telegram"""
    lines = []
    
    if opens or closes or milestones:
        lines.append("[REPORT] THE BEAST Activity")
        lines.append("")
        
        if opens:
            lines.append("[OPEN] New Trades Opened:")
            for trade in opens[-3:]:  # Show max 3 recent
                symbol = trade.get('symbol', 'UNKNOWN')
                direction = trade.get('direction', 'BUY')
                volume = trade.get('volume', 0)
                price = trade.get('entry_price', 0)
                lines.append(f"  - {symbol} {direction} {volume} lots @ {price}")
            lines.append("")
        
        if closes:
            lines.append("[CLOSE] Trades Closed:")
            for trade in closes[-3:]:
                symbol = trade.get('symbol', 'UNKNOWN')
                pnl = trade.get('pnl', 0)
                status = "PROFIT" if pnl > 0 else "LOSS" if pnl < 0 else "BREAKEVEN"
                lines.append(f"  - {symbol}: {pnl:+.2f} USD [{status}]")
            lines.append("")
        
        if milestones:
            lines.append("[MILESTONE] TARGET REACHED!")
            for m in milestones:
                lines.append(f"  - Profit: +{m}% ({total_pnl:+.2f} USD)")
            lines.append("")
        
        lines.append(f"Total Trades: {entry_count}")
        lines.append(f"Current PnL: {total_pnl:+.2f} USD ({profit_pct:.2f}%)")
        lines.append(f"Target: 10% ($11,000)")
        
        return "\n".join(lines)
    
    return "HEARTBEAT_OK"

def main():
    """Main monitor function"""
    # Load state
    state = load_state()
    
    # Read journal
    entries = read_journal()
    
    # Check for new activity
    opens, closes, entry_count = check_new_trades(entries, state)
    milestones, profit_pct, total_pnl = check_milestones(entries)
    
    # Filter milestones to only new ones
    reported = state.get('reported_milestones', [])
    new_milestones = [m for m in milestones if m not in reported]
    
    # Update reported milestones
    state['reported_milestones'] = list(set(reported + milestones))
    
    # Format output
    output = format_output(opens, closes, new_milestones, profit_pct, total_pnl, entry_count)
    
    # Update state
    state['last_check'] = datetime.now(timezone.utc).isoformat()
    state['last_trade_count'] = entry_count
    state['last_pnl'] = total_pnl
    state['last_profit_pct'] = profit_pct
    
    save_state(state)
    
    print(output)
    
    return 0

if __name__ == "__main__":
    exit(main())
