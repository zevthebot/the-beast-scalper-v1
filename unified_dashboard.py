#!/usr/bin/env python3
"""
Unified Trading Dashboard
Shows FTMO + Pepperstone performance side by side
"""

import json
from pathlib import Path
from datetime import datetime, timedelta

FTMO_JOURNAL = Path(r"C:\Users\Claw\.openclaw\workspace\mt5_trader\trade_journal_v2.jsonl")
PEPPERSTONE_JOURNAL = Path(r"C:\Users\Claw\.openclaw\workspace\mt5_trader\pepperstone_journal.jsonl")

class UnifiedDashboard:
    def __init__(self):
        self.ftmo_trades = []
        self.pepperstone_trades = []
        self.load_data()
    
    def load_data(self):
        # Load FTMO trades
        if FTMO_JOURNAL.exists():
            with open(FTMO_JOURNAL, 'r') as f:
                for line in f:
                    try:
                        event = json.loads(line.strip())
                        if event.get('event') == 'EXIT' and event.get('pnl') is not None:
                            self.ftmo_trades.append({
                                'account': 'FTMO',
                                'symbol': event['symbol'],
                                'pnl': event['pnl'],
                                'result': 'WIN' if event['pnl'] > 0 else 'LOSS'
                            })
                        elif event.get('status') == 'CLOSED' and event.get('pnl') is not None:
                            self.ftmo_trades.append({
                                'account': 'FTMO',
                                'symbol': event['symbol'],
                                'pnl': event['pnl'],
                                'result': 'WIN' if event['pnl'] > 0 else 'LOSS'
                            })
                    except:
                        continue
        
        # Load Pepperstone trades
        if PEPPERSTONE_JOURNAL.exists():
            with open(PEPPERSTONE_JOURNAL, 'r') as f:
                for line in f:
                    try:
                        event = json.loads(line.strip())
                        if event.get('event') == 'EXIT' and event.get('pnl') is not None:
                            self.pepperstone_trades.append({
                                'account': 'Pepperstone',
                                'symbol': event['symbol'],
                                'pnl': event['pnl'],
                                'result': 'WIN' if event['pnl'] > 0 else 'LOSS'
                            })
                    except:
                        continue
    
    def display(self):
        print(f"\n{'='*70}")
        print("           UNIFIED TRADING DASHBOARD")
        print(f"{'='*70}")
        
        # FTMO Stats
        ftmo_wins = len([t for t in self.ftmo_trades if t['result'] == 'WIN'])
        ftmo_total = len(self.ftmo_trades)
        ftmo_pnl = sum(t['pnl'] for t in self.ftmo_trades)
        ftmo_wr = ftmo_wins / ftmo_total * 100 if ftmo_total > 0 else 0
        
        # Pepperstone Stats
        ps_wins = len([t for t in self.pepperstone_trades if t['result'] == 'WIN'])
        ps_total = len(self.pepperstone_trades)
        ps_pnl = sum(t['pnl'] for t in self.pepperstone_trades)
        ps_wr = ps_wins / ps_total * 100 if ps_total > 0 else 0
        
        # Combined Stats
        total_trades = ftmo_total + ps_total
        total_wins = ftmo_wins + ps_wins
        total_pnl = ftmo_pnl + ps_pnl
        combined_wr = total_wins / total_trades * 100 if total_trades > 0 else 0
        
        print(f"\n[ACCOUNT COMPARISON]")
        print(f"{'-'*70}")
        print(f"{'Account':<15} {'Trades':<10} {'Win Rate':<12} {'PnL':<15}")
        print(f"{'-'*70}")
        print(f"{'FTMO':<15} {ftmo_total:<10} {ftmo_wr:>6.1f}%{'':<5} ${ftmo_pnl:>+8.2f}")
        print(f"{'Pepperstone':<15} {ps_total:<10} {ps_wr:>6.1f}%{'':<5} ${ps_pnl:>+8.2f}")
        print(f"{'-'*70}")
        print(f"{'TOTAL':<15} {total_trades:<10} {combined_wr:>6.1f}%{'':<5} ${total_pnl:>+8.2f}")
        print(f"{'='*70}")
        
        # Symbol breakdown by account
        print(f"\n[SYMBOL PERFORMANCE BY ACCOUNT]")
        print(f"{'-'*70}")
        
        ftmo_symbols = {}
        for t in self.ftmo_trades:
            sym = t['symbol']
            if sym not in ftmo_symbols:
                ftmo_symbols[sym] = {'trades': 0, 'pnl': 0}
            ftmo_symbols[sym]['trades'] += 1
            ftmo_symbols[sym]['pnl'] += t['pnl']
        
        ps_symbols = {}
        for t in self.pepperstone_trades:
            sym = t['symbol']
            if sym not in ps_symbols:
                ps_symbols[sym] = {'trades': 0, 'pnl': 0}
            ps_symbols[sym]['trades'] += 1
            ps_symbols[sym]['pnl'] += t['pnl']
        
        all_symbols = set(list(ftmo_symbols.keys()) + list(ps_symbols.keys()))
        
        print(f"{'Symbol':<10} {'FTMO Trades':<12} {'FTMO PnL':<12} {'PS Trades':<12} {'PS PnL':<12}")
        print(f"{'-'*70}")
        for sym in sorted(all_symbols):
            ft = ftmo_symbols.get(sym, {'trades': 0, 'pnl': 0})
            ps = ps_symbols.get(sym, {'trades': 0, 'pnl': 0})
            print(f"{sym:<10} {ft['trades']:<12} ${ft['pnl']:<+11.2f} {ps['trades']:<12} ${ps['pnl']:<+11.2f}")
        
        print(f"{'='*70}")
        
        # ML Insights for Pepperstone
        if ps_total > 0:
            print(f"\n[PEPPERSTONE ML INSIGHTS]")
            print(f"{'-'*70}")
            print(f"Pepperstone uses ML-enhanced scoring (0-100) for signal quality")
            print(f"Current ML state tracks:")
            print(f"  * Symbol performance (adapts to best pairs)")
            print(f"  * Session performance (best times to trade)")
            print(f"  * RSI thresholds (optimizes entry conditions)")
            print(f"  * Auto-optimizes every 20 trades")
            
            # Try to load ML state
            ml_state_path = Path(r"C:\Users\Claw\.openclaw\workspace\mt5_trader\pepperstone_ml_state.json")
            if ml_state_path.exists():
                with open(ml_state_path, 'r') as f:
                    ml_state = json.load(f)
                print(f"\n  ML Stats:")
                print(f"    Trades analyzed: {ml_state.get('trade_count', 0)}")
                print(f"    Current win rate: {ml_state.get('win_count', 0)/max(ml_state.get('trade_count', 1), 1)*100:.1f}%")
                print(f"    Total PnL from ML: ${ml_state.get('total_pnl', 0):+.2f}")
                if ml_state.get('last_optimized'):
                    print(f"    Last optimized: {ml_state['last_optimized'][:19]}")
        
        print(f"\n{'='*70}")
        print(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*70}\n")

if __name__ == "__main__":
    dashboard = UnifiedDashboard()
    dashboard.display()
