#!/usr/bin/env python3
"""
Critical Alert System - Sends notification only on actual errors
"""

import MetaTrader5 as mt5
import sys
from datetime import datetime

def check_and_alert():
    """Check for critical issues and return alert message if found"""
    alerts = []
    
    # Check MT5 connection
    if not mt5.initialize():
        alerts.append("🚨 MT5 CONNECTION FAILED")
        return "\n".join(alerts)
    
    # Get account info
    account = mt5.account_info()
    if account is None:
        mt5.shutdown()
        alerts.append("🚨 ACCOUNT DISCONNECTED")
        return "\n".join(alerts)
    
    # Check margin level
    if account.margin_level < 100:
        alerts.append(f"🚨 MARGIN CALL: {account.margin_level:.1f}%")
    
    # Check drawdown
    if account.balance > 0:
        dd = (account.balance - account.equity) / account.balance * 100
        if dd > 10:
            alerts.append(f"🚨 LARGE DRAWDOWN: {dd:.1f}%")
    
    mt5.shutdown()
    
    if alerts:
        return f"**CRITICAL ALERT - {datetime.now().strftime('%H:%M')}**\n" + "\n".join(alerts)
    
    return None  # No alert needed

if __name__ == "__main__":
    result = check_and_alert()
    if result:
        print(result)
        sys.exit(1)  # Signal there's an alert
    else:
        sys.exit(0)  # Silent - no alert
