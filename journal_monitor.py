"""
Zev Journal Monitor — Lightweight monitoring script for cron job.
Reads EA status, maintains trade journal, detects changes.

Usage: python journal_monitor.py [--check|--report|--journal]
  --check   : Quick status check, output only if something changed or noteworthy
  --report  : Full status report
  --journal : Show recent journal entries
"""

import json
import os
import sys
import csv
from datetime import datetime, timezone
from pathlib import Path

# Paths
WORKSPACE = Path(r"C:\Users\Claw\.openclaw\workspace\mt5_trader")
JOURNAL_FILE = WORKSPACE / "trade_journal.jsonl"
STATE_FILE = WORKSPACE / "monitor_state.json"

# EA writes to MT5 Common Files directory
MT5_COMMON_FILES = Path(r"C:\Users\Claw\AppData\Roaming\MetaQuotes\Terminal\Common\Files")
EA_STATUS_FILE = MT5_COMMON_FILES / "ZevBot_Status.json"
EA_TRADE_LOG = MT5_COMMON_FILES / "ZevBot_TradeLog.csv"

# Fallback: check workspace too (Python bot may write here)
FALLBACK_STATUS = WORKSPACE / "mt5_ftmo_status.json"


def load_json(path):
    """Load JSON file, return None on error."""
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except:
        return None


def load_state():
    """Load previous monitor state."""
    return load_json(STATE_FILE) or {
        "last_check": None,
        "last_balance": 0,
        "last_equity": 0,
        "last_positions": [],
        "last_position_count": 0,
        "milestones_reported": [],
        "trades_logged": 0,
        "daily_high_equity": 0,
        "account": None,
        "phase": None
    }


def save_state(state):
    """Save monitor state."""
    state["last_check"] = datetime.now(timezone.utc).isoformat()
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)


def get_status():
    """Get current EA status from available sources."""
    # Try EA status file first
    status = load_json(EA_STATUS_FILE)
    if status:
        return status, "EA"
    
    # Fallback to Python bot status
    status = load_json(FALLBACK_STATUS)
    if status:
        return status, "PythonBot"
    
    return None, None


def get_new_trades(state):
    """Read EA trade log CSV and find new entries."""
    if not EA_TRADE_LOG.exists():
        return []
    
    try:
        new_trades = []
        with open(EA_TRADE_LOG, 'r') as f:
            reader = csv.DictReader(f)
            count = 0
            for row in reader:
                count += 1
                if count > state.get("trades_logged", 0):
                    new_trades.append(row)
        return new_trades
    except:
        return []


def count_csv_rows():
    """Count data rows in trade log CSV."""
    if not EA_TRADE_LOG.exists():
        return 0
    try:
        with open(EA_TRADE_LOG, 'r') as f:
            return max(0, sum(1 for _ in f) - 1)  # Minus header
    except:
        return 0


def log_journal_entry(entry):
    """Append entry to trade journal JSONL."""
    entry["logged_at"] = datetime.now(timezone.utc).isoformat()
    with open(JOURNAL_FILE, 'a') as f:
        f.write(json.dumps(entry) + "\n")


def detect_milestones(profit_pct, reported):
    """Check if new milestones were hit."""
    milestones = [2, 4, 5, 6, 7, 8, 9, 10]
    new_milestones = []
    for m in milestones:
        if profit_pct >= m and m not in reported:
            new_milestones.append(m)
    return new_milestones


def detect_position_changes(current_positions, last_positions):
    """Detect opened/closed positions."""
    current_tickets = {p.get("ticket") for p in current_positions}
    last_tickets = {p.get("ticket") for p in last_positions}
    
    opened = current_tickets - last_tickets
    closed = last_tickets - current_tickets
    
    return opened, closed


def check(verbose=False):
    """Main check routine. Returns status string or None if nothing noteworthy."""
    status, source = get_status()
    if not status:
        return "ERROR: Cannot read EA status. MT5 may be disconnected."
    
    state = load_state()
    output_parts = []
    noteworthy = False
    
    # Extract key metrics
    balance = status.get("balance", 0)
    equity = status.get("equity", 0)
    positions = status.get("positions", [])
    pos_count = len(positions)
    account = status.get("account", "unknown")
    server = status.get("server", "unknown")
    
    # FILTER: Only monitor FTMO Challenge account 541144102
    TARGET_ACCOUNT = 541144102
    if str(account) != str(TARGET_ACCOUNT):
        return f"INFO: Status file shows account {account}, not target {TARGET_ACCOUNT}. Skipping." if verbose else None
    
    # Calculate profit
    starting = status.get("starting_balance", status.get("ftmo_limits", {}).get("starting_balance", 10000))
    profit_pct = ((balance - starting) / starting) * 100 if starting > 0 else 0
    
    # FTMO daily loss
    daily_loss = status.get("daily_loss_pct", status.get("ftmo", {}).get("daily_loss_current", 0))
    if isinstance(daily_loss, float) and daily_loss > 1:  # Already in percentage
        pass
    elif isinstance(daily_loss, float):  # In decimal
        daily_loss *= 100
    
    # Detect position changes
    opened, closed = detect_position_changes(positions, state.get("last_positions", []))
    
    if opened:
        noteworthy = True
        for ticket in opened:
            pos = next((p for p in positions if p.get("ticket") == ticket), None)
            if pos:
                output_parts.append(f"NEW TRADE: {pos.get('symbol')} {pos.get('type')} {pos.get('volume')} lots @ {pos.get('open_price')}")
                # Log to journal
                log_journal_entry({
                    "event": "TRADE_OPEN",
                    "account": account,
                    "server": server,
                    "ticket": ticket,
                    "symbol": pos.get("symbol"),
                    "direction": pos.get("type"),
                    "volume": pos.get("volume"),
                    "entry_price": pos.get("open_price"),
                    "sl": pos.get("sl"),
                    "tp": pos.get("tp"),
                    "comment": pos.get("comment", "")
                })
    
    if closed:
        noteworthy = True
        for ticket in closed:
            old_pos = next((p for p in state.get("last_positions", []) if p.get("ticket") == ticket), None)
            if old_pos:
                output_parts.append(f"TRADE CLOSED: {old_pos.get('symbol')} {old_pos.get('type')} (was {old_pos.get('profit', 0):.2f} floating)")
                log_journal_entry({
                    "event": "TRADE_CLOSE",
                    "account": account,
                    "server": server,
                    "ticket": ticket,
                    "symbol": old_pos.get("symbol"),
                    "direction": old_pos.get("type"),
                    "volume": old_pos.get("volume"),
                    "last_known_profit": old_pos.get("profit"),
                    "balance_after": balance
                })
    
    # Check milestones
    new_milestones = detect_milestones(profit_pct, state.get("milestones_reported", []))
    if new_milestones:
        noteworthy = True
        for m in new_milestones:
            if m == 10:
                output_parts.append(f"FTMO TARGET HIT: +{m}% profit! Phase complete!")
            else:
                output_parts.append(f"MILESTONE: +{m}% profit reached")
        state.setdefault("milestones_reported", []).extend(new_milestones)
    
    # FTMO risk alerts
    if daily_loss >= 3.0:
        noteworthy = True
        output_parts.append(f"RISK ALERT: Daily loss at {daily_loss:.1f}% (limit: 4%)")
    
    # Process new trades from EA log
    new_ea_trades = get_new_trades(state)
    for trade in new_ea_trades:
        log_journal_entry({
            "event": "EA_TRADE_LOG",
            "account": account,
            "server": server,
            **trade
        })
    state["trades_logged"] = count_csv_rows()
    
    # Update state
    state["last_balance"] = balance
    state["last_equity"] = equity
    state["last_positions"] = positions
    state["last_position_count"] = pos_count
    state["account"] = account
    if equity > state.get("daily_high_equity", 0):
        state["daily_high_equity"] = equity
    
    save_state(state)
    
    # Build output
    if verbose or noteworthy:
        header = f"Account: {account} | Balance: ${balance:.2f} | Equity: ${equity:.2f} | Profit: {profit_pct:.2f}% | Positions: {pos_count}"
        
        if output_parts:
            return header + "\n" + "\n".join(output_parts)
        elif verbose:
            pos_detail = ""
            for p in positions:
                pos_detail += f"\n  {p.get('symbol')} {p.get('type')} {p.get('volume')} lots | PnL: ${p.get('profit', 0):.2f}"
            return header + pos_detail
        return header
    
    return None  # Nothing noteworthy


def report():
    """Full status report."""
    return check(verbose=True) or "No data available."


def show_journal(limit=20):
    """Show recent journal entries."""
    if not JOURNAL_FILE.exists():
        return "No journal entries yet."
    
    entries = []
    with open(JOURNAL_FILE, 'r') as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except:
                    pass
    
    if not entries:
        return "No journal entries yet."
    
    recent = entries[-limit:]
    output = f"=== Trade Journal ({len(entries)} total entries, showing last {len(recent)}) ===\n"
    for e in recent:
        event = e.get("event", "?")
        ts = e.get("logged_at", "?")[:19]
        sym = e.get("symbol", "?")
        direction = e.get("direction", "")
        
        if event == "TRADE_OPEN":
            output += f"  [{ts}] OPEN: {sym} {direction} {e.get('volume')} lots @ {e.get('entry_price')}\n"
        elif event == "TRADE_CLOSE":
            output += f"  [{ts}] CLOSE: {sym} {direction} | Last PnL: ${e.get('last_known_profit', 0):.2f}\n"
        else:
            output += f"  [{ts}] {event}: {sym} {direction}\n"
    
    return output


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "--check"
    
    if mode == "--check":
        result = check()
        if result:
            print(result)
        else:
            print("HEARTBEAT_OK")
    elif mode == "--report":
        print(report())
    elif mode == "--journal":
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 20
        print(show_journal(limit))
    else:
        print(f"Unknown mode: {mode}")
        print("Usage: python journal_monitor.py [--check|--report|--journal]")
