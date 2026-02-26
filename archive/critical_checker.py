#!/usr/bin/env python3
"""
Critical Alert System - Sends notification ONLY on actual errors
Uses direct message for critical alerts
"""

import MetaTrader5 as mt5
import sys
from datetime import datetime
from pathlib import Path
import json

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

def check_critical_issues():
    """Check for critical issues and return alert details if found"""
    alerts = []
    
    # Check MT5 connection
    if not mt5.initialize():
        return {
            "critical": True,
            "message": "🚨 MT5 CONNECTION FAILED\n\nTrading bot cannot connect to MetaTrader 5."
        }
    
    # Get account info
    account = mt5.account_info()
    if account is None:
        mt5.shutdown()
        return {
            "critical": True,
            "message": "🚨 ACCOUNT DISCONNECTED\n\nPlease login to MT5 manually."
        }
    
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
        return {
            "critical": True,
            "message": f"**CRITICAL ALERT - {datetime.now().strftime('%H:%M')}**\n\n" + "\n".join(alerts)
        }
    
    return {"critical": False, "message": "OK"}

def send_telegram_alert(message):
    """Send alert via Telegram using direct message"""
    # This creates a system event that will be delivered
    print(f"CRITICAL_ALERT_TRIGGERED:{message}")
    return True

if __name__ == "__main__":
    result = check_critical_issues()
    
    if result["critical"]:
        # Write alert to file for pickup
        alert_file = Path(__file__).parent / "critical_alert_pending.json"
        with open(alert_file, 'w') as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "alert": result["message"]
            }, f)
        print("CRITICAL_ALERT_FILE_CREATED")
        sys.exit(1)
    else:
        print("NO_ALERT")
        sys.exit(0)
