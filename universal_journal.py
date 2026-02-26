#!/usr/bin/env python3
"""
Universal Trade Journal
Works with all bot versions and accounts
Single source of truth for all trading activity
"""

import json
from pathlib import Path
from datetime import datetime, timezone
import MetaTrader5 as mt5

# Single universal journal path
UNIVERSAL_JOURNAL = Path(r"C:\Users\Claw\.openclaw\workspace\mt5_trader\universal_trade_journal.jsonl")

class UniversalJournal:
    """Universal logging system for all trades across all accounts and bot versions"""
    
    @staticmethod
    def log_entry(account_id, server, symbol, direction, lot_size, entry_price, 
                  sl, tp, strategy, bot_version, ml_score=None, features=None):
        """Log trade entry - works with any bot version"""
        
        entry = {
            "event": "ENTRY",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "account_id": account_id,
            "server": server,
            "symbol": symbol,
            "direction": direction,
            "lot_size": lot_size,
            "entry_price": entry_price,
            "sl": sl,
            "tp": tp,
            "strategy": strategy,  # e.g., "EMA_CROSS", "PIN_BAR", "ENGULFING"
            "bot_version": bot_version,  # e.g., "3.0", "4.0"
            "ml_score": ml_score,
            "features": features or {}
        }
        
        with open(UNIVERSAL_JOURNAL, 'a') as f:
            f.write(json.dumps(entry) + '\n')
        
        return entry
    
    @staticmethod
    def log_exit(position_id, account_id, symbol, direction, entry_price, exit_price,
                 exit_reason, pnl, pips, duration_min, bot_version, ml_features=None):
        """Log trade exit with results"""
        
        exit_data = {
            "event": "EXIT",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "position_id": position_id,
            "account_id": account_id,
            "symbol": symbol,
            "direction": direction,
            "entry_price": entry_price,
            "exit_price": exit_price,
            "exit_reason": exit_reason,  # "TP", "SL", "MANUAL", "SYSTEM"
            "pnl": pnl,
            "pips": pips,
            "duration_min": duration_min,
            "bot_version": bot_version,
            "ml_features": ml_features or {}
        }
        
        with open(UNIVERSAL_JOURNAL, 'a') as f:
            f.write(json.dumps(exit_data) + '\n')
        
        return exit_data
    
    @staticmethod
    def get_stats(account_id=None, bot_version=None, days=30):
        """Get trading statistics - filterable by account or version"""
        
        entries = {}
        exits = []
        
        if not UNIVERSAL_JOURNAL.exists():
            return None
        
        with open(UNIVERSAL_JOURNAL, 'r') as f:
            for line in f:
                try:
                    event = json.loads(line.strip())
                    
                    # Apply filters
                    if account_id and event.get('account_id') != account_id:
                        continue
                    if bot_version and event.get('bot_version') != bot_version:
                        continue
                    
                    if event.get('event') == 'ENTRY':
                        entries[event.get('position_id')] = event
                    elif event.get('event') == 'EXIT':
                        exits.append(event)
                        
                except:
                    continue
        
        # Match entries with exits
        trades = []
        for exit_event in exits:
            pos_id = exit_event.get('position_id')
            if pos_id in entries:
                entry = entries[pos_id]
                trades.append({
                    **exit_event,
                    'entry_time': entry.get('timestamp'),
                    'strategy': entry.get('strategy'),
                    'entry_ml_score': entry.get('ml_score')
                })
        
        if not trades:
            return None
        
        # Calculate stats
        total_pnl = sum(t['pnl'] for t in trades)
        wins = [t for t in trades if t['pnl'] > 0]
        losses = [t for t in trades if t['pnl'] < 0]
        
        return {
            'total_trades': len(trades),
            'win_count': len(wins),
            'loss_count': len(losses),
            'win_rate': len(wins) / len(trades) * 100 if trades else 0,
            'total_pnl': total_pnl,
            'avg_pnl': total_pnl / len(trades) if trades else 0,
            'avg_win': sum(t['pnl'] for t in wins) / len(wins) if wins else 0,
            'avg_loss': sum(t['pnl'] for t in losses) / len(losses) if losses else 0
        }


if __name__ == "__main__":
    # Test
    print("Universal Trade Journal System")
    print(f"Journal path: {UNIVERSAL_JOURNAL}")
    print()
    
    # Example log entry
    entry = UniversalJournal.log_entry(
        account_id=62108425,
        server="PepperstoneUK-Demo",
        symbol="EURUSD",
        direction="BUY",
        lot_size=0.2,
        entry_price=1.0850,
        sl=1.0835,
        tp=1.0880,
        strategy="PIN_BAR",
        bot_version="4.0",
        ml_score=75
    )
    print(f"Logged entry: {entry['symbol']} {entry['direction']}")
    
    # Example log exit
    exit_data = UniversalJournal.log_exit(
        position_id=12345,
        account_id=62108425,
        symbol="EURUSD",
        direction="BUY",
        entry_price=1.0850,
        exit_price=1.0880,
        exit_reason="TP",
        pnl=30.0,
        pips=30,
        duration_min=45,
        bot_version="4.0"
    )
    print(f"Logged exit: {exit_data['symbol']} PnL: ${exit_data['pnl']}")
    
    # Get stats
    stats = UniversalJournal.get_stats()
    if stats:
        print(f"\nStats:")
        print(f"  Total trades: {stats['total_trades']}")
        print(f"  Win rate: {stats['win_rate']:.1f}%")
        print(f"  Total PnL: ${stats['total_pnl']:+.2f}")
