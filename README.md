# THE BEAST 4.0 - Conservative Scalping Bot

## 🎯 Overview

**THE BEAST 4.0** is an automated forex scalping bot designed for aggressive yet controlled short-term trading on the MetaTrader 5 platform.

- **Strategy:** Price Action (Pin Bar, Engulfing, Breakout) + Volume Confirmation
- **Account:** Pepperstone Demo (62108425)
- **Platform:** MetaTrader 5 (PepperstoneUK-Demo)
- **Status:** Active 24/7 via standalone runner

---

## 📅 Important Dates

| Date | Event |
|------|-------|
| **2026-02-27** | Beast 4.0 launched with conservative settings |
| **2026-03-02** | Critical bug fixes (SL/TP calculation, 10-pip hard limit) |
| **2026-03-02** | Session filter removed for 24/7 trading |
| **2026-03-02** | Win rate: 48.8%, Profit: +$53.73 (first test day) |

---

## ⚙️ Strategy Parameters

### Trading Settings
```python
LOT_SIZE = 1.0              # Fixed lot size (1.0 lots per trade)
MAX_POSITIONS = 10          # Maximum concurrent trades
SYMBOLS = [                 # 6 major pairs
    "EURUSD",
    "GBPUSD", 
    "USDJPY",
    "GBPJPY",
    "AUDUSD",
    "EURGBP"
]
```

### Risk Management (CRITICAL)
```python
# CONSERVATIVE SCALPING - Hard limits
SL_DISTANCE = min(ATR × 1.0, 10 pips)   # Max 10 pips stop loss
TP_DISTANCE = min(ATR × 1.0, 10 pips)   # Max 10 pips take profit

# Risk/Reward Ratio: 1:1
# Target: ~10 pips per trade (both directions)
```

**Why 10 pips?**
- Quick scalps (entries/exits within minutes to hours)
- Controlled risk per trade
- High frequency opportunities
- Manageable with 1:1 RR

### Signal Generation
- **Primary Signals:** Pin Bar > Engulfing > Breakout
- **Volume Filter:** Minimum 0.6x average volume
- **Signal Strength:** Minimum 60/100
- **Session:** 24/7 (no time restrictions)

### Entry Conditions
1. Price action pattern detected (Pin Bar, Engulfing, or Breakout)
2. Volume confirmation (>0.6x average)
3. Signal strength >60
4. Less than MAX_POSITIONS open

### Exit Conditions
1. **Take Profit hit** (10 pips) - Primary target
2. **Stop Loss hit** (10 pips) - Risk limit
3. **Manual close** - If needed

---

## 📊 Performance Metrics (2026-03-02)

### Day 1 Results
| Metric | Value |
|--------|-------|
| **Total Trades** | 70+ entries |
| **Win Rate** | 48.8% (20/41 closed trades) |
| **Net Profit** | +$53.73 |
| **Gross Profit** | +$1,091.23 |
| **Gross Loss** | -$1,037.50 |
| **Profit Factor** | 1.05 |

### Analysis
- **Overtrading detected:** 70+ trades in one day is excessive
- **SL/TP Bug fixed:** Originally calculated 100-200+ pips, now capped at 10
- **Contra-trend trades:** Bot traded against clear trends on some pairs
- **Best performers:** EURUSD, GBPJPY, AUDUSD
- **Worst performers:** EURGBP, some GBPUSD trades

---

## 🐛 Known Issues & Fixes

### Fixed (2026-03-02)
1. **SL/TP Calculation Bug**
   - **Problem:** SL/TP calculated at 100-200+ pips due to ATR volatility
   - **Fix:** Hard limit of 10 pips maximum for both SL and TP
   - **Impact:** Trades now close within minutes instead of never hitting targets

2. **Exit Logging Bug**
   - **Problem:** Some exits not logged in universal journal
   - **Fix:** Fallback mechanism using SL/TP prices when history_deals_get() fails
   - **Impact:** All trades now properly tracked

3. **Session Filter**
   - **Problem:** Bot only traded 09:00-17:00 UTC
   - **Fix:** Disabled for 24/7 trading
   - **Impact:** More opportunities, especially during volatility

### Pending Review
1. **Overtrading** - Consider reducing max trades per day
2. **Trend Filter** - Add H4 trend direction filter
3. **Volume Threshold** - May increase from 0.6x to 0.8x

---

## 🚀 Quick Start

### Start the Bot
```powershell
Start-Process pythonw.exe -ArgumentList "C:\Users\Claw\.openclaw\workspace\mt5_trader\standalone_bot.py"
```

### Stop the Bot
```powershell
taskkill /F /IM pythonw.exe
```

### Check Status
```powershell
# Is bot running?
tasklist /FI "IMAGENAME eq pythonw.exe"

# Check positions
cd mt5_trader
python _check_beast.py

# Analyze today's performance
python analyze_today.py
```

---

## 📁 File Structure

```
mt5_trader/
├── Core Files
│   ├── standalone_bot.py              # 24/7 runner (use this to start)
│   ├── the_beast_v4_price_action.py   # Main trading logic
│   └── universal_journal.py           # Logging system
│
├── Configuration
│   ├── USAGE.md                       # This file
│   ├── LOGGING_RULES.md               # Absolute logging rules
│   └── BOT_STATUS_SNAPSHOT.md         # Current status
│
├── Analysis Tools
│   ├── analyze_today.py               # Daily performance
│   ├── full_audit.py                  # Complete history
│   ├── beast_live_check.py            # Live monitoring
│   └── quick_journal_check.py         # Quick journal view
│
└── Data
    └── universal_trade_journal.jsonl  # All trades (single source of truth)
```

---

## 📝 Logging System

### Universal Journal
**File:** `universal_trade_journal.jsonl`

Every trade is logged with:
- Entry timestamp, symbol, direction, price
- SL/TP distances (now capped at 10 pips)
- Position ID for matching
- Exit data (PnL, pips, duration, reason)

### Critical Logging Rules
1. **Every entry** must be logged before execution
2. **Every exit** must be logged with actual PnL
3. **Position ID** required for entry-exit matching
4. **No trade** executes without logging

See `LOGGING_RULES.md` for complete rules.

---

## 🎓 Strategy Philosophy

### Conservative Scalping
- **Quick entries/exits** (minutes to hours)
- **Small, consistent profits** (10 pips target)
- **Controlled risk** (1:1 RR, max 10 pips loss)
- **High frequency** (many small trades vs few large ones)

### Why This Works
1. **10 pips is achievable** - Markets move 10 pips constantly
2. **1:1 RR is realistic** - Don't need 70% win rate to be profitable
3. **Quick feedback** - Know if trade works within minutes
4. **Compounding** - Small profits add up over time

### Target Performance
- **Win Rate:** 55%+ (currently 48.8%)
- **Avg Trade:** +$10-15 profit (1.0 lot)
- **Daily Trades:** 20-30 (not 70+)
- **Daily Profit:** +$200-300 target

---

## 🔧 Development History

### Version 4.0 (2026-03-02)
- Conservative scalping mode
- 10-pip hard limit for SL/TP
- 24/7 trading enabled
- Fixed logging bugs
- 1:1 RR strategy

### Previous Versions
- v3.0: ML-enhanced (pepperstone_ml_trader.py)
- v2.0: Price action + volume
- v1.0: Basic EMA crossover

---

## ⚠️ Risk Warning

**Forex trading carries significant risk:**
- Past performance does not guarantee future results
- Demo account results may differ from live trading
- Always test thoroughly before using real money
- Never risk more than you can afford to lose

**Current Status:** DEMO ACCOUNT ONLY - Not tested on live funds.

---

## 📞 Support & Monitoring

### Automated Monitoring
- Bot logs every 60 seconds to `standalone_bot.log`
- All trades logged to `universal_trade_journal.jsonl`
- Auto-restart on crash with exponential backoff

### Manual Checks
```powershell
# View live bot status
python beast_live_check.py

# View today's trades
python analyze_today.py

# View last 20 log entries
Get-Content logs/standalone_bot.log -Tail 20
```

---

## 🎯 Next Steps

1. **Continue testing** with current settings (10 pip SL/TP, 1:1 RR)
2. **Collect 3-5 days** of data for statistical significance
3. **Review results** - Target 55%+ win rate
4. **Optimize** - Add trend filter if needed
5. **Scale** - Consider live account if demo profitable

---

**Last Updated:** 2026-03-02  
**Active Version:** 4.0 - Conservative Scalping  
**Status:** Testing Phase (Demo)
