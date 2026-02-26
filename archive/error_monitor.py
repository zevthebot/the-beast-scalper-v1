#!/usr/bin/env python3
"""
Critical Error Monitor for MT5 Trading Bot
Checks for critical errors and sends immediate notifications
"""

import MetaTrader5 as mt5
import json
from datetime import datetime, timedelta
from pathlib import Path

ERROR_LOG_PATH = Path(__file__).parent / "error_log.json"
CRITICAL_ERRORS = [
    "MT5_CONNECTION_FAILED",
    "ORDER_FAILED_REPEATEDLY", 
    "ACCOUNT_DISCONNECTED",
    "MARGIN_CALL",
    "LARGE_DRAWDOWN"
]

def check_mt5_connection():
    """Check if MT5 is connected and logged in"""
    if not mt5.initialize():
        return False, "MT5_CONNECTION_FAILED"
    
    account = mt5.account_info()
    if account is None:
        mt5.shutdown()
        return False, "ACCOUNT_DISCONNECTED"
    
    mt5.shutdown()
    return True, None

def check_account_health():
    """Check for margin issues or large drawdowns"""
    if not mt5.initialize():
        return None
    
    account = mt5.account_info()
    if account is None:
        mt5.shutdown()
        return None
    
    issues = []
    
    # Check margin level (critical if below 100%)
    margin_level = account.margin_level
    if margin_level < 100:
        issues.append(f"MARGIN_CALL: Level {margin_level:.1f}%")
    
    # Check drawdown (alert if >10%)
    balance = account.balance
    equity = account.equity
    if balance > 0:
        drawdown = (balance - equity) / balance * 100
        if drawdown > 10:
            issues.append(f"LARGE_DRAWDOWN: {drawdown:.1f}%")
    
    mt5.shutdown()
    return issues

def check_recent_errors():
    """Check for repeated order failures"""
    if not ERROR_LOG_PATH.exists():
        return []
    
    try:
        with open(ERROR_LOG_PATH, 'r') as f:
            errors = json.load(f)
        
        # Count errors in last hour
        hour_ago = datetime.now() - timedelta(hours=1)
        recent_errors = [
            e for e in errors 
            if datetime.fromisoformat(e['time']) > hour_ago
        ]
        
        order_failures = sum(1 for e in recent_errors if 'ORDER_FAILED' in e['type'])
        
        if order_failures >= 3:
            return [f"ORDER_FAILED_REPEATEDLY: {order_failures} failures in last hour"]
        
        return []
    except:
        return []

def run_monitor():
    """Main monitoring loop"""
    errors_found = []
    
    # Check MT5 connection
    connected, error = check_mt5_connection()
    if not connected:
        errors_found.append(error)
    
    # Check account health
    health_issues = check_account_health()
    if health_issues:
        errors_found.extend(health_issues)
    
    # Check recent errors
    recent_errors = check_recent_errors()
    if recent_errors:
        errors_found.extend(recent_errors)
    
    if errors_found:
        # Log the errors
        log_error(errors_found)
        # Return error message for notification
        return f"🚨 CRITICAL ERRORS DETECTED:\n" + "\n".join(f"• {e}" for e in errors_found)
    
    return None

def log_error(errors):
    """Log errors to file"""
    log_entry = {
        "time": datetime.now().isoformat(),
        "errors": errors
    }
    
    existing = []
    if ERROR_LOG_PATH.exists():
        try:
            with open(ERROR_LOG_PATH, 'r') as f:
                existing = json.load(f)
        except:
            pass
    
    existing.append(log_entry)
    
    # Keep only last 100 errors
    existing = existing[-100:]
    
    with open(ERROR_LOG_PATH, 'w') as f:
        json.dump(existing, f, indent=2)

def send_critical_alert(message):
    """Send critical alert via message tool"""
    import json
    import os
    
    # This will be handled by the cron system
    print(f"CRITICAL_ALERT:{message}")
    return True

if __name__ == "__main__":
    result = run_monitor()
    if result:
        print(result)
        # The agent will check output and decide to notify
        exit(1)  # Signal error
    else:
        print("NO_ALERT")
        exit(0)
