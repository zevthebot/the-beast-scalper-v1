#!/usr/bin/env python3
"""
MT5 Low-Token Connector - Optimized for minimal API usage
Reads signals from MT5 EA JSON export, applies risk rules, executes trades
"""

import MetaTrader5 as mt5
import json
import os
from datetime import datetime
from pathlib import Path

# Configuration
SIGNALS_PATH = Path(__file__).parent / "signals.json"
STATE_PATH = Path(__file__).parent / "state.json"
MAX_POSITIONS = 10      # Extended to 10 slots
RISK_PER_TRADE = 0.02   # 2%

# Tiered slot thresholds
SLOTS_NORMAL = 6        # Slots 1-6: score >= 70
SLOTS_PREMIUM = 4       # Slots 7-10: score >= 85
SCORE_THRESHOLD_NORMAL = 70
SCORE_THRESHOLD_PREMIUM = 85

CORRELATED_PAIRS = [
    ["EURUSD", "GBPUSD"],  # High positive correlation
    ["USDJPY", "EURJPY", "GBPJPY"],  # JPY group
    ["AUDUSD", "NZDUSD"],  # Commodity dollars
]

class MT5State:
    """Persistent state management"""
    def __init__(self):
        self.data = {
            "last_scan": None,
            "positions_at_last_scan": 0,
            "active_symbols": [],
            "daily_stats": {
                "trades_today": 0,
                "profit_today": 0.0,
                "max_drawdown_today": 0.0
            },
            "session": None
        }
        self.load()
    
    def load(self):
        if STATE_PATH.exists():
            try:
                with open(STATE_PATH, 'r') as f:
                    self.data.update(json.load(f))
            except Exception as e:
                print(f"[WARN] Could not load state: {e}")
    
    def save(self):
        try:
            with open(STATE_PATH, 'w') as f:
                json.dump(self.data, f, indent=2)
        except Exception as e:
            print(f"[WARN] Could not save state: {e}")
    
    def update(self, **kwargs):
        self.data.update(kwargs)
        self.data["last_scan"] = datetime.now().isoformat()
        self.save()

class MT5ConnectorOptimized:
    """Low-token MT5 connector - no LLM analysis, just execution"""
    
    def __init__(self):
        self.connected = False
        self.state = MT5State()
        
    def connect(self):
        """Connect to MT5"""
        if not mt5.initialize():
            print(f"[ERROR] MT5 init failed: {mt5.last_error()}")
            return False
        
        account = mt5.account_info()
        if account is None:
            print("[ERROR] MT5 not logged in")
            return False
        
        self.connected = True
        print(f"[OK] MT5 connected | Account: {account.login} | Balance: {account.balance:.2f} EUR")
        return True
    
    def get_positions(self):
        """Get current positions"""
        positions = mt5.positions_get()
        if positions is None:
            return []
        return [
            {
                "ticket": p.ticket,
                "symbol": p.symbol,
                "type": "BUY" if p.type == 0 else "SELL",
                "volume": p.volume,
                "open_price": p.price_open,
                "sl": p.sl,
                "tp": p.tp,
                "profit": p.profit
            }
            for p in positions
        ]
    
    def has_position_on_symbol(self, symbol):
        """Check if symbol already has position"""
        positions = self.get_positions()
        return any(p["symbol"] == symbol for p in positions)
    
    def check_correlation(self, symbol, active_symbols):
        """Check if symbol correlates with active positions"""
        for group in CORRELATED_PAIRS:
            if symbol in group:
                # Check if any other symbol in this group is active
                for other in group:
                    if other != symbol and other in active_symbols:
                        return True, other
        return False, None
    
    def place_order(self, symbol, direction, entry, sl, tp, lot_size=0.01):
        """Execute trade"""
        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            return None, f"Symbol {symbol} not found"
        
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
            "comment": f"LT_{direction[:1]}",  # Short comment
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        
        result = mt5.order_send(request)
        
        if result is None:
            return None, f"Order failed: {mt5.last_error()}"
        
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            return None, f"Order failed: {result.retcode} - {result.comment}"
        
        return {
            "order_id": result.order,
            "symbol": symbol,
            "direction": direction,
            "volume": lot_size,
            "price": price
        }, None
    
    def read_signals(self):
        """Read signals from MT5 EA export"""
        if not SIGNALS_PATH.exists():
            return None, "Signals file not found"
        
        try:
            with open(SIGNALS_PATH, 'r') as f:
                return json.load(f), None
        except json.JSONDecodeError:
            return None, "Invalid JSON in signals file"
        except Exception as e:
            return None, f"Error reading signals: {e}"
    
    def get_score_threshold(self, current_positions):
        """Determine score threshold based on how many slots are filled"""
        if current_positions < SLOTS_NORMAL:
            # Slots 1-6: Normal threshold
            return SCORE_THRESHOLD_NORMAL, "NORMAL"
        else:
            # Slots 7-10: Premium threshold
            return SCORE_THRESHOLD_PREMIUM, "PREMIUM"
    
    def process_signals(self, signals_data):
        """Process signals with tiered slot system"""
        if signals_data is None:
            return [], "No signals data"
        
        account = signals_data.get("account", {})
        signals = signals_data.get("signals", [])
        positions = self.get_positions()
        current_count = len(positions)
        
        # Risk checks
        if current_count >= MAX_POSITIONS:
            return [], f"Max positions reached ({current_count}/{MAX_POSITIONS})"
        
        # Determine current threshold based on filled slots
        score_threshold, tier = self.get_score_threshold(current_count)
        
        active_symbols = [p["symbol"] for p in positions]
        executed = []
        skipped = []
        
        # Filter signals by score threshold and sort by score desc
        qualified_signals = [
            s for s in signals 
            if s.get("score", 0) >= score_threshold
        ]
        
        # Sort by score descending (highest first)
        qualified_signals.sort(key=lambda s: s.get("score", 0), reverse=True)
        
        for signal in qualified_signals:
            if current_count + len(executed) >= MAX_POSITIONS:
                skipped.append(f"{signal['symbol']}: Max positions limit")
                continue
            
            symbol = signal["symbol"]
            direction = signal["signal"]
            score = signal.get("score", 0)
            
            # Check if already positioned
            if self.has_position_on_symbol(symbol):
                skipped.append(f"{symbol}: Already positioned")
                continue
            
            # Check correlation
            correlates, existing_symbol = self.check_correlation(symbol, active_symbols)
            if correlates:
                skipped.append(f"{symbol}: Correlates with {existing_symbol}")
                continue
            
            # Execute trade
            result, error = self.place_order(
                symbol=symbol,
                direction=direction,
                entry=signal["entry"],
                sl=signal["sl"],
                tp=signal["tp"],
                lot_size=0.01
            )
            
            if result:
                executed.append({
                    "symbol": symbol,
                    "direction": direction,
                    "strategy": signal.get("strategy", "UNKNOWN"),
                    "score": score,
                    "tier": tier,
                    "order_id": result["order_id"]
                })
            else:
                skipped.append(f"{symbol}: {error}")
        
        # Update state
        self.state.update(
            positions_at_last_scan=current_count + len(executed),
            active_symbols=active_symbols + [e["symbol"] for e in executed],
            daily_stats={
                "trades_today": self.state.data["daily_stats"]["trades_today"] + len(executed),
                "profit_today": account.get("profit", 0),
                "max_drawdown_today": self.state.data["daily_stats"]["max_drawdown_today"]
            }
        )
        
        return executed, skipped
    
    def generate_report(self, executed, skipped, signals_data):
        """Generate minimal report with tier info"""
        if signals_data is None:
            return "[ERROR] No signals data available"
        
        account = signals_data.get("account", {})
        positions = self.get_positions()
        count = len(positions)
        
        # Determine current tier
        if count < SLOTS_NORMAL:
            tier_status = f"NORMAL ({count}/{SLOTS_NORMAL})"
            threshold = SCORE_THRESHOLD_NORMAL
        elif count < MAX_POSITIONS:
            tier_status = f"PREMIUM ({count - SLOTS_NORMAL}/{SLOTS_PREMIUM})"
            threshold = SCORE_THRESHOLD_PREMIUM
        else:
            tier_status = "FULL"
            threshold = 0
        
        lines = [
            f"[OK] MT5 | Balance: {account.get('balance', 0):.2f} EUR",
            f"Slots: {count}/{MAX_POSITIONS} [{tier_status}] | Threshold: {threshold}+"
        ]
        
        if executed:
            lines.append(f"Executed: {len(executed)}")
            for trade in executed:
                tier_marker = "★" if trade.get('tier') == "PREMIUM" else "•"
                lines.append(f"  {tier_marker} {trade['direction']} {trade['symbol']} (scor: {trade.get('score', 'N/A')}) #{trade['order_id']}")
        
        return " | ".join(lines)
    
    def run(self):
        """Main execution loop"""
        if not self.connect():
            return "[ERROR] Connection failed"
        
        try:
            signals_data, error = self.read_signals()
            if error:
                return f"[WARN] {error}"
            
            executed, skipped = self.process_signals(signals_data)
            report = self.generate_report(executed, skipped, signals_data)
            
            # Return short status for cron
            if executed:
                return f"[TRADE] {report}"
            else:
                return f"[SCAN] {report}"
                
        finally:
            mt5.shutdown()


def main():
    """Entry point for cron execution"""
    connector = MT5ConnectorOptimized()
    result = connector.run()
    print(result)


if __name__ == "__main__":
    main()
