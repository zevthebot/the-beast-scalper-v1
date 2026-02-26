import MetaTrader5 as mt5

print('=== CLOSING XAUUSD SELL POSITION ===')
print()

if not mt5.initialize():
    print('Failed to connect to MT5')
    exit()

account = mt5.account_info()
print(f'Account: {account.login}')
print(f'Balance: {account.balance:.2f} EUR')
print()

# Find XAUUSD SELL position to close
positions = mt5.positions_get(symbol="XAUUSD")
if not positions:
    print('No XAUUSD positions found')
    mt5.shutdown()
    exit()

print(f'Found {len(positions)} XAUUSD position(s):')
for pos in positions:
    direction = "BUY" if pos.type == 0 else "SELL"
    print(f'  {direction} #{pos.ticket} @ {pos.price_open} | Profit: {pos.profit:.2f} EUR')
print()

# Close SELL positions (type 1 = SELL)
closed_count = 0
for pos in positions:
    if pos.type == 1:  # SELL position
        symbol_info = mt5.symbol_info("XAUUSD")
        
        # To close SELL, we BUY at ask
        request = {
            'action': mt5.TRADE_ACTION_DEAL,
            'position': pos.ticket,
            'symbol': 'XAUUSD',
            'volume': pos.volume,
            'type': mt5.ORDER_TYPE_BUY,  # Buy to close SELL
            'price': symbol_info.ask,
            'deviation': 10,
            'magic': 234000,
            'comment': 'Close SELL - hedging eliminated',
            'type_time': mt5.ORDER_TIME_GTC,
            'type_filling': mt5.ORDER_FILLING_IOC,
        }
        
        result = mt5.order_send(request)
        
        if result and result.retcode == mt5.TRADE_RETCODE_DONE:
            print(f'✅ CLOSED SELL #{pos.ticket} | Profit: {pos.profit:.2f} EUR')
            closed_count += 1
        else:
            error = result.comment if result else 'Unknown error'
            print(f'❌ FAILED: {error}')

print()
print(f'Closed: {closed_count} SELL position(s)')

# Check remaining XAUUSD positions
remaining = mt5.positions_get(symbol="XAUUSD")
print(f'Remaining XAUUSD positions: {len(remaining)}')
for pos in remaining:
    direction = "BUY" if pos.type == 0 else "SELL"
    print(f'  {direction} #{pos.ticket} @ {pos.price_open}')

mt5.shutdown()
print()
print('Hedging eliminated. Only one XAUUSD direction active.')
