import MetaTrader5 as mt5
mt5.initialize()

tick = mt5.symbol_info_tick('EURUSD')
price = tick.ask
point = mt5.symbol_info('EURUSD').point
digits = mt5.symbol_info('EURUSD').digits

sl = round(price - 30 * point * 10, digits)
tp = round(price + 60 * point * 10, digits)

request = {
    'action': mt5.TRADE_ACTION_DEAL,
    'symbol': 'EURUSD',
    'volume': 0.01,
    'type': mt5.ORDER_TYPE_BUY,
    'price': price,
    'sl': sl,
    'tp': tp,
    'deviation': 10,
    'magic': 234000,
    'comment': 'Zev TEST',
    'type_time': mt5.ORDER_TIME_GTC,
    'type_filling': mt5.ORDER_FILLING_IOC,
}

result = mt5.order_send(request)
if result and result.retcode == mt5.TRADE_RETCODE_DONE:
    print(f'OK - EURUSD BUY 0.01 lots @ {price}')
    print(f'Ticket: {result.order}')
    print(f'SL: {sl} | TP: {tp}')
else:
    code = result.retcode if result else 'None'
    comment = result.comment if result else str(mt5.last_error())
    print(f'FAILED: {code} - {comment}')

mt5.shutdown()
