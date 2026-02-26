"""
MT5 AI Trading Bot - FTMO Challenge Connector
Connects to already-logged-in FTMO MT5 instance
"""
import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from datetime import datetime
import json
import time
import sys

# FTMO Configuration
FTMO_ACCOUNT = 541144102
FTMO_SERVER = "FTMO-Server4"
INITIAL_BALANCE = 10000  # USD

# FTMO Limits
MAX_DAILY_LOSS_PCT = 0.04   # 4% (buffer from 5% FTMO limit)
MAX_TOTAL_LOSS_PCT = 0.08   # 8% (buffer from 10% FTMO limit)
MAX_POSITIONS = 5           # Updated to 5 positions
RISK_PER_TRADE = 0.01       # 1% conservative
FIXED_LOT_SIZE = 0.01       # Fixed micro lot
TRAILING_STOP_PIPS = 30     # Trailing stop distance

class FTMOBot:
    def __init__(self):
        self.connected = False
        self.starting_balance = INITIAL_BALANCE
        
    def connect(self):
        """Connect to running MT5 instance"""
        if not mt5.initialize():
            error = mt5.last_error()
            print(f"Initialize failed: {error}")
            return False
        
        # Check if already logged in
        account_info = mt5.account_info()
        if account_info is None:
            print("MT5 not logged in. Please login manually first.")
            print(f"  Account: {FTMO_ACCOUNT}")
            print(f"  Server: {FTMO_SERVER}")
            mt5.shutdown()
            return False
        
        # Verify FTMO account
        if account_info.login != FTMO_ACCOUNT:
            print(f"WARNING: Connected to {account_info.login}, expected {FTMO_ACCOUNT}")
            mt5.shutdown()
            return False
        
        self.connected = True
        self.starting_balance = account_info.balance
        print(f"[OK] Connected to FTMO Challenge")
        print(f"  Account: {account_info.login}")
        print(f"  Server: {account_info.server}")
        print(f"  Balance: {account_info.balance:.2f} {account_info.currency}")
        print(f"  Equity: {account_info.equity:.2f}")
        return True
    
    def check_limits(self):
        """Check FTMO trading objectives - WITH HARD STOP"""
        if not self.connected:
            return False, "Not connected"
        
        info = mt5.account_info()
        daily_loss = (self.starting_balance - info.equity) / self.starting_balance
        total_loss = (INITIAL_BALANCE - info.equity) / INITIAL_BALANCE
        positions = mt5.positions_total()
        
        # HARD STOP - Daily Loss 4%
        if daily_loss >= MAX_DAILY_LOSS_PCT:
            self.hard_stop_all("DAILY LOSS LIMIT 4%")
            return False, f"🚨 HARD STOP: Daily loss {daily_loss:.2%}"
        
        # HARD STOP - Total Loss 8%
        if total_loss >= MAX_TOTAL_LOSS_PCT:
            self.hard_stop_all("TOTAL LOSS LIMIT 8%")
            return False, f"🚨 HARD STOP: Total loss {total_loss:.2%}"
        
        # Max positions
        if positions >= MAX_POSITIONS:
            return False, f"MAX POSITIONS: {positions}"
        
        return True, f"OK | Daily: {daily_loss:.1%} | Total: {total_loss:.1%} | Pos: {positions}"
    
    def get_status(self):
        """Get current account status"""
        if not self.connected:
            return None
        info = mt5.account_info()
        return {
            'account': info.login,
            'server': info.server,
            'balance': info.balance,
            'equity': info.equity,
            'margin': info.margin,
            'free_margin': info.margin_free,
            'profit': info.profit,
            'currency': info.currency,
            'profit_pct': (info.equity - INITIAL_BALANCE) / INITIAL_BALANCE
        }
    
    def get_positions(self):
        """Get open positions"""
        if not self.connected:
            return []
        positions = mt5.positions_get()
        if positions is None:
            return []
        return [(p.symbol, p.volume, p.profit, 'BUY' if p.type == 0 else 'SELL', p.ticket) for p in positions]
    
    def export_status(self, filepath="ftmo_live_status.json"):
        """Export status to JSON"""
        status = self.get_status()
        if status is None:
            return False
        
        status['positions'] = self.get_positions()
        status['timestamp'] = datetime.now().isoformat()
        status['limits'] = {
            'max_daily_loss': MAX_DAILY_LOSS_PCT,
            'max_total_loss': MAX_TOTAL_LOSS_PCT,
            'max_positions': MAX_POSITIONS,
            'risk_per_trade': RISK_PER_TRADE
        }
        
        try:
            with open(filepath, 'w') as f:
                json.dump(status, f, indent=2, default=str)
            return True
        except:
            return False
    
    def analyze_market(self, symbol="EURUSD"):
        """Simple MA crossover strategy"""
        if not self.connected:
            return None
        
        rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M15, 0, 50)
        if rates is None:
            return None
        
        df = pd.DataFrame(rates)
        df['ma20'] = df['close'].rolling(20).mean()
        df['ma50'] = df['close'].rolling(50).mean()
        
        latest = df.iloc[-1]
        prev = df.iloc[-2]
        
        signal = None
        if latest['close'] > latest['ma20'] > latest['ma50']:
            if prev['close'] < prev['ma20']:
                signal = "BUY"
        elif latest['close'] < latest['ma20'] < latest['ma50']:
            if prev['close'] > prev['ma20']:
                signal = "SELL"
        
        return {
            'symbol': symbol,
            'price': latest['close'],
            'signal': signal,
            'ma20': latest['ma20'],
            'ma50': latest['ma50']
        }
    
    def place_order(self, symbol, direction, lot_size=0.01, sl_pips=50, tp_pips=100):
        """Place market order with FTMO checks - Uses FIXED lot size"""
        if not self.connected:
            return {'success': False, 'error': 'Not connected'}
        
        # OVERRIDE: Always use fixed lot size for FTMO safety
        lot_size = FIXED_LOT_SIZE
        
        # Check limits
        can_trade, msg = self.check_limits()
        if not can_trade:
            return {'success': False, 'error': msg}
        
        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            return {'success': False, 'error': f'Symbol {symbol} not found'}
        
        point = symbol_info.point
        digits = symbol_info.digits
        
        if direction.upper() == "BUY":
            order_type = mt5.ORDER_TYPE_BUY
            price = symbol_info.ask
            sl = price - sl_pips * point * 10
            tp = price + tp_pips * point * 10
        else:
            order_type = mt5.ORDER_TYPE_SELL
            price = symbol_info.bid
            sl = price + sl_pips * point * 10
            tp = price - tp_pips * point * 10
        
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
            "comment": "FTMO Bot",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        
        result = mt5.order_send(request)
        
        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            return {'success': False, 'error': f'Order failed: {result.retcode if result else "Unknown"}'}
        
        return {
            'success': True,
            'order_id': result.order,
            'symbol': symbol,
            'direction': direction,
            'volume': lot_size,
            'price': price,
            'sl': sl,
            'tp': tp
        }
    
    def hard_stop_all(self, reason="HARD STOP"):
        """EMERGENCY: Close all positions immediately"""
        print(f"\n🚨 {reason} - CLOSING ALL POSITIONS 🚨")
        
        positions = mt5.positions_get()
        if not positions:
            print("No positions to close.")
            return []
        
        results = []
        for pos in positions:
            close_type = mt5.ORDER_TYPE_SELL if pos.type == 0 else mt5.ORDER_TYPE_BUY
            tick = mt5.symbol_info_tick(pos.symbol)
            price = tick.bid if pos.type == 0 else tick.ask
            
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": pos.symbol,
                "volume": pos.volume,
                "type": close_type,
                "position": pos.ticket,
                "price": price,
                "deviation": 10,
                "magic": 234000,
                "comment": f"FTMO {reason}",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            
            result = mt5.order_send(request)
            success = result is not None and result.retcode == mt5.TRADE_RETCODE_DONE
            
            results.append({
                'ticket': pos.ticket,
                'symbol': pos.symbol,
                'success': success,
                'profit': pos.profit if success else 0
            })
            
            status = "✓" if success else "✗"
            print(f"{status} {pos.symbol} #{pos.ticket} closed | P&L: {pos.profit:.2f}")
            time.sleep(0.3)
        
        print(f"\nHARD STOP COMPLETE: Closed {len([r for r in results if r['success']])}/{len(positions)} positions")
        return results
    
    def update_trailing_stops(self):
        """Update trailing stops for all positions"""
        positions = mt5.positions_get()
        if not positions:
            return []
        
        updated = []
        for pos in positions:
            if pos.magic != 234000:  # Only our bot's positions
                continue
            
            symbol = pos.symbol
            tick = mt5.symbol_info_tick(symbol)
            if tick is None:
                continue
            
            point = mt5.symbol_info(symbol).point
            digits = mt5.symbol_info(symbol).digits
            
            new_sl = None
            
            if pos.type == 0:  # BUY
                current_price = tick.bid
                profit_pips = (current_price - pos.price_open) / (point * 10)
                if profit_pips > TRAILING_STOP_PIPS:
                    proposed_sl = current_price - (TRAILING_STOP_PIPS * point * 10)
                    if proposed_sl > pos.sl or pos.sl == 0:
                        new_sl = proposed_sl
            else:  # SELL
                current_price = tick.ask
                profit_pips = (pos.price_open - current_price) / (point * 10)
                if profit_pips > TRAILING_STOP_PIPS:
                    proposed_sl = current_price + (TRAILING_STOP_PIPS * point * 10)
                    if proposed_sl < pos.sl or pos.sl == 0:
                        new_sl = proposed_sl
            
            if new_sl:
                request = {
                    "action": mt5.TRADE_ACTION_SLTP,
                    "position": pos.ticket,
                    "symbol": symbol,
                    "sl": round(new_sl, digits),
                    "tp": round(pos.tp, digits) if pos.tp else 0
                }
                
                result = mt5.order_send(request)
                if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                    locked = abs(new_sl - pos.price_open) / (point * 10)
                    print(f"[TRAILING] {symbol}: SL → {new_sl:.5f} (locked {locked:.1f} pips)")
                    updated.append({'ticket': pos.ticket, 'symbol': symbol, 'locked_pips': locked})
        
        return updated
    
    def shutdown(self):
        mt5.shutdown()
        self.connected = False


if __name__ == "__main__":
    bot = FTMOBot()
    
    if bot.connect():
        print("\n" + "="*50)
        print("FTMO CHALLENGE - Account Monitor")
        print("="*50)
        
        # Export status immediately
        bot.export_status()
        print("\n[OK] Status exported to ftmo_live_status.json")
        
        # Show current status
        status = bot.get_status()
        print(f"\nBalance: {status['balance']:.2f} {status['currency']}")
        print(f"Equity: {status['equity']:.2f}")
        print(f"Profit: {status['profit']:.2f} ({status['profit_pct']:.2%})")
        
        # Show positions
        positions = bot.get_positions()
        print(f"\nOpen Positions: {len(positions)}")
        for pos in positions:
            print(f"  {pos[0]} {pos[3]} {pos[1]} lots | P&L: {pos[2]:.2f}")
        
        # Check limits
        can_trade, msg = bot.check_limits()
        print(f"\n[FTMO CHECK] {msg}")
        
        bot.shutdown()
    else:
        print("\n[!] Please login to FTMO account manually:")
        print(f"   Account: {FTMO_ACCOUNT}")
        print(f"   Server: {FTMO_SERVER}")
