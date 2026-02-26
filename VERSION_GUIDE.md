# THE BEAST - VERSION COMPARISON GUIDE

## 📊 Overview

| Version | Style | Timeframe | Best For | Status |
|---------|-------|-----------|----------|--------|
| **1.0 Swing** | Swing Trading | M15 | Longer holds, fewer trades | ✅ Stable |
| **2.0 Day Trading** | Day Trading | M5 | Quick entries/exits, more data | 🔄 Current |

---

## 🐂 THE BEAST 1.0 - SWING TRADING (Original)

**File:** `the_beast_1_0_swing.py`

### Configuration:
- **Timeframe:** M15 (15 minutes)
- **Scan Interval:** 5 minutes
- **Hold Time:** 1-3 days
- **SL/TP:** 30-50 pips / 50-60 pips
- **H4 Filter:** ✅ ENABLED (trend alignment required)
- **Min Confidence:** 60%
- **Max Positions:** 10
- **Risk per Trade:** 1%

### Strategies:
- TREND (EMA20/50 on M15)
- BREAKOUT (M15 Bollinger)
- RANGE (M15 Bollinger + RSI)
- FVG: ❌ Disabled

### Best For:
- FTMO challenges
- Lower stress trading
- Quality over quantity
- Beginners

### Use When:
```bash
python the_beast_1_0_swing.py --continuous
```

---

## 🚀 THE BEAST 2.0 - DAY TRADING (Current)

**File:** `the_beast_2_0_daytrading.py` ⭐ DEFAULT

### Configuration:
- **Timeframe:** M5 (5 minutes)
- **Scan Interval:** 2 minutes
- **Hold Time:** 2-6 hours (same day)
- **SL/TP:** 15-25 pips / 25-30 pips (tight)
- **H4 Filter:** ❌ DISABLED (M5 only)
- **Min Confidence:** 50%
- **Max Positions:** 10
- **Risk per Trade:** 0.5% (fixed)
- **Session:** 10:00-19:00 EET only
- **Pairs:** 15 (most liquid)

### Strategies:
- TREND (EMA10/20 on M5 - FAST)
- BREAKOUT (M5 with volume)
- RANGE (M5 Bollinger - ADX < 28)
- FVG: ❌ Disabled

### Key Features:
- **Fixed 0.5% Risk:** Lot calculated dynamically based on SL distance
- **No H4 Filter:** Trades any direction on M5
- **Session Filter:** Only trades during London + NY overlap
- **Tight Stops:** Quick exits, smaller losses
- **ADX > 25** for trend, **ADX < 28** for range

### Best For:
- Fast data collection for ML
- Higher trade frequency
- Testing strategies quickly
- Advanced traders

### Use When (DEFAULT):
```bash
# This is the default - always use this unless specified otherwise
python bot_controller.py --continuous

# OR explicitly
python the_beast_2_0_daytrading.py --continuous
```

---

## 🔄 SWITCHING BETWEEN VERSIONS

### To Use Swing Trading (1.0):
```powershell
# Backup current
Copy-Item bot_controller.py bot_controller_backup.py

# Switch to 1.0
Copy-Item the_beast_1_0_swing.py bot_controller.py

# Start
python bot_controller.py --continuous
```

### To Use Day Trading (2.0) - DEFAULT:
```powershell
# Already set as default
python bot_controller.py --continuous

# OR explicitly
python the_beast_2_0_daytrading.py --continuous
```

---

## 📈 PERFORMANCE COMPARISON

| Metric | 1.0 Swing | 2.0 Day Trading |
|--------|-----------|-----------------|
| Trades/Day | 1-2 | 3-5 |
| Hold Time | 1-3 days | 2-6 hours |
| Data/Week | 10-15 trades | 20-30 trades |
| SL Size | 30-50 pips | 15-25 pips |
| Stress Level | Medium | High |
| Win Rate Target | 40% | 45% |
| Best Session | Any | 10-19 EET |

---

## 🎯 RECOMMENDATIONS

### Use 1.0 Swing When:
- FTMO challenge (conservative approach)
- Less time for monitoring
- Learning phase
- Market is choppy/no clear direction

### Use 2.0 Day Trading When:
- Need fast ML data collection
- High volatility periods (London/NY)
- Testing new strategies
- Comfortable with quick decisions

---

## 📝 CHANGELOG

### 2026-02-24 - Day Trading Implementation
- ✅ M5 timeframe (was M15)
- ✅ 2-minute scan (was 5 min)
- ✅ Fixed 0.5% risk per trade
- ✅ EMA10/20 (was SMA20/50)
- ✅ H4 filter removed
- ✅ Session filter 10-19 EET
- ✅ Min confidence 50% (was 60%)
- ✅ 15 pairs (was 20)
- ✅ Tight SL/TP (15-25 / 25-30 pips)

---

## ⚠️ IMPORTANT NOTES

1. **Default is 2.0 Day Trading** - Always use unless specified
2. **1.0 is backup** - For conservative/FTMO scenarios
3. **Journal is shared** - Both versions write to same journal
4. **Risk settings differ** - 1% (1.0) vs 0.5% (2.0)

---

**Current Default: THE BEAST 2.0 DAY TRADING** 🚀
