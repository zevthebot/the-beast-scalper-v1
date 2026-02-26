#!/usr/bin/env python3
"""Full trading system audit"""
import MetaTrader5 as mt5
import json, os
from datetime import datetime, timedelta, timezone

mt5.initialize()

print("=" * 60)
print("FULL TRADING SYSTEM AUDIT")
print(f"Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
print("=" * 60)

# 1. Account
info = mt5.account_info()
print(f"\n--- ACCOUNT ---")
print(f"Login: {info.login} | Server: {info.server}")
print(f"Balance: ${info.balance:.2f} | Equity: ${info.equity:.2f}")
print(f"P/L: ${info.profit:.2f} | Margin Free: ${info.margin_free:.2f}")
print(f"Leverage: 1:{info.leverage}")
profit_pct = ((info.equity - 10000) / 10000) * 100
print(f"FTMO Progress: {profit_pct:.2f}% (target: 10%)")
daily_loss = ((10000 - info.equity) / 10000) * 100 if info.equity < 10000 else 0
print(f"Daily Loss: {daily_loss:.2f}% (limit: 5%)")

# 2. Open positions
positions = mt5.positions_get()
print(f"\n--- OPEN POSITIONS ({len(positions) if positions else 0}) ---")
if positions:
    for p in positions:
        tp = "BUY" if p.type == 0 else "SELL"
        print(f"  {p.symbol} {tp} | {p.volume} lots | PnL: ${p.profit:.2f}")
        print(f"    Open: {p.price_open} | SL: {p.sl} | TP: {p.tp}")
        print(f"    Magic: {p.magic} | Comment: {p.comment}")
else:
    print("  No open positions")

# 3. Recent deals (7 days)
now = datetime.now(timezone.utc)
deals = mt5.history_deals_get(now - timedelta(days=7), now)
print(f"\n--- DEALS LAST 7 DAYS ({len(deals) if deals else 0}) ---")
if deals:
    total_pnl = 0
    for d in deals:
        if d.profit != 0 or d.volume > 0:
            dt = datetime.fromtimestamp(d.time, tz=timezone.utc)
            tp = "BUY" if d.type == 0 else "SELL" if d.type == 1 else f"type{d.type}"
            print(f"  {dt.strftime('%m/%d %H:%M')} | {d.symbol} {tp} | {d.volume} lots | PnL: ${d.profit:.2f} | {d.comment}")
            total_pnl += d.profit
    print(f"  Total 7d PnL: ${total_pnl:.2f}")

# 4. EA Status
print(f"\n--- EA STATUS ---")
ea_path = r'C:\Users\Claw\AppData\Roaming\MetaQuotes\Terminal\Common\Files\ZevBot_Status.json'
try:
    with open(ea_path, 'rb') as f:
        ea = json.loads(f.read().decode('utf-16'))
    print(f"  Last update: {ea.get('timestamp', 'unknown')}")
    print(f"  Session active: {ea.get('session_active')}")
    print(f"  EA positions: {ea.get('positions_count', 0)}")
    
    # Check if EA timestamp is stale
    ts = ea.get('timestamp', '')
    if ts:
        try:
            ea_time = datetime.strptime(ts, '%Y.%m.%d %H:%M:%S')
            age_hours = (datetime.utcnow() - ea_time).total_seconds() / 3600
            if age_hours > 1:
                print(f"  WARNING: EA status is {age_hours:.1f}h old!")
            else:
                print(f"  Status age: {age_hours*60:.0f} minutes")
        except:
            pass
except Exception as e:
    print(f"  ERROR: {e}")

# 5. MT5 connection
print(f"\n--- MT5 CONNECTION ---")
term_info = mt5.terminal_info()
print(f"  Connected: {term_info.connected}")
print(f"  Trade allowed: {term_info.trade_allowed}")
print(f"  Path: {term_info.path}")

# 6. Check symbols availability
print(f"\n--- SYMBOLS CHECK ---")
symbols = ["EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "USDCAD", "NZDUSD",
           "EURGBP", "EURJPY", "GBPJPY", "AUDJPY", "XAUUSD"]
ok = 0
fail = 0
for s in symbols:
    info_s = mt5.symbol_info(s)
    if info_s and info_s.visible:
        ok += 1
    else:
        print(f"  MISSING: {s}")
        fail += 1
print(f"  {ok}/{len(symbols)} symbols available" + (f" | {fail} MISSING" if fail else " - ALL OK"))

# 7. Check journal files
print(f"\n--- JOURNAL FILES ---")
journal_paths = [
    r'C:\Users\Claw\.openclaw\workspace\mt5_trader\trade_journal.jsonl',
    r'C:\Users\Claw\.openclaw\workspace\mt5_trader\trade_journal_v3.jsonl',
]
for jp in journal_paths:
    if os.path.exists(jp):
        lines = sum(1 for _ in open(jp))
        print(f"  {os.path.basename(jp)}: {lines} entries")
    else:
        print(f"  {os.path.basename(jp)}: NOT FOUND")

# 8. Quick scan test
print(f"\n--- QUICK SCAN (12 pairs) ---")
import pandas as pd
import numpy as np

def calc_rsi(prices, period=14):
    delta = prices.diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs)).iloc[-1]

for s in symbols:
    try:
        rates_h4 = mt5.copy_rates_from_pos(s, mt5.TIMEFRAME_H4, 0, 200)
        rates_h1 = mt5.copy_rates_from_pos(s, mt5.TIMEFRAME_H1, 0, 100)
        rates_m15 = mt5.copy_rates_from_pos(s, mt5.TIMEFRAME_M15, 0, 100)
        
        if rates_h4 is None or rates_h1 is None or rates_m15 is None:
            print(f"  {s}: NO DATA")
            continue
        
        df_h4 = pd.DataFrame(rates_h4)
        df_h1 = pd.DataFrame(rates_h1)
        df_m15 = pd.DataFrame(rates_m15)
        
        h4_ma20 = df_h4['close'].rolling(20).mean().iloc[-1]
        h4_ma50 = df_h4['close'].rolling(50).mean().iloc[-1]
        h1_ma20 = df_h1['close'].rolling(20).mean().iloc[-1]
        h1_ma50 = df_h1['close'].rolling(50).mean().iloc[-1]
        rsi = calc_rsi(df_m15['close'], 14)
        
        h4_trend = "BULL" if h4_ma20 > h4_ma50 else "BEAR"
        h1_trend = "BULL" if h1_ma20 > h1_ma50 else "BEAR"
        aligned = "YES" if h4_trend == h1_trend else "NO"
        
        price = df_m15['close'].iloc[-1]
        print(f"  {s:8s} | H4:{h4_trend} H1:{h1_trend} Aligned:{aligned} | RSI:{rsi:.0f} | Price:{price}")
    except Exception as e:
        print(f"  {s}: ERROR - {e}")

mt5.shutdown()

print(f"\n{'='*60}")
print("AUDIT COMPLETE")
print(f"{'='*60}")
