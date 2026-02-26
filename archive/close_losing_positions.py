import MetaTrader5 as mt5

print('=== CLOSING LOSING POSITIONS ===')
print()

if not mt5.initialize():
    print('Failed to connect')
    exit()

account = mt5.account_info()
print(f'Account: {account.login}')
print(f'Balance: {account.balance:.2f} EUR')
print()

# Get all positions
positions = mt5.positions_get()
if not positions:
    print('No positions to close')
    mt5.shutdown()
    exit()

# Close positions with negative profit
closed_count = 0
total_loss = 0

for pos in positions:
    if pos.profit < 0:
        symbol = pos.symbol
        symbol_info = mt5.symbol_info(symbol)
        
        # Determine close direction
        if pos.type == 0:  # BUY -> SELL to close
            order_type = mt5.ORDER_TYPE_SELL
            price = symbol_info.bid
        else:  # SELL -> BUY to close
            order_type = mt5.ORDER_TYPE_BUY
            price = symbol_info.ask
        
        request = {
            'action': mt5.TRADE_ACTION_DEAL,
            'position': pos.ticket,
            'symbol': symbol,
            'volume': pos.volume,
            'type': order_type,
            'price': price,
            'deviation': 10,
            'magic': 234000,
            'comment': 'Close losing position',
            'type_time': mt5.ORDER_TIME_GTC,
            'type_filling': mt5.ORDER_FILLING_IOC,
        }
        
        result = mt5.order_send(request)
        
        if result and result.retcode == mt5.TRADE_RETCODE_DONE:
            print(f'[CLOSED] {symbol} {pos.profit:.2f} EUR')
            closed_count += 1
            total_loss += pos.profit
        else:
            error = result.comment if result else 'Unknown error'
            print(f'[FAILED] {symbol}: {error}')

print()
print(f'Closed: {closed_count} positions')
print(f'Total loss: {total_loss:.2f} EUR')

# Check remaining
remaining = mt5.positions_get()
print(f'Remaining positions: {len(remaining)}')

for pos in remaining:
    print(f'  {pos.symbol}: {pos.profit:.2f} EUR')

mt5.shutdown()
print()
print('Slots freed for new opportunities!')
