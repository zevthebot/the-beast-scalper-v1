import MetaTrader5 as mt5
import datetime

if not mt5.initialize():
    print('Failed to initialize MT5')
    exit()

account = mt5.account_info()
print(f'Account: {account.login}')
print(f'Balance: {account.balance:.2f} {account.currency}')
print(f'Equity: {account.equity:.2f}')
print(f'Margin: {account.margin:.2f}')
print(f'Free Margin: {account.margin_free:.2f}')
print(f'Profit: {account.profit:.2f}')
print()

positions = mt5.positions_get()
print(f'Open Positions: {len(positions)}')
print()

for pos in positions:
    profit = pos.profit + pos.swap
    direction = "BUY" if pos.type == 0 else "SELL"
    print(f'[{pos.ticket}] {pos.symbol} {direction} {pos.volume} lots @ {pos.price_open:.5f} | Current: {pos.price_current:.5f} | P/L: {profit:.2f}')

mt5.shutdown()
