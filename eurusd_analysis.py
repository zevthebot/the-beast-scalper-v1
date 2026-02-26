import MetaTrader5 as mt5
import pandas as pd
import numpy as np

mt5.initialize()

# Get EURUSD M15 data
rates_m15 = mt5.copy_rates_from_pos('EURUSD', mt5.TIMEFRAME_M15, 0, 50)
df_m15 = pd.DataFrame(rates_m15)

# Bollinger Bands
df_m15['sma20'] = df_m15['close'].rolling(20).mean()
df_m15['std20'] = df_m15['close'].rolling(20).std()
df_m15['upper'] = df_m15['sma20'] + (df_m15['std20'] * 2)
df_m15['lower'] = df_m15['sma20'] - (df_m15['std20'] * 2)

latest = df_m15.iloc[-1]
prev = df_m15.iloc[-2]

print('=== EURUSD TECHNICAL ANALYSIS ===')
print(f"Price: {latest['close']:.5f}")
print(f"BB Upper: {latest['upper']:.5f}")
print(f"BB Lower: {latest['lower']:.5f}")
print(f"BB Middle (SMA20): {latest['sma20']:.5f}")
print(f"Price vs Lower BB: {latest['close'] - latest['lower']:.5f}")
print(f"Price vs Upper BB: {latest['close'] - latest['upper']:.5f}")

# Check if price is below lower band
is_below_lower = latest['close'] <= latest['lower']
print(f"\nPrice <= Lower BB: {is_below_lower}")

# Check last 3 candles for FVG
c1 = df_m15.iloc[-3]
c2 = df_m15.iloc[-2]
c3 = df_m15.iloc[-1]

print(f"\n=== FVG CHECK ===")
print(f"C1 High: {c1['high']:.5f}, Low: {c1['low']:.5f}")
print(f"C2 High: {c2['high']:.5f}, Low: {c2['low']:.5f}")
print(f"C3 High: {c3['high']:.5f}, Low: {c3['low']:.5f}")

# Bullish FVG: Low(C3) > High(C1)
bullish_fvg = c3['low'] > c1['high']
print(f"Bullish FVG (C3.low > C1.high): {bullish_fvg}")

if bullish_fvg:
    gap_top = c3['low']
    gap_bottom = c1['high']
    fill_50 = gap_bottom + (gap_top - gap_bottom) * 0.5
    print(f"Gap: {gap_bottom:.5f} - {gap_top:.5f}")
    print(f"50% fill: {fill_50:.5f}")
    print(f"Current price in gap: {gap_bottom <= c3['close'] <= gap_top}")

# H1 trend
rates_h1 = mt5.copy_rates_from_pos('EURUSD', mt5.TIMEFRAME_H1, 0, 50)
df_h1 = pd.DataFrame(rates_h1)
df_h1['ma20'] = df_h1['close'].rolling(20).mean()
df_h1['ma50'] = df_h1['close'].rolling(50).mean()

h1_latest = df_h1.iloc[-1]
print(f"\n=== H1 TREND ===")
print(f"Price: {h1_latest['close']:.5f}")
print(f"MA20: {h1_latest['ma20']:.5f}")
print(f"MA50: {h1_latest['ma50']:.5f}")
trend = "BULL" if h1_latest['close'] > h1_latest['ma20'] else "BEAR"
print(f"Trend: {trend}")

mt5.shutdown()
