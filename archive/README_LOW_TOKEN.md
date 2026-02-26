# MT5 Trading System - Low-Token Mode

Sistem de trading optimizat care reduce consumul de tokeni de la ~65k la ~5-8k per scan prin mutarea calculelor în EA și raportare minimală.

## Arhitectură Nouă

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  SimpleAIBot_EA │────▶│   signals.json   │────▶│ connector_opt.  │
│   (MT5/MQL5)    │     │   (JSON Export)  │     │   (Python)      │
└─────────────────┘     └──────────────────┘     └─────────────────┘
         │                                                  │
         │ Calculează:                                      │ Risk Rules
         │ • MA20, MA50                                     │ • Max 6 poz
         │ • RSI, ADX                                       │ • 1 per simbol
         │ • Bollinger Bands                                │ • Corelație
         │ • Semnale TREND/RANGE/BREAKOUT                   │
         ▼                                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                        state.json                               │
│  • Poziții active                                               │
│  • Stats zilnice                                                │
│  • Ultimul scan                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Flux de Date

1. **EA (MQL5)** rulează pe fiecare bară M15 și exportă `signals.json`
2. **connector_optimized.py** citește semnalele și aplică risk rules
3. Trade-urile se execută direct în MT5 fără LLM
4. Raport minimal este generat automat
5. LLM full doar la: trade nou, SL/TP atins, eroare, drawdown >5%

## Files

| File | Descriere |
|------|-----------|
| `SimpleAIBot_EA.mq5` | EA modificat cu `ExportSignalsToJSON()` |
| `connector_optimized.py` | Conector Python optimizat (fără LLM pentru analiză) |
| `state.json` | Stare persistentă (poziții, stats) |
| `cron_scanner.py` | Script pentru rulare periodică cu raport minimal |
| `signals.json` | Exportat de EA, citit de Python |

## Deploy

### 1. Compilează EA în MT5

1. Deschide MetaEditor 5
2. Deschide `SimpleAIBot_EA.mq5`
3. Apasă F7 (Compile)
4. Fără erori, EA e gata de attach

### 2. Attach EA pe Chart

1. În MT5, deschide un chart EURUSD M15
2. Drag & drop `SimpleAIBot_EA` pe chart
3. Settings:
   - `JsonExportPath`: lasă default sau modifică dacă e necesar
   - `SymbolsToScan`: lista de simboluri separate prin virgulă
   - Enable `Allow DLL imports` (pentru JSON export)
4. OK - EA începe să exporte semnale

### 3. Setup Python Environment

```bash
cd C:\Users\Claw\.openclaw\workspace\mt5_trader
pip install MetaTrader5 pandas
```

### 4. Testează Conectorul

```bash
python connector_optimized.py --verbose
```

Ar trebui să vezi:
```
📊 MT5 Scan 08:30
💰 2 poziții, P&L: -12.50 USD
✅ Niciun trade nou
```

### 5. Setup Cron (Task Scheduler)

**Windows Task Scheduler:**

1. Deschide Task Scheduler
2. Create Basic Task:
   - Name: `MT5_Trading_Scan`
   - Trigger: Daily, every 15 minutes
   - Action: Start a program
   - Program: `python`
   - Arguments: `C:\Users\Claw\.openclaw\workspace\mt5_trader\cron_scanner.py`

**Sau folosește Python schedule:**

```bash
pip install schedule
```

Creează `scheduler.py`:
```python
import schedule
import time
import subprocess
import sys

def run_scan():
    result = subprocess.run([sys.executable, "cron_scanner.py"], capture_output=True, text=True)
    print(result.stdout)
    if result.returncode == 2:
        # LLM review needed
        print("LLM review triggered!")

schedule.every(15).minutes.do(run_scan)

while True:
    schedule.run_pending()
    time.sleep(60)
```

## Format Semnale JSON

```json
{
  "timestamp": "2026-02-13T08:30:00",
  "account": {
    "balance": 1076.65,
    "equity": 1073.61
  },
  "signals": [
    {
      "symbol": "EURUSD",
      "strategy": "RANGE",
      "signal": "BUY",
      "strength": "STRONG",
      "entry": 1.18609,
      "sl": 1.184,
      "tp": 1.19
    }
  ],
  "positions": [
    {
      "symbol": "EURUSD",
      "type": "BUY",
      "profit": -1.13
    }
  ]
}
```

## Risk Rules Implementate

1. **Max 6 poziții** - nu se deschid mai mult de 6 poziții simultan
2. **1 poziție per simbol** - nu se dublează pe același simbol
3. **Corelație** - evităm poziții multiple pe perechi corelate:
   - EUR: EURUSD, EURJPY, EURGBP
   - GBP: GBPUSD, GBPJPY, EURGBP
   - JPY: USDJPY, EURJPY, GBPJPY, AUDJPY
   - AUD: AUDUSD, AUDJPY

## Strategii Implementate

### TREND (Trend Following)
- MA20 > MA50 pentru uptrend
- MA20 < MA50 pentru downtrend
- RSI filtru între 30-70
- Best for: London-NY overlap

### RANGE (Mean Reversion)
- ADX < 25 (ranging market)
- Entry la Bollinger Bands (touch upper/lower)
- TP la mijlocul range-ului
- Best for: Tokyo session

### BREAKOUT
- Break peste recent high/low
- Confirmare cu volum > 120% average
- Target = 1x range
- Best for: Tokyo-London overlap

## Raportare

### Normal (fără evenimente)
```
📊 MT5 Scan 08:30
💰 5 poziții, P&L: +2.3%
✅ Niciun trade nou
```

### Cu trade nou
```
📊 MT5 Scan 08:30
💰 6 poziții, P&L: +1.8%
🟢 1 trade nou:
   • BUY EURUSD (RANGE)
[LLM_ALERT: New trade executed]
```

### Cu eroare
```
📊 MT5 Scan 08:30
💰 5 poziții, P&L: +2.1%
🔴 1 eroare
[LLM_ALERT: Trade errors occurred]
```

## Exit Codes

| Code | Semnificație |
|------|--------------|
| 0 | Success, niciun trade nou |
| 1 | Eroare critică (MT5 neconectat, etc.) |
| 2 | LLM review needed (trade nou, eroare, drawdown) |

## Troubleshooting

### EA nu exportă JSON
- Verifică dacă path-ul există
- Verifică permisiunile de scriere
- Verifică log-ul Experts în MT5

### Python nu găsește signals.json
- Verifică dacă EA rulează
- Verifică path-ul în `SIGNALS_FILE`
- Verifică dacă fișierul e creat

### MT5 nu se conectează
- Asigură-te că MT5 e deschis și logged in
- Verifică dacă account_info() returnează date

### Trade-uri nu se execută
- Verifică max 6 poziții
- Verifică 1 poziție per simbol
- Verifică corelația
- Verifică log-ul de erori

## Comparare Token Usage

| Componentă | Mod Vechi | Low-Token Mode |
|------------|-----------|----------------|
| Indicatori | Python (~15k) | EA MQL5 (0) |
| Analiză semnale | LLM (~25k) | EA MQL5 (0) |
| Raport | LLM (~20k) | Python (0) |
| Total per scan | ~65k tokeni | ~5-8k tokeni |
| Reducere | - | **~90%** |

## Note

- EA calculează toți indicatorii în MQL5 (rapid, 0 tokeni)
- Python doar citește și execută (fără calcule complexe)
- LLM e apelat doar la evenimente semnificative
- State persistence în `state.json` evită re-trimiterea datelor la LLM
