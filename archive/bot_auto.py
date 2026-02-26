"""
MT5 AI Trading Bot - Auto Execution Mode
Orchestrates trading strategy and executes automatically
"""
import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from datetime import datetime
import json
import time
import os

# Trading Configuration
CONFIG = {
    'risk_per_trade': 0.02,      # 2% risk per trade
    'max_positions': 3,          # Max 3 concurrent positions
    'stop_loss_pips': 50,        # 50 pips SL
    'take_profit_pips': 100,     # 100 pips TP (2:1 R/R)
    'trailing_enabled': True,
    'symbols': ['EURUSD', 'GBPUSD', 'USDJPY', 'XAUUSD'],
    'timeframe': mt5.TIMEFRAME_M15,
    'magic_number': 234000,
    'fast_ma': 20,               # Fast MA period
    'slow_ma': 50,               # Slow MA period
}

class AutoTrader:
    def __init__(self):
        self.connected = False
        self.last_check = {}
        
    def connect(self):
        """Connect to running MT5 instance"""
        if not mt5.initialize():
            print(f"[ERROR] Initialize failed: {mt5.last_error()}")
            return False
        
        account_info = mt5.account_info()
        if account_info is None:
            print("[ERROR] MT5 not logged in. Please login manually.")
            mt5.shutdown()
            return False
        
        self.connected = True
        print(f"\n{'='*60}")
        print(f"[OK] MT5 AI Trading Bot Activated")
        print(f"{'='*60}")
        print(f"Account: {account_info.login}")
        print(f"Server: {account_info.server}")
        print(f"Balance: {account_info.balance:.2f} {account_info.currency}")
        print(f"Equity: {account_info.equity:.2f}")
        print(f"Strategy: Trend Following + RSI (M15)")
        print(f"Risk: {CONFIG['risk_per_trade']*100}% per trade | Max {CONFIG['max_positions']} positions")
        print(f"{'='*60}\n")
        return True
    
    def log_trade(self, action, symbol, details):
        """Log all trading activity"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"[{timestamp}] {action} | {symbol} | {details}\n"
        
        with open('trading_log.txt', 'a', encoding='utf-8') as f:
            f.write(log_entry)
        print(log_entry.strip())
    
    def get_account_status(self):
        """Get current account status"""
        if not self.connected:
            return None
        info = mt5.account_info()
        return {
            'balance': info.balance,
            'equity': info.equity,
            'margin': info.margin,
            'free_margin': info.margin_free,
            'profit': info.profit,
        }
    
    def count_positions(self):
        """Count bot's open positions"""
        if not self.connected:
            return 0
        positions = mt5.positions_get()
        if positions is None:
            return 0
        return sum(1 for p in positions if p.magic == CONFIG['magic_number'])
    
    def get_symbol_positions(self, symbol):
        """Check if we have position on symbol"""
        if not self.connected:
            return []
        positions = mt5.positions_get(symbol=symbol)
        if positions is None:
            return []
        return [p for p in positions if p.magic == CONFIG['magic_number']]
    
    def analyze_market(self, symbol):
        """Analyze market and return trading signal"""
        if not self.connected:
            return None
        
        # Get historical data
        rates = mt5.copy_rates_from_pos(symbol, CONFIG['timeframe'], 0, 100)
        if rates is None or len(rates) < 50:
            return None
        
        df = pd.DataFrame(rates)
        
        # Calculate indicators
        df['ma_fast'] = df['close'].rolling(CONFIG['fast_ma']).mean()
        df['ma_slow'] = df['close'].rolling(CONFIG['slow_ma']).mean()
        
        # RSI
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # Get latest values
        latest = df.iloc[-1]
        prev = df.iloc[-2]
        
        signal = None
        
        # BUY Signal: Price crosses above fast MA, fast > slow, RSI not overbought
        if (latest['close'] > latest['ma_fast'] and 
            latest['ma_fast'] > latest['ma_slow'] and
            prev['close'] <= prev['ma_fast'] and
            30 < latest['rsi'] < 70):
            signal = 'BUY'
        
        # SELL Signal: Price crosses below fast MA, fast < slow, RSI not oversold
        elif (latest['close'] < latest['ma_fast'] and 
              latest['ma_fast'] < latest['ma_slow'] and
              prev['close'] >= prev['ma_fast'] and
              30 < latest['rsi'] < 70):
            signal = 'SELL'
        
        return {
            'symbol': symbol,
            'signal': signal,
            'price': latest['close'],
            'ma_fast': latest['ma_fast'],
            'ma_slow': latest['ma_slow'],
            'rsi': latest['rsi']
        }
    
    def calculate_lot_size(self, symbol, stop_loss_pips):
        """Calculate position size based on risk"""
        account = mt5.account_info()
        symbol_info = mt5.symbol_info(symbol)
        
        if account is None or symbol_info is None:
            return 0.01
        
        risk_amount = account.balance * CONFIG['risk_per_trade']
        
        # Calculate pip value
        tick_size = symbol_info.trade_tick_size
        tick_value = symbol_info.trade_tick_value
        lot_step = symbol_info.volume_step
        min_lot = symbol_info.volume_min
        max_lot = symbol_info.volume_max
        
        if tick_size == 0 or tick_value == 0:
            return min_lot
        
        # For forex: 1 pip = 0.0001 (0.01 for JPY pairs)
        pip_size = 0.01 if 'JPY' in symbol else 0.0001
        pip_value = (pip_size / tick_size) * tick_value
        
        if pip_value == 0:
            return min_lot
        
        lot_size = risk_amount / (stop_loss_pips * pip_value)
        
        # Apply constraints
        lot_size = max(min_lot, min(max_lot, lot_size))
        lot_size = round(lot_size / lot_step) * lot_step
        
        return round(lot_size, 2)
    
    def place_order(self, symbol, signal, price):
        """Execute market order"""
        if not self.connected:
            return None
        
        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            return None
        
        # Determine order type and price
        if signal == 'BUY':
            order_type = mt5.ORDER_TYPE_BUY
            entry_price = symbol_info.ask
            sl = entry_price - CONFIG['stop_loss_pips'] * symbol_info.point
            tp = entry_price + CONFIG['take_profit_pips'] * symbol_info.point
        else:  # SELL
            order_type = mt5.ORDER_TYPE_SELL
            entry_price = symbol_info.bid
            sl = entry_price + CONFIG['stop_loss_pips'] * symbol_info.point
            tp = entry_price - CONFIG['take_profit_pips'] * symbol_info.point
        
        # Calculate lot size
        lot_size = self.calculate_lot_size(symbol, CONFIG['stop_loss_pips'])
        
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": lot_size,
            "type": order_type,
            "price": entry_price,
            "sl": sl,
            "tp": tp,
            "deviation": 10,
            "magic": CONFIG['magic_number'],
            "comment": f"AI {signal}",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        
        result = mt5.order_send(request)
        
        if result.retcode == mt5.TRADE_RETCODE_DONE:
            self.log_trade("EXECUTED", symbol, 
                          f"{signal} {lot_size} lots @ {entry_price:.5f} | SL:{sl:.5f} TP:{tp:.5f}")
            return result
        else:
            self.log_trade("FAILED", symbol, f"{signal} - Error {result.retcode}")
            return None
    
    def update_trailing_stops(self):
        """Update trailing stops for open positions"""
        if not self.connected or not CONFIG['trailing_enabled']:
            return
        
        positions = mt5.positions_get()
        if positions is None:
            return
        
        for pos in positions:
            if pos.magic != CONFIG['magic_number']:
                continue
            
            symbol_info = mt5.symbol_info(pos.symbol)
            if symbol_info is None:
                continue
            
            # Calculate trailing distance (50% of original SL)
            trail_distance = CONFIG['stop_loss_pips'] * symbol_info.point * 0.5
            
            if pos.type == mt5.ORDER_TYPE_BUY:
                new_sl = symbol_info.bid - trail_distance
                if new_sl > pos.sl and new_sl > pos.price_open:
                    self.modify_sl(pos.ticket, new_sl, pos.tp)
            
            elif pos.type == mt5.ORDER_TYPE_SELL:
                new_sl = symbol_info.ask + trail_distance
                if (new_sl < pos.sl or pos.sl == 0) and new_sl < pos.price_open:
                    self.modify_sl(pos.ticket, new_sl, pos.tp)
    
    def modify_sl(self, ticket, new_sl, tp):
        """Modify stop loss"""
        request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "position": ticket,
            "sl": new_sl,
            "tp": tp,
        }
        mt5.order_send(request)
    
    def run_cycle(self):
        """One trading cycle"""
        if not self.connected:
            return
        
        # Update trailing stops
        self.update_trailing_stops()
        
        # Check if we can open new positions
        current_positions = self.count_positions()
        if current_positions >= CONFIG['max_positions']:
            return
        
        # Analyze each symbol
        for symbol in CONFIG['symbols']:
            # Skip if already have position on this symbol
            if self.get_symbol_positions(symbol):
                continue
            
            analysis = self.analyze_market(symbol)
            if analysis is None:
                continue
            
            # Check for signal
            if analysis['signal']:
                self.place_order(symbol, analysis['signal'], analysis['price'])
    
    def run(self, interval_seconds=60):
        """Main loop"""
        print(f"[BOT] Starting auto-trading loop (check every {interval_seconds}s)")
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
        print("[BOT] Disconnected from MT5")


if __name__ == "__main__":
    print("[INFO] Single strategy bot - use bot_multi_strategy.py for both strategies")
    trader = AutoTrader()
    
    if trader.connect():
        # Run continuous trading
        trader.run(interval_seconds=30)  # Check every 30 seconds
        trader.shutdown()
    else:
        print("[ERROR] Failed to connect. Exiting.")
