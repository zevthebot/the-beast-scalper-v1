import MetaTrader5 as mt5
from datetime import datetime

mt5.initialize()
info = mt5.account_info()
print(f"[{datetime.now().strftime('%H:%M:%S')}] Connected: {info.login}")

symbol = 'EURUSD'
symbol_info = mt5.symbol_info(symbol)
tick = mt5.symbol_info_tick(symbol)

# Trade parameters for $100 with 3:1 RR
lot_size = 0.10
sl_pips = 20
tp_pips = 60

entry = tick.ask
sl = entry - sl_pips * 0.0001
tp = entry + tp_pips * 0.0001

request = {
    'action': mt5.TRADE_ACTION_DEAL,
    'symbol': symbol,
    'volume': lot_size,
    'type': mt5.ORDER_TYPE_BUY,
    'price': entry,
    'sl': sl,
    'tp': tp,
    'deviation': 10,
    'magic': 234000,
    'comment': 'TEST 3RR',
    'type_time': mt5.ORDER_TIME_GTC,
    'type_filling': mt5.ORDER_FILLING_IOC,
}

result = mt5.order_send(request)

if result.retcode == mt5.TRADE_RETCODE_DONE:
    print()
    print("[OK] TEST TRADE EXECUTED SUCCESSFULLY!")
    print(f"Order ID: {result.order}")
    print(f"Deal ID: {result.deal}")
    print(f"Volume: {result.volume} lots")
    print(f"Entry Price: {result.price}")
    print(f"Stop Loss: {sl:.5f} ({sl_pips} pips)")
    print(f"Take Profit: {tp:.5f} ({tp_pips} pips)")
    print("Risk/Reward: 1:3")
    
    # Log to file
    with open('trading_log.txt', 'a') as f:
        f.write(f"[{datetime.now()}] EXECUTED | {symbol} | BUY {lot_size} lots @ {result.price} | SL:{sl:.5f} TP:{tp:.5f} | 3RR TEST\n")
else:
    print(f"[ERROR] Trade failed. Retcode: {result.retcode}")
    print(f"Comment: {result.comment}")

# Check open positions
positions = mt5.positions_get()
print()
print(f"Open Positions: {len(positions)}")
for pos in positions:
    print(f"  {pos.symbol}: {pos.volume} lots | Profit: {pos.profit:.2f} {info.currency}")

mt5.shutdown()
