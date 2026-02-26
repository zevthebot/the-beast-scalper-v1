# USAGE.md - THE BEAST 4.1 OPTIMIZED

## Overview

THE BEAST is a precision trading system optimized for passing prop firm challenges (FTMO, etc.). Version 4.1 focuses on maximum quality over quantity with strict filters and superior risk-reward ratios.

**Core Philosophy:** Fewer, higher-quality trades with exceptional R:R ratio (1:2.5)

---

## Quick Start

### Start THE BEAST 4.1
```powershell
cd mt5_trader
python thebeast_v4_1.py
```

### Check Status
```powershell
python beast_dashboard.py
```

### View Universal Journal
```powershell
Get-Content universal_trade_journal.jsonl -Tail 10
```

---

## System Components

### 1. thebeast_v4_1.py
**Main trading bot - THE BEAST 4.1 OPTIMIZED**

- Connects to your trading account (FTMO/Prop Firm ready)
- Scans 6 premium pairs every scan interval
- Multi-strategy signal detection
- Strict session filtering (09:00-17:00 UTC only)
- Universal journal logging

**Features:**
- 6 Major Pairs Only: EURUSD, GBPUSD, USDJPY, EURJPY, GBPJPY, XAUUSD
- London + NY Core Session: 09:00-17:00 UTC strict filter
- Volume Confirmation: 1.8x average threshold
- Risk-Reward: 1:2.5 ratio (TP ~25 pips, SL ~10 pips)
- Fixed Lot Size: 0.2 (no variable sizing complications)
- Multi-strategy approach: Trend > Breakout > Reversal
- Correlation filtering (max 1 position per correlated group)

**Lot Size:**
- Fixed: 0.2 lots (all pairs including XAUUSD)

---

### 2. beast_dashboard.py
**Real-time status dashboard**

Shows:
- Current open positions
- Session status (active/inactive)
- Daily/weekly statistics
- Symbol performance breakdown
- Recent trade history
- Universal journal health

---

### 3. beast_analyzer.py
**Performance analysis and reporting**

Run manually to see:
- Win rate and PnL statistics
- Strategy effectiveness breakdown
- Best/worst performing pairs
- Session-based performance
- Risk analysis (drawdown, R:R achieved)
- Trade duration insights

**Output:**
- Console report
- JSON report saved to `beast_analysis_report.json`

---

## Data Files

### universal_trade_journal.jsonl
**CENTRALIZED TRADE LOG - All trades across all sessions**

Contains:
- ENTRY events: Full context (symbol, price, strategy, session, indicators)
- EXIT events: Results, PnL, duration, exit reason, R:R achieved
- Universal format for cross-account analysis

Format:
```json
{"event": "ENTRY", "position_id": 12345, "symbol": "EURUSD", "strategy": "TREND", "timestamp": "2026-02-26T14:30:00Z", ...}
{"event": "EXIT", "position_id": 12345, "pnl": 50.00, "exit_reason": "TP_HIT", ...}
```

**Location:** `mt5_trader/universal_trade_journal.jsonl`

**Purpose:** Single source of truth for all trading activity. Survives account resets (FTMO phases, prop firm migrations).

---

## How THE BEAST 4.1 Works

### Trading Hours (Strict)

**Active Session:** 09:00 - 17:00 UTC ONLY
- London Core: 09:00-12:00 UTC
- London/NY Overlap: 12:00-17:00 UTC (highest priority)

Outside these hours: No new positions opened. Existing positions managed by SL/TP.

### Symbol Selection (6 Pairs Only)

**Majors:**
- EURUSD - Primary focus (best liquidity)
- GBPUSD - Secondary (good volatility)
- USDJPY - Asian bridge

**Crosses:**
- EURJPY - Volatility + trend
- GBPJPY - Higher volatility (filtered carefully)

**Commodity:**
- XAUUSD (Gold) - Trend diversification

*Why only 6?* Maximum focus on quality setups. Each pair thoroughly analyzed.

### Volume Filter

**Minimum Volume:** 1.8x 20-period average
- Ensures genuine market interest
- Avoids low-liquidity false signals
- Reduces spread impact

### Signal Detection (Multi-Strategy)

**Strategy Priority (highest to lowest):**

1. **TREND** (Priority 1)
   - EMA alignment (fast > medium > slow)
   - Pullback to EMA 8
   - ADX > 25 for trend strength
   
2. **BREAKOUT** (Priority 2)
   - 20-period high/low breach
   - Volume confirmation (1.8x)
   - Momentum alignment
   
3. **REVERSAL** (Priority 3)
   - RSI extreme (>70 or <30)
   - Support/resistance test
   - Candlestick confirmation

### Risk Management

**Per Trade:**
- Stop Loss: ~10 pips (technical-based, not arbitrary)
- Take Profit: ~25 pips (2.5x SL)
- Risk-Reward: 1:2.5 minimum

**Account Protection:**
- Max positions: 3 (strict)
- Correlation filter: Max 1 position per group
  - Group A: EURUSD, EURJPY, EURGBP (if enabled)
  - Group B: GBPUSD, GBPJPY
  - Group C: USDJPY
  - Group D: XAUUSD
- Daily loss limit respected (prop firm compliance)

### Correlation Management

Prevents over-exposure to single currency:
- EUR group: Only 1 position at a time
- GBP group: Only 1 position at a time
- JPY exposure limited across pairs

---

## Configuration

Edit these values in `thebeast_v4_1.py`:

```python
# Trading Schedule (UTC)
SESSION_START = "09:00"      # London open + 1 hour
SESSION_END = "17:00"        # NY open overlap ends

# Symbols (6 pairs only - DO NOT EXPAND)
SYMBOLS = [
    "EURUSD",
    "GBPUSD", 
    "USDJPY",
    "EURJPY",
    "GBPJPY",
    "XAUUSD"
]

# Risk Settings
FIXED_LOT_SIZE = 0.2         # Fixed lots - no variable sizing
MAX_POSITIONS = 3            # Max concurrent trades
SL_PIPS = 10                 # Base SL (may adjust technically)
TP_PIPS = 25                 # Target TP (2.5x SL)
MIN_VOLUME_RATIO = 1.8       # 1.8x average volume required

# Strategy Thresholds
MIN_ADX_TREND = 25           # Trend strength threshold
RSI_OVERBOUGHT = 70          # Reversal short threshold
RSI_OVERSOLD = 30            # Reversal long threshold
```

**Important:** Do not modify pair list, session times, or volume threshold without understanding the impact on win rate and R:R.

---

## Monitoring Commands

### Check Bot is Running
```powershell
tasklist | findstr python
```

### View Recent Trades
```powershell
Get-Content universal_trade_journal.jsonl -Tail 10
```

### View Today's Activity
```powershell
python beast_dashboard.py
```

### Check MT5 Connection
```powershell
tasklist | findstr terminal64
```

### Analyze Performance
```powershell
python beast_analyzer.py
```

---

## Performance Targets

**Version 4.1 Targets:**
- Win Rate: 45-55% (acceptable with 1:2.5 R:R)
- Profit Factor: >2.0
- Average R:R: 2.0+ (target 2.5)
- Max Drawdown: <5% daily

**Quality Metrics:**
- Trade frequency: 1-3 per session (quality > quantity)
- Volume rejection rate: ~40% (good - strict filtering)
- Session win rate: Higher during 12:00-17:00 UTC

**Break-even Analysis:**
- At 40% win rate with 1:2.5 R:R → Profitable
- At 50% win rate with 1:2.5 R:R → Strong profit
- Focus on execution quality, not win rate alone

---

## Troubleshooting

### Bot Not Trading
1. Check UTC time: ```[DateTime]::UtcNow.ToString("HH:mm")```
   - Must be between 09:00-17:00 UTC
2. Verify MT5 is running: ```tasklist | findstr terminal64```
3. Check volume conditions - 1.8x threshold is strict
4. Review journal for signals that didn't qualify

### Too Few Trades
- This is by design in V4.1
- Expected: 1-3 trades per 8-hour session
- If zero trades for multiple sessions: Check MT5 data feed, volume settings

### Lot Size Not Applied
- V4.1 uses FIXED_LOT_SIZE = 0.2 always
- No ML-based or confidence-based sizing
- Override in code if account size requires adjustment

### Universal Journal Not Updating
- Verify write permissions: ```Test-Path universal_trade_journal.jsonl```
- Check disk space
- Review Python console for errors

---

## Stopping the Bot

**Graceful Stop:**
1. Press `Ctrl+C` in terminal
2. Bot completes current cycle, closes positions (if configured)
3. Positions remain managed by SL/TP

**Force Stop:**
```powershell
taskkill /F /IM python.exe
```

**Emergency Close All Positions:**
```python
# In MT5 or via MT5 terminal
Close all manual/EA positions immediately
```

---

## Universal Journal