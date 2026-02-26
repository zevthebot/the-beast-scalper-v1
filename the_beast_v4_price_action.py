#!/usr/bin/env python3
"""
THE BEAST 4.0 - Price Action + Volume ML Scalping
Account: Pepperstone Demo (62108425)
"""

import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta
import time
import json
from pathlib import Path

# Config
ACCOUNT = 62108425
SERVER = "PepperstoneUK-Demo"
LOT_SIZE = 0.2
MAX_POSITIONS = 3
RISK_PER_TRADE = 0.01

SYMBOLS = ["EURUSD", "GBPUSD", "USDJPY", "EURJPY", "GBPJPY", 
           "AUDUSD", "EURGBP", "USDCHF", "AUDJPY", "XAUUSD"]

# Paths
JOURNAL_PATH = Path(r"C:\Users\Claw\.openclaw\workspace\mt5_trader\pepperstone_journal_v2.jsonl")

class PriceActionAnalyzer:
    """Detect price action patterns for scalping"""
    
    @staticmethod
    def detect_pin_bar(df):
        """Detect pin bar pattern (rejection candle)"""
        if len(df) < 2:
            return None
        
        latest = df.iloc[-1]
        prev = df.iloc[-2]
        
        body = abs(latest['close'] - latest['open'])
        upper_wick = latest['high'] - max(latest['close'], latest['open'])
        lower_wick = min(latest['close'], latest['open']) - latest['low']
        
        # Bearish pin bar (rejection up) - wick up, body down
        if upper_wick > body * 2 and latest['close'] < latest['open']:
            return {'pattern': 'PIN_BAR_BEARISH', 'strength': min(upper_wick / body, 5)}
        
        # Bullish pin bar (rejection down) - wick down, body up  
        if lower_wick > body * 2 and latest['close'] > latest['open']:
            return {'pattern': 'PIN_BAR_BULLISH', 'strength': min(lower_wick / body, 5)}
        
        return None
    
    @staticmethod
    def detect_engulfing(df):
        """Detect engulfing pattern"""
        if len(df) < 2:
            return None
        
        latest = df.iloc[-1]
        prev = df.iloc[-2]
        
        latest_body = abs(latest['close'] - latest['open'])
        prev_body = abs(prev['close'] - prev['open'])
        
        latest_bullish = latest['close'] > latest['open']
        prev_bullish = prev['close'] > prev['open']
        
        # Bullish engulfing
        if latest_bullish and not prev_bullish:
            if latest['open'] <= prev['close'] and latest['close'] >= prev['open']:
                if latest_body > prev_body * 1.2:
                    return {'pattern': 'ENGULFING_BULLISH', 'strength': latest_body / prev_body}
        
        # Bearish engulfing
        if not latest_bullish and prev_bullish:
            if latest['open'] >= prev['close'] and latest['close'] <= prev['open']:
                if latest_body > prev_body * 1.2:
                    return {'pattern': 'ENGULFING_BEARISH', 'strength': latest_body / prev_body}
        
        return None
    
    @staticmethod
    def detect_breakout(df, lookback=10):
        """Detect breakout from range with volume confirmation"""
        if len(df) < lookback + 1:
            return None
        
        latest = df.iloc[-1]
        recent = df.tail(lookback)
        
        range_high = recent['high'].max()
        range_low = recent['low'].min()
        
        # Breakout up
        if latest['close'] > range_high:
            return {'pattern': 'BREAKOUT_UP', 'strength': 1.0, 'target': range_high}
        
        # Breakout down
        if latest['close'] < range_low:
            return {'pattern': 'BREAKOUT_DOWN', 'strength': 1.0, 'target': range_low}
        
        return None
    
    @staticmethod
    def calculate_vwap(df):
        """Calculate Volume Weighted Average Price"""
        typical_price = (df['high'] + df['low'] + df['close']) / 3
        vwap = (typical_price * df['tick_volume']).cumsum() / df['tick_volume'].cumsum()
        return vwap.iloc[-1]
    
    @staticmethod
    def analyze(symbol):
        """Main analysis function - combines all patterns"""
        rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M5, 0, 50)
        if rates is None or len(rates) < 20:
            return None
        
        df = pd.DataFrame(rates)
        
        # Calculate indicators
        df['sma20'] = df['close'].rolling(20).mean()
        df['volume_sma'] = df['tick_volume'].rolling(20).mean()
        df['volume_ratio'] = df['tick_volume'] / df['volume_sma']
        
        # Price action patterns
        pin_bar = PriceActionAnalyzer.detect_pin_bar(df)
        engulfing = PriceActionAnalyzer.detect_engulfing(df)
        breakout = PriceActionAnalyzer.detect_breakout(df)
        vwap = PriceActionAnalyzer.calculate_vwap(df)
        
        latest = df.iloc[-1]
        volume_confirmed = latest['volume_ratio'] > 1.5
        
        # VWAP distance
        vwap_distance = (latest['close'] - vwap) / vwap * 10000  # in pips
        
        features = {
            'close': float(latest['close']),
            'vwap': float(vwap),
            'vwap_distance_pips': float(vwap_distance),
            'volume_ratio': float(latest['volume_ratio']),
            'volume_confirmed': volume_confirmed,
            'pattern': None,
            'signal': None,
            'strength': 0
        }
        
        # Pattern priority: Pin Bar > Engulfing > Breakout
        if pin_bar and volume_confirmed:
            features['pattern'] = pin_bar['pattern']
            features['strength'] = min(pin_bar['strength'] * 20, 100)  # Scale to 0-100
            features['signal'] = 'BUY' if 'BULLISH' in pin_bar['pattern'] else 'SELL'
            
        elif engulfing and volume_confirmed:
            features['pattern'] = engulfing['pattern']
            features['strength'] = min(engulfing['strength'] * 30, 100)
            features['signal'] = 'BUY' if 'BULLISH' in engulfing['pattern'] else 'SELL'
            
        elif breakout and volume_confirmed and latest['volume_ratio'] > 2.0:
            # Only take breakouts with strong volume
            features['pattern'] = breakout['pattern']
            features['strength'] = 70  # Breakouts are strong but riskier
            features['signal'] = 'BUY' if 'UP' in breakout['pattern'] else 'SELL'
        
        # VWAP filter - don't trade too far from VWAP (>30 pips)
        if abs(vwap_distance) > 30 and features['signal']:
            # Price extended, look for mean reversion or skip
            if features['signal'] == 'BUY' and vwap_distance > 30:
                features['strength'] -= 20  # Reduce score - overbought
            elif features['signal'] == 'SELL' and vwap_distance < -30:
                features['strength'] -= 20  # Reduce score - oversold
        
        return features if features['signal'] else None


class DynamicRiskManager:
    """Dynamic SL/TP based on ATR and market conditions"""
    
    @staticmethod
    def calculate_levels(symbol, entry_price, direction, atr_multiplier=1.5):
        """Calculate dynamic SL and TP based on ATR"""
        rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M5, 0, 14)
        if rates is None:
            return None, None
        
        df = pd.DataFrame(rates)
        
        # Calculate ATR
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = np.max(ranges, axis=1)
        atr = true_range.rolling(14).mean().iloc[-1]
        
        # Dynamic SL/TP (1:2 risk/reward minimum)
        sl_distance = atr * atr_multiplier
        tp_distance = atr * atr_multiplier * 2  # 1:2 RR
        
        if 'JPY' in symbol:
            sl_distance *= 100
            tp_distance *= 100
        else:
            sl_distance *= 10000
            tp_distance *= 10000
        
        if direction == 'BUY':
            sl = entry_price - sl_distance
            tp = entry_price + tp_distance
        else:
            sl = entry_price + sl_distance
            tp = entry_price - tp_distance
        
        return sl, tp, atr


class MLLogger:
    """Logger for ML analysis"""
    
    @staticmethod
    def log_entry(trade_data):
        """Log entry with full context"""
        entry = {
            "event": "ENTRY",
            "account": ACCOUNT,
            "server": SERVER,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **trade_data
        }
        with open(JOURNAL_PATH, 'a') as f:
            f.write(json.dumps(entry) + '\n')
    
    @staticmethod
    def log_exit(position_id, symbol, direction, entry_price, exit_price, exit_reason, pnl, pips, duration_min, ml_features=None):
        """Log exit with results"""
        exit_data = {
            "event": "EXIT",
            "account": ACCOUNT,
            "position_id": position_id,
            "symbol": symbol,
            "direction": direction,
            "entry_price": entry_price,
            "exit_price": exit_price,
            "exit_reason": exit_reason,
            "pnl": pnl,
            "pips": pips,
            "duration_min": duration_min,
            "exit_time": datetime.now(timezone.utc).isoformat(),
            "ml_features": ml_features or {}
        }
        with open(JOURNAL_PATH, 'a') as f:
            f.write(json.dumps(exit_data) + '\n')


class MLTrader:
    """Main trading class with Price Action + Volume"""
    
    def __init__(self):
        self.positions = {}
    
    def initialize(self):
        if not mt5.initialize():
            return False
        if not mt5.login(ACCOUNT, server=SERVER):
            return False
        
        account_info = mt5.account_info()
        if account_info:
            print(f"Connected to {SERVER}")
            print(f"Balance: ${account_info.balance:.2f}")
            print(f"Equity: ${account_info.equity:.2f}")
        return True
    
    def count_positions(self):
        positions = mt5.positions_get()
        return len(positions) if positions else 0
    
    def has_position(self, symbol):
        """Check if already have position on this symbol"""
        positions = mt5.positions_get(symbol=symbol)
        return len(positions) > 0 if positions else False
    
    def execute_trade(self, symbol, direction, features):
        """Execute trade with dynamic risk management"""
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            return None
        
        price = tick.ask if direction == 'BUY' else tick.bid
        
        # Dynamic SL/TP
        sl, tp, atr = DynamicRiskManager.calculate_levels(symbol, price, direction)
        if sl is None:
            return None
        
        # Adjust lot size based on confidence
        confidence = features['strength']
        if confidence >= 80:
            lot = LOT_SIZE * 1.5
        elif confidence >= 60:
            lot = LOT_SIZE
        else:
            lot = LOT_SIZE * 0.5
        
        # Session filter - only trade London and NY
        hour = datetime.now(timezone.utc).hour
        if hour < 8 or hour >= 22:  # Skip Asian and late NY
            print(f"[SKIP] {symbol} - Outside trading hours ({hour}:00 UTC)")
            return None
        
        request = {
            'action': mt5.TRADE_ACTION_DEAL,
            'symbol': symbol,
            'volume': round(lot, 2),
            'type': mt5.ORDER_TYPE_BUY if direction == 'BUY' else mt5.ORDER_TYPE_SELL,
            'price': price,
            'sl': sl,
            'tp': tp,
            'deviation': 10,
            'magic': 444555,
            'comment': f'PA_{features["pattern"]}_{confidence:.0f}',
            'type_time': mt5.ORDER_TIME_GTC,
            'type_filling': mt5.ORDER_FILLING_IOC,
        }
        
        result = mt5.order_send(request)
        
        if result.retcode == mt5.TRADE_RETCODE_DONE:
            print(f"[EXECUTED] {symbol} {direction} {lot} lots @ {result.price}")
            print(f"           Pattern: {features['pattern']}, Score: {confidence}")
            print(f"           SL: {sl:.5f}, TP: {tp:.5f}, ATR: {atr:.5f}")
            
            # Log entry
            trade_data = {
                'position_id': result.order,
                'symbol': symbol,
                'direction': direction,
                'lot_size': lot,
                'entry_price': result.price,
                'sl': sl,
                'tp': tp,
                'ml_score': confidence,
                'pattern': features['pattern'],
                'volume_ratio': features['volume_ratio'],
                'vwap_distance': features.get('vwap_distance_pips'),
                'atr': atr
            }
            MLLogger.log_entry(trade_data)
            
            # Track position
            self.positions[result.order] = {
                'symbol': symbol,
                'direction': direction,
                'entry_price': result.price,
                'entry_time': datetime.now(timezone.utc),
                'ml_score': confidence,
                'pattern': features['pattern']
            }
            
            return result.order
        else:
            print(f"[FAILED] {result.retcode} - {result.comment}")
            return None
    
    def check_closed_positions(self):
        """Check for closed positions and log results"""
        positions = mt5.positions_get()
        current_tickets = set(p.ticket for p in positions) if positions else set()
        
        # Find closed trades
        closed = []
        for ticket, trade_info in list(self.positions.items()):
            if ticket not in current_tickets:
                closed.append((ticket, trade_info))
        
        # Process closed trades
        for ticket, trade_info in closed:
            from_date = trade_info['entry_time'] - timedelta(hours=24)
            to_date = datetime.now(timezone.utc) + timedelta(hours=1)
            deals = mt5.history_deals_get(from_date, to_date)
            
            if deals:
                exit_deal = None
                total_pnl = 0.0
                exit_price = None
                
                for deal in deals:
                    if deal.position_id == ticket:
                        total_pnl += deal.profit + deal.commission + deal.swap
                        if deal.entry == 1:  # DEAL_ENTRY_OUT
                            exit_deal = deal
                            exit_price = deal.price
                
                if exit_deal:
                    pnl = total_pnl
                    exit_price = exit_price or trade_info['entry_price']
                    
                    multiplier = 10000 if 'JPY' not in trade_info['symbol'] else 100
                    if trade_info['direction'] == 'BUY':
                        pips = (exit_price - trade_info['entry_price']) * multiplier
                    else:
                        pips = (trade_info['entry_price'] - exit_price) * multiplier
                    
                    duration = (datetime.now(timezone.utc) - trade_info['entry_time']).total_seconds() / 60
                    result = 'WIN' if pnl > 0 else ('BREAKEVEN' if pnl == 0 else 'LOSS')
                    
                    MLLogger.log_exit(
                        ticket,
                        trade_info['symbol'],
                        trade_info['direction'],
                        trade_info['entry_price'],
                        exit_price,
                        'TP' if result == 'WIN' and pips > 0 else ('SL' if result == 'LOSS' else 'UNKNOWN'),
                        pnl,
                        pips,
                        duration,
                        {
                            'ml_score_at_entry': trade_info['ml_score'],
                            'pattern': trade_info['pattern']
                        }
                    )
                    
                    print(f"[CLOSED] {trade_info['symbol']} {result} ${pnl:.2f} ({pips:.1f} pips)")
                    del self.positions[ticket]
    
    def run(self):
        print("\n" + "="*60)
        print("THE BEAST 4.0 - Price Action + Volume ML")
        print("="*60)
        print("Strategy: Pin Bar | Engulfing | Breakout + Volume")
        print("Filters: VWAP | Session (London+NY) | Max 3 positions")
        print("Risk: Dynamic SL/TP based on ATR (1:2 RR)")
        print("="*60)
        
        cycle = 0
        while True:
            try:
                cycle += 1
                
                # Check for closed positions first
                self.check_closed_positions()
                
                # Check existing positions
                current_positions = self.count_positions()
                
                for symbol in SYMBOLS:
                    if current_positions >= MAX_POSITIONS:
                        break
                    
                    # Skip if already have position on this symbol
                    if self.has_position(symbol):
                        continue
                    
                    # Analyze
                    features = PriceActionAnalyzer.analyze(symbol)
                    
                    if features and features['strength'] >= 60:
                        print(f"\n[SIGNAL] {symbol} {features['signal']} - {features['pattern']}")
                        print(f"         Score: {features['strength']:.0f}, Volume: {features['volume_ratio']:.2f}x")
                        
                        self.execute_trade(symbol, features['signal'], features)
                        current_positions += 1
                
                if cycle % 10 == 0:
                    print(f"\n[STATUS] Cycle {cycle}, Positions: {current_positions}/{MAX_POSITIONS}")
                
                time.sleep(60)  # 1 minute between scans
                
            except KeyboardInterrupt:
                print("\n[STOPPING] Bot stopped")
                break
            except Exception as e:
                print(f"[ERROR] {e}")
                import traceback
                traceback.print_exc()
                time.sleep(60)


if __name__ == "__main__":
    trader = MLTrader()
    if trader.initialize():
        trader.run()
