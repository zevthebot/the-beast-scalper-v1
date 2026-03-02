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
LOT_SIZE = 1.0
MAX_POSITIONS = 10
RISK_PER_TRADE = 0.01

# 6 major pairs only - maximum liquidity, lowest spread
SYMBOLS = ["EURUSD", "GBPUSD", "USDJPY", "GBPJPY", "AUDUSD", "EURGBP"]

# Import universal journal
from universal_journal import UniversalJournal

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
    def calc_rsi(series, period=14):
        """Calculate RSI"""
        delta = series.diff()
        gain = delta.where(delta > 0, 0).rolling(period, min_periods=1).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(period, min_periods=1).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    @staticmethod
    def calc_adx(df, period=14):
        """Calculate ADX (trend strength)"""
        plus_dm = df['high'].diff()
        minus_dm = -df['low'].diff()
        plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0)
        minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0)

        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)

        atr = tr.rolling(period, min_periods=1).mean()
        plus_di = (plus_dm.rolling(period, min_periods=1).mean() / atr) * 100
        minus_di = (minus_dm.rolling(period, min_periods=1).mean() / atr) * 100
        dx = (np.abs(plus_di - minus_di) / (plus_di + minus_di)) * 100
        adx = dx.rolling(period, min_periods=1).mean()
        return adx

    @staticmethod
    def get_h4_trend(symbol):
        """Get H4 trend direction"""
        rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H4, 0, 30)
        if rates is None or len(rates) < 21:
            return 'UNKNOWN'
        df = pd.DataFrame(rates)
        ema8 = df['close'].ewm(span=8).mean().iloc[-1]
        ema21 = df['close'].ewm(span=21).mean().iloc[-1]
        if ema8 > ema21:
            return 'BULLISH'
        elif ema8 < ema21:
            return 'BEARISH'
        return 'FLAT'

    @staticmethod
    def get_session(hour_utc):
        """Map UTC hour to session name"""
        if 0 <= hour_utc < 8:
            return 'Asian'
        elif 8 <= hour_utc < 13:
            return 'London'
        elif 13 <= hour_utc < 17:
            return 'London_NY_Overlap'
        elif 17 <= hour_utc < 22:
            return 'NY'
        return 'Off_Hours'

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
        df['ema8'] = df['close'].ewm(span=8).mean()
        df['ema21'] = df['close'].ewm(span=21).mean()
        df['rsi'] = PriceActionAnalyzer.calc_rsi(df['close'])
        df['adx'] = PriceActionAnalyzer.calc_adx(df)

        # ATR
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df['atr'] = tr.rolling(14, min_periods=1).mean()

        # Price action patterns
        pin_bar = PriceActionAnalyzer.detect_pin_bar(df)
        engulfing = PriceActionAnalyzer.detect_engulfing(df)
        breakout = PriceActionAnalyzer.detect_breakout(df)
        vwap = PriceActionAnalyzer.calculate_vwap(df)
        
        latest = df.iloc[-1]
        volume_confirmed = latest['volume_ratio'] > 0.6  # Reduced threshold for early session entries
        
        # VWAP distance
        vwap_distance = (latest['close'] - vwap) / vwap * 10000  # in pips

        # Pip multiplier
        pip_mult = 100 if ('JPY' in symbol or 'XAU' in symbol) else 10000
        atr_pips = float(latest['atr'] * pip_mult)

        now_utc = datetime.now(timezone.utc)
        
        features = {
            'close': float(latest['close']),
            'vwap': float(vwap),
            'vwap_distance_pips': float(vwap_distance),
            'volume_ratio': float(latest['volume_ratio']),
            'volume_confirmed': volume_confirmed,
            'pattern': None,
            'signal': None,
            'strength': 0,
            # --- rich features for journal ---
            'adx': float(latest['adx']) if not pd.isna(latest['adx']) else 0.0,
            'atr_pips': atr_pips,
            'rsi': float(latest['rsi']) if not pd.isna(latest['rsi']) else 50.0,
            'session': PriceActionAnalyzer.get_session(now_utc.hour),
            'hour_utc': now_utc.hour,
            'day_of_week': now_utc.strftime('%A'),
            'h4_trend': PriceActionAnalyzer.get_h4_trend(symbol),
            'price_vs_ema8': float((latest['close'] - latest['ema8']) / latest['ema8'] * 10000),
            'price_vs_ema21': float((latest['close'] - latest['ema21']) / latest['ema21'] * 10000),
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
            
        elif breakout and volume_confirmed and latest['volume_ratio'] > 1.5:
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
        
        # Calculate max 10 pips distance in price units
        # Hard limit to prevent huge SL/TP during high volatility
        pip_value = 0.01 if ('JPY' in symbol or 'XAU' in symbol) else 0.0001
        max_distance = 10 * pip_value  # 10 pips max
        
        # Use ATR if smaller, otherwise cap at 10 pips
        sl_distance = min(atr * 1.0, max_distance)
        tp_distance = min(atr * 1.0, max_distance)  # Same = exact 1:1 RR
        
        if direction == 'BUY':
            sl = entry_price - sl_distance
            tp = entry_price + tp_distance
        else:
            sl = entry_price + sl_distance
            tp = entry_price - tp_distance
        
        return sl, tp, atr


# Use UniversalJournal for all logging
# All trades from all versions go to universal_trade_journal.jsonl


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
        
        # Sync with MT5 - track existing positions
        self.sync_with_mt5()
        return True
    
    def sync_with_mt5(self):
        """Sync with MT5 to track existing open positions"""
        print("\n[SYNC] Checking for existing positions in MT5...")
        positions = mt5.positions_get()
        if positions:
            print(f"[SYNC] Found {len(positions)} open positions, adding to tracking...")
            for pos in positions:
                if pos.ticket not in self.positions:
                    direction = 'BUY' if pos.type == mt5.ORDER_TYPE_BUY else 'SELL'
                    self.positions[pos.ticket] = {
                        'symbol': pos.symbol,
                        'direction': direction,
                        'entry_price': pos.price_open,
                        'entry_time': datetime.now(timezone.utc),  # Approximate
                        'ml_score': 0,  # Unknown for pre-existing
                        'pattern': 'PREEXISTING'
                    }
                    print(f"[SYNC] Tracking: {pos.symbol} {direction} (Ticket: {pos.ticket})")
            print(f"[SYNC] Now tracking {len(self.positions)} positions\n")
        else:
            print("[SYNC] No existing positions found\n")
    
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
        
        # Fixed lot size for discipline
        confidence = features['strength']
        lot = LOT_SIZE  # Fixed 0.2 lots regardless of confidence
        
        # Session filter - COMPLETELY DISABLED
        # Trading allowed 24/7
        pass
        
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
            
            # Calculate SL/TP in pips and planned RR
            pip_mult = 100 if ('JPY' in symbol or 'XAU' in symbol) else 10000
            sl_pips = abs(result.price - sl) * pip_mult
            tp_pips = abs(tp - result.price) * pip_mult
            rr_planned = tp_pips / sl_pips if sl_pips > 0 else 0.0

            # Log entry to universal journal with rich features
            UniversalJournal.log_entry(
                account_id=ACCOUNT,
                server=SERVER,
                symbol=symbol,
                direction=direction,
                lot_size=lot,
                entry_price=result.price,
                sl=sl,
                tp=tp,
                strategy=features['pattern'],
                bot_version="4.0",
                ml_score=confidence,
                features={
                    'adx': features.get('adx'),
                    'atr_pips': features.get('atr_pips'),
                    'rsi': features.get('rsi'),
                    'volume_ratio': features.get('volume_ratio'),
                    'session': features.get('session'),
                    'hour_utc': features.get('hour_utc'),
                    'day_of_week': features.get('day_of_week'),
                    'h4_trend': features.get('h4_trend'),
                    'vwap_distance_pips': features.get('vwap_distance_pips'),
                    'price_vs_ema8': features.get('price_vs_ema8'),
                    'price_vs_ema21': features.get('price_vs_ema21'),
                    'sl_pips': round(sl_pips, 1),
                    'tp_pips': round(tp_pips, 1),
                    'rr_planned': round(rr_planned, 2),
                },
                position_id=result.order
            )
            
            # Track position (with MAE/MFE tracking)
            self.positions[result.order] = {
                'symbol': symbol,
                'direction': direction,
                'entry_price': result.price,
                'entry_time': datetime.now(timezone.utc),
                'ml_score': confidence,
                'pattern': features['pattern'],
                'sl': sl,
                'tp': tp,
                'sl_pips': sl_pips,
                'tp_pips': tp_pips,
                'rr_planned': rr_planned,
                'mae_pips': 0.0,  # Maximum Adverse Excursion
                'mfe_pips': 0.0,  # Maximum Favorable Excursion
                'features': features,
            }
            
            return result.order
        else:
            print(f"[FAILED] {result.retcode} - {result.comment}")
            return None
    
    def update_mae_mfe(self):
        """Update MAE/MFE for all open positions every cycle"""
        for ticket, info in self.positions.items():
            # Ensure MAE/MFE fields exist (for synced positions)
            if 'mae_pips' not in info:
                info['mae_pips'] = 0.0
            if 'mfe_pips' not in info:
                info['mfe_pips'] = 0.0

            tick = mt5.symbol_info_tick(info['symbol'])
            if tick is None:
                continue

            pip_mult = 100 if ('JPY' in info['symbol'] or 'XAU' in info['symbol']) else 10000

            if info['direction'] == 'BUY':
                # For BUY: favorable = price goes UP, adverse = price goes DOWN
                current_favorable = (tick.bid - info['entry_price']) * pip_mult
                current_adverse = (info['entry_price'] - tick.bid) * pip_mult
            else:
                # For SELL: favorable = price goes DOWN, adverse = price goes UP
                current_favorable = (info['entry_price'] - tick.ask) * pip_mult
                current_adverse = (tick.ask - info['entry_price']) * pip_mult

            if current_favorable > info['mfe_pips']:
                info['mfe_pips'] = current_favorable
            if current_adverse > info['mae_pips']:
                info['mae_pips'] = current_adverse

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
                
                # Log exit even if exit_deal not found (use available data)
                if exit_deal or total_pnl != 0:
                    pnl = total_pnl
                    # If exit_price not found, estimate from SL/TP or use entry
                    if exit_price is None:
                        if trade_info['direction'] == 'BUY':
                            if pnl > 0:
                                exit_price = trade_info.get('tp', trade_info['entry_price'])
                            else:
                                exit_price = trade_info.get('sl', trade_info['entry_price'])
                        else:
                            if pnl > 0:
                                exit_price = trade_info.get('tp', trade_info['entry_price'])
                            else:
                                exit_price = trade_info.get('sl', trade_info['entry_price'])
                    
                    multiplier = 100 if ('JPY' in trade_info['symbol'] or 'XAU' in trade_info['symbol']) else 10000
                    if trade_info['direction'] == 'BUY':
                        pips = (exit_price - trade_info['entry_price']) * multiplier
                    else:
                        pips = (trade_info['entry_price'] - exit_price) * multiplier
                    
                    duration = (datetime.now(timezone.utc) - trade_info['entry_time']).total_seconds() / 60
                    result = 'WIN' if pnl > 0 else ('BREAKEVEN' if pnl == 0 else 'LOSS')

                    # Determine detailed exit reason
                    sl_pips = trade_info.get('sl_pips', 0)
                    tp_pips = trade_info.get('tp_pips', 0)
                    if result == 'WIN' and abs(pips - tp_pips) < 2:
                        exit_reason = 'TP'
                        exit_reason_detail = 'TP_HIT'
                    elif result == 'LOSS' and abs(abs(pips) - sl_pips) < 2:
                        exit_reason = 'SL'
                        exit_reason_detail = 'SL_HIT'
                    elif result == 'WIN':
                        exit_reason = 'MANUAL'
                        exit_reason_detail = 'MANUAL_CLOSE_PROFIT'
                    elif result == 'LOSS':
                        exit_reason = 'MANUAL'
                        exit_reason_detail = 'MANUAL_CLOSE_LOSS'
                    else:
                        exit_reason = 'BREAKEVEN'
                        exit_reason_detail = 'BREAKEVEN'

                    # Calculate achieved RR
                    rr_achieved = abs(pips) / sl_pips if sl_pips > 0 and result == 'WIN' else (
                        -(abs(pips) / sl_pips) if sl_pips > 0 else 0.0
                    )

                    mae_pips = round(trade_info.get('mae_pips', 0.0), 1)
                    mfe_pips = round(trade_info.get('mfe_pips', 0.0), 1)
                    
                    UniversalJournal.log_exit(
                        position_id=ticket,
                        account_id=ACCOUNT,
                        symbol=trade_info['symbol'],
                        direction=trade_info['direction'],
                        entry_price=trade_info['entry_price'],
                        exit_price=exit_price,
                        exit_reason=exit_reason,
                        pnl=pnl,
                        pips=pips,
                        duration_min=duration,
                        bot_version="4.0",
                        ml_features={
                            'ml_score_at_entry': trade_info['ml_score'],
                            'pattern': trade_info['pattern'],
                            'mae_pips': mae_pips,
                            'mfe_pips': mfe_pips,
                            'rr_achieved': round(rr_achieved, 2),
                            'rr_planned': round(trade_info.get('rr_planned', 0), 2),
                            'exit_reason_detail': exit_reason_detail,
                        }
                    )
                    
                    print(f"[CLOSED] {trade_info['symbol']} {result} ${pnl:.2f} ({pips:.1f} pips) MAE:{mae_pips} MFE:{mfe_pips}")
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
                
                # Update MAE/MFE for open positions
                self.update_mae_mfe()
                
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
