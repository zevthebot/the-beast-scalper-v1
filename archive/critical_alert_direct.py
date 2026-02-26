#!/usr/bin/env python3
"""
Critical Alert with Direct Message - Only alerts on actual errors
"""

import MetaTrader5 as mt5
import sys
from datetime import datetime
from pathlib import Path

# Import message tool
sys.path.insert(0, str(Path(__file__).parent.parent))

def check_and_notify():
    """Check for critical issues and send direct message if found"""
    alerts = []
    
    # Check MT5 connection
    if not mt5.initialize():
        alert_msg = "🚨 **MT5 CONNECTION FAILED**\n\nTrading bot cannot connect to MetaTrader 5. Please check if MT5 is running."
        send_alert(alert_msg)
        return
    
    # Get account info
    account = mt5.account_info()
    if account is None:
        mt5.shutdown()
        alert_msg = "🚨 **ACCOUNT DISCONNECTED**\n\nPlease login to MT5 manually (Account: 62108425)."
        send_alert(alert_msg)
        return
    
    # Check margin level
    if account.margin_level < 100:
        alerts.append(f"⚠️ MARGIN CALL: {account.margin_level:.1f}%")
    
    # Check drawdown
    if account.balance > 0:
        dd = (account.balance - account.equity) / account.balance * 100
        if dd > 10:
            alerts.append(f"⚠️ LARGE DRAWDOWN: {dd:.1f}%")
    
    mt5.shutdown()
    
    if alerts:
        alert_msg = f"**CRITICAL ALERT - {datetime.now().strftime('%H:%M')}**\n\n" + "\n".join(alerts)
        send_alert(alert_msg)
    else:
        print("NO_ALERT")

def send_alert(message):
    """Send alert - will be handled by the agent if output contains CRITICAL"""
    print(f"CRITICAL_ERROR_DETECTED:{message}")
    # Also write to file for backup
    alert_file = Path(__file__).parent / "last_critical_alert.txt"
    with open(alert_file, 'w') as f:
        f.write(f"{datetime.now().isoformat()}\n{message}")

if __name__ == "__main__":
    check_and_notify()
