import MetaTrader5 as mt5

if mt5.initialize():
    acc = mt5.account_info()
    if acc:
        print(f"Account: {acc.login}")
        print(f"Balance: {acc.balance:.2f} EUR")
        print(f"Equity: {acc.equity:.2f} EUR")
        print(f"Profit: {acc.profit:.2f} EUR")
        print()
        
        positions = mt5.positions_get()
        if positions:
            print(f"Open Positions: {len(positions)}")
            for p in positions:
                direction = "BUY" if p.type == 0 else "SELL"
                print(f"  {p.symbol}: {direction} @ {p.price_open:.5f} | Volume: {p.volume} | Profit: {p.profit:.2f} EUR")
        else:
            print("No open positions")
    else:
        print("Not logged in")
    mt5.shutdown()
else:
    print("MT5 not initialized")
