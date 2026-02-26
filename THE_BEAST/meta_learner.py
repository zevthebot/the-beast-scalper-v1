#!/usr/bin/env python3
"""
The Beast Meta-Learner
Analyzes trade performance every 50 trades and auto-adjusts strategy weights
"""

import json
import os
from datetime import datetime
from pathlib import Path
import statistics

# Paths
JOURNAL_FILE = Path(r"C:\Users\Claw\.openclaw\workspace\mt5_trader\trade_journal_v2.jsonl")
ANALYSIS_FILE = Path(r"C:\Users\Claw\.openclaw\workspace\mt5_trader\THE_BEAST\strategy_analysis.json")
CONFIG_FILE = Path(r"C:\Users\Claw\.openclaw\workspace\mt5_trader\THE_BEAST\strategy_weights.py")

class TradeAnalyzer:
    def __init__(self):
        self.trades = []
        self.analysis = {
            'last_trade_count': 0,
            'total_trades_analyzed': 0,
            'strategies': {},
            'last_updated': None
        }
        
    def load_trades(self):
        """Load all completed trades from journal"""
        if not JOURNAL_FILE.exists():
            return []
        
        trades = []
        try:
            with open(JOURNAL_FILE, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                        # Only analyze completed trades (status: CLOSED from v2 journal)
                        if entry.get('status') == 'CLOSED' or entry.get('event') == 'EXIT':
                            trades.append(entry)
                    except:
                        continue
        except Exception as e:
            print(f"[ERROR] Loading trades: {e}")
        
        return trades
    
    def analyze_by_strategy(self, trades):
        """Analyze performance by strategy"""
        strategies = {}
        
        for trade in trades:
            strat = trade.get('strategy', 'UNKNOWN')
            
            if strat not in strategies:
                strategies[strat] = {
                    'trades': [],
                    'wins': 0,
                    'losses': 0,
                    'total_pnl': 0,
                    'confidences': [],
                    'avg_profit': 0,
                    'avg_loss': 0,
                    'win_rate': 0
                }
            
            pnl = trade.get('pnl', 0)
            confidence = trade.get('confidence', 0)
            
            strategies[strat]['trades'].append(trade)
            strategies[strat]['total_pnl'] += pnl
            strategies[strat]['confidences'].append(confidence)
            
            if pnl > 0:
                strategies[strat]['wins'] += 1
            elif pnl < 0:
                strategies[strat]['losses'] += 1
        
        # Calculate metrics
        for strat, data in strategies.items():
            total = len(data['trades'])
            if total > 0:
                data['win_rate'] = (data['wins'] / total) * 100
                valid_confidences = [c for c in data['confidences'] if c is not None]
                data['avg_confidence'] = statistics.mean(valid_confidences) if valid_confidences else 0
                
                profits = [t.get('pnl', 0) for t in data['trades'] if t.get('pnl', 0) > 0]
                losses = [t.get('pnl', 0) for t in data['trades'] if t.get('pnl', 0) < 0]
                
                data['avg_profit'] = statistics.mean(profits) if profits else 0
                data['avg_loss'] = statistics.mean(losses) if losses else 0
                data['profit_factor'] = abs(sum(profits) / sum(losses)) if losses and sum(losses) != 0 else float('inf')
        
        return strategies
    
    def generate_recommendations(self, strategies):
        """Generate strategy adjustments based on performance"""
        recommendations = []
        weights = {}
        
        for strat, data in strategies.items():
            win_rate = data['win_rate']
            total_pnl = data['total_pnl']
            trade_count = len(data['trades'])
            
            # Minimum sample size: 5 trades
            if trade_count < 5:
                weights[strat] = 'DEFAULT'  # Keep as-is
                recommendations.append(f"{strat}: Insufficient data ({trade_count} trades), keeping defaults")
                continue
            
            # High performer: >60% win rate AND positive PnL
            if win_rate >= 60 and total_pnl > 0:
                weights[strat] = 'INCREASE'
                recommendations.append(f"{strat}: STRONG - {win_rate:.1f}% win rate, +${total_pnl:.2f}. Increase priority!")
            
            # Medium performer: 45-60% win rate
            elif win_rate >= 45 and total_pnl >= 0:
                weights[strat] = 'KEEP'
                recommendations.append(f"{strat}: DECENT - {win_rate:.1f}% win rate, +${total_pnl:.2f}. Keep current.")
            
            # Poor performer: <45% win rate OR negative PnL
            else:
                weights[strat] = 'DECREASE'
                recommendations.append(f"{strat}: WEAK - {win_rate:.1f}% win rate, ${total_pnl:.2f}. Decrease priority/raise min confidence.")
        
        return recommendations, weights
    
    def update_strategy_config(self, weights):
        """Generate new strategy configuration based on analysis"""
        # Priority mapping: Higher number = higher priority
        priority_adjustments = {
            'INCREASE': +1,   # Bump up priority
            'KEEP': 0,        # No change
            'DECREASE': -1,   # Lower priority
            'DEFAULT': 0
        }
        
        # Base priorities
        base_priorities = {
            'FVG': 4,
            'BREAKOUT': 3,
            'RANGE': 2,
            'TREND': 1
        }
        
        # Confidence adjustments
        confidence_adjustments = {
            'INCREASE': -5,   # Lower threshold (easier to enter)
            'KEEP': 0,
            'DECREASE': +10,  # Raise threshold (harder to enter)
            'DEFAULT': 0
        }
        
        config = {
            'generated_at': datetime.now().isoformat(),
            'strategies': {}
        }
        
        for strat, weight in weights.items():
            if strat in base_priorities:
                config['strategies'][strat] = {
                    'priority': max(1, min(5, base_priorities[strat] + priority_adjustments[weight])),
                    'min_confidence_adjust': confidence_adjustments[weight],
                    'status': weight
                }
        
        return config
    
    def run_analysis(self):
        """Main analysis routine"""
        print("=" * 60)
        print("THE BEAST META-LEARNER")
        print("=" * 60)
        
        # Load trades
        trades = self.load_trades()
        total_trades = len(trades)
        
        print(f"\nTotal completed trades: {total_trades}")
        
        # Check if we have 50 new trades since last analysis
        last_count = 0
        if ANALYSIS_FILE.exists():
            try:
                with open(ANALYSIS_FILE, 'r') as f:
                    old_analysis = json.load(f)
                    last_count = old_analysis.get('total_trades_analyzed', 0)
            except:
                pass
        
        new_trades = total_trades - last_count
        print(f"New trades since last analysis: {new_trades}")
        
        if new_trades < 50:
            print(f"\n[SKIP] Only {new_trades} new trades. Analysis runs every 50 trades.")
            return False
        
        # Analyze
        print("\nAnalyzing performance by strategy...")
        strategies = self.analyze_by_strategy(trades)
        
        if not strategies:
            print("[WARNING] No strategy data found")
            return False
        
        # Generate recommendations
        recommendations, weights = self.generate_recommendations(strategies)
        
        # Create config
        config = self.update_strategy_config(weights)
        
        # Save analysis
        analysis = {
            'timestamp': datetime.now().isoformat(),
            'total_trades_analyzed': total_trades,
            'new_trades': new_trades,
            'strategies': strategies,
            'recommendations': recommendations,
            'config': config
        }
        
        try:
            with open(ANALYSIS_FILE, 'w') as f:
                json.dump(analysis, f, indent=2)
            print(f"\n[OK] Analysis saved to: {ANALYSIS_FILE}")
        except Exception as e:
            print(f"[ERROR] Saving analysis: {e}")
        
        # Print report
        print("\n" + "=" * 60)
        print("ANALYSIS REPORT")
        print("=" * 60)
        
        for strat, data in strategies.items():
            print(f"\n{strat}:")
            print(f"  Trades: {len(data['trades'])}")
            print(f"  Win Rate: {data['win_rate']:.1f}%")
            print(f"  Total PnL: ${data['total_pnl']:.2f}")
            print(f"  Avg Confidence: {data.get('avg_confidence', 0):.1f}%")
            if data['avg_profit']:
                print(f"  Avg Win: +${data['avg_profit']:.2f}")
            if data['avg_loss']:
                print(f"  Avg Loss: ${data['avg_loss']:.2f}")
        
        print("\n" + "=" * 60)
        print("RECOMMENDATIONS")
        print("=" * 60)
        for rec in recommendations:
            print(f"  • {rec}")
        
        print("\n" + "=" * 60)
        print("CONFIG UPDATES")
        print("=" * 60)
        for strat, cfg in config['strategies'].items():
            print(f"  {strat}: Priority {cfg['priority']} | Conf adjust {cfg['min_confidence_adjust']:+.0f}% | {cfg['status']}")
        
        return True

if __name__ == "__main__":
    analyzer = TradeAnalyzer()
    analyzer.run_analysis()
