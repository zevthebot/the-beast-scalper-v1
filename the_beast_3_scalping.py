"""
THE BEAST 3.0 - SCALPING MODE (Ultra Simplified)
Only EMA crossover, no other filters, tight SL/TP, trade frequently
"""
import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
import time
import json
import os

# Account - Pepperstone Demo
ACCOUNT = 62108425
SERVER = "PepperstoneUK-Demo"
PASSWORD = ""

# Ultra simple config
INITIAL_BALANCE = 10000
RISK_PER_TRADE = 0.005  # 0.5%
MAX_POSITIONS = 5  # Max 5 positions
SL_PIPS = 10  # Tight SL (10 pips)
TP_PIPS = 15  # Tight TP (15 pips, 1:1.5 R:R)
LOT_SIZE = 0.1  # Fixed small lot

# Only 10 most liquid pairs
SYMBOLS = [
    "EURUSD", "GBPUSD", "USDJPY", 
    "EURJPY", "GBPJPY", "AUDUSD",
    "EURGBP", "XAUUSD", "USDCHF",
    "AUDJPY"
]

class ScalpingStrategy:
    def __init__(self, trader):
        self.trader = trader
        self.active_symbols = set()
        
    def get_rates(self, symbol, count=50):
        rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M5, 0, count)
        if rates is None or len(rates) == 0:
            return None
        return pd.DataFrame(rates)
    
    def analyze(self, symbol):
        """Ultra simple: EMA5/10 crossover only"""
        df = self.get_rates(symbol, 30)
        if df is None or len(df) < 20:
            return None
            
        # Fast EMAs for scalping (EMA3 and EMA8)
        df['ema3'] = df['close'].ewm(span=3, adjust=False).mean()
        df['ema8'] = df['close'].ewm(span=8, adjust=False).mean()
        
        latest = df.iloc[-1]
        prev = df.iloc[-2]
        
        # BUY: Price crosses above EMA3 and EMA3 > EMA8
        if latest['close'] > latest['ema3'] > latest['ema8'] and prev['close'] <= prev['ema3']:
            return {'signal': 'BUY', 'strength': 100, 'reason': 'EMA_CROSS_UP'}
        
        # SELL: Price crosses below EMA3 and EMA3 < EMA8
        elif latest['close'] < latest['ema3'] < latest['ema8'] and prev['close'] >= prev['ema3']:
            return {'signal': 'SELL', 'strength': 100, 'reason': 'EMA_CROSS_DOWN'}
        
        return None
    
    def run(self, auto_trade=True):
        for symbol in SYMBOLS:
            if len(self.active_symbols) >= MAX_POSITIONS:
                print(f"[MAX] {len(self.active_symbols)}/{MAX_POSITIONS} positions - skipping {symbol}")
                continue
                
            if symbol in self.active_symbols:
                continue
                
            result = self.analyze(symbol)
            if result:
                signal = result['signal']
                strength = result['strength']
                
                print(f"[SIGNAL] {symbol} {signal} - Strength: {strength}%")
                
                if auto_trade and strength >= 50:
                    success = self.execute_signal(symbol, signal, strength)
                    if success:
                        return  # One trade per cycle
    
    def execute_signal(self, symbol, direction, strength):
        print(f"[EXECUTING] {symbol} {direction}")
        
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            return False
            
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
            'volume': LOT_SIZE,
            'type': order_type,
            'price': price,
            'sl': sl,
            'tp': tp,
            'deviation': 10,
            'magic': 123456,
            'comment': f'SCALPING {direction}',
            'type_time': mt5.ORDER_TIME_GTC,
            'type_filling': mt5.ORDER_FILLING_IOC,
        }
        
        result = mt5.order_send(request)
        
        if result.retcode == mt5.TRADE_RETCODE_DONE:
            print(f"[EXECUTED] {symbol} {direction} {LOT_SIZE} lots @ {result.price}")
            self.active_symbols.add(symbol)
            return True
        else:
            print(f"[FAILED] {result.retcode} - {result.comment}")
            return False
    
    def update_active_symbols(self):
        positions = mt5.positions_get()
        self.active_symbols = set(p.symbol for p in positions) if positions else set()
        return len(self.active_symbols)

class ScalpingBot:
    def __init__(self):
        self.strategy = ScalpingStrategy(self)
        
    def initialize(self):
        if not mt5.initialize():
            print("MT5 init failed")
            return False
        
        authorized = mt5.login(ACCOUNT, password=PASSWORD, server=SERVER)
        if not authorized:
            print(f"Login failed: {mt5.last_error()}")
            return False
            
        print(f"Connected to {SERVER}")
        return True
    
    def run(self):
        print("\n" + "="*60)
        print("THE BEAST 3.0 - SCALPING MODE")
        print("="*60)
        print("Strategy: EMA3/8 Crossover only")
        print("SL/TP: 10/15 pips (1:1.5 R:R)")
        print("Lot: 0.1 fixed")
        print("Scan: Every 60 seconds")
        print("="*60)
        
        cycle = 0
        while True:
            cycle += 1
            now = datetime.now(timezone(timedelta(hours=2)))
            
            # Update positions
            pos_count = self.strategy.update_active_symbols()
            
            # Scan for signals every minute
            self.strategy.run(auto_trade=True)
            
            print(f"[{now.strftime('%H:%M:%S')}] Cycle {cycle} | Positions: {pos_count}")
            
            time.sleep(60)  # 1 minute between scans

if __name__ == '__main__':
    bot = ScalpingBot()
    if bot.initialize():
        bot.run()
    else:
        print("Failed to initialize")
