#!/usr/bin/env python3
"""Diagnostic script for EURUSD"""
import MetaTrader5 as mt5
import pandas as pd
import numpy as np

print('='*60)
print('DIAGNOSTIC COMPLET: EURUSD')
print('='*60)

mt5.initialize()

symbol = 'EURUSD'
rates_m15 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M15, 0, 100)
rates_h1 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 0, 100)
rates_h4 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H4, 0, 200)
tick = mt5.symbol_info_tick(symbol)

if rates_m15 is None or rates_h1 is None or tick is None:
    print('ERROR: Cannot get data')
    mt5.shutdown()
    exit()

df_m15 = pd.DataFrame(rates_m15)
df_h1 = pd.DataFrame(rates_h1)
df_h4 = pd.DataFrame(rates_h4)

# Prices
current_price = df_m15['close'].iloc[-1]
print(f'\n--- PRICES ---')
print(f'Current Price: {current_price:.5f}')
print(f'Bid: {tick.bid:.5f} | Ask: {tick.ask:.5f}')
print(f'Spread: {(tick.ask - tick.bid)/0.0001:.1f} pips')

# M15 Analysis
df_m15['ma20'] = df_m15['close'].rolling(20).mean()
df_m15['ma50'] = df_m15['close'].rolling(50).mean()
m15_close = df_m15['close'].iloc[-1]
m15_ma20 = df_m15['ma20'].iloc[-1]
m15_ma50 = df_m15['ma50'].iloc[-1]
m15_prev_close = df_m15['close'].iloc[-2]
m15_prev_ma20 = df_m15['ma20'].iloc[-2]

# ATR
high_low = df_m15['high'] - df_m15['low']
high_close = abs(df_m15['high'] - df_m15['close'].shift())
low_close = abs(df_m15['low'] - df_m15['close'].shift())
tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
atr = tr.rolling(14).mean().iloc[-1]

# RSI
delta = df_m15['close'].diff()
gain = delta.where(delta > 0, 0).rolling(14).mean()
loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
rs = gain / loss
rsi = (100 - (100 / (1 + rs))).iloc[-1]

print(f'\n--- M15 (ENTRY) ---')
print(f'Close: {m15_close:.5f}')
print(f'MA20: {m15_ma20:.5f} | MA50: {m15_ma50:.5f}')
print(f'Prev Close: {m15_prev_close:.5f} | Prev MA20: {m15_prev_ma20:.5f}')
print(f'RSI: {rsi:.1f} (range: 30-70 ideal)')
print(f'ATR: {atr:.5f} ({atr/0.0001:.1f} pips)')

# H1 Analysis
df_h1['ma20'] = df_h1['close'].rolling(20).mean()
df_h1['ma50'] = df_h1['close'].rolling(50).mean()
h1_close = df_h1['close'].iloc[-1]
h1_ma20 = df_h1['ma20'].iloc[-1]
h1_ma50 = df_h1['ma50'].iloc[-1]

print(f'\n--- H1 (TREND DIRECTION) ---')
print(f'Close: {h1_close:.5f}')
print(f'MA20: {h1_ma20:.5f} | MA50: {h1_ma50:.5f}')
h1_bull = h1_ma20 > h1_ma50 and h1_close > h1_ma20
h1_bear = h1_ma20 < h1_ma50 and h1_close < h1_ma20
if h1_bull:
    print('Trend: BULLISH (Price > MA20 > MA50)')
elif h1_bear:
    print('Trend: BEARISH (Price < MA20 < MA50)')
else:
    print('Trend: NO CLEAR TREND')

# H4 Analysis
df_h4['ma20'] = df_h4['close'].rolling(20).mean()
df_h4['ma50'] = df_h4['close'].rolling(50).mean()
h4_ma20 = df_h4['ma20'].iloc[-1]
h4_ma50 = df_h4['ma50'].iloc[-1]

print(f'\n--- H4 (MAJOR TREND) ---')
print(f'MA20: {h4_ma20:.5f} | MA50: {h4_ma50:.5f}')
h4_bull = h4_ma20 > h4_ma50
h4_bear = h4_ma20 < h4_ma50
if h4_bull:
    print('Major Trend: BULLISH')
elif h4_bear:
    print('Major Trend: BEARISH')

# PULLBACK CHECK
print(f'\n--- ENTRY CONDITIONS ---')
dist_ma20 = abs(m15_close - m15_ma20) / atr if atr > 0 else 999
print(f'Distance from MA20: {dist_ma20:.2f} ATR units')
if 0 < dist_ma20 < 1.5:
    print('Pullback: YES - Near MA20')
else:
    print('Pullback: NO - Too far from MA20')

# CROSSOVER
buy_cross = m15_close > m15_ma20 > m15_ma50 and m15_prev_close < m15_prev_ma20
sell_cross = m15_close < m15_ma20 < m15_ma50 and m15_prev_close > m15_prev_ma20
if buy_cross:
    print('Crossover: FRESH BUY CROSSOVER')
elif sell_cross:
    print('Crossover: FRESH SELL CROSSOVER')
else:
    print('Crossover: NO FRESH CROSSOVER')

# RSI FILTER
if 30 < rsi < 70:
    print('RSI: IN RANGE (30-70)')
elif rsi >= 70:
    print('RSI: OVERBOUGHT (>70)')
else:
    print('RSI: OVERSOLD (<30)')

# FINAL VERDICT
print(f'\n=== VERDICT ===')
aligned = (h1_bull and h4_bull) or (h1_bear and h4_bear)
pullback_ok = 0 < dist_ma20 < 1.5
rsi_ok = 30 < rsi < 70

if aligned:
    trend_dir = 'BUY' if h1_bull else 'SELL'
    print(f'Trends ALIGNED: {trend_dir}')
else:
    print('Trends NOT ALIGNED')

if pullback_ok:
    print('Pullback: GOOD')
else:
    print('Pullback: FAILED')

if rsi_ok:
    print('RSI: GOOD')
else:
    print('RSI: FAILED')
    
if aligned and pullback_ok and rsi_ok:
    direction = 'BUY' if h1_bull else 'SELL'
    print(f'\n*** SETUP VALID: {symbol} {direction} ***')
    print(f'Entry: ~{current_price:.5f}')
    sl = current_price - atr*1.5 if h1_bull else current_price + atr*1.5
    tp = current_price + atr*2.0 if h1_bull else current_price - atr*2.0
    print(f'SL: ~{sl:.5f} | TP: ~{tp:.5f}')
else:
    print('\n*** NO VALID SETUP FOUND ***')

mt5.shutdown()
print('='*60)
