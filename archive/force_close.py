import MetaTrader5 as mt5

if mt5.initialize():
    print('Force closing ALL positions...')
    
    positions = mt5.positions_get()
    closed = 0
    attempts = 0
    max_attempts = 20
    
    while positions and len(positions) > 0 and attempts < max_attempts:
        attempts += 1
        print(f'Attempt {attempts}: {len(positions)} positions')
        
        for pos in positions:
            symbol = pos.symbol
            symbol_info = mt5.symbol_info(symbol)
            
            if pos.type == 0:  # BUY -> SELL
                order_type = mt5.ORDER_TYPE_SELL
                price = symbol_info.bid
            else:  # SELL -> BUY
                order_type = mt5.ORDER_TYPE_BUY
                price = symbol_info.ask
            
            request = {
                'action': mt5.TRADE_ACTION_DEAL,
                'symbol': symbol,
                'volume': pos.volume,
                'type': order_type,
                'price': price,
                'deviation': 10,
                'magic': 234000,
                'comment': 'Force Close',
                'type_time': mt5.ORDER_TIME_GTC,
                'type_filling': mt5.ORDER_FILLING_IOC,
            }
            
            result = mt5.order_send(request)
            if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                closed += 1
                print(f'  Closed position {pos.ticket}')
            else:
                error_msg = result.comment if result else 'unknown'
                print(f'  Failed {pos.ticket}: {error_msg}')
        
        positions = mt5.positions_get()
    
    print(f'Total closed: {closed}')
    
    # Final check
    positions = mt5.positions_get()
    if not positions:
        print('[OK] All positions closed')
    else:
        print(f'Warning: {len(positions)} positions still open')
    
    account = mt5.account_info()
    print(f'Balance: {account.balance:.2f} EUR')
    print(f'Equity: {account.equity:.2f} EUR')
    
    mt5.shutdown()
