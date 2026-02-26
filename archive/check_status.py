"""Quick FTMO account status check"""
import MetaTrader5 as mt5
import json
from datetime import datetime

ACCOUNT = 541144102
INITIAL_BALANCE = 10000

def check_status():
    if not mt5.initialize():
        print(json.dumps({"error": "MT5 not initialized", "timestamp": datetime.now().isoformat()}))
        return
    
    info = mt5.account_info()
    if info is None:
        print(json.dumps({"error": "Not connected", "timestamp": datetime.now().isoformat()}))
        mt5.shutdown()
        return
    
    # Get positions
    positions = mt5.positions_get()
    
    # Get today's deals
    from datetime import datetime, timedelta
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    deals = mt5.history_deals_get(today, datetime.now())
    
    result = {
        "timestamp": datetime.now().isoformat(),
        "connected": True,
        "account": info.login,
        "server": info.server,
        "balance": info.balance,
        "equity": info.equity,
        "initial_balance": INITIAL_BALANCE,
        "profit_total": info.equity - INITIAL_BALANCE,
        "profit_pct": (info.equity - INITIAL_BALANCE) / INITIAL_BALANCE * 100,
        "daily_profit": info.equity - info.balance,  # Unrealized for today
        "open_positions": len(positions) if positions else 0,
        "positions_details": [],
        "today_trades": len(deals) if deals else 0
    }
    
    if positions:
        for pos in positions:
            result["positions_details"].append({
                "symbol": pos.symbol,
                "type": "BUY" if pos.type == 0 else "SELL",
                "volume": pos.volume,
                "profit": pos.profit,
                "open_price": pos.price_open,
                "current_price": pos.price_current
            })
    
    print(json.dumps(result, indent=2))
    mt5.shutdown()

if __name__ == "__main__":
    check_status()
