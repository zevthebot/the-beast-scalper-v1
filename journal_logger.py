"""
Live Journal Logger — Logs entries and exits to trade_journal_v2.jsonl
Imported by bot_controller.py. Does NOT execute trades or modify positions.
"""
import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from datetime import datetime, timezone
import json
import os

JOURNAL_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "trade_journal_v2.jsonl")

# Track known positions to detect closes
_known_positions = {}  # ticket -> entry_data

class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        if isinstance(obj, (np.ndarray,)):
            return obj.tolist()
        return super().default(obj)


def get_session(hour_gmt):
    if 12 <= hour_gmt < 15:
        return 'London_NY_Overlap'
    elif 7 <= hour_gmt < 15:
        return 'London'
    elif 12 <= hour_gmt < 21:
        return 'NY'
    elif 0 <= hour_gmt < 7:
        return 'Asian'
    return 'Off_Hours'


def calc_indicators_live(symbol):
    """Calculate indicators from current live data"""
    indicators = {}
    try:
        # M15 indicators
        rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M15, 0, 60)
        if rates is not None and len(rates) >= 50:
            df = pd.DataFrame(rates)
            
            # ATR
            df['tr'] = np.maximum(
                df['high'] - df['low'],
                np.maximum(
                    abs(df['high'] - df['close'].shift(1)),
                    abs(df['low'] - df['close'].shift(1))
                )
            )
            indicators['atr'] = round(float(df['tr'].rolling(14).mean().iloc[-1]), 6)
            
            # RSI
            delta = df['close'].diff()
            gain = delta.where(delta > 0, 0).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            indicators['rsi'] = round(float(rsi.iloc[-1]), 2)
            
            # ADX
            plus_dm = df['high'].diff()
            minus_dm = -df['low'].diff()
            plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0)
            minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0)
            tr = np.maximum(df['high'] - df['low'], np.maximum(abs(df['high'] - df['close'].shift(1)), abs(df['low'] - df['close'].shift(1))))
            atr14 = tr.rolling(14).mean()
            plus_di = 100 * (plus_dm.rolling(14).mean() / atr14)
            minus_di = 100 * (minus_dm.rolling(14).mean() / atr14)
            dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
            adx_val = dx.rolling(14).mean().iloc[-1]
            indicators['adx'] = round(float(adx_val), 2) if not np.isnan(adx_val) else None
            
            # SMAs
            indicators['sma20'] = round(float(df['close'].rolling(20).mean().iloc[-1]), 6)
            indicators['sma50'] = round(float(df['close'].rolling(50).mean().iloc[-1]), 6)
            
            # Spread
            tick = mt5.symbol_info_tick(symbol)
            if tick:
                point = mt5.symbol_info(symbol).point
                indicators['spread'] = round((tick.ask - tick.bid) / point, 1) if point > 0 else 0
        
        # H4 trend
        h4 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H4, 0, 220)
        if h4 is not None and len(h4) >= 200:
            h4_df = pd.DataFrame(h4)
            h4_df['ema50'] = h4_df['close'].ewm(span=50, adjust=False).mean()
            h4_df['ema200'] = h4_df['close'].ewm(span=200, adjust=False).mean()
            latest = h4_df.iloc[-1]
            
            if latest['close'] > latest['ema50'] > latest['ema200']:
                indicators['h4_trend'] = 'BULLISH'
            elif latest['close'] < latest['ema50'] < latest['ema200']:
                indicators['h4_trend'] = 'BEARISH'
            else:
                indicators['h4_trend'] = 'CHOPPY'
            indicators['h4_ema50'] = round(float(latest['ema50']), 6)
            indicators['h4_ema200'] = round(float(latest['ema200']), 6)
    
    except Exception as e:
        print(f"  [JOURNAL] Indicator calc error for {symbol}: {e}")
    
    return indicators


def log_entry(symbol, direction, lot_size, entry_price, sl, tp, strategy, confidence, 
              signal_data=None, daily_loss_pct=0, open_positions=0, risk_status='SAFE',
              order_ticket=None):
    """Log a new trade entry to journal"""
    try:
        now = datetime.now(timezone.utc)
        indicators = calc_indicators_live(symbol)
        
        h4_trend = indicators.get('h4_trend', 'UNKNOWN')
        if h4_trend == 'BULLISH' and direction == 'BUY':
            trend_alignment = 'WITH_TREND'
        elif h4_trend == 'BEARISH' and direction == 'SELL':
            trend_alignment = 'WITH_TREND'
        elif h4_trend == 'CHOPPY':
            trend_alignment = 'CHOPPY'
        elif h4_trend != 'UNKNOWN':
            trend_alignment = 'AGAINST_TREND'
        else:
            trend_alignment = 'UNKNOWN'
        
        entry = {
            'event': 'ENTRY',
            'position_id': int(order_ticket) if order_ticket else None,
            'account': 541144102,
            'symbol': symbol,
            'direction': direction,
            'lot_size': lot_size,
            'entry_time': now.isoformat(),
            'entry_price': entry_price,
            'sl': sl,
            'tp': tp,
            'entry_day_of_week': now.strftime('%A'),
            'entry_hour_gmt': now.hour,
            'session': get_session(now.hour),
            
            # Indicators
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
            
            # Strategy
            'strategy': strategy,
            'confidence': round(confidence, 1) if confidence else None,
            
            # Context
            'daily_loss_pct': round(daily_loss_pct, 4),
            'open_positions': open_positions,
            'risk_status': risk_status,
        }
        
        # Store for exit matching
        if order_ticket:
            _known_positions[int(order_ticket)] = entry
        
        _append_journal(entry)
        print(f"  [JOURNAL] Entry logged: {symbol} {direction} {lot_size} | {strategy} C:{confidence:.0f}%")
        
    except Exception as e:
        print(f"  [JOURNAL] Entry log error: {e}")


def check_closed_positions():
    """Detect positions that closed since last check, log exits"""
    try:
        # Get current open positions
        current_positions = mt5.positions_get()
        current_tickets = set()
        if current_positions:
            current_tickets = {p.ticket for p in current_positions}
        
        # Find positions that were open but are now closed
        closed_tickets = set(_known_positions.keys()) - current_tickets
        
        for ticket in closed_tickets:
            entry_data = _known_positions.pop(ticket)
            _log_exit(ticket, entry_data)
    
    except Exception as e:
        print(f"  [JOURNAL] Close detection error: {e}")


def _log_exit(ticket, entry_data):
    """Log a trade exit"""
    try:
        now = datetime.now(timezone.utc)
        
        # Try to get deal info from MT5 history
        from_date = datetime(2026, 2, 1, tzinfo=timezone.utc)
        deals = mt5.history_deals_get(from_date, now)
        
        exit_price = None
        pnl = None
        exit_reason = 'UNKNOWN'
        commission = 0
        swap = 0
        
        if deals:
            # Find the closing deal for this position
            for deal in reversed(deals):
                if deal.position_id == ticket and deal.entry == 1:  # entry==1 means exit deal
                    exit_price = deal.price
                    pnl = round(deal.profit, 2)
                    commission = round(deal.commission, 2)
                    swap = round(deal.swap, 2)
                    
                    comment = str(deal.comment).lower()
                    if 'sl' in comment or 'stop' in comment:
                        exit_reason = 'SL'
                    elif 'tp' in comment or 'take' in comment:
                        exit_reason = 'TP'
                    elif 'trailing' in comment:
                        exit_reason = 'TRAILING'
                    else:
                        exit_reason = 'SL' if pnl < 0 else 'TP_OR_TRAILING' if pnl > 0 else 'BREAKEVEN'
                    break
        
        # Calculate pips
        symbol = entry_data.get('symbol', '')
        entry_price = entry_data.get('entry_price', 0)
        direction = entry_data.get('direction', '')
        pips = None
        if exit_price and entry_price:
            if 'JPY' in symbol:
                pips = round((exit_price - entry_price) * 100, 1) if direction == 'BUY' else round((entry_price - exit_price) * 100, 1)
            else:
                pips = round((exit_price - entry_price) * 10000, 1) if direction == 'BUY' else round((entry_price - exit_price) * 10000, 1)
        
        # Duration
        entry_time_str = entry_data.get('entry_time', '')
        duration_min = None
        if entry_time_str:
            try:
                entry_time = datetime.fromisoformat(entry_time_str)
                duration_min = round((now - entry_time).total_seconds() / 60, 1)
            except:
                pass
        
        exit_entry = {
            'event': 'EXIT',
            'position_id': int(ticket),
            'account': 541144102,
            'symbol': symbol,
            'direction': direction,
            'lot_size': entry_data.get('lot_size'),
            'entry_time': entry_time_str,
            'entry_price': entry_price,
            'exit_time': now.isoformat(),
            'exit_price': exit_price,
            'exit_reason': exit_reason,
            'pnl': pnl,
            'pips': pips,
            'duration_min': duration_min,
            'result': 'WIN' if pnl and pnl > 0 else 'LOSS' if pnl and pnl < 0 else 'BREAKEVEN',
            'commission': commission,
            'swap': swap,
            
            # Copy entry context for ML convenience
            'strategy': entry_data.get('strategy'),
            'confidence': entry_data.get('confidence'),
            'session': entry_data.get('session'),
            'h4_trend': entry_data.get('h4_trend'),
            'trend_alignment': entry_data.get('trend_alignment'),
            'rsi': entry_data.get('rsi'),
            'adx': entry_data.get('adx'),
            'atr': entry_data.get('atr'),
            'risk_status': entry_data.get('risk_status'),
        }
        
        _append_journal(exit_entry)
        result_str = f"${pnl:.2f}" if pnl else "unknown"
        print(f"  [JOURNAL] Exit logged: {symbol} {direction} -> {exit_reason} {result_str}")
        
    except Exception as e:
        print(f"  [JOURNAL] Exit log error: {e}")


def load_known_positions():
    """Load currently open positions into tracker on startup"""
    try:
        positions = mt5.positions_get()
        if positions:
            for p in positions:
                _known_positions[p.ticket] = {
                    'symbol': p.symbol,
                    'direction': 'BUY' if p.type == 0 else 'SELL',
                    'lot_size': p.volume,
                    'entry_price': p.price_open,
                    'entry_time': datetime.fromtimestamp(p.time, tz=timezone.utc).isoformat(),
                    'strategy': 'UNKNOWN',  # Can't determine retroactively
                    'confidence': None,
                    'session': get_session(datetime.fromtimestamp(p.time, tz=timezone.utc).hour),
                    'h4_trend': None,
                    'trend_alignment': None,
                    'rsi': None,
                    'adx': None,
                    'atr': None,
                    'risk_status': None,
                }
            print(f"  [JOURNAL] Loaded {len(positions)} existing positions into tracker")
    except Exception as e:
        print(f"  [JOURNAL] Load positions error: {e}")


def _append_journal(entry):
    """Append a single entry to the journal file"""
    with open(JOURNAL_FILE, 'a', encoding='utf-8') as f:
        f.write(json.dumps(entry, ensure_ascii=False, cls=NumpyEncoder) + '\n')
