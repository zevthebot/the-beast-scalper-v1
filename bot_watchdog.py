#!/usr/bin/env python3
"""
Bot Watchdog - Keeps pepperstone_ml_trader.py running 24/7
Prevents multiple instances using PID file
"""

import subprocess
import time
import sys
import os
from datetime import datetime

# ABSOLUTE PATH
BOT_SCRIPT = r"C:\Users\Claw\.openclaw\workspace\mt5_trader\pepperstone_ml_trader.py"
LOG_FILE = r"C:\Users\Claw\.openclaw\workspace\mt5_trader\watchdog.log"
PID_FILE = r"C:\Users\Claw\.openclaw\workspace\mt5_trader\watchdog.pid"

def log(message):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_msg = f"[{timestamp}] {message}"
    print(log_msg, flush=True)
    with open(LOG_FILE, 'a') as f:
        f.write(log_msg + '\n')

def is_already_running():
    """Check if another watchdog is already running"""
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE, 'r') as f:
                old_pid = int(f.read().strip())
            # Check if process exists
            import ctypes
            kernel32 = ctypes.windll.kernel32
            handle = kernel32.OpenProcess(1, False, old_pid)
            if handle:
                kernel32.CloseHandle(handle)
                return True
        except:
            pass
    return False

def write_pid():
    """Write current PID to file"""
    with open(PID_FILE, 'w') as f:
        f.write(str(os.getpid()))

def remove_pid():
    """Remove PID file"""
    try:
        os.remove(PID_FILE)
    except:
        pass

def run_bot():
    """Run the bot and return when it exits"""
    log(f"Starting bot: {BOT_SCRIPT}")
    
    if not os.path.exists(BOT_SCRIPT):
        log(f"ERROR: Bot script not found: {BOT_SCRIPT}")
        return -1
    
    try:
        process = subprocess.Popen(
            [sys.executable, '-u', BOT_SCRIPT],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        
        log(f"Bot started with PID {process.pid}")
        
        for line in process.stdout:
            print(line, end='', flush=True)
            if any(k in line for k in ['[EXECUTED]', '[CLOSED]', '[ERROR]', '[MAX]', '[SIGNAL]']):
                log(line.strip())
        
        return_code = process.wait()
        log(f"Bot exited with code {return_code}")
        return return_code
        
    except Exception as e:
        log(f"Error running bot: {e}")
        import traceback
        log(traceback.format_exc())
        return -1

def main():
    # Check if already running
    if is_already_running():
        print("Watchdog already running! Exiting.")
        sys.exit(0)
    
    write_pid()
    
    try:
        log("=" * 60)
        log("WATCHDOG STARTED - 24/7 Bot Monitoring")
        log(f"Target script: {BOT_SCRIPT}")
        log("=" * 60)
        
        restart_count = 0
        
        while True:
            restart_count += 1
            log(f"Bot run attempt #{restart_count}")
            
            exit_code = run_bot()
            
            if exit_code == 0:
                log("Bot exited normally")
            else:
                log(f"Bot crashed or exited with error (code: {exit_code})")
            
            log("Waiting 10 seconds before restart...")
            time.sleep(10)
            log("Restarting bot...")
    
    finally:
        remove_pid()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("Watchdog stopped by user")
        remove_pid()
        sys.exit(0)
