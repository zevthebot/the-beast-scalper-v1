#!/usr/bin/env python3
"""
Bot Watchdog - Keeps pepperstone_ml_trader.py running 24/7
Restarts automatically if bot crashes or stops
"""

import subprocess
import time
import sys
import os
from datetime import datetime

BOT_SCRIPT = r"C:\Users\Claw\.openclaw\workspace\mt5_trader\pepperstone_ml_trader.py"
LOG_FILE = r"C:\Users\Claw\.openclaw\workspace\mt5_trader\watchdog.log"

def log(message):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_msg = f"[{timestamp}] {message}"
    print(log_msg)
    with open(LOG_FILE, 'a') as f:
        f.write(log_msg + '\n')

def run_bot():
    """Run the bot and return when it exits"""
    log("Starting bot...")
    try:
        # Run bot in subprocess
        process = subprocess.Popen(
            [sys.executable, BOT_SCRIPT],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        
        log(f"Bot started with PID {process.pid}")
        
        # Read output in real-time
        for line in process.stdout:
            print(line, end='')
            # Also log to file if needed
            if '[EXECUTED]' in line or '[CLOSED]' in line or '[ERROR]' in line:
                log(line.strip())
        
        # Wait for process to complete
        return_code = process.wait()
        log(f"Bot exited with code {return_code}")
        return return_code
        
    except Exception as e:
        log(f"Error running bot: {e}")
        return -1

def main():
    log("=" * 50)
    log("WATCHDOG STARTED - 24/7 Bot Monitoring")
    log("=" * 50)
    
    restart_count = 0
    
    while True:
        restart_count += 1
        log(f"Bot run attempt #{restart_count}")
        
        exit_code = run_bot()
        
        if exit_code == 0:
            log("Bot exited normally (unexpected)")
        else:
            log(f"Bot crashed or exited with error (code: {exit_code})")
        
        # Wait before restarting
        log("Waiting 10 seconds before restart...")
        time.sleep(10)
        
        log("Restarting bot...")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("Watchdog stopped by user")
        sys.exit(0)
