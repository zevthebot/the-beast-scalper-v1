# Zev Trading System v3.0 — USAGE

> **Arhitectură nouă**: Python Controller (LLM reasoning) + EA Protection-only
> **Data**: 2026-02-18
> **Status**: Implementat și activ

---

## Overview

Sistemul de trading a fost restructurat complet:

| Componentă | Rol | Execuție |
|------------|-----|----------|
| **bot_controller_v3.py** | Scanează, analizează, decide | La 15 minute (cron) |
| **Zev (LLM)** | Validare reasoning pentru fiecare setup | La fiecare scan |
| **EA v2** | Doar trailing stop și breakeven | Continuu pe tick |
| **MT5** | Execuție trade-uri, date piață | 24/7 |

**Motivație schimbare:**
- EA rigid a generat trade-uri cu RR negativ (USDCHF SL > TP)
- Python controller anterior a făcut +5% în 24h cu reasoning bun
- Acum: LLM analizează fiecare setup înainte de execuție

---

## Workflow Complet

```
Cron (15 min)
    ↓
Python Controller pornește
    ↓
1. Colectează date MT5 (prețuri, indicatori, poziții)
    ↓
2. Găsește setups potențiale (Trend strategy)
    ↓
3. Filtrare automată:
   - RR >= 1:2?
   - Confidence >= 75%?
   - Sesiune activă?
   - Max poziții?
    ↓
4. Pentru fiecare setup valid:
   Zev (LLM) analizează:
   - Trend H1 + H4 aliniat?
   - Context macro
   - Corelație cu poziții existente
   - Quality de entry
    ↓
5. Decizie:
   APPROVED → Execută trade prin MT5 API
   REJECTED → Log + așteaptă următorul scan
    ↓
EA v2 (continuu):
   - Gestionează trailing stop pe pozițiile existente
   - Mută SL la breakeven când profit >= 1 ATR
   - Fallback dacă Python pică
```

---

## Configurare

### Parametri (în cod Python)

```python
CONFIG = {
    "risk_per_trade": 0.5,      # 0.5% din balance
    "max_lot": 0.5,             # Hard cap 0.5 lots
    "max_positions": 3,         # Max 3 poziții simultane
    "min_rr": 2.0,              # Risk:Reward minim 1:2
    "min_confidence": 75,       # Min 75% confidence
    "magic_number": 234000,     # Magic number comun
    "symbols": [                 # Doar 6 perechi lichide
        "EURUSD", "GBPUSD", "USDJPY", 
        "AUDUSD", "USDCAD", "EURJPY"
    ],
    "session_start": 7,         # GMT 07:00
    "session_end": 17,          # GMT 17:00
}
```

### Modificări posibile

| Ce modifici | Unde | Efect |
|-------------|------|-------|
| Risk % | `bot_controller_v3.py` line ~15 | % din balance per trade |
| Max lot | `bot_controller_v3.py` line ~16 | Hard cap lot size |
| Max poziții | `bot_controller_v3.py` line ~17 | Câte poziții max simultan |
| Min RR | `bot_controller_v3.py` line ~18 | Risk:Reward minim |
| Perechi | `bot_controller_v3.py` line ~23 | Lista simboluri active |
| Sesiune | `bot_controller_v3.py` line ~24-25 | Ore trading |

**Note:** După modificare, restart MT5 nu e necesar (Python e external).

---

## Validări Automate (Hard Constraints)

Înainte să ajungă la Zev (LLM), fiecare setup trece prin:

1. **Sesiune activă**: GMT 07:00-17:00 (London + overlap)
2. **Max poziții**: Nu mai mult de 3 simultane
3. **RR minim**: SL vs TP trebuie >= 1:2
4. **Confidence minim**: 75% (calculat din indicatori)
5. **Trend aliniat**: M15, H1, H4 în aceeași direcție
6. **RSI valid**: Între 25-75 (nu overbought/oversold)
7. **Fără poziție existentă**: Pe acel simbol
8. **Fără corelație**: Nu dublu exposure pe aceeași monedă

---

## LLM Reasoning (Zev)

Pentru fiecare setup care trece validările automate, Zev analizează:

### Date primite:
- Simbol, direcție, preț entry
- SL, TP, RR ratio
- Indicatori: RSI, ATR, MA20/50, ADX
- Trend pe M15, H1, H4
- Spread, sesiune
- Poziții existente (correlation)
- Account status (balance, equity, daily PnL)

### Check-uri reasoning:
1. **RR quality**: E 1:2 suficient? Poate fi 1:3?
2. **Trend strength**: ADX confirmă putere?
3. **Timing**: E prea târziu în sesiune?
4. **Context**: Am pierdut recent pe această pereche?
5. **Macro**: Evenimente economice astăzi?
6. **Confidence real**: 75% calculat e justificat?

### Output:
- **APPROVED** + lot size calculat + reasoning
- **REJECTED** + motiv (ex: "trend prea slab", "prea târziu în sesiune")

---

## Fișiere și Locații

### Active ( importante)

```
workspace/mt5_trader/
├── bot_controller_v3.py      # Controller principal (Python)
├── SimpleAIBot_EA_v2.mq5     # EA (doar trailing, no entry)
├── SimpleAIBot_EA_v2.ex5     # Compilat în MT5
├── USAGE.md                  # Acest document
└── trade_journal_v3.jsonl    # Log trade-uri

MT5/Common/Files/
├── ZevBot_Config.ini         # Config EA (mai puțin relevant acum)
├── ZevBot_Status.json        # Status EA
└── ZevBot_TradeLog.csv       # Log EA (doar poziții existente)
```

### Legacy (nu se mai folosesc)

```
bot_controller.py             # Vechi - înlocuit
cron jobs vechi               # Dezactivate
protection_manager.py         # Integrat în EA
```

---

## Proceduri

### 1. Start Sistem

**Automat la boot:**
1. MT5 pornește (Windows startup)
2. EA v2 încărcat pe EURUSD M15 (protection mode)
3. Cron job pornește Python controller la 15 minute

**Manual (dacă trebuie):**
```powershell
# Start MT5
& "C:\Program Files\MetaTrader 5\terminal64.exe"

# Atașare EA (dacă nu e deja)
# În MT5: Navigator → Expert Advisors → SimpleAIBot_EA_v2
# Drag & drop pe EURUSD M15
# Check "Allow Algo Trading"
```

### 2. Verificare Status

```powershell
# Status rapid
python C:\Users\Claw\.openclaw\workspace\mt5_trader\bot_controller_v3.py --once

# Sau citește jurnal
Get-Content C:\Users\Claw\.openclaw\workspace\mt5_trader\trade_journal_v3.jsonl -Tail 10

# Status MT5 (UTF-16!)
python -c "
import json
f = open(r'C:\Users\Claw\AppData\Roaming\MetaQuotes\Terminal\Common\Files\ZevBot_Status.json', 'rb')
print(json.loads(f.read().decode('utf-16')))
f.close()
"
```

### 3. Oprire Emergență

**Oprește toate entry-urile:**
```powershell
# Stop cron job
openclaw cron remove <id_controller>

# Sau în MT5
# Butonul "Algo Trading" (roșu = OFF)
```

**Închide poziții deschise:**
```powershell
# Manual în MT5
# Tab "Trade" → Click dreapta pe poziție → Close Position
```

### 4. Modificare Parametri

1. Editează `bot_controller_v3.py`
2. Salvează
3. Nu e necesar restart MT5
4. Următorul scan (15 min) folosește noua config

### 5. Tranziție Cont FTMO (Phase 1 → 2 → Funded)

**Nu e necesară modificare cod!**

Doar schimbă login în MT5:
1. File → Login to Trade Account
2. Introdu credențiale cont nou
3. Python controller detectează automat noul account
4. Jurnalul continuă (tagged cu account ID diferit)

---

## Cron Jobs

### Active

| Nume | ID | Interval | Rol |
|------|-----|----------|-----|
| FTMO_Journal_Monitor | `0e89...` | 30 min | Monitor status, notifică Telegram |
| **ZEV_CONTROLLER_V3** | *(de creat)* | 15 min | Scan, analiză LLM, execuție |

### De creat

```bash
# Adaugă cron job pentru controller
openclaw cron add \
  --name "ZEV_CONTROLLER_V3" \
  --every "15m" \
  --command "python C:\Users\Claw\.openclaw\workspace\mt5_trader\bot_controller_v3.py --once" \
  --model "kimi" \
  --delivery "telegram"
```

---

## Troubleshooting

### "Nu se deschide niciun trade"

1. Verifică sesiunea: GMT 07:00-17:00?
2. Verifică max poziții: Avem deja 3 deschise?
3. Verifică setup-uri: Trece prin filtrele automate?
4. Verifică LLM: Aprobă Zev?
5. Verifică log: `trade_journal_v3.jsonl`

### "Python dă eroare"

```
ImportError: No module named 'MetaTrader5'
→ pip install MetaTrader5

Connection error
→ MT5 e deschis? E pe contul corect?
```

### "Trailing stop nu merge"

1. Verifică EA v2 încărcat pe chart
2. Verifică "Allow Algo Trading" ON
3. Verifică smiley face pe chart

### "Vreau să modific strategy"

Editează funcția `find_setups()` în `bot_controller_v3.py`.

---

## Istoric Decizii

| Data | Decizie | Motiv |
|------|---------|-------|
| 2026-02-18 | Switched to Python Controller v3 | EA rigid a generat trade-uri cu RR negativ |
| 2026-02-18 | Disabled EA entry execution | Prevenire trade-uri nevalidate |
| 2026-02-18 | LLM reasoning pentru fiecare trade | Maximizare calitate, minimizare erori |
| 2026-02-18 | 15 min scan interval | Suficient pentru swing, timp pentru analiză |

---

## Contact / Support

**Pentru Andrei:**
- Telegram: @vsoner
- Notificări: Automat prin cron job

**Pentru Zev (LLM):**
- Citește acest USAGE.md la fiecare sesiune
- Verifică trade_journal_v3.jsonl
- Analizează și optimizează continuu

---

*Document actualizat: 2026-02-18*
*Versiune sistem: 3.0*
