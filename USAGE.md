# USAGE.md - Trading System Documentation

## Overview

**THE BEAST 4.0** - Price Action Scalping System (Conservative Mode)
- **Account:** Pepperstone Demo (62108425) on PepperstoneUK-Demo
- **Strategy:** Price Action (Pin Bar, Engulfing, Breakout) + Volume
- **Trading Hours:** 24/7 (session filter disabled)
- **Last Updated:** 2026-03-02

---

## Current Configuration (2026-03-02)

### Account Status
- **Account:** 62108425
- **Server:** PepperstoneUK-Demo
- **Balance:** ~$10,500

### Trading Parameters
```python
LOT_SIZE = 1.0           # Fixed lot size (1.0 lots)
MAX_POSITIONS = 10       # Max 10 concurrent trades
RISK_PER_TRADE = 0.01
```

### Symbols (6 pairs)
```python
SYMBOLS = ["EURUSD", "GBPUSD", "USDJPY", "GBPJPY", "AUDUSD", "EURGBP"]
```

### Strategy Settings
- **Signals:** Pin Bar > Engulfing > Breakout (priority order)
- **Volume Threshold:** Minimum 0.6x average
- **Signal Strength:** Minimum 60+
- **Session:** 24/7 (no time filter - disabled for volatility)

### Risk Management (CRITICAL - Fixed 2026-03-02)
```python
# CONSERVATIVE SCALPING SETTINGS
SL_DISTANCE = min(ATR × 1.0, 10 pips)  # Hard cap at 10 pips
TP_DISTANCE = min(ATR × 1.0, 10 pips)  # Same = 1:1 RR

# Example:
# EURUSD: SL ~10 pips, TP ~10 pips, RR 1:1
# GBPJPY: SL ~10 pips, TP ~10 pips, RR 1:1
```

**CRITICAL FIX (2026-03-02):**
- Previous bug: SL/TP were calculated at 100-200+ pips
- Current fix: Hard limit of 10 pips max for both SL and TP
- This ensures quick scalps with controlled risk

---

## Today's Performance (2026-03-02)

### Summary
| Metric | Value |
|--------|-------|
| Total Entries | ~70+ (high activity day) |
| Total Exits | 41+ |
| Win Rate | 48.8% (20/41) |
| Total PnL | +$53.73 |
| Gross Profit | +$1,091.23 |
| Gross Loss | -$1,037.50 |

### Issues Identified Today
1. **Overtrading:** Too many entries (70+ in one day)
2. **SL/TP Bug:** Some trades had SL/TP at 100+ pips (FIXED)
3. **Contra-trend trades:** Bot traded against clear trends on some pairs
4. **Logging gaps:** Some exits not logged correctly (FIXED)

### Best Performing Symbols
- EURUSD: Multiple winning trades
- GBPJPY: High volatility = good scalping opportunities
- AUDUSD: Consistent signals

### Worst Performing Symbols
- EURGBP: Several losses
- Some GBPUSD trades hit SL quickly

---

## Architecture

```
standalone_bot.py (pythonw.exe - runs 24/7)
    |
    +-- the_beast_v4_price_action.py (trading logic)
    |       |
    |       +-- PriceActionAnalyzer (signals)
    |       +-- Conservative Risk Manager (10 pip max SL/TP)
    |       +-- MAE/MFE tracking (every 60s)
    |       |
    |       +-- UniversalJournal.log_entry()  --> universal_trade_journal.jsonl
    |       +-- UniversalJournal.log_exit()   --> universal_trade_journal.jsonl
    |
    +-- Auto-restart on crash
    +-- Lock file prevents duplicates
    +-- Logs: mt5_trader/logs/standalone_bot.log
```

---

## Quick Start

### Start the Bot
```powershell
Start-Process pythonw.exe -ArgumentList "C:\Users\Claw\.openclaw\workspace\mt5_trader\standalone_bot.py"
```

Auto-starts at Windows login via `start_bot.bat` in Startup folder.

### Stop the Bot
```powershell
taskkill /F /IM pythonw.exe
```

### Check if Running
```powershell
tasklist /FI "IMAGENAME eq pythonw.exe"
```

### Check MT5 Status
```powershell
cd mt5_trader
python _check_mt5.py
```

### Check Journal
```powershell
cd mt5_trader
python quick_journal_check.py
```

### Run Analysis
```powershell
cd mt5_trader
python analyze_today.py  # Today's trades only
python full_audit.py     # Complete history
```

---

## Logging System

### Universal Journal
**File:** `universal_trade_journal.jsonl`
**Single source of truth** for all trades.

### ENTRY Fields
```
position_id, symbol, direction, lot_size, entry_price, sl, tp,
strategy, bot_version, ml_score,
sl_pips, tp_pips, rr_planned,  # Now capped at 10 pips / 1:1 RR
```

### EXIT Fields
```
position_id, pnl, pips, exit_reason, duration_min,
mae_pips, mfe_pips, rr_achieved, exit_reason_detail
```

### Key Logging Rules
1. **Every trade** must log ENTRY
2. **Every closed trade** must log EXIT (with PnL)
3. **Position ID** required for matching
4. **No trade** should execute without logging

See `LOGGING_RULES.md` for complete rules.

---

## File Structure

```
mt5_trader/
  |-- standalone_bot.py          # 24/7 runner
  |-- the_beast_v4_price_action.py  # v4.0 - CONSERVATIVE MODE
  |-- universal_journal.py       # UniversalJournal class
  |-- LOGGING_RULES.md           # Absolute rules
  |-- USAGE.md                   # This file
  |
  |-- universal_trade_journal.jsonl  # ALL trades
  |
  |-- full_audit.py              # Complete analysis
  |-- analyze_today.py           # Daily analysis
  |-- check_mt5_history.py       # MT5 history verification
  |-- quick_journal_check.py     # Quick journal check
  |
  |-- logs/
  |     |-- standalone_bot.log   # Runner logs
  |     |-- standalone.lock      # Lock file
```

---

## Monitoring Commands

```powershell
# Is bot running?
tasklist /FI "IMAGENAME eq pythonw.exe"

# Check MT5
cd mt5_trader; python _check_mt5.py

# Today's performance
cd mt5_trader; python analyze_today.py

# Bot logs
Get-Content mt5_trader/logs/standalone_bot.log -Tail 20
```

---

## Known Issues & Fixes

### Fixed (2026-03-02)
1. **SL/TP Calculation Bug** - Fixed with hard 10-pip limit
2. **Exit Logging Bug** - Fixed to log even when deal not found immediately
3. **Session Filter** - Disabled for 24/7 trading

### Pending Review
1. **Overtrading** - 70+ trades in one day is too many
2. **Trend Filter** - Bot sometimes trades against clear trends
3. **Win Rate** - Currently 48.8%, target 55%+

### Recommendations for Tomorrow
1. Add H4 trend filter (trade only with trend)
2. Reduce max positions to 6-8 (from 10)
3. Consider volume filter increase (0.6x → 0.8x)

---

*Last Updated: 2026-03-02*
*Active Bot Version: 4.0 - CONSERVATIVE SCALPING*
*Settings: SL=TP=10 pips, 1:1 RR, 24/7 trading*
