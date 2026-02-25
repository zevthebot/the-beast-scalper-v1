# USAGE_ML.md - Pepperstone ML Trading System

## Overview

Machine Learning-enhanced scalping system for Pepperstone Demo account (62108425). The system learns from trade performance and auto-optimizes strategy parameters.

---

## Quick Start

### Start the ML Bot
```powershell
cd mt5_trader
python pepperstone_ml_trader.py
```

### Check Status
```powershell
python unified_dashboard.py
```

### View ML Analysis
```powershell
python pepperstone_ml_analyzer.py
```

---

## System Components

### 1. pepperstone_ml_trader.py
**Main trading bot with ML capabilities**

- Connects to Pepperstone Demo (62108425)
- Scans 10 pairs every 60 seconds
- Scores signals 0-100 using ML
- Auto-optimizes every 20 trades
- Logs rich data for analysis

**Features:**
- EMA 3/8 crossover signals
- RSI, ADX, Bollinger Bands analysis
- Volume confirmation
- Session-based filtering
- Dynamic lot sizing based on ML confidence

**Lot Size Rules:**
- Base lot: 0.3 (all pairs except XAUUSD)
- XAUUSD base lot: 0.1 (gold is more volatile/expensive)
- ML Score 80+: 1.5x base lot
- ML Score 60-79: 1.0x base lot
- ML Score <60: 0.5x base lot or skip

---

### 2. pepperstone_ml_analyzer.py
**Generates ML performance reports**

Run manually to see:
- Overall win rate and PnL
- ML Score effectiveness (does high score = more wins?)
- Best/worst performing symbols
- Best trading sessions
- RSI condition analysis
- Trade duration insights
- Auto-generated recommendations

**Output:**
- Console report
- JSON report saved to `pepperstone_ml_report.json`

---

### 3. unified_dashboard.py
**View all accounts in one place**

Shows:
- FTMO performance (if active)
- Pepperstone performance
- Combined statistics
- Symbol breakdown by account
- ML insights (if Pepperstone active)

---

## Data Files

### pepperstone_journal.jsonl
**Complete trade history with ML features**

Contains:
- ENTRY events: Full technical context (RSI, ADX, EMA, BB, volume, trend)
- EXIT events: Results, PnL, duration, exit reason
- ML features at entry time

Format:
```json
{"event": "ENTRY", "position_id": 12345, "symbol": "EURUSD", ...}
{"event": "EXIT", "position_id": 12345, "pnl": 25.50, ...}
```

### pepperstone_ml_state.json
**ML optimizer state**

Tracks:
- Total trades analyzed
- Win/loss counts
- Symbol performance
- Session performance
- RSI bucket performance
- Current optimized parameters

---

## How ML Works

### Signal Scoring (0-100)

Base score: 50

**Additions:**
- RSI in optimal range: +15
- ADX > threshold: +10
- Volume above average: +10
- Symbol has good history (>60% WR): +15
- Good session performance (>55% WR): +10

**Deductions:**
- RSI outside range: -20
- Poor symbol history (<40% WR): -15
- Poor session performance (<45% WR): -10

### Auto-Optimization

Every 20 trades, the system adjusts:

1. **RSI Thresholds**
   - If low RSI trades (<40) perform poorly: raise min RSI
   - If high RSI trades (>60) perform poorly: lower max RSI

2. **Symbol Priority**
   - Tracks win rate per symbol
   - Gives bonus/penalty based on history

3. **Session Filtering**
   - Tracks win rate per session
   - Adjusts scoring based on performance

4. **Parameter State**
   ```json
   {
     "min_rsi": 30,
     "max_rsi": 70,
     "min_adx": 20,
     "min_volume_ratio": 0.8
   }
   ```

---

## Monitoring Commands

### Check Bot is Running
```powershell
tasklist | findstr python
```

### View Recent Trades
```powershell
Get-Content pepperstone_journal.jsonl -Tail 5
```

### View ML State
```powershell
Get-Content pepperstone_ml_state.json | ConvertFrom-Json
```

### Check MT5 Connection
```powershell
tasklist | findstr terminal64
```

---

## Troubleshooting

### Bot Not Trading
1. Check MT5 is running: `tasklist | findstr terminal64`
2. Verify account connected in MT5
3. Check journal for errors: `Get-Content pepperstone_journal.jsonl -Tail 10`
4. Ensure market is open (London/NY session)

### No ML State File
- State creates after first trade closes
- Normal for first few trades

### Poor Performance
1. Run analyzer: `python pepperstone_ml_analyzer.py`
2. Check recommendations
3. Wait for 20+ trades for ML to optimize
4. Review which symbols/sessions work best

---

## Configuration

Edit these values in `pepperstone_ml_trader.py`:

```python
# Risk Settings
MAX_POSITIONS = 5        # Max concurrent trades
SL_PIPS = 10             # Stop loss distance
TP_PIPS = 15             # Take profit distance (1:1.5 R:R)
LOT_SIZE = 0.1           # Base lot size

# Symbols to Trade
SYMBOLS = [
    "EURUSD", "GBPUSD", "USDJPY", 
    "EURJPY", "GBPJPY", "AUDUSD",
    "EURGBP", "XAUUSD", "USDCHF",
    "AUDJPY"
]
```

---

## Performance Targets

**Good Performance:**
- Win Rate: >50%
- Profit Factor: >1.5
- ML Score 80+ hit rate: >65%

**Optimization Milestones:**
- 20 trades: First auto-optimization
- 50 trades: Reliable symbol rankings
- 100 trades: Mature ML model

---

## Stopping the Bot

**Graceful Stop:**
1. Press `Ctrl+C` in terminal (waits for current cycle)
2. Bot will finish current scan then exit
3. Positions remain open (managed by SL/TP)

**Force Stop:**
```powershell
taskkill /F /IM python.exe
```

---

## Integration with Main System

The Pepperstone ML journal (`pepperstone_journal.jsonl`) can be merged with FTMO data for cross-account analysis using `unified_dashboard.py`.

**Key Differences:**
- FTMO: Swing/day trading, lower frequency
- Pepperstone ML: Scalping, high frequency, ML-optimized

---

*Last Updated: 2026-02-25*
*System Version: 3.0 ML*
