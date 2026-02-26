"""
MT5 Trading Bot Controller - FTMO Challenge Account
Connects to MetaTrader 5 and manages automated trading strategies
"""
import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import json
import os

# FTMO Account credentials - $10,000 Challenge
ACCOUNT = 541144102
SERVER = "FTMO-Server4"
PASSWORD = "*BzLh?36N"  # FTMO Master Password - UPDATE THIS

# Trading configuration - FTMO Conservative Settings
INITIAL_BALANCE = 10000  # USD - FTMO Challenge Starting Balance
RISK_PER_TRADE = 0.01   # 1% risk per trade (conservative for FTMO)
FIXED_LOT_SIZE = 0.01   # Fixed micro lot size for all trades
MAX_POSITIONS = 10      # Max concurrent positions (tiered by confidence)
MAX_DAILY_LOSS = 0.04   # 4% max daily loss (FTMO allows 5%, we use buffer)
MAX_TOTAL_LOSS = 0.08   # 8% max total loss (FTMO allows 10%, we use buffer)

# FTMO Trading Objectives
PROFIT_TARGET_PHASE1 = 0.10  # 10% profit target Phase 1 ($1,000)
MIN_TRADING_DAYS = 4         # Minimum 4 trading days required

# FTMO resets daily loss at midnight CET/CEST (Prague time)
FTMO_RESET_HOUR = 0  # Midnight
FTMO_RESET_TIMEZONE = "Europe/Prague"

class MT5Trader:
    def __init__(self):
        self.connected = False
        self.account_info = None
        self.starting_balance = INITIAL_BALANCE
        self.daily_starting_equity = None  # Equity at start of trading day (00:00 CET)
        self.daily_max_equity = None       # Highest equity reached today
        self.daily_min_equity = None       # Lowest equity reached today
        self.daily_max_loss_pct = 0.0      # Current max daily loss % (from daily_starting_equity)
        self.last_reset_date = None        # Last date when daily reset occurred
        
    def connect(self):
        """Initialize and connect to MT5"""
        if not mt5.initialize():
            print(f"MT5 initialize failed, error: {mt5.last_error()}")
            return False
        
        print("MT5 initialized successfully")
        
        # Check if already logged in (manual login preferred for FTMO)
        account_info = mt5.account_info()
        if account_info is None:
            print("FTMO account not logged in. Please login manually first:")
            print(f"  Account: {ACCOUNT}")
            print(f"  Server: {SERVER}")
            print("  File -> Login to Trade Account")
            mt5.shutdown()
            return False
        
        # Verify we're on the correct account
        if account_info.login != ACCOUNT:
            print(f"WARNING: Connected to account {account_info.login}, expected {ACCOUNT}")
            print("Please login to the correct FTMO account.")
            mt5.shutdown()
            return False
        
        self.connected = True
        self.account_info = account_info
        self.starting_balance = account_info.balance
        print(f"[OK] Connected to FTMO Challenge Account")
        print(f"  Account: {account_info.login}")
        print(f"  Server: {account_info.server}")
        print(f"  Balance: {account_info.balance} {account_info.currency}")
        print(f"  Equity: {account_info.equity}")
        print(f"  Leverage: 1:{account_info.leverage}")
        return True
    
    def check_ftmo_limits(self):
        """Check if we're within FTMO trading objectives - WITH ADAPTIVE RISK"""
        if not self.connected:
            return False, "Not connected", False, None
        
        info = mt5.account_info()
        if info is None:
            return False, "Cannot get account info", False, None
        
        # Update daily metrics first
        self.update_daily_metrics()
        
        # Get adaptive risk parameters
        risk_status = self.get_risk_status()
        
        # Total loss check (independent of daily)
        total_loss_pct = (INITIAL_BALANCE - info.equity) / INITIAL_BALANCE if INITIAL_BALANCE > 0 else 0
        if total_loss_pct >= MAX_TOTAL_LOSS:
            print(f"\n[ALERT] HARD STOP - TOTAL LOSS LIMIT: {total_loss_pct:.2%} [ALERT]")
            self.hard_stop_all_positions("TOTAL LOSS LIMIT")
            return False, f"HARD STOP: TOTAL LOSS {total_loss_pct:.2%}", True, risk_status
        
        # Check if trading allowed based on risk status
        if not risk_status['can_trade']:
            return False, risk_status['message'], True, risk_status
        
        # Check position limit against adaptive max
        positions = mt5.positions_total()
        adaptive_max = risk_status['max_positions']
        if positions >= adaptive_max:
            return False, f"MAX POSITIONS: {positions}/{adaptive_max} ({risk_status['status']})", False, risk_status
        
        return True, risk_status['message'], False, risk_status
    
    def hard_stop_all_positions(self, reason):
        """EMERGENCY: Close all positions immediately"""
        print(f"\n[WARN]  EXECUTING HARD STOP - Reason: {reason}")
        print("="*50)
        
        positions = mt5.positions_get()
        if not positions:
            print("No positions to close.")
            return
        
        closed_count = 0
        total_profit = 0
        
        for pos in positions:
            result = self.close_position(pos)
            if result.get('success'):
                closed_count += 1
                total_profit += result.get('profit', 0)
                print(f"[OK] Closed {pos.symbol} #{pos.ticket} | P&L: {result.get('profit', 0):.2f}")
            else:
                print(f"[FAIL] Failed to close {pos.symbol} #{pos.ticket}: {result.get('error', 'Unknown')}")
            time.sleep(0.3)  # Small delay between closes
        
        print("="*50)
        print(f"HARD STOP COMPLETE: Closed {closed_count}/{len(positions)} positions")
        print(f"Total P&L from closure: {total_profit:.2f} {self.account_info.currency}")
        
        # Export emergency status
        self.export_status("ftmo_hard_stop_status.json")
    
    def update_daily_metrics(self):
        """Update daily equity tracking - call frequently to track min/max"""
        import pytz
        
        if not self.connected:
            return
            
        info = mt5.account_info()
        if info is None:
            return
            
        current_equity = info.equity
        
        # Get current time in FTMO timezone
        ftmo_tz = pytz.timezone(FTMO_RESET_TIMEZONE)
        now = datetime.now(ftmo_tz)
        current_date = now.date()
        
        # Check if new day (reset needed)
        if self.last_reset_date != current_date:
            # Daily reset occurred
            self.daily_starting_equity = current_equity
            self.daily_max_equity = current_equity
            self.daily_min_equity = current_equity
            self.daily_max_loss_pct = 0.0
            self.last_reset_date = current_date
            print(f"\n[RESET] FTMO DAILY RESET at {now.strftime('%Y-%m-%d %H:%M')} CET")
            print(f"   New daily base equity: ${self.daily_starting_equity:.2f}")
            return
        
        # Update min/max equity for the day
        if self.daily_max_equity is None or current_equity > self.daily_max_equity:
            self.daily_max_equity = current_equity
        if self.daily_min_equity is None or current_equity < self.daily_min_equity:
            self.daily_min_equity = current_equity
            
        # Calculate current max daily loss % (from starting equity)
        if self.daily_starting_equity and self.daily_starting_equity > 0:
            self.daily_max_loss_pct = (self.daily_starting_equity - self.daily_min_equity) / self.daily_starting_equity
    
    def get_risk_status(self):
        """Get current risk status and adaptive parameters"""
        self.update_daily_metrics()
        
        daily_loss = self.daily_max_loss_pct
        
        # Define risk tiers based on daily loss progression
        if daily_loss >= 0.04:  # 4% - Hard stop territory
            return {
                'status': 'CRITICAL',
                'can_trade': False,
                'max_positions': 0,
                'min_confidence': 100,
                'lot_multiplier': 0.0,
                'message': f'HARD STOP: Daily loss {daily_loss:.2%} at 4% limit'
            }
        elif daily_loss >= 0.03:  # 3% - Near limit, only 1-2 positions max
            return {
                'status': 'DANGER',
                'can_trade': True,
                'max_positions': 2,
                'min_confidence': 75,
                'lot_multiplier': 0.5,  # Half size
                'message': f'CAUTION: Daily loss {daily_loss:.2%}, reducing exposure'
            }
        elif daily_loss >= 0.02:  # 2% - Warning, be selective
            return {
                'status': 'WARNING',
                'can_trade': True,
                'max_positions': 5,
                'min_confidence': 60,
                'lot_multiplier': 0.75,  # 75% size
                'message': f'WARNING: Daily loss {daily_loss:.2%}, higher bar for entries'
            }
        elif daily_loss >= 0.01:  # 1% - Caution
            return {
                'status': 'CAUTION',
                'can_trade': True,
                'max_positions': 8,
                'min_confidence': 50,
                'lot_multiplier': 1.0,
                'message': f'CAUTION: Daily loss {daily_loss:.2%}, normal trading'
            }
        else:  # <1% - Normal operation
            return {
                'status': 'SAFE',
                'can_trade': True,
                'max_positions': 10,
                'min_confidence': 40,
                'lot_multiplier': 1.0,
                'message': f'SAFE: Daily loss {daily_loss:.2%}, full capacity'
            }
    
    def check_daily_reset(self):
        """Legacy function - now handled by update_daily_metrics"""
        import pytz
        ftmo_tz = pytz.timezone(FTMO_RESET_TIMEZONE)
        now = datetime.now(ftmo_tz)
        current_date = now.date()
        
        if self.last_reset_date != current_date and now.hour >= FTMO_RESET_HOUR:
            self.update_daily_metrics()
            return True
        return False
    
    def get_account_summary(self):
        """Get current account status"""
        if not self.connected:
            return None
        
        info = mt5.account_info()
        
        # Calculate FTMO progress
        profit_pct = (info.equity - INITIAL_BALANCE) / INITIAL_BALANCE if INITIAL_BALANCE > 0 else 0
        daily_loss_pct = (self.starting_balance - info.equity) / self.starting_balance if self.starting_balance > 0 else 0
        
        return {
            'account': info.login,
            'server': info.server,
            'balance': info.balance,
            'equity': info.equity,
            'margin': info.margin,
            'free_margin': info.margin_free,
            'profit': info.profit,
            'currency': info.currency,
            'profit_pct': profit_pct,
            'daily_loss_pct': daily_loss_pct,
            'phase1_progress': f"{profit_pct:.1%} / {PROFIT_TARGET_PHASE1:.0%}",
            'positions_count': mt5.positions_total()
        }
    
    def get_positions(self):
        """Get all open positions"""
        if not self.connected:
            return []
        return mt5.positions_get()
    
    def get_position_summary(self):
        """Get summary of open positions for FTMO monitoring"""
        positions = self.get_positions()
        if not positions:
            return []
        
        summary = []
        for pos in positions:
            summary.append({
                'ticket': pos.ticket,
                'symbol': pos.symbol,
                'type': 'BUY' if pos.type == 0 else 'SELL',
                'volume': pos.volume,
                'open_price': pos.price_open,
                'current_price': pos.price_current,
                'sl': pos.sl,
                'tp': pos.tp,
                'profit': pos.profit,
                'swap': pos.swap,
                'magic': pos.magic
            })
        return summary
    
    def get_symbols(self):
        """Get all available trading symbols"""
        if not self.connected:
            return []
        symbols = mt5.symbols_get()
        return [s.name for s in symbols]
    
    def get_rates(self, symbol, timeframe=mt5.TIMEFRAME_M15, count=100):
        """Get historical price data with error handling"""
        if not self.connected:
            return None
        
        try:
            rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, count)
            if rates is None or len(rates) == 0:
                print(f"[WARN] No data for {symbol}")
                return None
            
            df = pd.DataFrame(rates)
            df['time'] = pd.to_datetime(df['time'], unit='s')
            return df
        except Exception as e:
            print(f"[ERROR] get_rates failed for {symbol}: {e}")
            return None
    
    def calculate_lot_size(self, symbol, stop_loss_pips=None, risk_pct=None):
        """Calculate lot size - FTMO uses FIXED 0.01 lots"""
        return FIXED_LOT_SIZE  # Always use fixed micro lot for FTMO safety
    
    def place_order(self, symbol, order_type, lot_size, stop_loss=None, take_profit=None, 
                    sl_pips=50, tp_pips=100, magic=234000, comment="FTMO Bot"):
        """Place a market order with FTMO safety checks"""
        if not self.connected:
            return {'success': False, 'error': 'Not connected'}
        
        # Pre-trade FTMO checks (with adaptive risk)
        can_trade, message, hard_stop, risk_status = self.check_ftmo_limits()
        if not can_trade:
            print(f"[FTMO BLOCKED] {message}")
            return {'success': False, 'error': message}
        
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            print(f"Symbol {symbol} not found")
            return {'success': False, 'error': f'Symbol {symbol} not found'}
        
        price = tick.ask if order_type == mt5.ORDER_TYPE_BUY else tick.bid
        
        # Calculate SL/TP if not provided
        point = mt5.symbol_info(symbol).point
        if stop_loss is None and sl_pips > 0:
            stop_loss = price - sl_pips * point * 10 if order_type == mt5.ORDER_TYPE_BUY else price + sl_pips * point * 10
        if take_profit is None and tp_pips > 0:
            take_profit = price + tp_pips * point * 10 if order_type == mt5.ORDER_TYPE_BUY else price - tp_pips * point * 10
        
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": lot_size,
            "type": order_type,
            "price": price,
            "deviation": 10,
            "magic": magic,
            "comment": comment,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        
        if stop_loss:
            request["sl"] = round(stop_loss, mt5.symbol_info(symbol).digits)
        if take_profit:
            request["tp"] = round(take_profit, mt5.symbol_info(symbol).digits)
        
        print(f"[ORDER] {symbol} {'BUY' if order_type == mt5.ORDER_TYPE_BUY else 'SELL'} {lot_size} lots")
        print(f"        Price: {price}, SL: {request.get('sl')}, TP: {request.get('tp')}")
        
        result = mt5.order_send(request)
        
        if result is None:
            error = mt5.last_error()
            print(f"[ERROR] Order failed: {error}")
            return {'success': False, 'error': f'Order failed: {error}'}
        
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            print(f"[ERROR] Order failed: {result.retcode} - {result.comment}")
            return {'success': False, 'error': f'{result.retcode}: {result.comment}'}
        
        print(f"[SUCCESS] Order placed! Ticket: {result.order}, Deal: {result.deal}")
        
        return {
            'success': True,
            'order_id': result.order,
            'deal_id': result.deal,
            'symbol': symbol,
            'volume': lot_size,
            'price': price,
            'sl': request.get('sl'),
            'tp': request.get('tp'),
            'retcode': result.retcode
        }
    
    def close_position(self, position):
        """Close an open position"""
        if not self.connected:
            return {'success': False, 'error': 'Not connected'}
        
        tick = mt5.symbol_info_tick(position.symbol)
        price = tick.bid if position.type == mt5.ORDER_TYPE_BUY else tick.ask
        
        close_type = mt5.ORDER_TYPE_SELL if position.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
        
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": position.symbol,
            "volume": position.volume,
            "type": close_type,
            "position": position.ticket,
            "price": price,
            "deviation": 10,
            "magic": position.magic,
            "comment": "FTMO Bot Close",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        
        result = mt5.order_send(request)
        
        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            error = result.comment if result else mt5.last_error()
            return {'success': False, 'error': f'Close failed: {error}'}
        
        return {
            'success': True,
            'order_id': result.order,
            'profit': position.profit,
            'symbol': position.symbol
        }
    
    def close_all_positions(self):
        """Close all open positions - EMERGENCY FUNCTION"""
        if not self.connected:
            return []
        
        positions = mt5.positions_get()
        results = []
        
        for pos in positions:
            result = self.close_position(pos)
            results.append(result)
            time.sleep(0.5)  # Small delay between closes
        
        return results
    
    def apply_breakeven_protection(self, min_profit_pips=15):
        """
        PHASE 1: BREAKEVEN PROTECTION - Zero Risk Strategy
        
        When position reaches +15 pips profit:
        - Move SL to entry price (breakeven)
        - Position can no longer lose money
        - Only upside remains
        
        This is the MOST SECURE protection for FTMO Phase 1.
        """
        if not self.connected:
            return []
        
        positions = mt5.positions_get()
        if not positions:
            return []
        
        protected = []
        
        for pos in positions:
            # Only modify positions opened by our bot
            if pos.magic != 234000:
                continue
            
            symbol = pos.symbol
            ticket = pos.ticket
            pos_type = pos.type  # 0 = BUY, 1 = SELL
            open_price = pos.price_open
            current_sl = pos.sl
            
            tick = mt5.symbol_info_tick(symbol)
            if tick is None:
                continue
            
            point = mt5.symbol_info(symbol).point
            digits = mt5.symbol_info(symbol).digits
            
            # Check if already at breakeven or better
            if pos_type == 0:  # BUY
                # For BUY: SL should be >= open_price for breakeven
                if current_sl >= open_price:
                    continue  # Already protected
                current_price = tick.bid
                profit_pips = (current_price - open_price) / (point * 10)
                
                if profit_pips >= min_profit_pips:
                    new_sl = open_price  # Move to breakeven
                    
            else:  # SELL
                # For SELL: SL should be <= open_price for breakeven
                if current_sl <= open_price and current_sl != 0:
                    continue  # Already protected
                current_price = tick.ask
                profit_pips = (open_price - current_price) / (point * 10)
                
                if profit_pips >= min_profit_pips:
                    new_sl = open_price  # Move to breakeven
            
            # Apply breakeven protection
            if profit_pips >= min_profit_pips:
                request = {
                    "action": mt5.TRADE_ACTION_SLTP,
                    "position": ticket,
                    "symbol": symbol,
                    "sl": round(new_sl, digits),
                    "tp": round(pos.tp, digits) if pos.tp else 0
                }
                
                result = mt5.order_send(request)
                
                if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                    print(f"[PROTECT] [BREAKEVEN] {symbol} #{ticket}: SL moved to entry @ {new_sl:.5f} (profit: {profit_pips:.1f} pips)")
                    protected.append({
                        'ticket': ticket,
                        'symbol': symbol,
                        'protection_type': 'BREAKEVEN',
                        'profit_when_protected': profit_pips
                    })
        
        return protected
    
    def apply_aggressive_trailing(self):
        """
        PHASE 2: AGGRESSIVE TRAILING STOP - Lock Profits as Price Moves
        
        3-Tier trailing system for maximum profit protection:
        
        Tier 1 (+30 pips profit): Trail at +15 pips (lock half)
        Tier 2 (+50 pips profit): Trail at +30 pips (lock more)
        Tier 3 (+80 pips profit): Trail at +50 pips (lock most)
        
        Each tier only activates when price moves favorably.
        """
        if not self.connected:
            return []
        
        positions = mt5.positions_get()
        if not positions:
            return []
        
        trailing_config = [
            {'profit_threshold': 30, 'trail_distance': 15, 'label': 'TIER_1'},
            {'profit_threshold': 50, 'trail_distance': 30, 'label': 'TIER_2'},
            {'profit_threshold': 80, 'trail_distance': 50, 'label': 'TIER_3'}
        ]
        
        updated = []
        
        for pos in positions:
            if pos.magic != 234000:
                continue
            
            symbol = pos.symbol
            ticket = pos.ticket
            pos_type = pos.type
            open_price = pos.price_open
            current_sl = pos.sl
            current_tp = pos.tp
            
            tick = mt5.symbol_info_tick(symbol)
            if tick is None:
                continue
            
            point = mt5.symbol_info(symbol).point
            digits = mt5.symbol_info(symbol).digits
            
            # Calculate current profit
            if pos_type == 0:  # BUY
                current_price = tick.bid
                profit_pips = (current_price - open_price) / (point * 10)
            else:  # SELL
                current_price = tick.ask
                profit_pips = (open_price - current_price) / (point * 10)
            
            # Find which tier applies
            applicable_tier = None
            for tier in reversed(trailing_config):  # Check from highest tier first
                if profit_pips >= tier['profit_threshold']:
                    applicable_tier = tier
                    break
            
            if not applicable_tier:
                continue  # Not enough profit yet
            
            # Calculate new SL based on tier
            trail_distance = applicable_tier['trail_distance'] * point * 10
            new_sl = None
            
            if pos_type == 0:  # BUY
                proposed_sl = current_price - trail_distance
                # Only move if better than current SL
                if proposed_sl > current_sl:
                    new_sl = proposed_sl
            else:  # SELL
                proposed_sl = current_price + trail_distance
                if proposed_sl < current_sl or current_sl == 0:
                    new_sl = proposed_sl
            
            # Apply trailing stop
            if new_sl:
                request = {
                    "action": mt5.TRADE_ACTION_SLTP,
                    "position": ticket,
                    "symbol": symbol,
                    "sl": round(new_sl, digits),
                    "tp": round(current_tp, digits) if current_tp else 0
                }
                
                result = mt5.order_send(request)
                
                if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                    locked_pips = abs(new_sl - open_price) / (point * 10)
                    print(f"[TRAIL] [TRAILING {applicable_tier['label']}] {symbol} #{ticket}: "
                          f"SL→{new_sl:.5f} (locked {locked_pips:.1f} pips, current profit: {profit_pips:.1f})")
                    updated.append({
                        'ticket': ticket,
                        'symbol': symbol,
                        'tier': applicable_tier['label'],
                        'locked_pips': locked_pips,
                        'current_profit_pips': profit_pips
                    })
        
        return updated
    
    def run_full_protection_cycle(self):
        """
        EXECUTE COMPLETE PROTECTION CYCLE
        
        Order of operations:
        1. Breakeven protection (15+ pips profit)
        2. Aggressive trailing (30+ pips profit)
        
        Returns combined results from both phases.
        """
        print(f"\n[PROTECT] [{datetime.now().strftime('%H:%M:%S')}] RUNNING FULL PROTECTION CYCLE")
        print("-" * 50)
        
        # Phase 1: Breakeven
        breakeven_results = self.apply_breakeven_protection(min_profit_pips=15)
        
        # Phase 2: Trailing (only on positions already at breakeven or higher profit)
        trailing_results = self.apply_aggressive_trailing()
        
        total_protected = len(breakeven_results) + len(trailing_results)
        
        if total_protected > 0:
            print(f"[OK] Protection cycle complete: {len(breakeven_results)} breakeven, {len(trailing_results)} trailing")
        else:
            print("[INFO] No positions ready for protection yet")
        
        return {
            'breakeven': breakeven_results,
            'trailing': trailing_results,
            'total': total_protected
        }
    
    def export_status(self, filepath="mt5_ftmo_status.json"):
        """Export status to JSON for monitoring"""
        summary = self.get_account_summary()
        if summary is None:
            return False
        
        summary['positions'] = self.get_position_summary()
        summary['timestamp'] = datetime.now().isoformat()
        summary['ftmo_limits'] = {
            'max_daily_loss_pct': MAX_DAILY_LOSS,
            'max_total_loss_pct': MAX_TOTAL_LOSS,
            'max_positions': MAX_POSITIONS,
            'profit_target': PROFIT_TARGET_PHASE1
        }
        
        try:
            with open(filepath, 'w') as f:
                json.dump(summary, f, indent=2, default=str)
            return True
        except Exception as e:
            print(f"Export failed: {e}")
            return False
    
    def is_breakeven_or_better(self, pos):
        """Check if position SL is at breakeven or better (for reporting)"""
        if pos['type'] == 'BUY':
            return pos['sl'] >= pos['open_price']
        else:  # SELL
            return pos['sl'] <= pos['open_price'] and pos['sl'] > 0
    
    def shutdown(self):
        """Disconnect from MT5"""
        mt5.shutdown()
        self.connected = False
        print("[OK] MT5 disconnected")


class FTMO24_7SetupScanner:
    """24/7 Setup Scanner - The exact strategy that made 17% on Pepperstone
    
    Monitors 8 major pairs continuously with 3 strategies:
    - Trend Following (ADX > 25)
    - Range Trading (ADX < 25, Bollinger Bands)
    - Breakout (Asian range break + volume confirmation)
    
    Filters:
    - ADX filter to avoid ranging in trending markets
    - Volume confirmation for breakouts
    - Signal prioritization: STRONG > MODERATE
    - Duplicate prevention: one trade per symbol
    """
    
    def __init__(self, trader):
        self.trader = trader
        # 12 perechi populare pentru maximizare oportunități
        self.symbols = [
            "EURUSD", "GBPUSD", "USDJPY", "XAUUSD",  # Majors
            "EURJPY", "GBPJPY", "AUDJPY", "EURGBP",  # Crosses
            "USDCAD", "AUDUSD", "NZDUSD", "GBPAUD"   # Additional
        ]
        self.magic_number = 234000
        self.active_symbols = set()  # Duplicate prevention
    
    def calculate_adx(self, df, period=14):
        """Calculate ADX for trend strength"""
        df['high_low'] = df['high'] - df['low']
        df['high_close'] = abs(df['high'] - df['close'].shift())
        df['low_close'] = abs(df['low'] - df['close'].shift())
        df['tr'] = df[['high_low', 'high_close', 'low_close']].max(axis=1)
        
        df['plus_dm'] = df['high'].diff()
        df['minus_dm'] = df['low'].diff(-1).abs()
        
        df['plus_dm'] = np.where((df['plus_dm'] > df['minus_dm']) & (df['plus_dm'] > 0), df['plus_dm'], 0)
        df['minus_dm'] = np.where((df['minus_dm'] > df['plus_dm']) & (df['minus_dm'] > 0), df['minus_dm'], 0)
        
        df['atr'] = df['tr'].rolling(window=period).mean()
        df['plus_di'] = 100 * (df['plus_dm'].rolling(window=period).mean() / df['atr'])
        df['minus_di'] = 100 * (df['minus_dm'].rolling(window=period).mean() / df['atr'])
        df['dx'] = (abs(df['plus_di'] - df['minus_di']) / (df['plus_di'] + df['minus_di'])) * 100
        df['adx'] = df['dx'].rolling(window=period).mean()
        
        return df['adx'].iloc[-1] if len(df) >= period else 25
    
    def analyze_trend(self, symbol):
        """Trend Following Strategy - MA20/50 crossover with ADX filter"""
        df = self.trader.get_rates(symbol, mt5.TIMEFRAME_M15, 50)
        if df is None or len(df) < 50:
            return None
        
        # Indicators
        df['sma20'] = df['close'].rolling(20).mean()
        df['sma50'] = df['close'].rolling(50).mean()
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        df['rsi'] = 100 - (100 / (1 + (gain / loss)))
        
        # ADX for trend strength
        adx = self.calculate_adx(df)
        
        latest = df.iloc[-1]
        prev = df.iloc[-2]
        
        # ADX filter: only trade trends when ADX > 25
        if adx < 25:
            return None
        
        signal = None
        confidence = 0
        
        # Bullish crossover with RSI confirmation
        if latest['close'] > latest['sma20'] > latest['sma50']:
            if prev['close'] < prev['sma20'] and latest['rsi'] < 70:
                signal = 'BUY'
                confidence = min((adx / 50) * 100, 100)  # ADX-based confidence
        
        # Bearish crossover with RSI confirmation
        elif latest['close'] < latest['sma20'] < latest['sma50']:
            if prev['close'] > prev['sma20'] and latest['rsi'] > 30:
                signal = 'SELL'
                confidence = min((adx / 50) * 100, 100)
        
        return {
            'symbol': symbol,
            'signal': signal,
            'strategy': 'TREND',
            'confidence': confidence,
            'strength': 'STRONG' if confidence > 70 else 'MODERATE',
            'price': latest['close'],
            'adx': adx,
            'rsi': latest['rsi'],
            'sma20': latest['sma20'],
            'sma50': latest['sma50']
        } if signal else None
    
    def analyze_range(self, symbol):
        """Range Trading - Bollinger Bands bounce with ADX filter"""
        df = self.trader.get_rates(symbol, mt5.TIMEFRAME_M15, 50)
        if df is None or len(df) < 50:
            return None
        
        # Bollinger Bands
        df['sma20'] = df['close'].rolling(20).mean()
        df['std20'] = df['close'].rolling(20).std()
        df['upper'] = df['sma20'] + (df['std20'] * 2)
        df['lower'] = df['sma20'] - (df['std20'] * 2)
        
        # ADX - only trade range when ADX < 25 (low trend strength)
        adx = self.calculate_adx(df)
        if adx >= 25:
            return None
        
        # Check H1 trend - don't trade against strong trends
        df_h1 = self.trader.get_rates(symbol, mt5.TIMEFRAME_H1, 50)
        if df_h1 is not None and len(df_h1) >= 50:
            df_h1['ma20'] = df_h1['close'].rolling(20).mean()
            df_h1['ma50'] = df_h1['close'].rolling(50).mean()
            h1_latest = df_h1.iloc[-1]
            
            h1_bullish = h1_latest['close'] > h1_latest['ma20'] > h1_latest['ma50']
            h1_bearish = h1_latest['close'] < h1_latest['ma20'] < h1_latest['ma50']
        else:
            h1_bullish = False
            h1_bearish = False
        
        latest = df.iloc[-1]
        
        signal = None
        confidence = 0
        
        # Price at lower band = buy (mean reversion)
        # BUT: Don't buy if H1 is strongly bearish
        if latest['close'] <= latest['lower']:
            if h1_bearish:
                print(f"{symbol}: Range BUY skipped - H1 trend is bearish")
                return None
            signal = 'BUY'
            confidence = ((latest['lower'] - latest['close']) / latest['std20']) * 50 + 50
        
        # Price at upper band = sell (mean reversion)
        # BUT: Don't sell if H1 is strongly bullish
        elif latest['close'] >= latest['upper']:
            if h1_bullish:
                print(f"{symbol}: Range SELL skipped - H1 trend is bullish")
                return None
            signal = 'SELL'
            confidence = ((latest['close'] - latest['upper']) / latest['std20']) * 50 + 50
        
        return {
            'symbol': symbol,
            'signal': signal,
            'strategy': 'RANGE',
            'confidence': min(confidence, 100),
            'strength': 'STRONG' if confidence > 70 else 'MODERATE',
            'price': latest['close'],
            'adx': adx,
            'bb_upper': latest['upper'],
            'bb_lower': latest['lower'],
            'bb_mid': latest['sma20']
        } if signal else None
    
    def analyze_fvg(self, symbol):
        """Fair Value Gap (FVG) Strategy - ICT Price Action
        
        Detects 3-candle imbalance patterns:
        - Bullish FVG: Low(C3) > High(C1) → gap upward
        - Bearish FVG: High(C3) < Low(C1) → gap downward
        
        Entry: Price returns to fill 50-61.8% of the gap
        Best timeframe: M15, H1 (higher = stronger)
        Confluence: MSS + FVG = high probability
        """
        # Get M15 data for FVG detection
        df = self.trader.get_rates(symbol, mt5.TIMEFRAME_M15, 50)
        if df is None or len(df) < 20:
            return None
        
        # Calculate FVG for last 20 candles
        fvg_zones = []
        
        for i in range(len(df) - 3, len(df) - 15, -1):  # Check last 12 potential patterns
            if i < 3:
                break
                
            c1 = df.iloc[i-2]  # First candle
            c2 = df.iloc[i-1]  # Middle candle (impulsive)
            c3 = df.iloc[i]    # Third candle
            
            # Bullish FVG: Low(C3) > High(C1)
            if c3['low'] > c1['high']:
                gap_top = c3['low']
                gap_bottom = c1['high']
                gap_size = gap_top - gap_bottom
                
                # Check if price is currently near the gap (50-61.8% fill zone)
                current_price = df.iloc[-1]['close']
                fill_50 = gap_bottom + (gap_size * 0.5)
                fill_618 = gap_bottom + (gap_size * 0.618)
                
                # Price should be in the upper half of the gap (50-80% fill)
                if fill_50 <= current_price <= gap_top:
                    # Calculate confidence based on gap size (larger = more significant)
                    atr = (df['high'] - df['low']).rolling(14).mean().iloc[-1]
                    gap_size_atr = gap_size / atr if atr > 0 else 0
                    
                    confidence = min(50 + gap_size_atr * 15, 85)
                    
                    fvg_zones.append({
                        'type': 'BULLISH',
                        'confidence': confidence,
                        'gap_top': gap_top,
                        'gap_bottom': gap_bottom,
                        'fill_50': fill_50,
                        'fill_618': fill_618,
                        'gap_size_pips': gap_size * (100 if 'JPY' not in symbol else 1)
                    })
            
            # Bearish FVG: High(C3) < Low(C1)
            elif c3['high'] < c1['low']:
                gap_bottom = c3['high']
                gap_top = c1['low']
                gap_size = gap_top - gap_bottom
                
                current_price = df.iloc[-1]['close']
                fill_50 = gap_top - (gap_size * 0.5)
                fill_618 = gap_top - (gap_size * 0.618)
                
                # Price should be in the lower half of the gap
                if gap_bottom <= current_price <= fill_50:
                    atr = (df['high'] - df['low']).rolling(14).mean().iloc[-1]
                    gap_size_atr = gap_size / atr if atr > 0 else 0
                    
                    confidence = min(50 + gap_size_atr * 15, 85)
                    
                    fvg_zones.append({
                        'type': 'BEARISH',
                        'confidence': confidence,
                        'gap_top': gap_top,
                        'gap_bottom': gap_bottom,
                        'fill_50': fill_50,
                        'fill_618': fill_618,
                        'gap_size_pips': gap_size * (100 if 'JPY' not in symbol else 1)
                    })
        
        # Return the most recent and strongest FVG
        if fvg_zones:
            # Get the strongest FVG
            best_fvg = max(fvg_zones, key=lambda x: x['confidence'])
            
            current_price = df.iloc[-1]['close']
            
            if best_fvg['type'] == 'BULLISH':
                signal = 'BUY'
                entry_zone = f"{best_fvg['fill_618']:.5f} - {best_fvg['fill_50']:.5f}"
            else:
                signal = 'SELL'
                entry_zone = f"{best_fvg['fill_50']:.5f} - {best_fvg['fill_618']:.5f}"
            
            return {
                'symbol': symbol,
                'signal': signal,
                'strategy': 'FVG',
                'confidence': best_fvg['confidence'],
                'strength': 'STRONG' if best_fvg['confidence'] > 70 else 'MODERATE',
                'price': current_price,
                'gap_top': best_fvg['gap_top'],
                'gap_bottom': best_fvg['gap_bottom'],
                'entry_zone': entry_zone,
                'gap_size_pips': best_fvg['gap_size_pips']
            }
        
        return None
    
    def analyze_breakout(self, symbol):
        """Breakout Strategy - FAST MOVES for Day Trading
        
        Best for: Quick momentum plays (30min - 1 day holds)
        Logic: Break of recent range with volume
        Target: Quick 30-60 pip moves
        """
        # Get M30 data for quick breakouts (not H1)
        df = self.trader.get_rates(symbol, mt5.TIMEFRAME_M30, 12)  # 6 hours of data
        if df is None or len(df) < 8:
            return None
        
        # Recent range (last 8 candles = 4 hours)
        recent_high = df['high'].iloc[-8:].max()
        recent_low = df['low'].iloc[-8:].min()
        recent_range = recent_high - recent_low
        
        latest = df.iloc[-1]
        current_price = latest['close']
        
        # Volume confirmation - current vs average
        avg_volume = df['tick_volume'].iloc[-8:].mean()
        current_volume = latest['tick_volume']
        volume_confirmed = current_volume > avg_volume * 1.3  # 30% above average
        
        # Breakout threshold: smaller for day trading (1 pip)
        breakout_threshold = 0.0001 if 'JPY' not in symbol else 0.01
        
        signal = None
        confidence = 0
        
        # Bullish breakout
        if current_price > recent_high + breakout_threshold and volume_confirmed:
            signal = 'BUY'
            confidence = min((current_volume / avg_volume) * 40, 90)
        
        # Bearish breakout
        elif current_price < recent_low - breakout_threshold and volume_confirmed:
            signal = 'SELL'
            confidence = min((current_volume / avg_volume) * 40, 90)
        
        return {
            'symbol': symbol,
            'signal': signal,
            'strategy': 'BREAKOUT',
            'confidence': confidence,
            'strength': 'STRONG' if confidence > 70 else 'MODERATE',
            'price': current_price,
            'recent_high': recent_high,
            'recent_low': recent_low,
            'volume_ratio': current_volume / avg_volume if avg_volume > 0 else 0
        } if signal else None
    
    def load_strategy_weights(self):
        """Load dynamic strategy weights from meta-learner analysis"""
        import json
        analysis_file = r"C:\Users\Claw\.openclaw\workspace\mt5_trader\THE_BEAST\strategy_analysis.json"
        weights = {
            'FVG': {'priority': 4, 'min_conf': 50, 'enabled': True},
            'BREAKOUT': {'priority': 3, 'min_conf': 50, 'enabled': True},
            'RANGE': {'priority': 2, 'min_conf': 50, 'enabled': True},
            'TREND': {'priority': 1, 'min_conf': 65, 'enabled': True}
        }
        
        try:
            if os.path.exists(analysis_file):
                with open(analysis_file, 'r') as f:
                    analysis = json.load(f)
                    config = analysis.get('config', {}).get('strategies', {})
                    
                    for strat, cfg in config.items():
                        if strat in weights:
                            weights[strat]['priority'] = cfg.get('priority', weights[strat]['priority'])
                            weights[strat]['min_conf'] += cfg.get('min_confidence_adjust', 0)
                            if cfg.get('status') == 'DISABLE':
                                weights[strat]['enabled'] = False
                                
        except Exception as e:
            print(f"[WARN] Could not load strategy weights: {e}")
        
        return weights
    
    def get_best_signal(self, symbol):
        """Get best signal from all 4 strategies with dynamic prioritization"""
        # Duplicate prevention check
        if symbol in self.active_symbols:
            return None
        
        # Load dynamic weights
        weights = self.load_strategy_weights()
        
        # Try all 4 strategies
        signals = []
        
        # 1. FVG - Highest priority (ICT Fair Value Gap)
        if weights['FVG']['enabled']:
            fvg_signal = self.analyze_fvg(symbol)
            min_conf = weights['FVG']['min_conf']
            if fvg_signal and fvg_signal['confidence'] >= min_conf:
                fvg_signal['priority'] = weights['FVG']['priority']
                fvg_signal['source'] = 'FVG'
                signals.append(fvg_signal)
        
        # 2. BREAKOUT - fast moves
        if weights['BREAKOUT']['enabled']:
            breakout_signal = self.analyze_breakout(symbol)
            min_conf = weights['BREAKOUT']['min_conf']
            if breakout_signal and breakout_signal['confidence'] >= min_conf:
                breakout_signal['priority'] = weights['BREAKOUT']['priority']
                breakout_signal['source'] = 'BREAKOUT'
                signals.append(breakout_signal)
        
        # 3. RANGE - mean reversion
        if weights['RANGE']['enabled']:
            range_signal = self.analyze_range(symbol)
            min_conf = weights['RANGE']['min_conf']
            if range_signal and range_signal['confidence'] >= min_conf:
                range_signal['priority'] = weights['RANGE']['priority']
                range_signal['source'] = 'RANGE'
                signals.append(range_signal)
        
        # 4. TREND - only if very strong
        if weights['TREND']['enabled']:
            trend_signal = self.analyze_trend(symbol)
            min_conf = weights['TREND']['min_conf']
            if trend_signal and trend_signal['confidence'] >= min_conf:
                trend_signal['priority'] = weights['TREND']['priority']
                trend_signal['source'] = 'TREND'
                signals.append(trend_signal)
        
        if not signals:
            return None
        
        # Prioritization: Priority > Strength > Confidence
        strong_signals = [s for s in signals if s['strength'] == 'STRONG']
        if strong_signals:
            return max(strong_signals, key=lambda x: (x['priority'], x['confidence']))
        
        return max(signals, key=lambda x: (x['priority'], x['confidence']))
    
    def execute_signal(self, signal):
        """Execute a trading signal with FTMO adaptive risk management"""
        if signal is None or signal.get('signal') is None:
            return None
        
        symbol = signal['symbol']
        direction = signal['signal']
        confidence = signal['confidence']
        strategy = signal['strategy']
        
        # Get adaptive risk parameters from trader
        risk_status = self.trader.get_risk_status()
        
        # Check if trading allowed
        if not risk_status['can_trade']:
            print(f"[SKIP] {symbol}: Trading halted - {risk_status['message']}")
            return None
        
        # CIRCUIT BREAKER: Stop new trades if daily loss > 2%
        daily_loss_pct = self.trader.daily_max_loss_pct
        if daily_loss_pct >= 0.02:  # 2% daily loss
            print(f"[SKIP] {symbol}: CIRCUIT BREAKER - Daily loss {daily_loss_pct:.2%}. No new trades.")
            return None
        
        # Duplicate prevention: mark symbol as active
        self.active_symbols.add(symbol)
        
        # Tiered confidence based on open positions AND daily loss
        # Base tier: Slots 1-4: >= 40% | Slots 5-7: >= 60% | Slots 8-9: >= 75% | Slot 10: >= 85%
        # REDUCED in drawdown: Max 5 positions if daily loss > 1%
        open_count = len(self.active_symbols)
        max_slots = 5 if daily_loss_pct >= 0.01 else 10
        
        if open_count >= max_slots:
            print(f"[SKIP] {symbol}: Max positions reached ({open_count}/{max_slots}) in drawdown")
            return None
        
        if open_count >= 9:
            min_conf = 85
        elif open_count >= 7:
            min_conf = 75
        elif open_count >= 4:
            min_conf = 60
        else:
            min_conf = 40
        
        # Override with adaptive min_conf from risk status if higher
        adaptive_min = risk_status['min_confidence']
        if adaptive_min > min_conf:
            min_conf = adaptive_min
            print(f"[RISK] Daily loss elevated - min confidence raised to {min_conf}%")
        
        if confidence < min_conf:
            print(f"[SKIP] {symbol}: Confidence {confidence:.0f}% < required {min_conf}% (slots {open_count}/10, risk: {risk_status['status']})")
            self.active_symbols.discard(symbol)
            return None
        
        # Base lot size based on confidence
        # 40-60%: 0.1 lots | 60-75%: 0.2 lots | 75-85%: 0.3 lots | 85-95%: 0.4 lots | 95-100%: 0.5 lots
        if confidence >= 95:
            lot_size = 0.5
        elif confidence >= 85:
            lot_size = 0.4
        elif confidence >= 75:
            lot_size = 0.3
        elif confidence >= 60:
            lot_size = 0.2
        else:
            lot_size = 0.1
        
        # Apply adaptive lot multiplier from risk status
        lot_multiplier = risk_status['lot_multiplier']
        if lot_multiplier < 1.0:
            original_lot = lot_size
            lot_size = round(lot_size * lot_multiplier, 2)
            print(f"[RISK] Lot reduced {original_lot} -> {lot_size} (multiplier: {lot_multiplier}) due to {risk_status['status']}")
        
        # Dynamic SL/TP based on confidence - SHORT TERM for Day Trading
        # Higher confidence = tighter SL, wider TP for better R:R
        # Day Trading focus: trades should complete within 1-3 days, not weeks
        if confidence >= 80:
            sl_pips = 30  # Tight stop for quick moves
            tp_pips = 60  # 1:2 R/R - quick profit
        elif confidence >= 60:
            sl_pips = 40  # Moderate
            tp_pips = 60  # 1:1.5 R/R
        else:
            sl_pips = 50  # Wider for lower confidence
            tp_pips = 50  # 1:1 R/R - breakeven quick
        
        order_type = mt5.ORDER_TYPE_BUY if direction == 'BUY' else mt5.ORDER_TYPE_SELL
        
        result = self.trader.place_order(
            symbol=symbol,
            order_type=order_type,
            lot_size=lot_size,
            sl_pips=sl_pips,
            tp_pips=tp_pips,
            magic=self.magic_number,
            comment=f"FTMO {strategy} {direction} C:{confidence:.0f}%"
        )
        
        if result and result.get('success'):
            print(f"[EXECUTED] {symbol} {direction} | Lot: {lot_size} | SL: {sl_pips} | TP: {tp_pips} | Conf: {confidence:.0f}%")
        
        if result and result.get('success'):
            print(f"[EXECUTED] {symbol} {direction} | {strategy} | Conf: {confidence:.1f}%")
        else:
            # Remove from active if failed
            self.active_symbols.discard(symbol)
        
        return result
    
    def scan_all_pairs(self, auto_trade=False):
        """Scan all pairs and execute best signals with adaptive risk"""
        print(f"\n[{datetime.now()}] 24/7 SETUP SCANNER - FTMO")
        print("="*60)
        
        # Check FTMO limits first (with adaptive risk)
        can_trade, msg, hard_stop, risk_status = self.trader.check_ftmo_limits()
        print(f"[FTMO STATUS] {msg}")
        
        if not can_trade:
            if hard_stop:
                print("[ALERT] TRADING HALTED - HARD STOP ACTIVATED")
            return []
        
        # Get adaptive max positions from risk status
        adaptive_max = risk_status['max_positions'] if risk_status else MAX_POSITIONS
        
        # Reset active symbols (positions may have closed)
        positions = self.trader.get_position_summary()
        self.active_symbols = {p['symbol'] for p in positions}
        
        print(f"Active positions: {len(self.active_symbols)}/{adaptive_max} (adaptive max)")
        print(f"Daily loss: {self.trader.daily_max_loss_pct:.2%} | Status: {risk_status['status'] if risk_status else 'UNKNOWN'}")
        
        # Log strategy weights (dynamic from meta-learner)
        weights = self.load_strategy_weights()
        active_strats = [f"{k}(P:{v['priority']},C:{v['min_conf']:.0f})" for k,v in weights.items() if v['enabled']]
        print(f"Strategies: {', '.join(active_strats)}")
        
        print(f"Scanning {len(self.symbols)} pairs...\n")
        
        results = []
        signals_found = []
        
        for symbol in self.symbols:
            # Skip if already have position in this symbol
            if symbol in self.active_symbols:
                print(f"{symbol}: Already in position - SKIP")
                continue
            
            # Check if adaptive max positions reached
            if len(self.active_symbols) >= adaptive_max:
                print(f"{symbol}: Max positions reached ({len(self.active_symbols)}/{adaptive_max}) - SKIP")
                break
            
            # Get best signal for this symbol
            signal = self.get_best_signal(symbol)
            
            if signal:
                signals_found.append(signal)
                print(f"{symbol}: [{signal['strategy']}] {signal['signal']} "
                      f"(Conf: {signal['confidence']:.0f}%, {signal['strength']})")
                
                if auto_trade:
                    result = self.execute_signal(signal)
                    if result and result.get('success'):
                        results.append(result)
                        self.active_symbols.add(symbol)
            else:
                print(f"{symbol}: No signal")
        
        print(f"\n{'='*60}")
        print(f"Signals found: {len(signals_found)} | Executed: {len(results)}")
        
        return results
    
    def run_test_trades(self):
        """Execute test trades on major pairs for validation"""
        print(f"\n[TEST MODE] Executing validation trades...")
        print("="*60)
        
        test_pairs = [
            ("EURUSD", "BUY"),
            ("XAUUSD", "BUY"),
        ]
        
        results = []
        for symbol, direction in test_pairs:
            print(f"\n[TEST] Placing {direction} on {symbol}")
            
            order_type = mt5.ORDER_TYPE_BUY if direction == "BUY" else mt5.ORDER_TYPE_SELL
            
            result = self.trader.place_order(
                symbol=symbol,
                order_type=order_type,
                lot_size=FIXED_LOT_SIZE,
                sl_pips=50,
                tp_pips=100,
                magic=self.magic_number,
                comment=f"FTMO TEST {direction}"
            )
            
            if result and result.get('success'):
                print(f"[OK] TEST TRADE EXECUTED: {symbol} {direction}")
                print(f"   Ticket: {result.get('order_id')}")
                print(f"   Price: {result.get('price')}")
                results.append(result)
            else:
                print(f"[FAIL] TEST TRADE FAILED: {symbol}")
                print(f"   Error: {result.get('error', 'Unknown')}")
            
            time.sleep(1)  # Small delay between orders
        
        print(f"\n{'='*60}")
        print(f"Test trades executed: {len(results)}/{len(test_pairs)}")
        return results
    
    def run(self, auto_trade=False, test_mode=False):
        """Run one scan cycle or test trades"""
        if test_mode:
            return self.run_test_trades()
        return self.scan_all_pairs(auto_trade=auto_trade)


def run_continuous_mode(trader, strategy):
    """Run continuous trading with 5-minute scan intervals, 30-minute reports, and 2-minute protection"""
    import time
    from datetime import datetime, timedelta
    
    cycle = 0
    next_report = datetime.now()
    last_protection = datetime.now() - timedelta(minutes=5)  # Run immediately on start
    
    print("\n" + "="*60)
    print("CONTINUOUS TRADING MODE ENABLED")
    print("="*60)
    print("[REPORT] Scan interval: 5 minutes (find new setups)")
    print("[PROTECT] Protection interval: 2 minutes (breakeven + trailing)")
    print("[TRAIL] Report interval: 30 minutes (account status)")
    print("="*60)
    print("Press Ctrl+C to stop")
    
    try:
        while True:
            cycle += 1
            now = datetime.now()
            
            # Check MT5 connection - reconnect if needed
            if not mt5.terminal_info():
                print("[WARN] MT5 disconnected! Attempting to reconnect...")
                mt5.shutdown()
                time.sleep(2)
                if not mt5.initialize():
                    print("[ERROR] Failed to reconnect to MT5. Waiting 30 seconds...")
                    time.sleep(30)
                    continue
                print("[OK] Reconnected to MT5")
            
            # Check FTMO limits (with adaptive risk)
            try:
                can_trade, msg, hard_stop, risk_status = trader.check_ftmo_limits()
            except Exception as e:
                print(f"[ERROR] check_ftmo_limits failed: {e}")
                time.sleep(10)
                continue
            
            if hard_stop:
                print(f"\n{'='*60}")
                print("HARD STOP TRIGGERED - Trading halted")
                print(f"Reason: {msg}")
                print(f"{'='*60}")
                break
            
            # Display risk status if not normal
            if risk_status and risk_status['status'] != 'SAFE':
                print(f"[RISK STATUS: {risk_status['status']}] {risk_status['message']}")
            
            # ==== RUN PROTECTION CYCLE (every 2 minutes) ====
            if (now - last_protection).seconds >= 120:  # 2 minutes
                protection_results = trader.run_full_protection_cycle()
                last_protection = now
                time.sleep(1)  # Brief pause after protection
            
            # ==== RUN TRADING CYCLE (every 5 minutes) ====
            if cycle % 1 == 0:  # Every cycle (5 min)
                try:
                    print(f"\n[{now.strftime('%H:%M:%S')}] Cycle #{cycle}: Scanning for new setups...")
                    strategy.run(auto_trade=True)
                    trader.export_status()
                except Exception as e:
                    print(f"[ERROR] Trading cycle failed: {e}")
                    import traceback
                    traceback.print_exc()
                    time.sleep(10)
                    continue
            
            # ==== GENERATE REPORT (every 30 minutes) ====
            if now >= next_report:
                try:
                    summary = trader.get_account_summary()
                    positions = trader.get_position_summary()
                except Exception as e:
                    print(f"[ERROR] Report generation failed: {e}")
                    time.sleep(10)
                    continue
                
                profit = summary['profit']
                profit_pct = summary['profit_pct'] * 100
                equity = summary['equity']
                
                # Get daily metrics for report
                daily_start = trader.daily_starting_equity or summary['balance']
                daily_min = trader.daily_min_equity or daily_start
                daily_max_loss = (daily_start - daily_min) / daily_start * 100 if daily_start > 0 else 0
                
                print(f"\n{'='*60}")
                print(f"[REPORT] FTMO PHASE 1 REPORT - Cycle #{cycle}")
                print(f"Time: {now.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"{'='*60}")
                print(f"Balance: ${summary['balance']:.2f}")
                print(f"Equity:  ${equity:.2f}")
                print(f"P&L:     ${profit:.2f} ({profit_pct:.2f}%)")
                print(f"Progress: {profit_pct/10:.1f}% toward +10% target")
                print(f"Positions: {len(positions)}/{risk_status['max_positions'] if risk_status else MAX_POSITIONS}")
                print(f"Daily: Start ${daily_start:.2f} | Min ${daily_min:.2f} | Loss {daily_max_loss:.2f}% (limit 4%)")
                print(f"Risk: {risk_status['status'] if risk_status else 'UNKNOWN'} | Lot mult: {risk_status['lot_multiplier'] if risk_status else 1.0}")
                
                if positions:
                    print("\nActive Positions:")
                    for pos in positions:
                        # Check breakeven status
                        if pos['type'] == 'BUY':
                            is_be = pos['sl'] >= pos['open_price']
                        else:
                            is_be = pos['sl'] <= pos['open_price'] and pos['sl'] > 0
                        sl_status = "[PROTECT] BE" if is_be else f"SL@{pos['sl']}"
                        print(f"  - {pos['symbol']} {pos['type']}: ${pos['profit']:.2f} [{sl_status}]")
                
                # Check profit target
                if profit >= 1000:
                    print(f"\n[WIN] PROFIT TARGET REACHED! ${profit:.2f}")
                    break
                if profit <= -800:
                    print(f"\n[ALERT] TOTAL LOSS LIMIT: ${profit:.2f}")
                    break
                    
                print(f"{'='*60}")
                next_report = now + timedelta(minutes=30)
            
            # Wait 5 minutes
            print("  [TIMER]  Waiting 5 minutes...")
            time.sleep(300)
            
    except KeyboardInterrupt:
        print("\n\nTrading stopped by user")
    
    return True

if __name__ == "__main__":
    trader = MT5Trader()
    
    if trader.connect():
        print("\n" + "="*60)
        print("FTMO CHALLENGE ACCOUNT - $10,000")
        print("="*60)
        
        summary = trader.get_account_summary()
        print(f"\nAccount: {summary['account']}")
        print(f"Server: {summary['server']}")
        print(f"Balance: {summary['balance']} {summary['currency']}")
        print(f"Equity: {summary['equity']} {summary['currency']}")
        print(f"Profit: {summary['profit_pct']:.2%} ({summary['profit']:.2f} {summary['currency']})")
        print(f"Phase 1 Progress: {summary['phase1_progress']}")
        print(f"Open Positions: {summary['positions_count']}")
        
        # Export status
        trader.export_status()
        
        # Run 24/7 Setup Scanner strategy
        strategy = FTMO24_7SetupScanner(trader)
        
        # Check command line args
        import sys
        auto_trade = "--trade" in sys.argv
        test_mode = "--test" in sys.argv
        continuous = "--continuous" in sys.argv
        
        if test_mode:
            print("\n[TEST MODE ENABLED]")
            strategy.run(test_mode=True)
        elif continuous:
            print("\n[CONTINUOUS MODE ENABLED]")
            run_continuous_mode(trader, strategy)
        elif auto_trade:
            print("\n[AUTO TRADE MODE ENABLED]")
            print("24/7 Setup Scanner running with Trend/Range/Breakout strategies")
            strategy.run(auto_trade=True)
        else:
            strategy.run(auto_trade=False)
        
        trader.shutdown()
    else:
        print("\n[!] Failed to connect to FTMO account")
        print("    Please ensure:")
        print("    1. MT5 is open")
        print("    2. You're logged into FTMO account 541144102")
        print("    3. Server: FTMO-Server4")
