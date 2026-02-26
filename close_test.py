import MetaTrader5 as mt5
mt5.initialize()

pos = mt5.positions_get(ticket=105655903)
if pos:
    p = pos[0]
    price = mt5.symbol_info_tick(p.symbol).bid
    request = {
        'action': mt5.TRADE_ACTION_DEAL,
        'symbol': p.symbol,
        'volume': p.volume,
        'type': mt5.ORDER_TYPE_SELL,
        'position': p.ticket,
        'price': price,
        'deviation': 10,
        'magic': 234000,
        'comment': 'Close TEST',
        'type_time': mt5.ORDER_TIME_GTC,
        'type_filling': mt5.ORDER_FILLING_IOC,
    }
    result = mt5.order_send(request)
    if result and result.retcode == mt5.TRADE_RETCODE_DONE:
        print(f'Closed @ {price} | PnL: ${p.profit:.2f}')
    else:
        print(f'Failed: {result.retcode} - {result.comment}')
else:
    print('Position not found')

mt5.shutdown()
