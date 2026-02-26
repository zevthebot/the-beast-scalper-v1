import MetaTrader5 as mt5
import pandas as pd

if mt5.initialize():
    print('=== RANGE TRADING ANALYSIS (Tokyo Session Strategy) ===')
    print()
    
    pairs = ['USDJPY', 'EURJPY', 'AUDJPY']
    
    for symbol in pairs:
        print(f'--- {symbol} ---')
        
        # Get H1 for range
        rates_h1 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 0, 24)
        rates_m15 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M15, 0, 20)
        
        if rates_h1 is None or rates_m15 is None:
            print('  Data unavailable')
            continue
        
        df_h1 = pd.DataFrame(rates_h1)
        df_m15 = pd.DataFrame(rates_m15)
        
        # Calculate range
        range_high = df_h1['high'].max()
        range_low = df_h1['low'].min()
        range_mid = (range_high + range_low) / 2
        
        # Bollinger Bands
        df_m15['sma20'] = df_m15['close'].rolling(20).mean()
        df_m15['std20'] = df_m15['close'].rolling(20).std()
        df_m15['upper_band'] = df_m15['sma20'] + (df_m15['std20'] * 2)
        df_m15['lower_band'] = df_m15['sma20'] - (df_m15['std20'] * 2)
        
        latest = df_m15.iloc[-1]
        price = latest['close']
        
        point = mt5.symbol_info(symbol).point
        
        print(f'  Current Price: {price:.3f}')
        print(f'  24h Range: {range_low:.3f} - {range_high:.3f}')
        print(f'  Mid: {range_mid:.3f}')
        print(f'  Bollinger Lower: {latest["lower_band"]:.3f}')
        print(f'  Bollinger Upper: {latest["upper_band"]:.3f}')
        
        # Signal
        if price <= latest['lower_band'] or price <= range_low + (range_high-range_low)*0.1:
            signal = 'BUY'
            sl = range_low - 10 * point
            tp = range_mid
            print(f'  SIGNAL: {signal}')
            print(f'  Entry: {price:.3f}')
            print(f'  SL: {sl:.3f}')
            print(f'  TP: {tp:.3f}')
        elif price >= latest['upper_band'] or price >= range_high - (range_high-range_low)*0.1:
            signal = 'SELL'
            sl = range_high + 10 * point
            tp = range_mid
            print(f'  SIGNAL: {signal}')
            print(f'  Entry: {price:.3f}')
            print(f'  SL: {sl:.3f}')
            print(f'  TP: {tp:.3f}')
        else:
            print(f'  SIGNAL: No signal (price in middle of range)')
        
        print()
    
    mt5.shutdown()
