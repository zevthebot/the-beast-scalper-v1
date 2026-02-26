import MetaTrader5 as mt5
mt5.initialize()
info = mt5.account_info()
print(f'Account: {info.login}')
print(f'Balance: ${info.balance:.2f}')
print(f'Equity: ${info.equity:.2f}')
print(f'Positions: {mt5.positions_total()}')
for p in mt5.positions_get():
    dir = "BUY" if p.type==0 else "SELL"
    print(f'  {p.symbol} {dir} | PnL: ${p.profit:.2f}')
mt5.shutdown()
