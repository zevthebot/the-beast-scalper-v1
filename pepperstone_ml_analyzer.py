#!/usr/bin/env python3
"""
Pepperstone ML Analyzer
Analyzes trading patterns and generates insights
"""

import json
from pathlib import Path
from datetime import datetime, timedelta
import statistics

JOURNAL_PATH = Path(r"C:\Users\Claw\.openclaw\workspace\mt5_trader\pepperstone_journal.jsonl")
REPORT_PATH = Path(r"C:\Users\Claw\.openclaw\workspace\mt5_trader\pepperstone_ml_report.json")

class PepperstoneMLAnalyzer:
    def __init__(self):
        self.trades = []
        self.load_trades()
    
    def load_trades(self):
        """Load all trades from journal"""
        if not JOURNAL_PATH.exists():
            print("No journal found")
            return
        
        entries = {}
        exits = []
        
        with open(JOURNAL_PATH, 'r') as f:
            for line in f:
                try:
                    event = json.loads(line.strip())
                    if event.get('event') == 'ENTRY':
                        entries[event['position_id']] = event
                    elif event.get('event') == 'EXIT':
                        exits.append(event)
                except:
                    continue
        
        # Match entries with exits
        for exit_event in exits:
            pos_id = exit_event.get('position_id')
            if pos_id in entries:
                entry = entries[pos_id]
                self.trades.append({
                    'position_id': pos_id,
                    'symbol': entry['symbol'],
                    'direction': entry['direction'],
                    'entry_price': entry['entry_price'],
                    'exit_price': exit_event['exit_price'],
                    'entry_time': entry['timestamp'],
                    'exit_time': exit_event['exit_time'],
                    'pnl': exit_event['pnl'],
                    'pips': exit_event['pips'],
                    'duration_min': exit_event['duration_min'],
                    'ml_score': entry.get('ml_score', 50),
                    'rsi': entry.get('rsi'),
                    'adx': entry.get('adx'),
                    'session': entry.get('session'),
                    'trend_5m': entry.get('trend_5m'),
                    'bb_position': entry.get('bb_position'),
                    'volume_ratio': entry.get('volume_ratio')
                })
    
    def analyze(self):
        """Generate comprehensive analysis"""
        if not self.trades:
            print("No completed trades to analyze")
            return
        
        print(f"\n{'='*60}")
        print("PEPPERSTONE ML ANALYSIS REPORT")
        print(f"{'='*60}")
        print(f"Total Trades: {len(self.trades)}")
        
        # Overall performance
        wins = [t for t in self.trades if t['pnl'] > 0]
        losses = [t for t in self.trades if t['pnl'] < 0]
        breakeven = [t for t in self.trades if t['pnl'] == 0]
        
        total_pnl = sum(t['pnl'] for t in self.trades)
        win_rate = len(wins) / len(self.trades) * 100
        
        print(f"\n📊 OVERALL PERFORMANCE")
        print(f"  Wins: {len(wins)} | Losses: {len(losses)} | BE: {len(breakeven)}")
        print(f"  Win Rate: {win_rate:.1f}%")
        print(f"  Total PnL: ${total_pnl:+.2f}")
        print(f"  Avg Win: ${statistics.mean([t['pnl'] for t in wins]):.2f}" if wins else "  Avg Win: N/A")
        print(f"  Avg Loss: ${statistics.mean([t['pnl'] for t in losses]):.2f}" if losses else "  Avg Loss: N/A")
        
        # ML Score Analysis
        print(f"\n🤖 ML SCORE ANALYSIS")
        high_ml = [t for t in self.trades if t['ml_score'] >= 75]
        mid_ml = [t for t in self.trades if 55 <= t['ml_score'] < 75]
        low_ml = [t for t in self.trades if t['ml_score'] < 55]
        
        if high_ml:
            high_wr = len([t for t in high_ml if t['pnl'] > 0]) / len(high_ml) * 100
            print(f"  High ML (75+): {len(high_ml)} trades, {high_wr:.1f}% win rate, ${sum(t['pnl'] for t in high_ml):+.2f}")
        if mid_ml:
            mid_wr = len([t for t in mid_ml if t['pnl'] > 0]) / len(mid_ml) * 100
            print(f"  Mid ML (55-74): {len(mid_ml)} trades, {mid_wr:.1f}% win rate, ${sum(t['pnl'] for t in mid_ml):+.2f}")
        if low_ml:
            low_wr = len([t for t in low_ml if t['pnl'] > 0]) / len(low_ml) * 100
            print(f"  Low ML (<55): {len(low_ml)} trades, {low_wr:.1f}% win rate, ${sum(t['pnl'] for t in low_ml):+.2f}")
        
        # Symbol Analysis
        print(f"\n💱 SYMBOL PERFORMANCE")
        symbol_stats = {}
        for trade in self.trades:
            sym = trade['symbol']
            if sym not in symbol_stats:
                symbol_stats[sym] = {'trades': [], 'pnl': 0, 'wins': 0}
            symbol_stats[sym]['trades'].append(trade)
            symbol_stats[sym]['pnl'] += trade['pnl']
            if trade['pnl'] > 0:
                symbol_stats[sym]['wins'] += 1
        
        for sym, stats in sorted(symbol_stats.items(), key=lambda x: -x[1]['pnl']):
            wr = stats['wins'] / len(stats['trades']) * 100
            print(f"  {sym}: {len(stats['trades'])} trades, {wr:.0f}% WR, ${stats['pnl']:+.2f}")
        
        # Session Analysis
        print(f"\n⏰ SESSION PERFORMANCE")
        session_stats = {}
        for trade in self.trades:
            sess = trade.get('session', 'Unknown')
            if sess not in session_stats:
                session_stats[sess] = {'trades': [], 'pnl': 0, 'wins': 0}
            session_stats[sess]['trades'].append(trade)
            session_stats[sess]['pnl'] += trade['pnl']
            if trade['pnl'] > 0:
                session_stats[sess]['wins'] += 1
        
        for sess, stats in sorted(session_stats.items(), key=lambda x: -x[1]['pnl']):
            wr = stats['wins'] / len(stats['trades']) * 100
            print(f"  {sess}: {len(stats['trades'])} trades, {wr:.0f}% WR, ${stats['pnl']:+.2f}")
        
        # RSI Analysis
        print(f"\n📈 RSI CONDITIONS AT ENTRY")
        low_rsi = [t for t in self.trades if t.get('rsi', 50) < 40]
        mid_rsi = [t for t in self.trades if 40 <= t.get('rsi', 50) <= 60]
        high_rsi = [t for t in self.trades if t.get('rsi', 50) > 60]
        
        if low_rsi:
            wr = len([t for t in low_rsi if t['pnl'] > 0]) / len(low_rsi) * 100
            print(f"  RSI < 40 (oversold): {len(low_rsi)} trades, {wr:.1f}% WR")
        if mid_rsi:
            wr = len([t for t in mid_rsi if t['pnl'] > 0]) / len(mid_rsi) * 100
            print(f"  RSI 40-60 (neutral): {len(mid_rsi)} trades, {wr:.1f}% WR")
        if high_rsi:
            wr = len([t for t in high_rsi if t['pnl'] > 0]) / len(high_rsi) * 100
            print(f"  RSI > 60 (overbought): {len(high_rsi)} trades, {wr:.1f}% WR")
        
        # Duration Analysis
        print(f"\n⏱️ TRADE DURATION")
        short = [t for t in self.trades if t['duration_min'] < 30]
        medium = [t for t in self.trades if 30 <= t['duration_min'] <= 120]
        long = [t for t in self.trades if t['duration_min'] > 120]
        
        if short:
            wr = len([t for t in short if t['pnl'] > 0]) / len(short) * 100
            print(f"  <30 min (scalp): {len(short)} trades, {wr:.1f}% WR")
        if medium:
            wr = len([t for t in medium if t['pnl'] > 0]) / len(medium) * 100
            print(f"  30-120 min: {len(medium)} trades, {wr:.1f}% WR")
        if long:
            wr = len([t for t in long if t['pnl'] > 0]) / len(long) * 100
            print(f"  >120 min (swing): {len(long)} trades, {wr:.1f}% WR")
        
        # Generate recommendations
        print(f"\n🎯 ML RECOMMENDATIONS")
        recommendations = []
        
        # Best symbol
        best_symbol = max(symbol_stats.items(), key=lambda x: x[1]['pnl'])
        if best_symbol[1]['pnl'] > 0:
            recommendations.append(f"Focus on {best_symbol[0]} (best PnL: ${best_symbol[1]['pnl']:+.2f})")
        
        # Best session
        best_session = max(session_stats.items(), key=lambda x: x[1]['pnl'])
        if best_session[1]['pnl'] > 0:
            recommendations.append(f"Trade during {best_session[0]} (best session)")
        
        # ML score threshold
        if high_ml and len([t for t in high_ml if t['pnl'] > 0]) / len(high_ml) > 0.6:
            recommendations.append("Only take trades with ML score 75+")
        elif mid_ml and len([t for t in mid_ml if t['pnl'] > 0]) / len(mid_ml) > 0.55:
            recommendations.append("Minimum ML score 55 for entries")
        
        if not recommendations:
            recommendations.append("Need more data for confident recommendations")
        
        for rec in recommendations:
            print(f"  • {rec}")
        
        print(f"{'='*60}\n")
        
        # Save report
        report = {
            'timestamp': datetime.now().isoformat(),
            'total_trades': len(self.trades),
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'symbol_performance': {k: {
                'trades': len(v['trades']),
                'wins': v['wins'],
                'win_rate': v['wins'] / len(v['trades']) * 100,
                'pnl': v['pnl']
            } for k, v in symbol_stats.items()},
            'session_performance': {k: {
                'trades': len(v['trades']),
                'wins': v['wins'],
                'pnl': v['pnl']
            } for k, v in session_stats.items()},
            'ml_score_effectiveness': {
                'high': {'trades': len(high_ml), 'pnl': sum(t['pnl'] for t in high_ml)} if high_ml else None,
                'mid': {'trades': len(mid_ml), 'pnl': sum(t['pnl'] for t in mid_ml)} if mid_ml else None
            },
            'recommendations': recommendations
        }
        
        with open(REPORT_PATH, 'w') as f:
            json.dump(report, f, indent=2)
        
        return report

if __name__ == "__main__":
    analyzer = PepperstoneMLAnalyzer()
    analyzer.analyze()
