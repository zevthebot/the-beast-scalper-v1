"""
MT5 AI Trading Bot - Multi-Strategy Mode
Runs both MA+RSI (continuous) and London Breakout (morning session)
"""
import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
import time

# Trading Configuration
CONFIG = {
    'risk_per_trade': 0.02,
    'max_positions': 3,
    'magic_marsi': 234001,      # MA+RSI strategy
    'magic_breakout': 234002,   # London Breakout strategy
    'sl_pips_marsi': 50,
    'tp_pips_marsi': 100,
    'symbols': ['EURUSD', 'GBPUSD', 'USDJPY', 'XAUUSD'],
    'fast_ma': 20,
    'slow_ma': 50,
}

class MultiStrategyBot:
    def __init__(self):
        self.connected = False
        self.last_check = datetime.now()
        self.asian_ranges = {}  # Store Asian session ranges
        self.breakout_triggered = {}  # Track if breakout occurred today
        
    def connect(self):
        if not mt5.initialize():
            print(f"[ERROR] Initialize failed: {mt5.last_error()}")
            return False
        
        account_info = mt5.account_info()
        if account_info is None:
            print("[ERROR] MT5 not logged in")
            mt5.shutdown()
            return False
        
        self.connected = True
        print(f"\n{'='*60}")
        print(f"[OK] MT5 Multi-Strategy Bot Activated")
        print(f"{'='*60}")
        print(f"Account: {account_info.login}")
        print(f"Balance: {account_info.balance:.2f} {account_info.currency}")
        print(f"\nActive Strategies:")
        print(f"  1. MA+RSI Trend Following (M15, 24/7)")
        print(f"  2. London Breakout (08:00-12:00 GMT)")
        print(f"{'='*60}\n")
        return True
    
    def log(self, strategy, action, symbol, details):
        timestamp = datetime.now().strftime('%H:%M:%S')
        log_entry = f"[{timestamp}] [{strategy}] {action} | {symbol} | {details}\n"
        with open('trading_log.txt', 'a') as f:
            f.write(log_entry)
        print(log_entry.strip())
    
    def get_current_time_gmt(self):
        return datetime.now(timezone.utc)
    
    def count_positions_by_magic(self, magic):
        if not self.connected:
            return 0
        positions = mt5.positions_get()
        if positions is None:
            return 0
        return sum(1 for p in positions if p.magic == magic)
    
    def has_position_on_symbol(self, symbol, magic):
        if not self.connected:
            return False
        positions = mt5.positions_get(symbol=symbol)
        if positions is None:
            return False
        return any(p.magic == magic for p in positions)
    
    def calculate_lot_size(self, symbol, risk_amount):
        account = mt5.account_info()
        symbol_info = mt5.symbol_info(symbol)
        
        if account is None or symbol_info is None:
            return 0.01
        
        tick_value = symbol_info.trade_tick_value
        tick_size = symbol_info.trade_tick_size
        min_lot = symbol_info.volume_min
        
        if tick_value == 0 or tick_size == 0:
            return min_lot
        
        # Simplified lot calculation (1 pip ~ $1 for 0.1 lots on majors)
        lot_size = risk_amount / 10  # Approximate
        lot_size = max(min_lot, round(lot_size, 2))
        return lot_size
    
    def place_order(self, symbol, order_type, lot_size, sl, tp, magic, strategy_name):
        if not self.connected:
            return None
        
        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            return None
        
        price = symbol_info.ask if order_type == mt5.ORDER_TYPE_BUY else symbol_info.bid
        
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": lot_size,
            "type": order_type,
            "price": price,
            "sl": sl,
            "tp": tp,
            "deviation": 10,
            "magic": magic,
            "comment": strategy_name,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        
        result = mt5.order_send(request)
        return result
    
    # ========== STRATEGY 1: MA+RSI ==========
    def analyze_marsi(self, symbol):
        """MA+RSI Trend Following Strategy"""
        rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M15, 0, 100)
        if rates is None or len(rates) < 50:
            return None
        
        df = pd.DataFrame(rates)
        df['ma_fast'] = df['close'].rolling(CONFIG['fast_ma']).mean()
        df['ma_slow'] = df['close'].rolling(CONFIG['slow_ma']).mean()
        
        # RSI
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        latest = df.iloc[-1]
        prev = df.iloc[-2]
        
        signal = None
        if (latest['close'] > latest['ma_fast'] > latest['ma_slow'] and
            prev['close'] <= prev['ma_fast'] and
            30 < latest['rsi'] < 70):
            signal = 'BUY'
        elif (latest['close'] < latest['ma_fast'] < latest['ma_slow'] and
              prev['close'] >= prev['ma_fast'] and
              30 < latest['rsi'] < 70):
            signal = 'SELL'
        
        return {'signal': signal, 'price': latest['close']}
    
    def execute_marsi(self):
        """Execute MA+RSI strategy"""
        positions_count = self.count_positions_by_magic(CONFIG['magic_marsi'])
        if positions_count >= 2:  # Max 2 positions for this strategy
            return
        
        account = mt5.account_info()
        risk_amount = account.balance * CONFIG['risk_per_trade']
        
        for symbol in CONFIG['symbols']:
            if self.has_position_on_symbol(symbol, CONFIG['magic_marsi']):
                continue
            
            analysis = self.analyze_marsi(symbol)
            if analysis and analysis['signal']:
                lot_size = self.calculate_lot_size(symbol, risk_amount)
                symbol_info = mt5.symbol_info(symbol)
                
                if analysis['signal'] == 'BUY':
                    sl = analysis['price'] - CONFIG['sl_pips_marsi'] * symbol_info.point
                    tp = analysis['price'] + CONFIG['tp_pips_marsi'] * symbol_info.point
                    order_type = mt5.ORDER_TYPE_BUY
                else:
                    sl = analysis['price'] + CONFIG['sl_pips_marsi'] * symbol_info.point
                    tp = analysis['price'] - CONFIG['tp_pips_marsi'] * symbol_info.point
                    order_type = mt5.ORDER_TYPE_SELL
                
                result = self.place_order(symbol, order_type, lot_size, sl, tp, 
                                         CONFIG['magic_marsi'], 'MA+RSI')
                
                if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                    self.log('MA+RSI', 'EXECUTED', symbol, 
                            f"{analysis['signal']} {lot_size} lots @ {result.price:.5f}")
                break  # Only one trade per cycle
    
    # ========== STRATEGY 2: LONDON BREAKOUT ==========
    def calculate_asian_range(self, symbol):
        """Calculate Asian session range (00:00-08:00 GMT)"""
        now = self.get_current_time_gmt()
        
        # Check if we already calculated for today
        today = now.strftime('%Y-%m-%d')
        if symbol in self.asian_ranges and self.asian_ranges[symbol]['date'] == today:
            return self.asian_ranges[symbol]
        
        # Get rates from midnight to now
        rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 0, 24)
        if rates is None:
            return None
        
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        
        # Filter Asian session: 00:00-08:00 GMT
        asian_mask = df['time'].dt.hour < 8
        asian_data = df[asian_mask]
        
        if len(asian_data) < 3:  # Need at least 3 hours
            return None
        
        asian_high = asian_data['high'].max()
        asian_low = asian_data['low'].min()
        range_size = asian_high - asian_low
        
        self.asian_ranges[symbol] = {
            'date': today,
            'high': asian_high,
            'low': asian_low,
            'range': range_size
        }
        
        return self.asian_ranges[symbol]
    
    def execute_london_breakout(self):
        """Execute London Breakout strategy (08:00-12:00 GMT)"""
        now = self.get_current_time_gmt()
        hour = now.hour
        
        # Only trade during London session 08:00-12:00
        if hour < 8 or hour >= 12:
            return
        
        positions_count = self.count_positions_by_magic(CONFIG['magic_breakout'])
        if positions_count >= 2:  # Max 2 breakout positions
            return
        
        account = mt5.account_info()
        risk_amount = account.balance * CONFIG['risk_per_trade']
        
        for symbol in ['EURUSD', 'GBPUSD', 'USDJPY']:
            if self.has_position_on_symbol(symbol, CONFIG['magic_breakout']):
                continue
            
            range_data = self.calculate_asian_range(symbol)
            if range_data is None:
                continue
            
            # Check if already triggered today
            today = now.strftime('%Y-%m-%d')
            if symbol in self.breakout_triggered and self.breakout_triggered[symbol] == today:
                continue
            
            symbol_info = mt5.symbol_info(symbol)
            tick = mt5.symbol_info_tick(symbol)
            
            # Breakout thresholds (Asian high/low + buffer)
            buffer = 5 * symbol_info.point
            buy_trigger = range_data['high'] + buffer
            sell_trigger = range_data['low'] - buffer
            
            signal = None
            if tick.ask > buy_trigger:
                signal = 'BUY'
            elif tick.bid < sell_trigger:
                signal = 'SELL'
            
            if signal:
                lot_size = self.calculate_lot_size(symbol, risk_amount)
                
                # TP = 1.5x range, SL = opposite side of range
                if signal == 'BUY':
                    entry = tick.ask
                    sl = range_data['low'] - 10 * symbol_info.point
                    tp = entry + 1.5 * range_data['range']
                    order_type = mt5.ORDER_TYPE_BUY
                else:
                    entry = tick.bid
                    sl = range_data['high'] + 10 * symbol_info.point
                    tp = entry - 1.5 * range_data['range']
                    order_type = mt5.ORDER_TYPE_SELL
                
                result = self.place_order(symbol, order_type, lot_size, sl, tp,
                                         CONFIG['magic_breakout'], 'LONDON-BRK')
                
                if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                    self.log('LONDON', 'EXECUTED', symbol,
                            f"{signal} {lot_size} lots @ {result.price:.5f} | Range: {range_data['range']:.5f}")
                    self.breakout_triggered[symbol] = today
                break  # One breakout trade per cycle
    
    # ========== MAIN LOOP ==========
    def run_cycle(self):
        if not self.connected:
            return
        
        # Strategy 1: MA+RSI (runs continuously)
        self.execute_marsi()
        
        # Strategy 2: London Breakout (only 08:00-12:00 GMT)
        self.execute_london_breakout()
    
    def run(self, interval_seconds=60):
        print(f"[BOT] Running multi-strategy mode")
        print(f"[BOT] Check interval: {interval_seconds}s")
        print(f"[BOT] Press Ctrl+C to stop\n")
        
        try:
            while True:
                self.run_cycle()
                time.sleep(interval_seconds)
        except KeyboardInterrupt:
            print("\n[BOT] Stopped by user")
    
    def shutdown(self):
        mt5.shutdown()
        self.connected = False
        print("[BOT] Disconnected")


if __name__ == "__main__":
    bot = MultiStrategyBot()
    if bot.connect():
        bot.run(interval_seconds=30)
        bot.shutdown()
    else:
        print("[ERROR] Failed to connect")
