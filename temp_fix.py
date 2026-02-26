def run_continuous_mode(trader, strategy):
    """Run continuous trading with 5-minute scan intervals, 30-minute reports, and 2-minute protection"""
    import time
    from datetime import datetime, timedelta
    
    cycle = 0
    next_report = datetime.now()
    last_protection = datetime.now() - timedelta(minutes=5)  # Run immediately on start
    
    print("\n" + "="*60)
    print("CONTINUOUS TRADING MODE ENABLED")
    print("="*60)
    print("[REPORT] Scan interval: 5 minutes (find new setups)")
    print("[PROTECT] Protection interval: 2 minutes (breakeven + trailing)")
    print("[TRAIL] Report interval: 30 minutes (account status)")
    print("="*60)
    print("Press Ctrl+C to stop")
    
    logger.info("Continuous mode started")
    
    try:
        while True:
            try:
                cycle += 1
                now = datetime.now()
                logger.debug(f"Cycle #{cycle} starting")
                
                # Check FTMO limits (with adaptive risk)
                can_trade, msg, hard_stop, risk_status = trader.check_ftmo_limits()
                logger.debug(f"Risk check: can_trade={can_trade}, hard_stop={hard_stop}")
                
                if hard_stop:
                    logger.warning(f"HARD STOP TRIGGERED: {msg}")
                    print(f"\n{'='*60}")
                    print("HARD STOP TRIGGERED - Trading halted")
                    print(f"Reason: {msg}")
                    print(f"{'='*60}")
                    break
                
                # Display risk status if not normal
                if risk_status and risk_status['status'] != 'SAFE':
                    logger.info(f"Risk status: {risk_status['status']} - {risk_status['message']}")
                    print(f"[RISK STATUS: {risk_status['status']}] {risk_status['message']}")
                
                # ==== RUN PROTECTION CYCLE (every 2 minutes) ====
                if (now - last_protection).seconds >= 120:  # 2 minutes
                    try:
                        protection_results = trader.run_full_protection_cycle()
                        logger.debug(f"Protection cycle completed: {protection_results}")
                    except Exception as prot_err:
                        logger.error(f"Protection cycle error: {prot_err}")
                    last_protection = now
                    time.sleep(1)  # Brief pause after protection
                
                # ==== RUN TRADING CYCLE (every 5 minutes) ====
                if cycle % 1 == 0:  # Every cycle (5 min)
                    try:
                        print(f"\n[{now.strftime('%H:%M:%S')}] Cycle #{cycle}: Scanning for new setups...")
                        strategy.run(auto_trade=True)
                        trader.export_status()
                        logger.debug(f"Trading cycle #{cycle} completed")
                    except Exception as trade_err:
                        logger.error(f"Trading cycle error: {trade_err}")
                        logger.error(traceback.format_exc())
                
                # ==== GENERATE REPORT (every 30 minutes) ====
                if now >= next_report:
                    try:
                        summary = trader.get_account_summary()
                        positions = trader.get_position_summary()
                        
                        profit = summary['profit']
                        profit_pct = summary['profit_pct'] * 100
                        equity = summary['equity']
                        
                        # Get daily metrics for report
                        daily_start = trader.daily_starting_equity or summary['balance']
                        daily_min = trader.daily_min_equity or daily_start
                        daily_max_loss = (daily_start - daily_min) / daily_start * 100 if daily_start > 0 else 0
                        
                        print(f"\n{'='*60}")
                        print(f"[REPORT] FTMO PHASE 1 REPORT - Cycle #{cycle}")
                        print(f"Time: {now.strftime('%Y-%m-%d %H:%M:%S')}")
                        print(f"{'='*60}")
                        print(f"Balance: ${summary['balance']:.2f}")
                        print(f"Equity:  ${equity:.2f}")
                        print(f"P&L:     ${profit:.2f} ({profit_pct:.2f}%)")
                        print(f"Progress: {profit_pct/10:.1f}% toward +10% target")
                        print(f"Positions: {len(positions)}/{risk_status['max_positions'] if risk_status else MAX_POSITIONS}")
                        print(f"Daily: Start ${daily_start:.2f} | Min ${daily_min:.2f} | Loss {daily_max_loss:.2f}% (limit 4%)")
                        print(f"Risk: {risk_status['status'] if risk_status else 'UNKNOWN'} | Lot mult: {risk_status['lot_multiplier'] if risk_status else 1.0}")
                        
                        if positions:
                            print("\nActive Positions:")
                            for pos in positions:
                                # Check breakeven status
                                if pos['type'] == 'BUY':
                                    is_be = pos['sl'] >= pos['open_price']
                                else:
                                    is_be = pos['sl'] <= pos['open_price'] and pos['sl'] > 0
                                sl_status = "[PROTECT] BE" if is_be else f"SL@{pos['sl']}"
                                print(f"  - {pos['symbol']} {pos['type']}: ${pos['profit']:.2f} [{sl_status}]")
                        
                        # Check profit target
                        if profit >= 1000:
                            print(f"\n[WIN] PROFIT TARGET REACHED! ${profit:.2f}")
                            break
                        if profit <= -800:
                            print(f"\n[ALERT] TOTAL LOSS LIMIT: ${profit:.2f}")
                            break
                            
                        print(f"{'='*60}")
                        next_report = now + timedelta(minutes=30)
                    except Exception as report_err:
                        logger.error(f"Report generation error: {report_err}")
                
                # Wait 5 minutes
                print("  [TIMER]  Waiting 5 minutes...")
                time.sleep(300)
                
            except Exception as cycle_error:
                logger.error(f"ERROR in cycle #{cycle}: {cycle_error}")
                logger.error(traceback.format_exc())
                print(f"\n[ERROR] Cycle #{cycle} failed: {cycle_error}")
                print("[RECOVER] Continuing to next cycle...")
                time.sleep(60)
                continue
                
    except KeyboardInterrupt:
        logger.info("Trading stopped by user (KeyboardInterrupt)")
        print("\n\nTrading stopped by user")
    except Exception as e:
        logger.error(f"FATAL ERROR in continuous mode: {e}")
        logger.error(traceback.format_exc())
        print(f"\n[FATAL ERROR] {e}")
        raise
    
    return True
