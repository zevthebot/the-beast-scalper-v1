import sys
sys.path.insert(0, r'C:\Users\Claw\.openclaw\workspace\mt5_trader')

from bot_controller import MT5Trader, FTMO24_7SetupScanner

# Direct test execution
trader = MT5Trader()
if trader.connect():
    print("="*60)
    print("FTMO TEST TRADES - DIRECT EXECUTION")
    print("="*60)
    
    # Place test trades directly
    pairs = [
        ("EURUSD", 0),  # BUY
        ("XAUUSD", 0),  # BUY
    ]
    
    results = []
    for symbol, order_type in pairs:
        print(f"\nPlacing order: {symbol} {'BUY' if order_type == 0 else 'SELL'}")
        result = trader.place_order(
            symbol=symbol,
            order_type=order_type,
            lot_size=0.01,
            sl_pips=50,
            tp_pips=100,
            magic=234000,
            comment="FTMO TEST TRADE"
        )
        print(f"Result: {result}")
        results.append(result)
    
    print("\n" + "="*60)
    print("SUMMARY:")
    for i, res in enumerate(results):
        status = "✅ SUCCESS" if res and res.get('success') else "❌ FAILED"
        print(f"{pairs[i][0]}: {status}")
        if res and res.get('success'):
            print(f"  Ticket: {res.get('order_id')}")
            print(f"  Price: {res.get('price')}")
    
    trader.shutdown()
else:
    print("FAILED TO CONNECT")
