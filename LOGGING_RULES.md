# REGULI ABSOLUTE DE LOGGING - NU SE MODIFICĂ NICIODATĂ

## Regula #1 - Universal Journal este sacru

Orice trade executat în MT5, indiferent de:
- versiunea botului (v3, v4, v5, orice versiune viitoare)
- contul de tranzacționare (Pepperstone, FTMO, orice cont viitor)
- strategia folosită (PIN_BAR, ENGULFING, BREAKOUT, orice strategie viitoare)
- sesiunea de trading (London, NY, orice sesiune)

TREBUIE să logheze în universal_trade_journal.jsonl via UniversalJournal.

## Regula #2 - Câmpuri obligatorii la ENTRY

position_id, symbol, direction, lot_size, entry_price, sl, tp, strategy, bot_version, sl_pips, tp_pips, rr_planned, adx, atr_pips, rsi, volume_ratio, session, hour_utc, day_of_week, h4_trend, vwap_distance_pips, price_vs_ema8, price_vs_ema21

## Regula #3 - Câmpuri obligatorii la EXIT

position_id, pnl, pips, exit_reason, duration_min, mae_pips, mfe_pips, rr_achieved, exit_reason_detail

## Regula #4 - Niciun bot nu apelează mt5.order_send() direct

Toate execuțiile trec prin execute_trade() care include logging. Niciun shortcut, nicio excepție.

## Regula #5 - La orice versiune nouă

Primul lucru verificat înainte de a porni un bot nou:
- UniversalJournal.log_entry() apelat după order_send
- UniversalJournal.log_exit() apelat în check_closed_positions
- Toate câmpurile obligatorii prezente
