"""
MT5 Position Close - Fixed Version
Properly closes positions by referencing position ticket
"""
import MetaTrader5 as mt5

def close_all_positions():
    """Close all open positions properly"""
    if not mt5.initialize():
        print("Failed to connect to MT5")
        return False
    
    account = mt5.account_info()
    print(f"Account: {account.login}")
    print(f"Balance: {account.balance:.2f} EUR")
    print()
    
    positions = mt5.positions_get()
    if not positions:
        print("No positions to close")
        mt5.shutdown()
        return True
    
    print(f"Found {len(positions)} positions to close")
    print()
    
    closed_count = 0
    failed_count = 0
    
    for pos in positions:
        symbol = pos.symbol
        symbol_info = mt5.symbol_info(symbol)
        
        if symbol_info is None:
            print(f"[ERROR] Symbol {symbol} not found")
            failed_count += 1
            continue
        
        # Determine close direction (opposite of position type)
        if pos.type == 0:  # BUY position -> SELL to close
            order_type = mt5.ORDER_TYPE_SELL
            price = symbol_info.bid
        else:  # SELL position -> BUY to close
            order_type = mt5.ORDER_TYPE_BUY
            price = symbol_info.ask
        
        # CRITICAL FIX: Include position ticket to specify which position to close
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "position": pos.ticket,  # <-- THIS WAS MISSING! Specifies which position to close
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
        
        pos_type_str = "BUY" if pos.type == 0 else "SELL"
        
        if result is None:
            print(f"[ERROR] {pos_type_str} {symbol} #{pos.ticket}: Send failed - {mt5.last_error()}")
            failed_count += 1
        elif result.retcode == mt5.TRADE_RETCODE_DONE:
            print(f"[OK] Closed {pos_type_str} {symbol} #{pos.ticket} at {price}")
            closed_count += 1
        else:
            print(f"[ERROR] {pos_type_str} {symbol} #{pos.ticket}: {result.retcode} - {result.comment}")
            failed_count += 1
    
    print()
    print(f"Results: {closed_count} closed, {failed_count} failed")
    
    # Verify
    remaining = mt5.positions_get()
    if remaining:
        print(f"Warning: {len(remaining)} positions still open")
    else:
        print("[OK] All positions closed successfully")
    
    account = mt5.account_info()
    print(f"Final Balance: {account.balance:.2f} EUR")
    print(f"Final Equity: {account.equity:.2f} EUR")
    
    mt5.shutdown()
    return len(remaining) == 0

if __name__ == "__main__":
    close_all_positions()
