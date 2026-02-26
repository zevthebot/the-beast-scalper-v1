# Quick script to check MT5 status and history
import MetaTrader5 as mt5
from datetime import datetime, timedelta

def show_mt5_status():
    """Display MT5 account status and positions"""
    if not mt5.initialize():
        print("Failed to connect to MT5")
        return
    
    # Account info
    account = mt5.account_info()
    print(f"Account: {account.login}")
    print(f"Balance: {account.balance:.2f} {account.currency}")
    print(f"Equity: {account.equity:.2f}")
    print(f"Profit: {account.profit:.2f}")
    print()
    
    # Open positions
    print("--- Open Positions ---")
    positions = mt5.positions_get()
    if positions:
        for p in positions:
            pos_type = 'BUY' if p.type == 0 else 'SELL'
            print(f"  {p.symbol} | {pos_type} | Vol: {p.volume} | Profit: {p.profit:.2f} | Open: {p.price_open}")
    else:
        print("  No open positions")
    print()
    
    mt5.shutdown()

def show_trade_history(days_back=1):
    """Display trade history for specified days
    
    HOW TO USE:
    - Run: python mt5_history.py
    - Or import: from mt5_history import show_trade_history
    - Call: show_trade_history(days_back=7) for last week
    """
    if not mt5.initialize():
        print("Failed to connect to MT5")
        return
    
    from_date = datetime.now() - timedelta(days=days_back)
    to_date = datetime.now()
    
    print(f"--- Trade History (Last {days_back} day(s)) ---")
    
    # Get deals (executed trades)
    deals = mt5.history_deals_get(from_date, to_date)
    if deals:
        print(f"\nDeals ({len(deals)} total):")
        for d in deals:
            deal_type = 'BUY' if d.type == 0 else 'SELL'
            time_str = datetime.fromtimestamp(d.time).strftime('%Y-%m-%d %H:%M:%S')
            print(f"  {time_str} | {d.symbol} | {deal_type} | Vol: {d.volume} | Price: {d.price} | Profit: {d.profit:.2f}")
    else:
        print("\n  No deals found")
    
    # Get orders (placed orders, including cancelled)
    orders = mt5.history_orders_get(from_date, to_date)
    if orders:
        print(f"\nOrders ({len(orders)} total):")
        for o in orders:
            order_type = 'BUY' if o.type == 0 else 'SELL'
            time_str = datetime.fromtimestamp(o.time_setup).strftime('%Y-%m-%d %H:%M:%S')
            state_names = ['Started', 'Placed', 'Canceled', 'Partial', 'Filled', 'Rejected', 'Expired']
            state = state_names[o.state] if o.state < len(state_names) else str(o.state)
            print(f"  {time_str} | {o.symbol} | {order_type} | State: {state}")
    else:
        print("\n  No orders found")
    
    mt5.shutdown()

def close_all_positions(symbol="EURUSD"):
    """Close all positions for a symbol"""
    if not mt5.initialize():
        print("Failed to connect to MT5")
        return
    
    positions = mt5.positions_get(symbol=symbol)
    if not positions:
        print(f"No positions found for {symbol}")
        mt5.shutdown()
        return
    
    symbol_info = mt5.symbol_info(symbol)
    
    for pos in positions:
        # Determine close direction
        if pos.type == 0:  # BUY -> SELL to close
            order_type = mt5.ORDER_TYPE_SELL
            price = symbol_info.bid
        else:  # SELL -> BUY to close
            order_type = mt5.ORDER_TYPE_BUY
            price = symbol_info.ask
        
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": pos.volume,
            "type": order_type,
            "price": price,
            "deviation": 10,
            "magic": 234000,
            "comment": "Close Position",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        
        result = mt5.order_send(request)
        
        if result and result.retcode == mt5.TRADE_RETCODE_DONE:
            print(f"[OK] Closed {symbol} position: {result.order}")
        else:
            print(f"[ERROR] Failed to close: {result.comment if result else 'Unknown error'}")
    
    mt5.shutdown()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--history":
            days = int(sys.argv[2]) if len(sys.argv) > 2 else 1
            show_trade_history(days_back=days)
        elif sys.argv[1] == "--close":
            symbol = sys.argv[2] if len(sys.argv) > 2 else "EURUSD"
            close_all_positions(symbol)
        elif sys.argv[1] == "--status":
            show_mt5_status()
    else:
        show_mt5_status()
        print("\n--- Usage ---")
        print("python mt5_history.py              # Show status")
        print("python mt5_history.py --status     # Show status")
        print("python mt5_history.py --history    # Show today's history")
        print("python mt5_history.py --history 7  # Show last 7 days")
        print("python mt5_history.py --close      # Close EURUSD positions")
        print("python mt5_history.py --close GBPUSD  # Close GBPUSD positions")
