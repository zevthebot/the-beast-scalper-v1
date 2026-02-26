#!/usr/bin/env python3
"""
Zev Trading Controller v3.2 - Enhanced Autonomous Trading System
Features:
- Session filter (avoid dead hours 17-19 GMT)
- Dual timeframe entry (H1 trend + M15 pullback)
- Adaptive SL/TP per pair volatility and confidence
- Dynamic lot sizing based on confidence

Usage:
  python bot_controller_v3.py --once        # Single scan
  python bot_controller_v3.py --once --dry-run  # Test mode
  python bot_controller_v3.py               # Continuous mode
"""

import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from datetime import datetime, timezone
import json
import sys
from pathlib import Path
import argparse

# Configuration - ENHANCED v3.2
CONFIG = {
    "account": 541144102,
    "server": "FTMO-Server4",
    "risk_per_trade": 0.5,
    "max_lot": 0.5,
    "min_lot": 0.1,
    "max_positions": 5,
    "min_rr_hard": 1.2,
    "min_confidence_hard": 60,
    "target_confidence": 75,
    "magic": 234000,
    "symbols": [
        "EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "USDCAD",
        "NZDUSD", "EURGBP", "EURJPY", "GBPJPY", "AUDJPY", "XAUUSD"
    ],
    # Session settings - DISABLED (24/7 trading)
    "session_filter": False,
    "session_good_hours": [(0, 24)],  # All hours active
}

WORKSPACE = Path("C:/Users/Claw/.openclaw/workspace/mt5_trader")


def log_event(event_type, data):
    """Log event to journal"""
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": event_type,
        **data
    }
    with open(WORKSPACE / "trade_journal_v3.jsonl", "a") as f:
        f.write(json.dumps(entry) + "\n")


def check_trading_session():
    """Session check - 24/7 active (no restrictions)"""
    # All restrictions removed per user request
    # Bot runs 24/7 including weekends, dead hours, off hours
    now = datetime.now(timezone.utc)
    hour = now.hour
    minute = now.minute
    
    return True, f"24/7 Active ({hour:02d}:{minute:02d} GMT)"


def calculate_lot_size(confidence):
    """Calculate lot size based on confidence (60-100% -> 0.1-0.5 lot)"""
    min_conf = CONFIG["min_confidence_hard"]
    max_conf = 100
    min_lot = CONFIG["min_lot"]
    max_lot = CONFIG["max_lot"]
    
    if confidence <= min_conf:
        lots = min_lot
    elif confidence >= max_conf:
        lots = max_lot
    else:
        lots = min_lot + (confidence - min_conf) * 0.01
    
    lots = round(lots, 2)
    lots = max(min_lot, min(lots, max_lot))
    
    print(f"   Lot: {confidence}% confidence -> {lots} lots")
    return lots


def calculate_adaptive_sl_tp(symbol, entry, direction, atr, confidence):
    """Adaptive SL/TP based on pair volatility and confidence"""
    
    # Get symbol info
    symbol_info = mt5.symbol_info(symbol)
    if symbol_info is None:
        return None, None, 0, 0, 0
    
    digits = symbol_info.digits
    point = symbol_info.point
    
    # Adaptive multipliers based on confidence
    if confidence >= 85:
        sl_mult = 0.8
        tp_mult = 2.5
    elif confidence >= 70:
        sl_mult = 1.0
        tp_mult = 2.0
    else:
        sl_mult = 1.3
        tp_mult = 1.8
    
    # Pair-specific max SL in pips
    if "JPY" in symbol:
        max_sl_pips = 80
        pip_size = 0.01
    elif symbol == "XAUUSD":
        max_sl_pips = 400
        pip_size = 0.1
    else:
        max_sl_pips = 60
        pip_size = 0.0001
    
    # Calculate SL distance
    sl_distance = atr * sl_mult
    
    # Convert to pips for sanity check
    sl_pips = sl_distance / pip_size
    
    # Cap SL if too wide
    if sl_pips > max_sl_pips:
        print(f"   ⚠️ Capping SL: {sl_pips:.1f} -> {max_sl_pips} pips (max for {symbol})")
        sl_distance = max_sl_pips * pip_size
    
    # Calculate SL and TP
    if direction == "BUY":
        sl = entry - sl_distance
        tp = entry + (atr * tp_mult)
    else:
        sl = entry + sl_distance
        tp = entry - (atr * tp_mult)
    
    # Round to symbol digits
    sl = round(sl, digits)
    tp = round(tp, digits)
    
    # Calculate actual RR
    sl_pips_final = abs(entry - sl) / pip_size
    tp_pips_final = abs(tp - entry) / pip_size
    actual_rr = tp_pips_final / sl_pips_final if sl_pips_final > 0 else 0
    
    print(f"   SL/TP: {sl} ({sl_pips_final:.1f}p) / {tp} ({tp_pips_final:.1f}p) | RR: 1:{actual_rr:.2f}")
    
    return sl, tp, actual_rr, sl_pips_final, tp_pips_final


def execute_trade(setup, lot_size):
    """Execute trade via MT5 API"""
    try:
        if not mt5.initialize():
            print("❌ MT5 init failed")
            return None
        
        symbol = setup["symbol"]
        direction = setup["direction"]
        
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            print(f"❌ Cannot get tick for {symbol}")
            mt5.shutdown()
            return None
        
        price = tick.ask if direction == "BUY" else tick.bid
        
        order_type = mt5.ORDER_TYPE_BUY if direction == "BUY" else mt5.ORDER_TYPE_SELL
        
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": lot_size,
            "type": order_type,
            "price": price,
            "sl": setup["sl"],
            "tp": setup["tp"],
            "deviation": 10,
            "magic": CONFIG["magic"],
            "comment": f"Zev_v3_{setup['confidence']:.0f}conf",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        
        result = mt5.order_send(request)
        mt5.shutdown()
        
        if result is None:
            print(f"❌ Order failed: {mt5.last_error()}")
            return None
        
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            print(f"❌ Order rejected: {result.retcode}")
            return None
        
        print(f"\n✅ TRADE EXECUTED: Ticket {result.order}, {result.volume} lots @ {result.price}")
        
        return {
            "ticket": result.order,
            "volume": result.volume,
            "price": result.price,
        }
        
    except Exception as e:
        print(f"❌ Execution error: {e}")
        return None


def get_mt5_data():
    """Get all necessary data from MT5"""
    if not mt5.initialize():
        return None, "MT5 init failed"
    
    account = mt5.account_info()
    if account is None:
        mt5.shutdown()
        return None, "Not logged in"
    
    # Get positions
    positions = []
    for pos in mt5.positions_get():
        if pos.magic == CONFIG["magic"]:
            positions.append({
                "symbol": pos.symbol,
                "type": "BUY" if pos.type == 0 else "SELL",
                "volume": pos.volume,
                "profit": pos.profit,
            })
    
    # Get data for each symbol
    symbol_data = {}
    for symbol in CONFIG["symbols"]:
        if any(p["symbol"] == symbol for p in positions):
            continue
        
        rates_m15 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M15, 0, 100)
        rates_h1 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 0, 100)
        rates_h4 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H4, 0, 200)
        tick = mt5.symbol_info_tick(symbol)
        
        if rates_m15 is None or rates_h1 is None or rates_h4 is None or tick is None:
            continue
        
        df_m15 = pd.DataFrame(rates_m15)
        df_h1 = pd.DataFrame(rates_h1)
        df_h4 = pd.DataFrame(rates_h4)
        
        # Calculate indicators
        df_m15['ma20'] = df_m15['close'].rolling(20).mean()
        df_m15['ma50'] = df_m15['close'].rolling(50).mean()
        df_h1['ma20'] = df_h1['close'].rolling(20).mean()
        df_h1['ma50'] = df_h1['close'].rolling(50).mean()
        
        symbol_data[symbol] = {
            "bid": tick.bid,
            "ask": tick.ask,
            "spread_pips": round((tick.ask - tick.bid) / 0.0001, 1),
            "m15_close": df_m15['close'].iloc[-1],
            "m15_ma20": df_m15['ma20'].iloc[-1],
            "m15_ma50": df_m15['ma50'].iloc[-1],
            "m15_prev_close": df_m15['close'].iloc[-2],
            "m15_prev_ma20": df_m15['ma20'].iloc[-2],
            "h1_ma20": df_h1['ma20'].iloc[-1],
            "h1_ma50": df_h1['ma50'].iloc[-1],
            "h1_close": df_h1['close'].iloc[-1],
            "h4_ma20": df_h4['close'].rolling(20).mean().iloc[-1],
            "h4_ma50": df_h4['close'].rolling(50).mean().iloc[-1],
            "atr": round(calculate_atr(df_m15, 14), 5),
            "rsi": round(calculate_rsi(df_m15['close'], 14), 1),
        }
    
    mt5.shutdown()
    
    return {
        "account": {"balance": account.balance, "equity": account.equity},
        "positions": positions,
        "symbol_data": symbol_data,
    }, None


def calculate_atr(df, period=14):
    high_low = df['high'] - df['low']
    high_close = abs(df['high'] - df['close'].shift())
    low_close = abs(df['low'] - df['close'].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return tr.rolling(period).mean().iloc[-1]


def calculate_rsi(prices, period=14):
    delta = prices.diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs)).iloc[-1]


def find_setups_enhanced(data):
    """Enhanced setup detection: H1 trend + M15 pullback"""
    setups = []
    
    for symbol, d in data["symbol_data"].items():
        # H1 Trend Analysis
        h1_trend_up = d["h1_ma20"] > d["h1_ma50"] and d["m15_close"] > d["h1_ma20"]
        h1_trend_down = d["h1_ma20"] < d["h1_ma50"] and d["m15_close"] < d["h1_ma20"]
        
        # H4 Trend Alignment (filter)
        h4_aligned_up = d["h4_ma20"] > d["h4_ma50"]
        h4_aligned_down = d["h4_ma20"] < d["h4_ma50"]
        
        # M15 Pullback Entry
        dist_from_ma20 = abs(d["m15_close"] - d["m15_ma20"]) / d["atr"] if d["atr"] > 0 else 999
        
        # BUY Setup
        if h1_trend_up and h4_aligned_up:
            # Price near MA20 (pullback) or fresh breakout above
            near_ma20 = 0 < dist_from_ma20 < 1.5
            fresh_breakout = (
                d["m15_close"] > d["m15_ma20"] > d["m15_ma50"] and
                d["m15_prev_close"] < d["m15_prev_ma20"]
            )
            
            if (near_ma20 or fresh_breakout) and 30 < d["rsi"] < 70:
                direction = "BUY"
                conf = calculate_confidence(d, direction, h1_trend_up, h4_aligned_up)
                
                entry = d["ask"]
                sl, tp, rr, sl_pips, tp_pips = calculate_adaptive_sl_tp(
                    symbol, entry, direction, d["atr"], conf
                )
                
                if sl and rr >= CONFIG["min_rr_hard"]:
                    setups.append(create_setup(symbol, direction, entry, sl, tp, rr, conf, 
                                              sl_pips, tp_pips, d, "H1_TREND_PULLBACK"))
        
        # SELL Setup
        elif h1_trend_down and h4_aligned_down:
            near_ma20 = 0 < dist_from_ma20 < 1.5
            fresh_breakout = (
                d["m15_close"] < d["m15_ma20"] < d["m15_ma50"] and
                d["m15_prev_close"] > d["m15_prev_ma20"]
            )
            
            if (near_ma20 or fresh_breakout) and 30 < d["rsi"] < 70:
                direction = "SELL"
                conf = calculate_confidence(d, direction, h1_trend_down, h4_aligned_down)
                
                entry = d["bid"]
                sl, tp, rr, sl_pips, tp_pips = calculate_adaptive_sl_tp(
                    symbol, entry, direction, d["atr"], conf
                )
                
                if sl and rr >= CONFIG["min_rr_hard"]:
                    setups.append(create_setup(symbol, direction, entry, sl, tp, rr, conf,
                                              sl_pips, tp_pips, d, "H1_TREND_PULLBACK"))
    
    return setups


def calculate_confidence(d, direction, h1_trend, h4_aligned):
    """Calculate confidence score"""
    conf = 50
    
    # RSI confirmation
    if direction == "BUY" and d["rsi"] > 45:
        conf += 10
    elif direction == "SELL" and d["rsi"] < 55:
        conf += 10
    
    # Spread quality
    if d["spread_pips"] < 1.5:
        conf += 15
    elif d["spread_pips"] < 2.5:
        conf += 10
    
    # Trend strength
    if h1_trend and h4_aligned:
        conf += 15
    
    # ATR health (not too volatile, not too dead)
    atr_pips = d["atr"] / 0.0001
    if 10 < atr_pips < 40:
        conf += 10
    
    return min(100, conf)


def create_setup(symbol, direction, entry, sl, tp, rr, conf, sl_pips, tp_pips, d, strategy):
    """Create setup dictionary"""
    return {
        "symbol": symbol,
        "direction": direction,
        "entry": round(entry, 5),
        "sl": round(sl, 5),
        "tp": round(tp, 5),
        "rr": round(rr, 2),
        "confidence": conf,
        "sl_pips": round(sl_pips, 1),
        "tp_pips": round(tp_pips, 1),
        "rsi": d["rsi"],
        "spread": d["spread_pips"],
        "atr": d["atr"],
        "strategy": strategy,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true", help="Single scan mode")
    parser.add_argument("--dry-run", action="store_true", help="Test mode")
    args = parser.parse_args()
    
    print("Zev Trading Controller v3.2 - Enhanced System")
    print("=" * 50)
    
    # Session check
    can_trade, reason = check_trading_session()
    print(f"Session: {reason}")
    if not can_trade:
        print("Trading skipped (session filter)")
        return
    
    # Get data
    data, error = get_mt5_data()
    if error:
        print(f"Error: {error}")
        return
    
    print(f"Account: ${data['account']['equity']:.2f}")
    print(f"Positions: {len(data['positions'])}")
    for p in data['positions']:
        print(f"  {p['symbol']} {p['type']} | ${p['profit']:.2f}")
    
    if len(data['positions']) >= CONFIG["max_positions"]:
        print(f"Max positions reached ({CONFIG['max_positions']})")
        return
    
    # Find setups
    setups = find_setups_enhanced(data)
    print(f"\nFound {len(setups)} setups")
    
    valid = [s for s in setups if s["confidence"] >= CONFIG["min_confidence_hard"]]
    print(f"Passed confidence >= {CONFIG['min_confidence_hard']}%: {len(valid)}")
    
    if not valid:
        print("No valid setups")
        return
    
    valid.sort(key=lambda x: x["confidence"], reverse=True)
    best = valid[0]
    
    print(f"\nBEST SETUP:")
    print(f"  {best['symbol']} {best['direction']} | {best['strategy']}")
    print(f"  Entry: {best['entry']}, SL: {best['sl']}, TP: {best['tp']}")
    print(f"  RR: 1:{best['rr']}, Confidence: {best['confidence']}%")
    
    # Safeguards
    print("\n" + "=" * 40)
    print("EXECUTION CHECKS")
    print("=" * 40)
    
    # 1. No duplicate
    if any(p["symbol"] == best["symbol"] for p in data["positions"]):
        print(f"❌ REJECTED: Duplicate symbol")
        log_event("TRADE_REJECTED", {"reason": "duplicate", "symbol": best["symbol"]})
        return
    print("✓ No duplicate")
    
    # 2. Max positions
    if len(data["positions"]) >= CONFIG["max_positions"]:
        print("❌ REJECTED: Max positions")
        return
    print("✓ Under max positions")
    
    # 3. Daily loss check
    daily_loss = (10000 - data["account"]["equity"]) / 10000 * 100
    if daily_loss >= 3.0:
        print(f"❌ REJECTED: Daily loss {daily_loss:.2f}%")
        return
    print(f"✓ Daily loss OK ({daily_loss:.2f}%)")
    
    # 4. Dynamic RR threshold
    if best["confidence"] >= 85:
        min_rr = 1.3
    elif best["confidence"] >= 70:
        min_rr = 1.5
    else:
        min_rr = 2.0
    
    if best["rr"] < min_rr:
        print(f"❌ REJECTED: RR {best['rr']} < {min_rr} (for {best['confidence']}% conf)")
        log_event("TRADE_REJECTED", {"reason": "low_rr", "rr": best["rr"], "min_rr": min_rr})
        return
    print(f"✓ RR OK: {best['rr']} >= {min_rr}")
    
    # Calculate lot
    lot_size = calculate_lot_size(best["confidence"])
    
    # Execute
    print(f"\n✅ APPROVED: {best['symbol']} {best['direction']}")
    print(f"   Lot: {lot_size}")
    
    if args.dry_run:
        print("\n🧪 DRY RUN - No execution")
        log_event("TRADE_DRY_RUN", {"setup": best, "lot": lot_size})
        return
    
    result = execute_trade(best, lot_size)
    if result:
        log_event("TRADE_EXECUTED", {**best, "lot_size": lot_size, "result": result})
    else:
        log_event("TRADE_FAILED", best)


if __name__ == "__main__":
    main()
