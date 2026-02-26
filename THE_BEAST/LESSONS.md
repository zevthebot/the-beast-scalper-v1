# LESSONS LEARNED — 2026-02-19

## Ce-a Mers Greșit (Drawdown $140+)

### 1. EURUSD BUY — Trade Contra-Trend (Greșeala #1)
**Setup:** Range strategy, preț sub Lower BB  
**Realitate:** H1 trend BEARISH puternic  
**Rezultat:** -$16.80 și crescând (a fost și mai rău la un moment dat)

**Lecție:** Range trades ÎMPOTRIVA trendului H1 au win rate scăzut. Filtrul adăugat acum (nu mai luăm Range contra H1) e corect, dar a venit prea târziu.

### 2. Prea Multe Poziții Deschise (Greșeala #2)
**Vârf:** 6 poziții simultane  
**Problemă:** Când piața merge împotrivă, drawdown se amplifică rapid  
**Lecție:** Max 10 e prea mult când corelația e mare (toate GBP, toate JPY)

### 3. Bot Instabil (Greșeala #3)
**Crashes:** 5+ restarts în câteva ore  
**Consecință:** Gap-uri în trading, posibile rateări de exit/entry  
**Fix implementat:** Reconectare automată, try-catch în toate funcțiile

---

## Ajustări Implementate

| Problemă | Soluție | Status |
|----------|---------|--------|
| Range contra-trend | Filtru H1 în analyze_range() | ✅ Activ |
| Bot crashes | Try-catch + reconectare MT5 | ✅ Activ |
| Prea multe poziții | Adaptive max (5 la WARNING) | ✅ Activ |

---

## Reguli Noi pentru The Beast

1. **NU Range contra H1 trend** — Filtru activ
2. **Max 5 poziții în drawdown** — Adaptive risk
3. **Circuit breaker:** Dacă daily loss > 2%, stop new entries
4. **SL strict 50 pips max** — Nu lăsăm drawdown să crească

---

## Obiectiv Recuperare

**Target:** Revin la profit +5% (de la +4.5% actual)
**Plan:** 
- Lăsăm pozițiile active cu trailing stop
- Nu mai deschidem poziții noi până nu vedem profit
- Focalizare pe protecție, nu pe agresivitate

**Motto nou:** "Protejăm ce avem, profitul vine după."

---

*Documentat: 2026-02-19 14:30*  
*Status: Learning mode activated* 🎯
