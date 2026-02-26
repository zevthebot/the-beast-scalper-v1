#!/usr/bin/env python3
"""
FTMO Protection Manager - Management Avansat Posiții
Rulează paralel cu EA-ul din MT5, DOAR pentru protecție (breakeven + trailing)
Nu deschide poziții noi - lasă EA-ul să tranzacționeze.
"""

import MetaTrader5 as mt5
import time
from datetime import datetime, timedelta
import json
import sys

# Configurare
MAGIC_NUMBER = 234000  # Același ca EA-ul din MT5
MIN_PROFIT_PIPS_BE = 15  # Breakeven la +15 pips
EXPORT_PATH = "mt5_ftmo_status.json"

# Culori pentru output
COLOR_GREEN = '\033[92m'
COLOR_YELLOW = '\033[93m'
COLOR_RED = '\033[91m'
COLOR_BLUE = '\033[94m'
COLOR_RESET = '\033[0m'


def log(msg, color=COLOR_RESET):
    timestamp = datetime.now().strftime('%H:%M:%S')
    print(f"{color}[{timestamp}] {msg}{COLOR_RESET}")
    sys.stdout.flush()


def connect_mt5():
    """Conectează la MT5"""
    if not mt5.initialize():
        log("❌ Eroare initializare MT5", COLOR_RED)
        return False
    
    account_info = mt5.account_info()
    if account_info is None:
        log("⚠️ MT5 deschis dar nu ești logat în cont", COLOR_YELLOW)
        return False
    
    log(f"✅ Conectat la MT5 - Cont: {account_info.login}", COLOR_GREEN)
    return True


def get_positions():
    """Obține toate pozițiile deschise cu magic number-ul nostru"""
    positions = mt5.positions_get()
    if positions is None:
        return []
    
    # Filtrează doar pozițiile deschise de bot/EA (magic number)
    our_positions = [p for p in positions if p.magic == MAGIC_NUMBER]
    return our_positions


def apply_breakeven():
    """Mută SL la prețul de intrare când profitul e >= 15 pips"""
    positions = get_positions()
    if not positions:
        return 0
    
    protected = 0
    
    for pos in positions:
        symbol = pos.symbol
        ticket = pos.ticket
        pos_type = pos.type  # 0 = BUY, 1 = SELL
        open_price = pos.price_open
        current_sl = pos.sl
        
        # Obține info simbol
        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            continue
        
        point = symbol_info.point
        digits = symbol_info.digits
        
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            continue
        
        # Calculează profit în pips
        if pos_type == 0:  # BUY
            # Skip dacă e deja protejat
            if current_sl >= open_price:
                continue
            current_price = tick.bid
            profit_pips = (current_price - open_price) / (point * 10)
            new_sl = open_price
        else:  # SELL
            if current_sl <= open_price and current_sl != 0:
                continue
            current_price = tick.ask
            profit_pips = (open_price - current_price) / (point * 10)
            new_sl = open_price
        
        # Aplică breakeven dacă profit >= 15 pips
        if profit_pips >= MIN_PROFIT_PIPS_BE:
            request = {
                "action": mt5.TRADE_ACTION_SLTP,
                "position": ticket,
                "symbol": symbol,
                "sl": round(new_sl, digits),
                "tp": round(pos.tp, digits) if pos.tp else 0
            }
            
            result = mt5.order_send(request)
            
            if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                log(f"🛡️ BREAKEVEN: {symbol} #{ticket} - SL mutat la {new_sl:.5f} (profit: {profit_pips:.1f} pips)", COLOR_GREEN)
                protected += 1
            else:
                log(f"⚠️ Eroare breakeven {symbol}: {result.retcode if result else 'N/A'}", COLOR_RED)
    
    return protected


def apply_trailing_stop():
    """
    Trailing stop în 3 trepte:
    +30 pips → trail la +15
    +50 pips → trail la +30
    +80 pips → trail la +50
    """
    positions = get_positions()
    if not positions:
        return 0
    
    trailed = 0
    
    for pos in positions:
        symbol = pos.symbol
        ticket = pos.ticket
        pos_type = pos.type
        open_price = pos.price_open
        current_sl = pos.sl
        current_tp = pos.tp
        
        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            continue
        
        point = symbol_info.point
        digits = symbol_info.digits
        
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            continue
        
        # Calculează profit în pips
        if pos_type == 0:  # BUY
            current_price = tick.bid
            profit_pips = (current_price - open_price) / (point * 10)
            
            # Definește noile nivele SL pentru BUY
            if profit_pips >= 80:
                new_sl = open_price + (50 * point * 10)
            elif profit_pips >= 50:
                new_sl = open_price + (30 * point * 10)
            elif profit_pips >= 30:
                new_sl = open_price + (15 * point * 10)
            else:
                continue
            
            # Mută SL doar dacă e mai bun decât cel actual
            if new_sl <= current_sl:
                continue
                
        else:  # SELL
            current_price = tick.ask
            profit_pips = (open_price - current_price) / (point * 10)
            
            # Definește noile nivele SL pentru SELL
            if profit_pips >= 80:
                new_sl = open_price - (50 * point * 10)
            elif profit_pips >= 50:
                new_sl = open_price - (30 * point * 10)
            elif profit_pips >= 30:
                new_sl = open_price - (15 * point * 10)
            else:
                continue
            
            # Mută SL doar dacă e mai bun decât cel actual
            if new_sl >= current_sl and current_sl != 0:
                continue
        
        # Aplică trailing stop
        request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "position": ticket,
            "symbol": symbol,
            "sl": round(new_sl, digits),
            "tp": round(current_tp, digits) if current_tp else 0
        }
        
        result = mt5.order_send(request)
        
        if result and result.retcode == mt5.TRADE_RETCODE_DONE:
            tier = "T3" if profit_pips >= 80 else "T2" if profit_pips >= 50 else "T1"
            log(f"📈 TRAILING {tier}: {symbol} #{ticket} - SL mutat la {new_sl:.5f} (profit: {profit_pips:.1f} pips)", COLOR_BLUE)
            trailed += 1
    
    return trailed


def export_status():
    """Exportă statusul contului în JSON"""
    account_info = mt5.account_info()
    if account_info is None:
        return
    
    positions = get_positions()
    
    status = {
        "account": account_info.login,
        "server": account_info.server,
        "balance": account_info.balance,
        "equity": account_info.equity,
        "margin": account_info.margin,
        "free_margin": account_info.margin_free,
        "profit": account_info.profit,
        "currency": account_info.currency,
        "profit_pct": account_info.profit / account_info.balance,
        "positions_count": len(positions),
        "positions": [
            {
                "ticket": p.ticket,
                "symbol": p.symbol,
                "type": "BUY" if p.type == 0 else "SELL",
                "volume": p.volume,
                "open_price": p.price_open,
                "current_price": p.price_current,
                "sl": p.sl,
                "tp": p.tp,
                "profit": p.profit,
                "swap": p.swap,
                "magic": p.magic
            }
            for p in positions
        ],
        "timestamp": datetime.now().isoformat(),
        "ftmo_limits": {
            "max_daily_loss_pct": 0.04,
            "max_total_loss_pct": 0.08,
            "max_positions": 5,
            "profit_target": 0.10
        }
    }
    
    try:
        with open(EXPORT_PATH, 'w') as f:
            json.dump(status, f, indent=2)
    except Exception as e:
        log(f"⚠️ Eroare export status: {e}", COLOR_RED)


def protection_cycle():
    """Rulează un ciclu complet de protecție"""
    now = datetime.now()
    print(f"\n{'='*60}")
    log(f"🛡️ PROTECTION CYCLE - {now.strftime('%H:%M:%S')}", COLOR_YELLOW)
    print(f"{'='*60}")
    
    # 1. Breakeven
    be_count = apply_breakeven()
    
    # 2. Trailing
    trail_count = apply_trailing_stop()
    
    # 3. Export status
    export_status()
    
    # Rezumat
    positions = get_positions()
    if be_count > 0 or trail_count > 0:
        log(f"✅ Rezultat: {be_count} breakeven, {trail_count} trailing | Poziții active: {len(positions)}", COLOR_GREEN)
    else:
        log(f"ℹ️ Nicio acțiune necesară | Poziții active: {len(positions)}", COLOR_RESET)
    
    print(f"{'='*60}\n")


def main():
    """Loop principal - rulează la fiecare 2 minute"""
    print("\n" + "="*60)
    print("FTMO PROTECTION MANAGER")
    print("Management avansat poziții - Breakeven + Trailing Stop")
    print("="*60)
    print("\nSetări:")
    print(f"  • Breakeven la: +{MIN_PROFIT_PIPS_BE} pips")
    print(f"  • Trailing tiers: +30/+50/+80 pips")
    print(f"  • Magic number: {MAGIC_NUMBER}")
    print(f"  • Interval ciclu: 2 minute")
    print("\n⚠️  Acest script NU deschide poziții noi!")
    print("   Doar gestionează SL/TP pentru pozițiile existente.")
    print("\nApasă Ctrl+C pentru a opri")
    print("="*60 + "\n")
    
    # Conectare
    if not connect_mt5():
        print("\n❌ Nu mă pot conecta la MT5. Verifică:")
        print("   1. Dacă MT5 este deschis")
        print("   2. Dacă ești logat în contul FTMO")
        input("\nApasă Enter pentru a ieși...")
        return
    
    cycle_count = 0
    
    try:
        while True:
            cycle_count += 1
            protection_cycle()
            
            # Așteaptă 2 minute
            log("⏱️  Aștept 2 minute pentru următorul ciclu... (Ctrl+C pentru oprire)")
            time.sleep(120)
            
    except KeyboardInterrupt:
        print("\n\n" + "="*60)
        print("Protection Manager oprit de utilizator")
        print(f"Cicluri executate: {cycle_count}")
        print("="*60)
    
    finally:
        mt5.shutdown()
        log("Deconectat de la MT5", COLOR_YELLOW)


if __name__ == "__main__":
    main()
