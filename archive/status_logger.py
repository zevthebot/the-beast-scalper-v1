# MT5 Status Logger
# Place this in MT5 Scripts folder and run it
# It creates mt5_status.json which I can read

import MetaTrader5 as mt5
import json
import os
import time
from datetime import datetime

OUTPUT_FILE = r"C:\Users\Claw\.openclaw\workspace\mt5_trader\live_status.json"

def get_status():
    if not mt5.initialize():
        return {"error": "MT5 not initialized"}
    
    info = mt5.account_info()
    if info is None:
        mt5.shutdown()
        return {"error": "Not logged in"}
    
    positions = mt5.positions_get()
    pos_data = []
    if positions:
        for p in positions:
            pos_data.append({
                "ticket": int(p.ticket),
                "symbol": p.symbol,
                "type": "BUY" if p.type == 0 else "SELL",
                "volume": float(p.volume),
                "profit": float(p.profit),
                "swap": float(p.swap)
            })
    
    status = {
        "timestamp": datetime.now().isoformat(),
        "account": int(info.login),
        "server": info.server,
        "balance": float(info.balance),
        "equity": float(info.equity),
        "margin": float(info.margin),
        "free_margin": float(info.margin_free),
        "currency": info.currency,
        "total_profit": float(info.profit),
        "position_count": len(pos_data),
        "positions": pos_data
    }
    
    mt5.shutdown()
    return status

def save_status():
    status = get_status()
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(status, f, indent=2)
    print(f"Status saved: {OUTPUT_FILE}")
    return status

if __name__ == "__main__":
    # Run once
    result = save_status()
    print(json.dumps(result, indent=2))
