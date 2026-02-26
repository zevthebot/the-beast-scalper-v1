# MT5 Low-Token Mode - Optimized Architecture

## Overview

This optimized version reduces token consumption from ~65k to ~5-8k per scan by moving all calculations to MT5 and using Python only for execution.

**Token Savings: ~85-90%**

## Architecture Changes

### Before (High Token Mode)
```
Python Script → Fetch OHLC data → Calculate indicators (MA, RSI, ADX) 
→ Analyze with LLM → Generate report → Execute trade
```
**Cost:** ~65k tokens per scan

### After (Low Token Mode - TIERED 10 SLOTS)
```
MT5 EA → Calculate all indicators → Export signals.json
Python Connector → Read JSON → Apply TIERED risk rules → Execute trade
```
**Cost:** ~5-8k tokens per scan

## Tiered Slot System (10 Positions)

**Sistem cu două niveluri de calitate:**

| Sloturi | Scor minim | Descriere |
|---------|-----------|-----------|
| 1-6 | ≥70 | Entry standard — semnale bune |
| 7-10 | ≥85 | Entry premium — doar cele mai bune oportunități |

**Beneficii:**
- Primele 6 poziții: Flexibilitate maximă, setup-uri frecvente
- Ultimele 4 poziții: Calitate superioară, probabilitate ridicată de câștig
- Nu ratezi oportunități bune din cauza sloturilor ocupate de trades lente

## File Structure

```
mt5_trader/
├── SimpleAIBot_EA.mq5          # Modified EA with ExportSignalsToJSON()
├── connector_optimized.py       # New lightweight connector
├── signals.json                 # MT5 signal export (auto-generated)
├── state.json                   # Persistent state (auto-updated)
└── README_OPTIMIZED.md          # This file
```

## Deployment Steps

### Step 1: Update MT5 EA

1. Open MetaEditor in MT5
2. Load `SimpleAIBot_EA.mq5`
3. Compile and attach EA to EURUSD M15 chart
4. Enable `Allow DLL imports` in EA properties
5. EA will auto-export `signals.json` every minute

### Step 2: Verify JSON Export

Check that `signals.json` is created and updated:
```json
{
  "timestamp": "2026-02-13T08:40:00",
  "account": {
    "balance": 1076.83,
    "equity": 1074.72,
    "profit": -2.01
  },
  "signals": [...],
  "positions": [...]
}
```

### Step 3: Update Cron Job

Replace old cron command:
```bash
# OLD (high token)
python mt5_trader/auto_trading_monitor.py

# NEW (low token)
python mt5_trader/connector_optimized.py
```

### Step 4: Test

Run manual test:
```bash
cd mt5_trader
python connector_optimized.py
```

Expected output:
```
[OK] MT5 connected | Account: 62108425 | Balance: 1076.83 EUR
[SCAN] Balance: 1076.83 | Equity: 1074.72 | Positions: 6/6 | P&L: -2.01 EUR
```

## Token Consumption Comparison

| Operation | Old (tokens) | New (tokens) | Savings |
|-----------|-------------|--------------|---------|
| Scan only | ~32k | ~3k | 90% |
| Scan + 1 trade | ~65k | ~8k | 88% |
| Daily (96 scans) | ~6.2M | ~500k | 92% |

## Features Preserved

✅ All 3 strategies (Trend, Range, Breakout)
✅ Risk management (2% per trade, max 6 positions)
✅ Correlation checks (EUR/USD + GBP/USD)
✅ Position tracking
✅ Daily stats

## Features Changed

⚠️ **No LLM analysis in normal scans** — trades executed based on JSON signals
⚠️ **Minimal reporting** — unless trade/error event occurs
⚠️ **EA does all calculations** — requires MT5 to be running

## Rollback Plan

If issues occur, revert to old system:
```bash
# Use old monitor
python mt5_trader/auto_trading_monitor.py
```

## Monitoring

Check state file for system health:
```bash
cat mt5_trader/state.json
```

## Troubleshooting

### Issue: `signals.json` not found
**Fix:** Ensure EA is running and has write permissions to folder

### Issue: EA not exporting
**Fix:** Check MT5 Experts tab for errors; verify JSON path is writable

### Issue: Trades not executing
**Fix:** Check MT5 is logged in; verify Python can connect to MT5

---

**Version:** 2.0 Low-Token Mode  
**Last Updated:** 2026-02-13
