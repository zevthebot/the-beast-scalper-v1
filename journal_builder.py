"""
Journal Builder — Extract MT5 trade history and build ML-ready journal
Run STANDALONE — does NOT affect bot_controller.py or live trading
"""
import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
import json
import os

JOURNAL_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "trade_journal_v2.jsonl")
ACCOUNT = 541144102

# Session definitions (GMT)
SESSIONS = {
    'Asian': (0, 7),
    'London': (7, 15),
    'NY': (12, 21),
    'London_NY_Overlap': (12, 15),
}

def get_session(hour_gmt):
    """Determine trading session from GMT hour"""
    if 12 <= hour_gmt < 15:
        return 'London_NY_Overlap'
    elif 7 <= hour_gmt < 15:
        return 'London'
    elif 12 <= hour_gmt < 21:
        return 'NY'
    elif 0 <= hour_gmt < 7:
        return 'Asian'
    return 'Off_Hours'

def calculate_indicators(symbol, timestamp, timeframe=mt5.TIMEFRAME_M15, h4_timeframe=mt5.TIMEFRAME_H4):
    """Calculate technical indicators at a specific point in time"""
    indicators = {}
    
    try:
        # Get M15 data for RSI, ADX, ATR
        rates = mt5.copy_rates_from(symbol, timeframe, timestamp, 60)
        if rates is not None and len(rates) >= 50:
            df = pd.DataFrame(rates)
            
            # ATR (14)
            df['tr'] = np.maximum(
                df['high'] - df['low'],
                np.maximum(
                    abs(df['high'] - df['close'].shift(1)),
                    abs(df['low'] - df['close'].shift(1))
                )
            )
            indicators['atr'] = round(df['tr'].rolling(14).mean().iloc[-1], 6)
            
            # RSI (14)
            delta = df['close'].diff()
            gain = delta.where(delta > 0, 0).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            indicators['rsi'] = round(rsi.iloc[-1], 2)
            
            # ADX (14)
            indicators['adx'] = calculate_adx_from_df(df)
            
            # Spread approximation (from last bar)
            indicators['spread'] = round(df['spread'].iloc[-1] if 'spread' in df.columns else 0, 1)
            
            # SMA20, SMA50
            indicators['sma20'] = round(df['close'].rolling(20).mean().iloc[-1], 6)
            indicators['sma50'] = round(df['close'].rolling(50).mean().iloc[-1], 6)
        
        # Get H4 data for trend
        h4_rates = mt5.copy_rates_from(symbol, h4_timeframe, timestamp, 220)
        if h4_rates is not None and len(h4_rates) >= 200:
            h4_df = pd.DataFrame(h4_rates)
            h4_df['ema50'] = h4_df['close'].ewm(span=50, adjust=False).mean()
            h4_df['ema200'] = h4_df['close'].ewm(span=200, adjust=False).mean()
            
            latest = h4_df.iloc[-1]
            if latest['close'] > latest['ema50'] > latest['ema200']:
                indicators['h4_trend'] = 'BULLISH'
            elif latest['close'] < latest['ema50'] < latest['ema200']:
                indicators['h4_trend'] = 'BEARISH'
            else:
                indicators['h4_trend'] = 'CHOPPY'
            
            indicators['h4_ema50'] = round(latest['ema50'], 6)
            indicators['h4_ema200'] = round(latest['ema200'], 6)
        
    except Exception as e:
        print(f"  [WARN] Indicator calc failed for {symbol}: {e}")
    
    return indicators

def calculate_adx_from_df(df, period=14):
    """Calculate ADX from dataframe"""
    try:
        plus_dm = df['high'].diff()
        minus_dm = -df['low'].diff()
        
        plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0)
        minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0)
        
        tr = np.maximum(
            df['high'] - df['low'],
            np.maximum(
                abs(df['high'] - df['close'].shift(1)),
                abs(df['low'] - df['close'].shift(1))
            )
        )
        
        atr = tr.rolling(period).mean()
        plus_di = 100 * (plus_dm.rolling(period).mean() / atr)
        minus_di = 100 * (minus_dm.rolling(period).mean() / atr)
        
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.rolling(period).mean().iloc[-1]
        return round(adx, 2) if not np.isnan(adx) else None
    except:
        return None

def extract_mt5_history():
    """Extract all trade history from MT5 and build journal entries"""
    if not mt5.initialize():
        print("[ERROR] Failed to initialize MT5")
        return []
    
    account = mt5.account_info()
    if account is None or account.login != ACCOUNT:
        print(f"[ERROR] Wrong account or not logged in. Expected {ACCOUNT}")
        mt5.shutdown()
        return []
    
    print(f"[OK] Connected to account {account.login}")
    
    # Get all deals from account start
    from_date = datetime(2026, 2, 1, tzinfo=timezone.utc)
    to_date = datetime.now(timezone.utc) + timedelta(days=1)
    
    deals = mt5.history_deals_get(from_date, to_date)
    if deals is None or len(deals) == 0:
        print("[WARN] No deals found")
        mt5.shutdown()
        return []
    
    print(f"[OK] Found {len(deals)} deals")
    
    # Convert to dataframe
    deals_df = pd.DataFrame(list(deals), columns=deals[0]._asdict().keys())
    
    # Filter: only actual trades (type 0=BUY, 1=SELL), skip balance ops
    trades_df = deals_df[deals_df['type'].isin([0, 1])].copy()
    
    # Group by position_id to match entries with exits
    positions = {}
    for _, deal in trades_df.iterrows():
        pos_id = deal['position_id']
        if pos_id not in positions:
            positions[pos_id] = []
        positions[pos_id].append(deal)
    
    print(f"[OK] Found {len(positions)} unique positions")
    
    journal_entries = []
    
    for pos_id, deals_list in positions.items():
        if len(deals_list) < 1:
            continue
        
        # Sort by time
        deals_list.sort(key=lambda x: x['time'])
        
        entry_deal = deals_list[0]
        exit_deal = deals_list[-1] if len(deals_list) > 1 else None
        
        # Entry info
        symbol = entry_deal['symbol']
        entry_time = datetime.fromtimestamp(entry_deal['time'], tz=timezone.utc)
        direction = 'BUY' if entry_deal['type'] == 0 else 'SELL'
        lot_size = entry_deal['volume']
        entry_price = entry_deal['price']
        
        print(f"  Processing: {symbol} {direction} {lot_size} @ {entry_price} ({entry_time.strftime('%Y-%m-%d %H:%M')})")
        
        # Calculate indicators at entry time
        indicators = calculate_indicators(symbol, entry_time)
        
        # Determine if trade was WITH or AGAINST H4 trend
        h4_trend = indicators.get('h4_trend', 'UNKNOWN')
        trend_alignment = 'UNKNOWN'
        if h4_trend == 'BULLISH' and direction == 'BUY':
            trend_alignment = 'WITH_TREND'
        elif h4_trend == 'BEARISH' and direction == 'SELL':
            trend_alignment = 'WITH_TREND'
        elif h4_trend == 'CHOPPY':
            trend_alignment = 'CHOPPY'
        elif h4_trend != 'UNKNOWN':
            trend_alignment = 'AGAINST_TREND'
        
        # Build entry
        entry = {
            'position_id': int(pos_id),
            'account': ACCOUNT,
            'symbol': symbol,
            'direction': direction,
            'lot_size': lot_size,
            'entry_time': entry_time.isoformat(),
            'entry_price': entry_price,
            'entry_day_of_week': entry_time.strftime('%A'),
            'entry_hour_gmt': entry_time.hour,
            'session': get_session(entry_time.hour),
            
            # Indicators at entry
            'rsi': indicators.get('rsi'),
            'adx': indicators.get('adx'),
            'atr': indicators.get('atr'),
            'spread': indicators.get('spread'),
            'sma20': indicators.get('sma20'),
            'sma50': indicators.get('sma50'),
            'h4_trend': h4_trend,
            'h4_ema50': indicators.get('h4_ema50'),
            'h4_ema200': indicators.get('h4_ema200'),
            'trend_alignment': trend_alignment,
            
            # Strategy info (from comment if available)
            'strategy': extract_strategy_from_comment(entry_deal.get('comment', '')),
            'confidence': None,  # Not available retroactively
            'magic': int(entry_deal.get('magic', 0)),
            
            # Commission and swap
            'commission': round(entry_deal.get('commission', 0) + (exit_deal.get('commission', 0) if exit_deal is not None else 0), 2),
            'swap': round(entry_deal.get('swap', 0) + (exit_deal.get('swap', 0) if exit_deal is not None else 0), 2),
        }
        
        # Exit info (if closed)
        if exit_deal is not None and len(deals_list) > 1:
            exit_time = datetime.fromtimestamp(exit_deal['time'], tz=timezone.utc)
            exit_price = exit_deal['price']
            duration_min = (exit_time - entry_time).total_seconds() / 60
            
            # PnL
            pnl = round(exit_deal['profit'], 2)
            
            # Pips calculation
            if 'JPY' in symbol:
                pips = round((exit_price - entry_price) * 100, 1) if direction == 'BUY' else round((entry_price - exit_price) * 100, 1)
            else:
                pips = round((exit_price - entry_price) * 10000, 1) if direction == 'BUY' else round((entry_price - exit_price) * 10000, 1)
            
            entry.update({
                'status': 'CLOSED',
                'exit_time': exit_time.isoformat(),
                'exit_price': exit_price,
                'exit_reason': guess_exit_reason(entry_deal, exit_deal, pnl),
                'pnl': pnl,
                'pips': pips,
                'duration_min': round(duration_min, 1),
                'result': 'WIN' if pnl > 0 else 'LOSS' if pnl < 0 else 'BREAKEVEN',
            })
        else:
            entry.update({
                'status': 'OPEN',
                'exit_time': None,
                'exit_price': None,
                'exit_reason': None,
                'pnl': None,
                'pips': None,
                'duration_min': None,
                'result': None,
            })
        
        journal_entries.append(entry)
    
    mt5.shutdown()
    return journal_entries

def extract_strategy_from_comment(comment):
    """Try to determine strategy from deal comment"""
    if not comment:
        return 'UNKNOWN'
    comment_upper = comment.upper()
    if 'FVG' in comment_upper:
        return 'FVG'
    elif 'BREAKOUT' in comment_upper:
        return 'BREAKOUT'
    elif 'RANGE' in comment_upper:
        return 'RANGE'
    elif 'TREND' in comment_upper:
        return 'TREND'
    elif 'BEAST' in comment_upper:
        return 'BEAST'
    return 'UNKNOWN'

def guess_exit_reason(entry_deal, exit_deal, pnl):
    """Guess exit reason based on available data"""
    comment = str(exit_deal.get('comment', ''))
    if 'sl' in comment.lower() or 'stop' in comment.lower():
        return 'SL'
    elif 'tp' in comment.lower() or 'take' in comment.lower():
        return 'TP'
    elif 'trailing' in comment.lower():
        return 'TRAILING'
    elif pnl == 0 or abs(pnl) < 0.5:
        return 'BREAKEVEN'
    # If small loss, likely SL. If profit, could be TP or trailing
    return 'SL' if pnl < 0 else 'TP_OR_TRAILING'

class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        if isinstance(obj, (np.ndarray,)):
            return obj.tolist()
        return super().default(obj)

def write_journal(entries):
    """Write journal entries to JSONL file"""
    with open(JOURNAL_FILE, 'w', encoding='utf-8') as f:
        for entry in entries:
            f.write(json.dumps(entry, ensure_ascii=False, cls=NumpyEncoder) + '\n')
    print(f"\n[OK] Written {len(entries)} entries to {JOURNAL_FILE}")

def print_summary(entries):
    """Print summary statistics"""
    closed = [e for e in entries if e['status'] == 'CLOSED']
    open_trades = [e for e in entries if e['status'] == 'OPEN']
    
    wins = [e for e in closed if e['result'] == 'WIN']
    losses = [e for e in closed if e['result'] == 'LOSS']
    
    total_pnl = sum(e['pnl'] for e in closed)
    
    with_trend = [e for e in closed if e['trend_alignment'] == 'WITH_TREND']
    against_trend = [e for e in closed if e['trend_alignment'] == 'AGAINST_TREND']
    
    with_trend_pnl = sum(e['pnl'] for e in with_trend) if with_trend else 0
    against_trend_pnl = sum(e['pnl'] for e in against_trend) if against_trend else 0
    
    print(f"\n{'='*60}")
    print(f"JOURNAL SUMMARY")
    print(f"{'='*60}")
    print(f"Total trades: {len(entries)} ({len(closed)} closed, {len(open_trades)} open)")
    print(f"Wins: {len(wins)} | Losses: {len(losses)} | Win rate: {len(wins)/len(closed)*100:.1f}%" if closed else "No closed trades")
    print(f"Total PnL: ${total_pnl:.2f}")
    print(f"")
    print(f"WITH H4 trend: {len(with_trend)} trades -> ${with_trend_pnl:.2f}")
    print(f"AGAINST H4 trend: {len(against_trend)} trades -> ${against_trend_pnl:.2f}")
    print(f"{'='*60}")
    
    # Per strategy breakdown
    strategies = set(e['strategy'] for e in closed)
    for strat in sorted(strategies):
        strat_trades = [e for e in closed if e['strategy'] == strat]
        strat_pnl = sum(e['pnl'] for e in strat_trades)
        strat_wins = len([e for e in strat_trades if e['result'] == 'WIN'])
        print(f"  {strat}: {len(strat_trades)} trades, ${strat_pnl:.2f}, WR: {strat_wins/len(strat_trades)*100:.1f}%")

if __name__ == '__main__':
    print("="*60)
    print("JOURNAL BUILDER — Extracting MT5 Trade History")
    print("="*60)
    
    entries = extract_mt5_history()
    
    if entries:
        print_summary(entries)
        write_journal(entries)
        print(f"\nJournal saved to: {JOURNAL_FILE}")
    else:
        print("[WARN] No entries to write")
