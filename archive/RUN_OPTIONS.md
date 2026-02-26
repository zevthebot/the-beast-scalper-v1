# FTMO Trading Bot - Opțiuni de Rulare

## Problemă Identificată
Exec tool-ul nu funcționează pentru execuție automată - nu captează output de la PowerShell/MT5.

## Soluții Disponibile

### Opțiunea 1: Rulare Manuală (Testată, Funcționează 100%)
```cmd
cd C:\Users\Claw\.openclaw\workspace\mt5_trader
python bot_controller.py --trade
```
- ✅ Funcționează imediat
- ⚠️ Trebuie să lași fereastra deschisă
- ✅ Pot citi statusul din ftmo_live_status.json

---

### Opțiunea 2: Serviciu Windows (Recomandat pentru 24/7)
**Pași:**
1. Click dreapta pe `Setup_Task.ps1` → "Run with PowerShell as Administrator"
2. Sau deschizi PowerShell ca Admin și rulezi:
   ```powershell
   C:\Users\Claw\.openclaw\workspace\mt5_trader\Setup_Task.ps1
   ```
3. Task-ul se crează automat și pornește la boot

**Avantaje:**
- ✅ Pornește automat cu Windows
- ✅ Rulează 24/7 fără intervenție
- ✅ Scrie loguri în `bot_console.log`

---

### Opțiunea 3: Rulare Ascunsă (Fără fereastră neagră)
Dublezi-click pe: `Run_Hidden.vbs`
- ✅ Rulează fără să arate fereastra CMD
- ✅ Botul lucrează în background
- ✅ Poți închide orice - botul continuă

---

### Opțiunea 4: Batch Continuu
Dublezi-click pe: `run_bot_service.bat`
- ✅ Rulează continuu, la fiecare 5 minute
- ✅ Log complet în `bot_console.log`
- ⚠️ Trebuie să lași fereastra deschisă

---

## Verificare Status

Pot citi oricând:
- `ftmo_live_status.json` - status cont și poziții
- `bot_console.log` - log complet (dacă folosești Opțiunea 2 sau 4)

## Recomandarea Mea

**Pentru acum:** Opțiunea 1 (manual) ca să validăm că totul merge.

**Pentru 24/7:** Opțiunea 2 (serviciu Windows) - setezi odată și rulează automat.

**Alegi care variantă?**
