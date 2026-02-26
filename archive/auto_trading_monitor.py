"""
MT5 Auto Trading Monitor - 24/7 Setup Scanner
Monitors for valid signals across all strategies and pairs 24/7
"""
import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime
import pytz

class MT5AutoTrader:
    def __init__(self):
        self.connected = False
        
    def connect(self):
        if not mt5.initialize():
            print(f"[ERROR] MT5 initialize failed: {mt5.last_error()}")
            return False
        
        account_info = mt5.account_info()
        if account_info is None:
            print("[ERROR] MT5 not logged in")
            mt5.shutdown()
            return False
        
        self.connected = True
        print(f"[OK] Connected to MT5 - Account: {account_info.login}")
        return True
    
    def analyze_all_strategies(self, symbol):
        """Analyze all strategies for a symbol and return best signal"""
        signals = []
        
        # 1. Trend Following Analysis
        trend_signal = self.analyze_trend(symbol)
        if trend_signal:
            signals.append(('TREND', trend_signal))
        
        # 2. Range Trading Analysis
        range_signal = self.analyze_range(symbol)
        if range_signal:
            signals.append(('RANGE', range_signal))
        
        # 3. Breakout Analysis (for pairs with clear ranges)
        breakout_signal = self.analyze_breakout(symbol)
        if breakout_signal:
            signals.append(('BREAKOUT', breakout_signal))
        
        return signals
    
    def get_sl_tp_pips(self, symbol):
        """Get appropriate SL/TP in price terms based on symbol"""
        if symbol == 'XAUUSD':
            # Gold has 2 decimal places, 1 pip = 0.01
            return 5.0, 10.0  # 50 pips = 0.50, 100 pips = 1.00
        elif 'JPY' in symbol:
            # JPY pairs have 3 decimal places, 1 pip = 0.01
            return 0.50, 1.00  # 50 pips, 100 pips
        else:
            # Standard forex has 5 decimal places, 1 pip = 0.0001
            return 0.0050, 0.0100  # 50 pips, 100 pips
    
    def analyze_trend(self, symbol):
        """Trend following analysis - works 24/7"""
        rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M15, 0, 50)
        if rates is None:
            return None
        
        df = pd.DataFrame(rates)
        df['ma20'] = df['close'].rolling(20).mean()
        df['ma50'] = df['close'].rolling(50).mean()
        
        # RSI calculation
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        latest = df.iloc[-1]
        prev = df.iloc[-2]
        
        sl_pips, tp_pips = self.get_sl_tp_pips(symbol)
        
        # Trend + RSI filter
        if latest['close'] > latest['ma20'] > latest['ma50']:
            if prev['close'] < prev['ma20'] and 30 < latest['rsi'] < 70:
                return {
                    'symbol': symbol,
                    'signal': 'BUY',
                    'entry': latest['close'],
                    'sl': latest['close'] - sl_pips,
                    'tp': latest['close'] + tp_pips,
                    'strength': 'STRONG' if latest['rsi'] > 50 else 'MODERATE'
                }
        elif latest['close'] < latest['ma20'] < latest['ma50']:
            if prev['close'] > prev['ma20'] and 30 < latest['rsi'] < 70:
                return {
                    'symbol': symbol,
                    'signal': 'SELL',
                    'entry': latest['close'],
                    'sl': latest['close'] + sl_pips,
                    'tp': latest['close'] - tp_pips,
                    'strength': 'STRONG' if latest['rsi'] < 50 else 'MODERATE'
                }
        return None
    
    def analyze_range(self, symbol):
        """Range trading analysis - mean reversion"""
        rates_h1 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 0, 24)
        rates_m15 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M15, 0, 20)
        
        if rates_h1 is None or rates_m15 is None:
            return None
        
        df_h1 = pd.DataFrame(rates_h1)
        df_m15 = pd.DataFrame(rates_m15)
        
        # Check if market is ranging (not trending)
        adx = self.calculate_adx(df_m15)
        if adx > 25:  # Trending market, skip range trading
            return None
        
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
        
        # Buy at lower band/support
        if price <= latest['lower_band'] * 1.001:  # Within 0.1% of lower band
            return {
                'symbol': symbol,
                'signal': 'BUY',
                'entry': price,
                'sl': range_low - 0.0010,
                'tp': range_mid,
                'strength': 'RANGE_BOUNCE'
            }
        
        # Sell at upper band/resistance
        if price >= latest['upper_band'] * 0.999:  # Within 0.1% of upper band
            return {
                'symbol': symbol,
                'signal': 'SELL',
                'entry': price,
                'sl': range_high + 0.0010,
                'tp': range_mid,
                'strength': 'RANGE_BOUNCE'
            }
        
        return None
    
    def analyze_breakout(self, symbol):
        """Breakout analysis - works when price breaks key levels"""
        rates_h1 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 0, 12)
        if rates_h1 is None:
            return None
        
        df = pd.DataFrame(rates_h1)
        
        # Find recent range
        recent_high = df['high'].iloc[-6:-1].max()
        recent_low = df['low'].iloc[-6:-1].min()
        
        latest = df.iloc[-1]
        price = latest['close']
        
        # Volume/confirmtion check
        avg_volume = df['tick_volume'].mean()
        current_volume = latest['tick_volume']
        
        # Breakout with volume
        breakout_threshold = 0.0002
        
        if price > recent_high + breakout_threshold and current_volume > avg_volume * 1.2:
            return {
                'symbol': symbol,
                'signal': 'BUY',
                'entry': price,
                'sl': recent_low,
                'tp': price + (recent_high - recent_low),
                'strength': 'BREAKOUT'
            }
        
        if price < recent_low - breakout_threshold and current_volume > avg_volume * 1.2:
            return {
                'symbol': symbol,
                'signal': 'SELL',
                'entry': price,
                'sl': recent_high,
                'tp': price - (recent_high - recent_low),
                'strength': 'BREAKOUT'
            }
        
        return None
    
    def calculate_adx(self, df, period=14):
        """Calculate ADX to determine trend strength"""
        df['high_diff'] = df['high'].diff()
        df['low_diff'] = -df['low'].diff()
        
        df['plus_dm'] = df['high_diff'].where((df['high_diff'] > df['low_diff']) & (df['high_diff'] > 0), 0)
        df['minus_dm'] = df['low_diff'].where((df['low_diff'] > df['high_diff']) & (df['low_diff'] > 0), 0)
        
        df['tr'] = pd.concat([
            df['high'] - df['low'],
            abs(df['high'] - df['close'].shift()),
            abs(df['low'] - df['close'].shift())
        ], axis=1).max(axis=1)
        
        df['atr'] = df['tr'].rolling(window=period).mean()
        df['plus_di'] = 100 * (df['plus_dm'].rolling(window=period).mean() / df['atr'])
        df['minus_di'] = 100 * (df['minus_dm'].rolling(window=period).mean() / df['atr'])
        df['dx'] = 100 * abs(df['plus_di'] - df['minus_di']) / (df['plus_di'] + df['minus_di'])
        df['adx'] = df['dx'].rolling(window=period).mean()
        
        return df['adx'].iloc[-1] if not pd.isna(df['adx'].iloc[-1]) else 0
    
    def count_positions(self):
        """Count current open positions"""
        positions = mt5.positions_get()
        return len(positions) if positions else 0
    
    def get_max_positions(self):
        """Tiered position limit - 6 normal + 4 premium"""
        return 10  # Extended from 6 to 10
    
    def get_min_strength_for_slot(self, current_count):
        """Determine minimum signal strength based on slot tier"""
        if current_count < 6:
            return "MODERATE"  # Slots 1-6: accept MODERATE and STRONG
        else:
            return "STRONG"    # Slots 7-10: accept only STRONG
    
    def has_position_on_symbol(self, symbol):
        """Check if we already have a position on this symbol"""
        positions = mt5.positions_get(symbol=symbol)
        return len(positions) > 0 if positions else False
    
    def has_opposing_position(self, symbol, direction):
        """Check if we have a position in the opposite direction"""
        positions = mt5.positions_get(symbol=symbol)
        if not positions:
            return False
        
        for pos in positions:
            # pos.type: 0 = BUY, 1 = SELL
            pos_direction = "BUY" if pos.type == 0 else "SELL"
            if pos_direction != direction:
                return True  # Found opposing position
        
        return False
    
    def place_order(self, symbol, direction, entry, sl, tp, lot_size=0.01):
        """Place market order"""
        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            return None
        
        if not symbol_info.visible:
            mt5.symbol_select(symbol, True)
        
        point = symbol_info.point
        digits = symbol_info.digits
        
        if direction == "BUY":
            order_type = mt5.ORDER_TYPE_BUY
            price = symbol_info.ask
        else:
            order_type = mt5.ORDER_TYPE_SELL
            price = symbol_info.bid
        
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": lot_size,
            "type": order_type,
            "price": round(price, digits),
            "sl": round(sl, digits),
            "tp": round(tp, digits),
            "deviation": 10,
            "magic": 234000,
            "comment": f"AI Bot 24/7 {direction}",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        
        return mt5.order_send(request)
    
    def run(self):
        """Main trading loop - 24/7 scanner with TIERED 10 slots"""
        if not self.connect():
            return
        
        print(f"\n=== MT5 24/7 Setup Scanner (Tiered 10 Slots) ===")
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # ALL major pairs - scanned 24/7 (Expanded to 12 pairs)
        all_pairs = [
            # Original 8 pairs
            'EURUSD', 'GBPUSD', 'USDJPY', 'XAUUSD', 
            'EURJPY', 'GBPJPY', 'AUDJPY', 'EURGBP',
            # NEW: 4 USD major pairs (Phase 1 expansion)
            'USDCHF',   # Safe haven, liquid
            'USDCAD',   # Oil-correlated
            'AUDUSD',   # Risk-on indicator
            'NZDUSD'    # Volatile opportunities
        ]
        
        print(f"Scanning {len(all_pairs)} pairs for valid setups...")
        
        # Check position limit - TIERED SYSTEM
        pos_count = self.count_positions()
        max_positions = self.get_max_positions()
        min_strength = self.get_min_strength_for_slot(pos_count)
        
        # Show tier info
        if pos_count < 6:
            tier_status = f"NORMAL (slots 1-6)"
        elif pos_count < 10:
            tier_status = f"PREMIUM (slots 7-10) - STRONG only"
        else:
            tier_status = "FULL"
        
        print(f"Open positions: {pos_count}/{max_positions} [{tier_status}]")
        
        if pos_count >= max_positions:
            print("Max positions reached (10). Monitoring only.")
            mt5.shutdown()
            return
        
        # Scan all pairs for signals
        all_signals = []
        
        for symbol in all_pairs:
            signals = self.analyze_all_strategies(symbol)
            for strategy, signal in signals:
                # TIER FILTER: Apply strength filter for slots 7-10
                if pos_count >= 6 and signal['strength'] != 'STRONG':
                    continue  # Skip MODERATE signals for premium slots
                all_signals.append((strategy, signal))
                print(f"  [{strategy}] {symbol}: {signal['signal']} @ {signal['entry']:.5f} ({signal['strength']})")
        
        # Execute best signals
        if all_signals and pos_count < max_positions:
            # Sort by strength (STRONG first)
            all_signals.sort(key=lambda x: 0 if x[1]['strength'] == 'STRONG' else 1)
            
            executed = 0
            for strategy, signal in all_signals:
                if executed >= (max_positions - pos_count):
                    break
                    
                symbol = signal['symbol']
                direction = signal['signal']
                strength = signal['strength']
                
                # Skip if already have position on this symbol
                if self.has_position_on_symbol(symbol):
                    print(f"  [SKIP] {symbol}: Already have position on this symbol")
                    continue
                
                # Skip if opposing position exists (prevent hedging)
                if self.has_opposing_position(symbol, direction):
                    print(f"  [SKIP] {symbol}: Opposing position exists (preventing hedge)")
                    continue
                
                # TIER FILTER: Double-check strength requirement
                current_slots_after = pos_count + executed
                if current_slots_after >= 6 and strength != 'STRONG':
                    print(f"  [SKIP] {symbol}: MODERATE signal rejected for premium slot")
                    continue
                
                result = self.place_order(
                    symbol, 
                    direction, 
                    signal['entry'],
                    signal['sl'],
                    signal['tp']
                )
                
                if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                    tier_marker = "[P]" if (pos_count + executed) >= 6 else "[N]"
                    print(f"[EXECUTED] {tier_marker} {direction} {symbol} ({strategy}, {strength}) - Order: {result.order}")
                    executed += 1
                else:
                    error = result.comment if result else str(mt5.last_error())
                    print(f"[FAILED] {direction} {symbol} - {error}")
        
        elif not all_signals:
            print("No valid setups found in current market conditions.")
        
        mt5.shutdown()
        print("\nScan complete.")

if __name__ == "__main__":
    trader = MT5AutoTrader()
    trader.run()
