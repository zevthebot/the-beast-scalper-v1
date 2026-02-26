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

## Universal Journal System

### Overview

The Universal Journal is a centralized, append-only trade log that persists across account changes, FTMO phases, and prop firm migrations.

**Benefits:**
- Account-agnostic: Works across FTMO Phase 1, Phase 2, and funded accounts
- Historical continuity: Track performance over months/years
- Data-driven decisions: Rich dataset for strategy optimization
- Backup resilience: Simple JSONL format, easy to backup/restore

### Journal Entries

**ENTRY Format:**
```json
{
  "event": "ENTRY",
  "timestamp": "2026-02-26T14:30:00Z",
  "position_id": 12345,
  "symbol": "EURUSD",
  "direction": "LONG",
  "entry_price": 1.08500,
  "lot_size": 0.2,
  "sl_pips": 10,
  "tp_pips": 25,
  "strategy": "TREND",
  "session": "LONDON_NY_OVERLAP",
  "indicators": {
    "rsi": 55,
    "adx": 28,
    "ema_fast": 1.08480,
    "ema_slow": 1.08450,
    "volume_ratio": 2.1
  },
  "account": "FTMO_Phase1"
}
```

**EXIT Format:**
```json
{
  "event": "EXIT",
  "timestamp": "2026-02-26T16:45:00Z",
  "position_id": 12345,
  "exit_price": 1.08750,
  "pnl": 50.00,
  "pnl_pips": 25,
  "exit_reason": "TP_HIT",
  "duration_minutes": 135,
  "rr_achieved": 2.5
}
```

### Working with the Journal

**Count Total Trades:**
```powershell
(Get-Content universal_trade_journal.jsonl | Where-Object { $_ -like "*ENTRY*" }).Count
```

**View Last 5 Trades:**
```powershell
Get-Content universal_trade_journal.jsonl -Tail 10 | ForEach-Object { $_ | ConvertFrom-Json | Select-Object event, symbol, strategy, pnl }
```

**Calculate Win Rate:**
```powershell
$exits = Get-Content universal_trade_journal.jsonl | Where-Object { $_ -like "*EXIT*" } | ForEach-Object { ($_ | ConvertFrom-Json).pnl }
$wins = ($exits | Where-Object { $_ -gt 0 }).Count
$total = $exits.Count
"Win Rate: $([math]::Round($wins/$total*100, 1))% ($wins/$total)"
```

**Filter by Symbol:**
```powershell
Get-Content universal_trade_journal.jsonl | Where-Object { $_ -like "*XAUUSD*" } | ForEach-Object { $_ | ConvertFrom-Json }
```

### Journal Maintenance

**Backup:**
```powershell
Copy-Item universal_trade_journal.jsonl "backup_journal_$(Get-Date -Format 'yyyyMMdd').jsonl"
```

**Archive Old Data:**
```powershell
# Extract entries older than 90 days to archive
$cutoff = (Get-Date).AddDays(-90).ToString("yyyy-MM")
Get-Content universal_trade_journal.jsonl | Where-Object { $_ -notlike "*$cutoff*" } | Set-Content archive_pre_${cutoff}.jsonl
```

**Verify Integrity:**
```powershell
# Check for unmatched entries (entry without exit)
$entries = Get-Content universal_trade_journal.jsonl | ConvertFrom-Json
$entryIds = $entries | Where-Object { $_.event -eq "ENTRY" } | Select-Object -ExpandProperty position_id
$exitIds = $entries | Where-Object { $_.event -eq "EXIT" } | Select-Object -ExpandProperty position_id
$entryIds | Where-Object { $_ -notin $exitIds }
```

---

## Changelog

### Version History

#### V3.0 ML (Legacy)
**Status:** Deprecated, superseded by V4

**Characteristics:**
- 10 pairs traded (EURUSD, GBPUSD, USDJPY, EURJPY, GBPJPY, AUDUSD, EURGBP, AUDJPY, USDCHF, XAUUSD)
- ML-based signal scoring (0-100)
- Dynamic lot sizing based on ML confidence
- Variable SL/TP based on ATR
- Session filter: 07:00-21:00 GMT (wide window)
- Volume threshold: 0.8x average (loose)
- Auto-optimization every 20 trades

**Lot Sizing:**
- Base: 0.3 lots (0.1 for XAUUSD)
- ML Score 80+: 1.5x base
- ML Score 60-79: 1.0x base
- ML Score <60: 0.5x base or skip

**Issues Identified:**
- Over-trading in low-quality conditions
- ML overfitting to recent data
- Variable lot sizing created inconsistent risk
- Too many pairs diluted focus
- Wide session window captured low-volatility periods

---

#### V4.0 (Major Refactor)
**Status:** Superseded by V4.1

**Key Changes from V3:**
- Reduced pairs from 10 to 8
- Tighter session filter: 08:00-18:00 UTC
- Volume threshold increased to 1.5x
- Fixed SL/TP ratios improved to 1:2.0
- Simplified entry logic (removed ML scoring)
- Manual lot sizing between 0.1-0.3

**Lessons Learned:**
- Quality over quantity showed promise
- Removing ML reduced complexity
- Correlation filtering became essential

---

#### V4.1 OPTIMIZED (Current)
**Status:** Active Production

**Major Improvements:**

| Parameter | V4 | V4.1 | Impact |
|-----------|-----|------|---------|
| **Pairs** | 8 | 6 (-25%) | Maximum focus |
| **Session** | 08:00-18:00 | 09:00-17:00 (-20%) | Core quality hours |
| **Volume Threshold** | 1.5x | 1.8x (+20%) | Stricter confirmation |
| **R:R Ratio** | 1:2.0 | 1:2.5 (+25%) | Superior profitability |
| **Lot Sizing** | 0.1-0.3 manual | 0.2 fixed | Consistent risk |
| **Max Positions** | 4 | 3 (-25%) | Better risk control |
| **Journal** | Account-specific | Universal | Historical persistence |

**Technical Changes:**
1. **Symbol Reduction:** Removed lower-performing pairs (AUDUSD, EURGBP, AUDJPY, USDCHF)
2. **Session Tightening:** Eliminated early London and late NY (lower volatility periods)
3. **Volume Filter:** 1.8x ensures genuine institutional participation
4. **Risk-Reward:** 25 pip TP vs 10 pip SL creates positive expectancy even at 40% win rate
5. **Fixed Lots:** Eliminates human error, ensures consistent risk per trade
6. **Universal Journal:** Single source of truth for all trading activity

**Expected Behavior Changes:**
- Fewer trades per session (1-3 vs 3-5 in V4)
- Higher quality setups (volume + session + correlation)
- More consistent profits (fixed sizing + better R:R)
- Better tracking (universal journal)
- Improved prop firm compliance (stricter limits)

**Performance Expectations:**
- Trade frequency: -40% (quality focus)
- Average R:R: +25% (2.5 vs 2.0)
- Win rate: Similar or slightly lower (stricter filters)
- Net profitability: Improved (R:R improvement outweighs frequency reduction)
- Drawdown: Reduced (fewer concurrent positions, better setups)

---

## Migration Notes

### Upgrading from V4 to V4.1

1. **Backup existing journal:**
   ```powershell
   Copy-Item trade_journal.jsonl "v4_journal_backup.jsonl"
   ```

2. **Review open positions:**
   - Close or manage manually during transition
   - V4.1 won't recognize V4 position IDs

3. **Update configuration:**
   - Remove old symbols from watchlist
   - Adjust trading hours in code

4. **Start V4.1:**
   ```powershell
   python thebeast_v4_1.py
   ```

5. **Verify universal journal:**
   - Check `universal_trade_journal.jsonl` exists
   - Confirm entries being written

### Data Continuity

The universal journal starts fresh with V4.1, but you can manually append old data:

```powershell
# Convert old V4 entries to universal format (if desired)
Get-Content v4_journal.jsonl | ForEach-Object {
    $entry = $_ | ConvertFrom-Json
    # Transform to universal format...
} | Add-Content universal_trade_journal.jsonl
```

---

## Best Practices

### Daily Routine

1. **Pre-Session (08:45 UTC):**
   - Verify bot is running
   - Check MT5 connection
   - Review overnight positions

2. **During Session (09:00-17:00 UTC):**
   - Monitor dashboard every 1-2 hours
   - Review journal for trades taken
   - No intervention needed (system is autonomous)

3. **Post-Session (17:00+ UTC):**
   - Run analyzer: `python beast_analyzer.py`
   - Note any issues
   - Plan any adjustments for next day

### Weekly Review

1. Run full analysis: `python beast_analyzer.py`
2. Review symbol performance
3. Check session breakdowns
4. Identify any patterns
5. Adjust if necessary (rare in V4.1)

### Monthly Maintenance

1. Backup universal journal
2. Review long-term performance trends
3. Archive old data if needed
4. Update this documentation if systems change

---

## FAQ

**Q: Why only 6 pairs?**
A: Maximum focus on quality. Fewer pairs = deeper understanding of each pair's behavior, better volume analysis, and reduced correlation risk. These 6 pairs offer the best liquidity-to-volatility ratio.

**Q: What if I want to trade outside 09:00-17:00 UTC?**
A: You can modify `SESSION_START` and `SESSION_END` in the code, but this is NOT recommended. The 09:00-17:00 window captures the highest quality price action. Trading outside this window historically reduced win rates.

**Q: Why fixed 0.2 lots?**
A: Consistent risk per trade. Variable lot sizing (ML-based or otherwise) introduced unpredictability. Fixed sizing ensures every trade carries identical risk, making performance analysis cleaner and drawdowns more predictable.

**Q: Can I change the R:R ratio?**
A: Not recommended. The 1:2.5 ratio is mathematically optimal. At 40% win rate (achievable with strict filters), you still profit. Lower R:R requires higher win rate, which is harder to maintain.

**Q: What happens if volume is never 1.8x?**
A: The bot won't trade. This is the filter working correctly. If no pairs meet volume criteria, market conditions aren't optimal. Don't lower the threshold—wait for quality setups.

**Q: Why is my win rate lower than V3/V4?**
A: Expected. V4.1 prioritizes R:R over win rate. A 45% win rate with 1:2.5 R:R is more profitable than 55% with 1:1.5 R:R. Check your profit factor, not just win rate.

**Q: Can I use V4.1 on live accounts?**
A: Yes, but start with prop firm challenges first. The system is designed for account growth, but always verify behavior on demo before live deployment.

**Q: What about news events?**
A: V4.1 doesn't filter news. The volume threshold (1.8x) naturally reduces entries during major news (volume often spikes unpredictably). For major events (NFP, FOMC), consider manual intervention or accept the filtered results.

**Q: How do I know if the bot is working correctly?**
A: Check the journal:
1. Entries have `event: "ENTRY"` during 09:00-17:00 UTC
2. Volume ratio is logged (should be >1.8)
3. Strategy field is populated (TREND/BREAKOUT/REVERSAL)
4. Exits have corresponding position_ids

**Q: Can I run multiple instances?**
A: Not recommended. The universal journal handles single-account trading. Multiple instances could create position ID conflicts.

---

## Support & Resources

### File Locations

```
mt5_trader/
├── thebeast_v4_1.py              # Main trading bot
├── beast_dashboard.py            # Status dashboard
├── beast_analyzer.py             # Performance analysis
├── universal_trade_journal.jsonl # Trade log (auto-created)
├── beast_analysis_report.json    # Analysis output
└── USAGE.md                      # This file
```

### Log Files

- **Console output:** Run bot in terminal with logging
- **Journal:** `universal_trade_journal.jsonl` (structured data)
- **MT5 logs:** Check MT5 terminal Experts tab

### Emergency Contacts

- **Bot issues:** Review this USAGE.md first
- **MT5 connection:** Check broker server status
- **Account issues:** Contact your prop firm/broker

---

## License & Usage

THE BEAST 4.1 is proprietary trading software. Use at your own risk. Past performance does not guarantee future results. Always verify functionality on demo accounts before live trading.

**Risk Warning:** Trading forex, CFDs, and commodities carries significant risk of loss. Only trade with capital you can afford to lose.

---

*Last Updated: 2026-02-26*
*System Version: 4.1 OPTIMIZED*
*Documentation Version: 1.0*