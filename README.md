# MT5 AI Trading Bot Setup

## Overview
Automated trading system for MetaTrader 5 with Pepperstone demo account.

## Account Details
- **Account:** 62108425
- **Server:** PepperstoneUK-Demo
- **Password:** gqiUmv)t1b
- **Balance:** 1,000 EUR (demo)
- **Leverage:** 1:30

## Files

### Python Scripts
- `bot_controller.py` - Full-featured trading bot with multiple strategies
- `bot_simple.py` - Lightweight connector for basic trading

### MQL5 Expert Advisor
- `SimpleAIBot_EA.mq5` - Native MT5 EA (most reliable)

## Installation

### Option 1: Python Bot (Recommended for development)
```bash
cd mt5_trader
python bot_simple.py
```

**Prerequisites:**
1. MetaTrader 5 must be running and logged in
2. Python packages: `MetaTrader5`, `pandas`, `numpy`

### Option 2: MQL5 Expert Advisor (Recommended for production)
1. Open MetaEditor (from MT5)
2. File → Open → Select `SimpleAIBot_EA.mq5`
3. Press F7 to compile
4. In MT5: Navigator → Expert Advisors → Drag SimpleAIBot to chart
5. Enable "Allow Algo Trading" and "Allow Live Trading"

## Strategy

### Current: Trend Following + RSI Filter
- **Timeframe:** M15 (15 minutes)
- **Entry:** MA20/MA50 crossover + RSI confirmation
- **Risk:** 2% per trade
- **Stop Loss:** 50 pips
- **Take Profit:** 100 pips (2:1 R/R)
- **Trailing Stop:** Enabled at 50% of SL

### Symbols Traded
- EURUSD (major pair)
- GBPUSD (volatile)
- USDJPY (trending)
- XAUUSD (gold)

## Risk Management
- Max 3 concurrent positions
- 2% risk per trade
- Automatic lot size calculation
- Trailing stops to protect profits

## Monitoring
The bot logs all activity to MT5's Experts tab. Check there for:
- Entry/exit signals
- Order execution status
- Errors or warnings

## Next Steps
1. Login to MT5 manually
2. Run `python bot_simple.py` to test connection
3. If successful, deploy EA for 24/7 trading
