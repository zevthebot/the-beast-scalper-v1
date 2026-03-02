#!/usr/bin/env python3
"""
THE BEAST 3.0 ML - SCALPING WITH MACHINE LEARNING
Account: Pepperstone Demo (62108425)
ML-Enhanced: Logs rich data, learns patterns, auto-optimizes
"""

import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
import time
import json
import os
from pathlib import Path
from universal_journal import UniversalJournal

# Account - Pepperstone Demo
ACCOUNT = 62108425
SERVER = "PepperstoneUK-Demo"
PASSWORD = ""

# Config
INITIAL_BALANCE = 10000
RISK_PER_TRADE = 0.005
MAX_POSITIONS = 5
SL_PIPS = 10
TP_PIPS = 15
LOT_SIZE = 0.3

# Journal Path
JOURNAL_PATH = Path(r"C:\Users\Claw\.openclaw\workspace\mt5_trader\pepperstone_journal.jsonl")
ML_STATE_PATH = Path(r"C:\Users\Claw\.openclaw\workspace\mt5_trader\pepperstone_ml_state.json")

SYMBOLS = [
    "EURUSD", "GBPUSD", "USDJPY",
    "GBPJPY", "AUDUSD", "EURGBP"
]

class MLLogger:
    """Rich trade logging for ML analysis"""
    
    @staticmethod
    def log_entry(trade_data):
        """Log entry with full technical context"""
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
    def log_exit(position_id, symbol, direction, entry_price, exit_price, 
                 exit_reason, pnl, pips, duration_min, ml_features=None):
        """Log exit with ML features"""
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

class FeatureExtractor:
    """Extract ML features from market data"""
    
    @staticmethod
    def get_features(symbol):
        """Extract comprehensive features for ML"""
        rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M5, 0, 50)
        if rates is None or len(rates) < 30:
            return None
        
        df = pd.DataFrame(rates)
        
        # Price action
        df['ema3'] = df['close'].ewm(span=3).mean()
        df['ema8'] = df['close'].ewm(span=8).mean()
        df['ema21'] = df['close'].ewm(span=21).mean()
        df['sma50'] = df['close'].rolling(window=50, min_periods=1).mean()
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14, min_periods=1).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14, min_periods=1).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # ATR
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = np.max(ranges, axis=1)
        df['atr'] = true_range.rolling(window=14, min_periods=1).mean()
        
        # Trend strength (ADX approximation)
        df['plus_dm'] = df['high'].diff()
        df['minus_dm'] = -df['low'].diff()
        df['plus_dm'] = df['plus_dm'].where((df['plus_dm'] > df['minus_dm']) & (df['plus_dm'] > 0), 0)
        df['minus_dm'] = df['minus_dm'].where((df['minus_dm'] > df['plus_dm']) & (df['minus_dm'] > 0), 0)
        df['adx'] = (df['plus_dm'].rolling(window=14, min_periods=1).mean() / df['atr'].rolling(window=14, min_periods=1).mean() * 100).rolling(window=14, min_periods=1).mean()
        
        # Bollinger Bands
        df['bb_middle'] = df['close'].rolling(window=20, min_periods=1).mean()
        df['bb_std'] = df['close'].rolling(window=20, min_periods=1).std()
        df['bb_upper'] = df['bb_middle'] + 2 * df['bb_std']
        df['bb_lower'] = df['bb_middle'] - 2 * df['bb_std']
        df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
        
        # Volume analysis
        df['volume_sma'] = df['tick_volume'].rolling(window=20, min_periods=1).mean()
        df['volume_ratio'] = df['tick_volume'] / df['volume_sma']
        
        # Session
        current_hour = datetime.now(timezone.utc).hour
        if 0 <= current_hour < 8:
            session = "Asian"
        elif 8 <= current_hour < 13:
            session = "London"
        elif 13 <= current_hour < 17:
            session = "London_NY_Overlap"
        elif 17 <= current_hour < 22:
            session = "NY"
        else:
            session = "Off_Hours"
        
        latest = df.iloc[-1]
        
        return {
            # Price features
            'close': float(latest['close']),
            'ema3': float(latest['ema3']),
            'ema8': float(latest['ema8']),
            'ema21': float(latest['ema21']),
            'ema_spread': float(latest['ema3'] - latest['ema8']),
            'price_vs_ema21': float((latest['close'] - latest['ema21']) / latest['ema21'] * 100),
            
            # Momentum
            'rsi': float(latest['rsi']),
            'adx': float(latest['adx']) if not pd.isna(latest['adx']) else 20.0,
            
            # Volatility
            'atr': float(latest['atr']),
            'atr_percent': float(latest['atr'] / latest['close'] * 100),
            
            # Bollinger
            'bb_position': float(latest['bb_position']),
            'bb_width': float((latest['bb_upper'] - latest['bb_lower']) / latest['bb_middle'] * 100),
            
            # Volume
            'volume_ratio': float(latest['volume_ratio']),
            
            # Context
            'session': session,
            'day_of_week': datetime.now().strftime('%A'),
            'hour': current_hour,
            
            # Trend classification
            'trend_5m': 'BULLISH' if latest['ema3'] > latest['ema8'] else 'BEARISH',
            'trend_15m': 'BULLISH' if latest['close'] > latest['ema21'] else 'BEARISH'
        }

class MLOptimizer:
    """Machine Learning optimizer for strategy parameters"""
    
    def __init__(self):
        self.state = self.load_state()
    
    def load_state(self):
        if ML_STATE_PATH.exists():
            with open(ML_STATE_PATH, 'r') as f:
                return json.load(f)
        return {
            'trade_count': 0,
            'win_count': 0,
            'loss_count': 0,
            'total_pnl': 0,
            'symbol_performance': {},
            'session_performance': {},
            'rsi_performance': {'low': {'wins': 0, 'losses': 0}, 
                              'mid': {'wins': 0, 'losses': 0}, 
                              'high': {'wins': 0, 'losses': 0}},
            'current_params': {
                'min_rsi': 30,
                'max_rsi': 70,
                'min_adx': 25,
                'min_atr_percent': 0.05,
                'min_volume_ratio': 0.8,
                'trend_filter': False
            },
            'last_optimized': None
        }
    
    def save_state(self):
        with open(ML_STATE_PATH, 'w') as f:
            json.dump(self.state, f, indent=2)
    
    def update_from_trade(self, symbol, features, direction, pnl, result):
        """Update ML state with trade result"""
        self.state['trade_count'] += 1
        self.state['total_pnl'] += pnl
        
        if result == 'WIN':
            self.state['win_count'] += 1
        else:
            self.state['loss_count'] += 1
        
        # Symbol performance
        if symbol not in self.state['symbol_performance']:
            self.state['symbol_performance'][symbol] = {'wins': 0, 'losses': 0, 'pnl': 0}
        self.state['symbol_performance'][symbol]['pnl'] += pnl
        if result == 'WIN':
            self.state['symbol_performance'][symbol]['wins'] += 1
        else:
            self.state['symbol_performance'][symbol]['losses'] += 1
        
        # Session performance
        session = features.get('session', 'Unknown')
        if session not in self.state['session_performance']:
            self.state['session_performance'][session] = {'wins': 0, 'losses': 0}
        if result == 'WIN':
            self.state['session_performance'][session]['wins'] += 1
        else:
            self.state['session_performance'][session]['losses'] += 1
        
        # RSI performance buckets
        rsi = features.get('rsi', 50)
        rsi_bucket = 'low' if rsi < 40 else ('high' if rsi > 60 else 'mid')
        if result == 'WIN':
            self.state['rsi_performance'][rsi_bucket]['wins'] += 1
        else:
            self.state['rsi_performance'][rsi_bucket]['losses'] += 1
        
        # Auto-optimize every 20 trades
        if self.state['trade_count'] % 20 == 0:
            self.optimize_parameters()
        
        self.save_state()
    
    def optimize_parameters(self):
        """Adjust strategy parameters based on performance"""
        print(f"\n[ML] Optimizing parameters after {self.state['trade_count']} trades...")
        
        total = self.state['trade_count']
        win_rate = self.state['win_count'] / total if total > 0 else 0.5
        
        # Adjust RSI thresholds based on performance
        low_rsi_total = self.state['rsi_performance']['low']['wins'] + self.state['rsi_performance']['low']['losses']
        if low_rsi_total > 5:
            low_rsi_wr = self.state['rsi_performance']['low']['wins'] / low_rsi_total
            if low_rsi_wr < 0.4:
                self.state['current_params']['min_rsi'] = min(45, self.state['current_params']['min_rsi'] + 5)
                print(f"  [ML] Raised min RSI to {self.state['current_params']['min_rsi']} (low RSI performance: {low_rsi_wr:.1%})")
        
        high_rsi_total = self.state['rsi_performance']['high']['wins'] + self.state['rsi_performance']['high']['losses']
        if high_rsi_total > 5:
            high_rsi_wr = self.state['rsi_performance']['high']['wins'] / high_rsi_total
            if high_rsi_wr < 0.4:
                self.state['current_params']['max_rsi'] = max(55, self.state['current_params']['max_rsi'] - 5)
                print(f"  [ML] Lowered max RSI to {self.state['current_params']['max_rsi']} (high RSI performance: {high_rsi_wr:.1%})")
        
        # Find best performing symbols
        symbol_win_rates = {}
        for sym, data in self.state['symbol_performance'].items():
            sym_total = data['wins'] + data['losses']
            if sym_total >= 3:
                symbol_win_rates[sym] = data['wins'] / sym_total
        
        if symbol_win_rates:
            best_symbol = max(symbol_win_rates, key=symbol_win_rates.get)
            print(f"  [ML] Best performing symbol: {best_symbol} ({symbol_win_rates[best_symbol]:.1%} win rate)")
        
        # Session analysis
        session_win_rates = {}
        for sess, data in self.state['session_performance'].items():
            sess_total = data['wins'] + data['losses']
            if sess_total >= 3:
                session_win_rates[sess] = data['wins'] / sess_total
        
        if session_win_rates:
            best_session = max(session_win_rates, key=session_win_rates.get)
            print(f"  [ML] Best performing session: {best_session} ({session_win_rates[best_session]:.1%} win rate)")
        
        self.state['last_optimized'] = datetime.now().isoformat()
        print(f"[ML] Current win rate: {win_rate:.1%}, Total PnL: ${self.state['total_pnl']:.2f}\n")
        
        return self.state['current_params']
    
    def get_signal_quality(self, features):
        """Score signal quality 0-100 based on ML learning"""
        score = 50  # Base score
        params = self.state['current_params']
        
        # RSI filter
        rsi = features.get('rsi', 50)
        if params['min_rsi'] <= rsi <= params['max_rsi']:
            score += 15
        else:
            score -= 20
        
        # ADX filter
        if features.get('adx', 0) > params['min_adx']:
            score += 10
        
        # ATR filter - volatility check
        if features.get('atr_percent', 0) > params['min_atr_percent']:
            score += 10
        
        # Volume filter
        if features.get('volume_ratio', 1) > params['min_volume_ratio']:
            score += 10
        
        # Symbol historical performance
        symbol = features.get('symbol', '')
        if symbol in self.state['symbol_performance']:
            sym_data = self.state['symbol_performance'][symbol]
            sym_total = sym_data['wins'] + sym_data['losses']
            if sym_total >= 3:
                sym_wr = sym_data['wins'] / sym_total
                if sym_wr > 0.6:
                    score += 15
                elif sym_wr < 0.4:
                    score -= 15
        
        # Session performance
        session = features.get('session', '')
        if session in self.state['session_performance']:
            sess_data = self.state['session_performance'][session]
            sess_total = sess_data['wins'] + sess_data['losses']
            if sess_total >= 3:
                sess_wr = sess_data['wins'] / sess_total
                if sess_wr > 0.55:
                    score += 10
                elif sess_wr < 0.45:
                    score -= 10
        
        return max(0, min(100, score))

class ScalpingStrategy:
    def __init__(self):
        self.active_symbols = set()
        self.open_trades = {}  # position_id -> trade info
        self.ml_optimizer = MLOptimizer()
    
    def get_rates(self, symbol, count=50):
        rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M5, 0, count)
        if rates is None or len(rates) == 0:
            return None
        return pd.DataFrame(rates)
    
    def analyze(self, symbol):
        """Analyze with ML-enhanced scoring"""
        df = self.get_rates(symbol, 30)
        if df is None or len(df) < 20:
            return None
        
        # Get rich features
        features = FeatureExtractor.get_features(symbol)
        if features is None:
            return None
        
        # BLOCK ASIAN SESSION COMPLETELY
        if features.get('session') == 'Asian':
            return None
        
        features['symbol'] = symbol
        
        # Basic EMA crossover
        df['ema3'] = df['close'].ewm(span=3).mean()
        df['ema8'] = df['close'].ewm(span=8).mean()
        
        latest = df.iloc[-1]
        prev = df.iloc[-2]
        
        signal = None
        
        # BUY: Price crosses above EMA3 and EMA3 > EMA8
        if latest['close'] > latest['ema3'] > latest['ema8'] and prev['close'] <= prev['ema3']:
            signal = 'BUY'
        
        # SELL: Price crosses below EMA3 and EMA3 < EMA8
        elif latest['close'] < latest['ema3'] < latest['ema8'] and prev['close'] >= prev['ema3']:
            signal = 'SELL'
        
        if signal:
            # Get ML quality score
            quality_score = self.ml_optimizer.get_signal_quality(features)
            
            return {
                'signal': signal,
                'strength': quality_score,
                'reason': 'EMA_CROSS_ML',
                'features': features
            }
        
        return None
    
    def execute_signal(self, symbol, direction, strength, features):
        print(f"[EXECUTING] {symbol} {direction} (ML Score: {strength})")
        
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            return None
        
        # Adjust lot size based on ML confidence and symbol
        # XAUUSD uses smaller lot size (0.1), others use 0.3
        base_lot = 0.1 if symbol == 'XAUUSD' else LOT_SIZE
        
        if strength >= 80:
            lot = base_lot * 1.5  # Increase size for high confidence
        elif strength >= 60:
            lot = base_lot
        else:
            lot = base_lot * 0.5  # Reduce size for low confidence
        
        if direction == 'BUY':
            price = tick.ask
            sl = price - (SL_PIPS * 0.0001 if 'JPY' not in symbol else SL_PIPS * 0.01)
            tp = price + (TP_PIPS * 0.0001 if 'JPY' not in symbol else TP_PIPS * 0.01)
            order_type = mt5.ORDER_TYPE_BUY
        else:
            price = tick.bid
            sl = price + (SL_PIPS * 0.0001 if 'JPY' not in symbol else SL_PIPS * 0.01)
            tp = price - (TP_PIPS * 0.0001 if 'JPY' not in symbol else TP_PIPS * 0.01)
            order_type = mt5.ORDER_TYPE_SELL
        
        request = {
            'action': mt5.TRADE_ACTION_DEAL,
            'symbol': symbol,
            'volume': round(lot, 2),
            'type': order_type,
            'price': price,
            'sl': sl,
            'tp': tp,
            'deviation': 10,
            'magic': 123456,
            'comment': f'BEAST3_ML_{strength}',
            'type_time': mt5.ORDER_TIME_GTC,
            'type_filling': mt5.ORDER_FILLING_IOC,
        }
        
        result = mt5.order_send(request)
        
        if result.retcode == mt5.TRADE_RETCODE_DONE:
            print(f"[EXECUTED] {symbol} {direction} {lot} lots @ {result.price}")
            
            # Log rich entry data
            trade_data = {
                'position_id': result.order,
                'symbol': symbol,
                'direction': direction,
                'lot_size': lot,
                'entry_price': result.price,
                'sl': sl,
                'tp': tp,
                'ml_score': strength,
                **features
            }
            MLLogger.log_entry(trade_data)
            
            UniversalJournal.log_entry(
                account_id=ACCOUNT,
                server=SERVER,
                symbol=symbol,
                direction=direction,
                lot_size=lot,
                entry_price=result.price,
                sl=sl,
                tp=tp,
                strategy='EMA_CROSS_ML',
                bot_version='3.0',
                ml_score=strength,
                features=features,
                position_id=result.order
            )
            
            # Store for tracking
            self.open_trades[result.order] = {
                'symbol': symbol,
                'direction': direction,
                'entry_price': result.price,
                'entry_time': datetime.now(timezone.utc),
                'features': features,
                'ml_score': strength
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
        for ticket, trade_info in list(self.open_trades.items()):
            if ticket not in current_tickets:
                closed.append((ticket, trade_info))
        
        # Process closed trades
        for ticket, trade_info in closed:
            # Get deal history for this position
            from_date = trade_info['entry_time'] - timedelta(hours=24)
            to_date = datetime.now(timezone.utc) + timedelta(hours=1)
            deals = mt5.history_deals_get(from_date, to_date)
            
            if deals:
                # Find the actual closing deal (the one with non-zero profit or opposite entry)
                exit_deal = None
                total_pnl = 0.0
                exit_price = None
                
                for deal in deals:
                    if deal.position_id == ticket:
                        # Sum up all profit/swap/commission for this position
                        total_pnl += deal.profit + deal.commission + deal.swap
                        # Check if this is the OUT deal (closing deal has entry type 1/OUT)
                        if deal.entry == 1:  # DEAL_ENTRY_OUT
                            exit_deal = deal
                            exit_price = deal.price
                
                # If we found the closing deal
                if exit_deal:
                    pnl = total_pnl
                else:
                    # Fallback: assume position was closed at market, use current price
                    tick = mt5.symbol_info_tick(trade_info['symbol'])
                    exit_price = tick.last if tick else trade_info['entry_price']
                    pnl = total_pnl  # Use whatever profit was recorded
                
                if exit_price is None:
                    exit_price = trade_info['entry_price']  # Fallback
                
                pips = self.calculate_pips(trade_info['symbol'], 
                                           trade_info['entry_price'], 
                                           exit_price, 
                                           trade_info['direction'])
                duration = (datetime.now(timezone.utc) - trade_info['entry_time']).total_seconds() / 60
                
                result = 'WIN' if pnl > 0 else ('BREAKEVEN' if pnl == 0 else 'LOSS')
                
                # Update ML optimizer
                self.ml_optimizer.update_from_trade(
                    trade_info['symbol'],
                    trade_info['features'],
                    trade_info['direction'],
                    pnl,
                    result
                )
                
                # Log exit with ML features
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
                        'entry_rsi': trade_info['features'].get('rsi'),
                        'entry_adx': trade_info['features'].get('adx'),
                        'entry_session': trade_info['features'].get('session')
                    }
                )
                
                UniversalJournal.log_exit(
                    position_id=ticket,
                    account_id=ACCOUNT,
                    symbol=trade_info['symbol'],
                    direction=trade_info['direction'],
                    entry_price=trade_info['entry_price'],
                    exit_price=exit_price,
                    exit_reason='TP' if result == 'WIN' and pips > 0 else ('SL' if result == 'LOSS' else 'UNKNOWN'),
                    pnl=pnl,
                    pips=pips,
                    duration_min=duration,
                    bot_version='3.0'
                )
                
                print(f"[CLOSED] {trade_info['symbol']} {result} ${pnl:.2f} ({pips:.1f} pips) - ML Score was {trade_info['ml_score']}")
                
                del self.open_trades[ticket]
    
    def calculate_pips(self, symbol, entry, exit_price, direction):
        """Calculate pips for trade"""
        multiplier = 10000 if 'JPY' not in symbol else 100
        if direction == 'BUY':
            return (exit_price - entry) * multiplier
        else:
            return (entry - exit_price) * multiplier
    
    def has_open_position(self, symbol, direction=None):
        """Check if we already have an open position on this symbol
        If direction specified, checks for that specific direction (anti-hedge)
        Returns: True if position exists, False otherwise
        """
        # Check MT5 positions directly (most reliable)
        positions = mt5.positions_get(symbol=symbol)
        if positions:
            for pos in positions:
                # If direction specified, check if it matches (would be a hedge)
                if direction:
                    pos_direction = 'BUY' if pos.type == mt5.ORDER_TYPE_BUY else 'SELL'
                    if pos_direction == direction:
                        return True  # Same direction - already in this trade
                    else:
                        # Opposite direction - this would be hedging!
                        print(f"[HEDGE BLOCKED] {symbol}: Already have {pos_direction} position, blocked {direction} signal")
                        return True
                return True  # Any position exists
        
        # Also check internal tracking
        for trade in self.open_trades.values():
            if trade['symbol'] == symbol:
                if direction and trade['direction'] != direction:
                    print(f"[HEDGE BLOCKED] {symbol}: Tracked {trade['direction']} position, blocked {direction} signal")
                return True
        
        return False
    
    def count_open_positions(self):
        """Count actual open positions in MT5 (not just tracked ones)"""
        positions = mt5.positions_get()
        return len(positions) if positions else 0
    
    def run(self, auto_trade=True):
        self.check_closed_positions()
        
        # Count actual positions in MT5 (including those from other sessions)
        actual_position_count = self.count_open_positions()
        
        for symbol in SYMBOLS:
            # Check actual position count from MT5
            if actual_position_count >= MAX_POSITIONS:
                print(f"[MAX] {actual_position_count}/{MAX_POSITIONS} positions - skipping {symbol}")
                continue
            
            # Skip if already have position in this symbol (anti-hedge protection)
            if self.has_open_position(symbol):
                continue
            
            result = self.analyze(symbol)
            if result:
                signal = result['signal']
                strength = result['strength']
                
                # Double-check no position exists before executing (race condition protection)
                if self.has_open_position(symbol, direction=signal):
                    print(f"[SKIP] {symbol} {signal}: Position appeared during analysis")
                    continue
                
                print(f"[SIGNAL] {symbol} {signal} - ML Quality: {strength}%")
                
                # Only trade if ML score is good enough
                if auto_trade and strength >= 55:
                    ticket = self.execute_signal(symbol, signal, strength, result['features'])
                    if ticket:
                        actual_position_count += 1  # Update count after successful open

class ScalpingBot:
    def __init__(self):
        self.strategy = ScalpingStrategy()
    
    def initialize(self):
        if not mt5.initialize():
            print("MT5 init failed")
            return False
        
        authorized = mt5.login(ACCOUNT, password=PASSWORD, server=SERVER)
        if not authorized:
            print(f"Login failed: {mt5.last_error()}")
            return False
        
        account_info = mt5.account_info()
        if account_info:
            print(f"Connected to {SERVER}")
            print(f"Balance: ${account_info.balance:.2f}")
            print(f"Equity: ${account_info.equity:.2f}")
            print(f"\nTHE BEAST 3.0 ML - SCALPING MODE")
            print(f"ML-Enhanced: Yes")
            print(f"Auto-optimize: Every 20 trades")
            print(f"Quality threshold: 55+")
            print(f"{'='*50}")
        return True
    
    def run(self):
        cycle = 0
        while True:
            try:
                cycle += 1
                self.strategy.run(auto_trade=True)
                
                if cycle % 60 == 0:  # Every hour
                    state = self.strategy.ml_optimizer.state
                    print(f"\n[STATUS] Trades: {state['trade_count']} | "
                          f"Win Rate: {state['win_count']/max(state['trade_count'],1)*100:.1f}% | "
                          f"PnL: ${state['total_pnl']:.2f}")
                
                time.sleep(60)
            except KeyboardInterrupt:
                print("\n[STOPPING] Bot stopped by user")
                break
            except Exception as e:
                print(f"[ERROR] {e}")
                time.sleep(60)

if __name__ == "__main__":
    bot = ScalpingBot()
    if bot.initialize():
        bot.run()
