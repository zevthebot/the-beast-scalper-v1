# USAGE.md — Zev Trading System v1.0 (Proven Architecture)

> **Document de referință pentru LLM-uri și operatori umani**
> **Arhitectura:** Python Controller v1 (Continuous Mode) + EA Protection-only
> **Data:** 2026-02-19
> **Status:** Active / Live — FTMO Challenge Phase 1
> **Account:** 541144102 (FTMO-Server4)

---

## 1. Arhitectura v1.0 (Sistemul care a făcut +5% în 2 zile)

```
┌─────────────────────────────────────────────────────────────────┐
│                    ZEV TRADING SYSTEM v1.0                       │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │    Python Controller v1 (bot_controller.py)              │    │
│  │    RULARE CONTINUĂ — Nu cron, nu intervale              │    │
│  │  ├─ Scanare: La fiecare 5 minute (12 perechi)          │    │
│  │  ├─ Protecție: La fiecare 2 minute (breakeven/trailing)│    │
│  │  ├─ Raport: La fiecare 30 minute (status complete)     │    │
│  │  ├─ 3 Strategii: Trend + Range + Breakout              │    │
│  │  ├─ Entry: Direct prin MT5 API (OrderSend)             │    │
│  │  ├─ SL/TP: Fixed pips (30/60, 40/60, 50/50)            │    │
│  │  ├─ Lot Size: 0.1-0.5 dinamic pe confidence (40-100%)  │    │
│  │  ├─ Max Positions: 10 tiered by confidence             │    │
│  │  ├─ Risk Adaptiv: 4 niveluri bazate pe daily loss      │    │
│  │  └─ Logging: trade_journal.jsonl                       │    │
│  └──────────────────┬──────────────────────────────────────┘    │
│                     │                                           │
│                     ▼                                           │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │              MetaTrader 5 (MT5)                         │    │
│  │  ├─ Date piață: Live de la FTMO-Server4                │    │
│  │  ├─ Execuție: OrderSend() instant                      │    │
│  │  ├─ Poziții: Management în timp real                   │    │
│  │  └─ EA: SimpleAIBot_EA_v2.ex5 (protection only)        │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │         EA v2 — Protection Mode (Backup)                │    │
│  │  ├─ Entry: DISABLED (Python handlează)                 │    │
│  │  ├─ Trailing Stop: Activ pe toate pozițiile            │    │
│  │  ├─ Breakeven: Mută SL la entry la +15 pips            │    │
│  │  └─ Fallback: Dacă Python pică, gestionează existent   │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. De ce v1.0 și nu v3.2?

| Metric | v3.2 (Abandonat) | v1.0 (Curent) |
|--------|------------------|---------------|
| **Rezultate** | 0% în 24h | **+5% în 2 zile** |
| **Entry** | Prea restrictiv (H1+H4+M15) | Direct pe M15 (3 strategii) |
| **Execuție** | Cron la 5 min (ratări) | **Continuu** (fără gap-uri) |
| **Strategii** | Doar Trend | **Trend + Range + Breakout** |
| **Protecție** | Manual | **Automat la 2 min** |

**Lecție învățată:** Sistemul simplu care rulează continuu și tranzacționează 3 strategii a dovedit că funcționează. Nu fixăm ce nu e stricat.

---

## 3. Componente Active

### 3.1 Python Controller v1 — `bot_controller.py`

**Fișier:** `workspace/mt5_trader/bot_controller.py` (46KB)

**Mod de rulare:** Continuous (NU cron!)
```powershell
python -u bot_controller.py --continuous
```

**Cicluri:**
- **5 minute:** Scanare 12 perechi pentru semnale noi
- **2 minute:** Protecție (breakeven + trailing stop)
- **30 minute:** Raport complet de status

**Perechi monitorizate (12):**
```python
symbols = [
    "EURUSD", "GBPUSD", "USDJPY", "XAUUSD",    # Majors
    "EURJPY", "GBPJPY", "AUDJPY", "EURGBP",    # Crosses
    "USDCAD", "AUDUSD", "NZDUSD", "GBPAUD"     # Additional
]
```

---

## 4. Cele 3 Strategii (Prioritate: Breakout > Range > Trend)

### 4.1 BREAKOUT (Prioritate 3 — Cele mai rapide mișcări)

**Logică:**
- Timeframe: M30 (6 ore de date)
- Range: High/Low ultimele 8 lumânări (4 ore)
- Confirmare: Volum > 30% peste media
- Entry: Break above recent high sau below recent low

**Parametri:**
- Confianță: 50%+ (bazat pe raport volum)
- SL/TP: 40 pips / 60 pips (1:1.5 R/R)
- Ideal pentru: Mișcări rapide în sesiunea London/NY

**Cod:**
```python
def analyze_breakout(self, symbol):
    df = self.trader.get_rates(symbol, mt5.TIMEFRAME_M30, 12)
    recent_high = df['high'].iloc[-8:].max()
    recent_low = df['low'].iloc[-8:].min()
    
    # Volum confirmation
    avg_volume = df['tick_volume'].iloc[-8:].mean()
    current_volume = latest['tick_volume']
    volume_confirmed = current_volume > avg_volume * 1.3
    
    # Breakout threshold
    if current_price > recent_high + threshold and volume_confirmed:
        return BUY signal
```

### 4.2 RANGE (Prioritate 2 — Mean Reversion)

**Logică:**
- Timeframe: M15
- Indicatori: Bollinger Bands (20, 2.0)
- Filtru: ADX < 25 (piață fără trend clar)
- Entry: Preț atinge lower BB (BUY) sau upper BB (SELL)

**Parametri:**
- Confianță: 50%+ (bazat pe distanța față de BB)
- SL/TP: 50 pips / 50 pips (1:1 R/R)
- Ideal pentru: Piețe laterale, consolidări

**Exemplu de trade reușit:**
- **EURJPY BUY @ 182.777** (19 Feb, 10:38)
- Strategy: RANGE
- Confidence: 57%
- Entry logic: Preț atins lower Bollinger Band
- Status: ACTIVE

### 4.3 TREND (Prioritate 1 — Doar dacă e puternic)

**Logică:**
- Timeframe: M15
- Indicatori: MA20/50 crossover, ADX > 25, RSI
- Filtru: ADX > 25 (trend confirmat)
- Entry: MA crossover + RSI în direcția trendului

**Parametri:**
- Confianță: 65%+ (mai strict)
- SL/TP: 30 pips / 60 pips (1:2 R/R)
- Ideal pentru: Trenduri clare cu momentum

---

## 5. Risk Management Adaptiv (NOU — Feb 19)

Sistemul ajustează automat expunerea bazat pe daily loss progress:

### 5.1 Nivele de Risk

| Nivel | Daily Loss | Max Poziții | Min Conf | Lot Size | Comportament |
|-------|-----------|-------------|----------|----------|--------------|
| **SAFE** | <1% | 10 | 40% | 100% | Trading normal |
| **CAUTION** | 1-2% | 8 | 50% | 100% | Monitorizat |
| **WARNING** | 2-3% | 5 | 60% | 75% | Redus, selectiv |
| **DANGER** | 3-4% | 2 | 75% | 50% | Doar high confidence |
| **CRITICAL** | ≥4% | 0 | — | 0% | **STOP TOTAL** |

### 5.2 Cum Funcționează

```python
# Exemplu: Avem deja 2.5% daily loss
if daily_loss >= 0.025:  # WARNING level
    max_positions = 5     # Down from 10
    min_confidence = 60   # Up from 40
    lot_multiplier = 0.75 # 25% smaller positions
```

**Scop:** Protejăm contul FTMO. Nu vom atinge niciodată limita de 5% pentru că ne oprim la 4%.

### 5.3 Tiered Position Slots

```python
# Slots 1-4: Confidence >= 40% (agresiv)
# Slots 5-7: Confidence >= 60% (moderat)  
# Slots 8-9: Confidence >= 75% (selectiv)
# Slot 10:  Confidence >= 85% (exceptional)
```

**Logică:** Primele poziții le luăm ușor, apoi devenim tot mai selectivi.

---

## 6. Protecție Automată (Breakeven + Trailing)

### 6.1 Breakeven Protection

**Trigger:** Poziția atinge +15 pips profit
**Acțiune:** SL mutat la prețul de intrare
**Rezultat:** Poziție fără risc (doar profit sau 0)

### 6.2 Aggressive Trailing Stop

| Profit | Trailing Distance | Locked |
|--------|------------------|--------|
| +30 pips | +15 pips | 50% profit |
| +50 pips | +30 pips | 60% profit |
| +80 pips | +50 pips | 62% profit |

**Frecvență:** La fiecare 2 minute

---

## 7. Cron Jobs (Doar Monitorizare)

### 7.1 FTMO_Journal_Monitor

**ID:** `0e89faa4-91c4-4a48-80f3-41cfadf2849d`  
**Frecvență:** La 30 minute  
**Model:** Kimi K2.5  
**Rol:** Monitorizare, nu execuție

**Detectează:**
- Trade-uri noi deschise/închise
- Milestones atinse (+6%, +7%, +8%, etc.)
- Risk alerts (daily loss >3%)

**Output:** Telegram doar dacă e ceva notabil

### 7.2 Alte Cron Jobs (DEZACTIVATE)

- `ZEV_CONTROLLER_V3` — Disabled (v3.2 nu a funcționat)
- `FTMO_Profit_Scanner_Aggressive` — Disabled (înlocuit cu v1)
- `FTMO_Milestone_Monitor` — Disabled (merged în Journal_Monitor)

---

## 8. Fișiere și Logging

### 8.1 Trading Journal

**Fișier:** `workspace/mt5_trader/trade_journal.jsonl`

**Format:** JSON Lines (un entry per linie)
```json
{"event": "TRADE_OPEN", "account": 541144102, "symbol": "EURJPY", 
 "direction": "BUY", "volume": 0.1, "entry_price": 182.777, ...}
```

**Conține:**
- TRADE_OPEN (la deschidere)
- TRADE_CLOSE (la închidere cu PnL)
- EA_TRADE_LOG (detalii complete de la EA)

### 8.2 Status Files (MT5 Common Files)

| Fișier | Scop | Encoding |
|--------|------|----------|
| `ZevBot_Status.json` | Status live (echity, poziții) | UTF-16 |
| `ZevBot_TradeLog.csv` | Log CSV cu toate trade-urile | UTF-16 |
| `ZevBot_Config.ini` | Config dinamic (opțional) | UTF-16 |

### 8.3 Log Bot

**Vizualizare live:**
```powershell
# Vezi ce face botul acum
openclaw process log --session <session-id>

# Verifică status
python -c "import MetaTrader5 as mt5; mt5.initialize(); print(mt5.positions_get()); mt5.shutdown()"
```

---

## 9. Proceduri Operationale

### 9.1 Start Sistem

**Automat la boot:**
1. Windows pornește
2. MT5 pornește (startup folder)
3. Login manual în contul FTMO 541144102
4. EA v2 pe EURUSD M15 (protection mode)
5. Python bot în continuous mode:
   ```powershell
   python -u C:\Users\Claw\.openclaw\workspace\mt5_trader\bot_controller.py --continuous
   ```

### 9.2 Verificare Status

```powershell
# Status rapid
python -c "
import MetaTrader5 as mt5
mt5.initialize()
info = mt5.account_info()
print(f'Balance: {info.balance} | Equity: {info.equity}')
print(f'Positions: {mt5.positions_total()}')
for p in mt5.positions_get():
    print(f'  {p.symbol} {p.type} | {p.profit} USD')
mt5.shutdown()
"
```

### 9.3 Oprire Emergență

**Stop trading (păstrează pozițiile):**
```powershell
# Kill Python bot
openclaw process kill --session <session-id>
# Sau în MT5: butonul "Algo Trading" OFF (roșu)
```

**Hard stop (închide tot):**
```powershell
# Botul face asta automat când daily loss >= 4%
# Manual: închide fiecare poziție în MT5
```

---

## 10. Configurare și Parametri

### 10.1 Parametri Principali (în cod)

```python
# Fișier: bot_controller.py (liniile 15-35)

INITIAL_BALANCE = 10000       # $10K FTMO Challenge
RISK_PER_TRADE = 0.01         # 1% risk per trade
MAX_POSITIONS = 10            # Max 10 poziții (tiered)
MAX_DAILY_LOSS = 0.04         # 4% hard stop (FTMO permite 5%)
MAX_TOTAL_LOSS = 0.08         # 8% hard stop (FTMO permite 10%)

# FTMO Reset
FTMO_RESET_HOUR = 0           # Midnight CET
FTMO_RESET_TIMEZONE = "Europe/Prague"

# Magic number pentru identificare poziții
magic_number = 234000
```

### 10.2 Lot Sizing Dinamic

```python
# Confidence-based lot sizing
if confidence >= 95: lot_size = 0.5  # Max
elif confidence >= 85: lot_size = 0.4
elif confidence >= 75: lot_size = 0.3
elif confidence >= 60: lot_size = 0.2
else: lot_size = 0.1                # Min

# Aplicat cu risk multiplier (la WARNING devine 0.075, etc.)
```

### 10.3 SL/TP pe Confidence

```python
if confidence >= 80:
    sl_pips = 30   # Tight
    tp_pips = 60   # 1:2 R/R
elif confidence >= 60:
    sl_pips = 40   # Moderate
    tp_pips = 60   # 1:1.5 R/R
else:
    sl_pips = 50   # Wide
    tp_pips = 50   # 1:1 R/R
```

---

## 11. Troubleshooting

### "Nu se deschide niciun trade"

1. **Verifică ora:** E weekend? Piața e închisă.
2. **Verifică confidence:** Pare trend puternic unidirectional? Botul așteaptă pullback.
3. **Verifică risk status:** Daily loss >3%? Sistemul e în mod conservativ.
4. **Verifică log:** `openclaw process log --session <id>`

### "Python dă eroare"

```powershell
# Reinstalează dependențele
pip install MetaTrader5 pandas numpy pytz

# Verifică MT5 e deschis
Get-Process terminal64
```

### "Trailing stop nu merge"

1. Verifică EA v2 încărcat pe chart
2. Verifică "Allow Algo Trading" e ON
3. Profitul e >15 pips? Breakeven vine primul.

---

## 12. Istoric și Decizii

### De ce am revenit la v1.0?

| Data | Eveniment | Decizie |
|------|-----------|---------|
| Feb 16 | Bot v1 face +5% în prima zi | Succes |
| Feb 17 | Bot v1 continuă cu protecție automată | Succes |
| Feb 18 | Încercare v3.2 (Python controller nou) | Eșec (0 trades) |
| Feb 19 | Revenire la v1.0, adăugat risk adaptiv | **Curent** |

**Principiu:** Dacă ceva funcționează, nu-l strica. Optimizăm în jurul lui, nu îl înlocuim.

---

## 13. Contact și Escalation

**Andrei (Utilizator):**
- Telegram: @vsoner
- Notificări: Automat prin FTMO_Journal_Monitor

**Zev (LLM):**
- Implementare: Claude Opus (sesiuni strategice)
- Execuție: Python bot v1 (continuous)
- Monitorizare: Kimi K2.5 (cron la 30 min)

**Escalation:**
- Probleme tehnice → Sesune nouă cu Zev
- Decizii strategice → Sesune nouă cu Zev
- Verificare rapidă → Comenzi în PowerShell

---

*Document actualizat: 2026-02-19 10:45 EET*  
*Versiune sistem: 1.0 (Proven Architecture)*  
*Target: +10% FTMO Phase 1 ($10K → $11K)*  
*Motto: "Protejăm contul mai întâi, profitul vine după"* 🛡️
