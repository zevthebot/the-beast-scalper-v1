#!/usr/bin/env python3
"""
The Beast Watchdog - Monitor 24/7 pentru runner
Verifică la fiecare 15 minute dacă runner-ul rulează și-l repornește dacă e nevoie

Usage: python the_beast_watchdog.py
"""

import subprocess
import sys
import os
from datetime import datetime
import time

# Configuration
RUNNER_SCRIPT = r"C:\Users\Claw\.openclaw\workspace\mt5_trader\THE_BEAST\the_beast_runner.py"
LOG_FILE = r"C:\Users\Claw\.openclaw\workspace\mt5_trader\THE_BEAST\watchdog.log"

def log(msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line)
    try:
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(line + "\n")
    except:
        pass

def is_process_running(process_name):
    """Check if a Python process is running with the given script"""
    try:
        result = subprocess.run(
            ['powershell', '-Command', 
             f'Get-Process python -ErrorAction SilentlyContinue | Where-Object {{$_.Path -like "*python*"}} | Select-Object Id'],
            capture_output=True,
            text=True,
            timeout=10
        )
        return 'Id' in result.stdout or result.returncode == 0
    except:
        return False

def restart_runner():
    """Restart the runner in background"""
    try:
        log("[WATCHDOG] Bot runner not running! Restarting...")
        
        process = subprocess.Popen(
            [sys.executable, RUNNER_SCRIPT],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS,
            close_fds=True
        )
        
        log(f"[WATCHDOG] Runner restarted with PID: {process.pid}")
        return True
        
    except Exception as e:
        log(f"[ERROR] Failed to restart: {e}")
        return False

def main():
    log("=" * 60)
    log("THE BEAST WATCHDOG - Check started")
    log("=" * 60)
    
    # Check if bot is running (via runner)
    if is_process_running("python"):
        # Additional check - see if it's actually our bot by checking recent log activity
        crash_log = r"C:\Users\Claw\.openclaw\workspace\mt5_trader\THE_BEAST\crash_log.txt"
        if os.path.exists(crash_log):
            mtime = os.path.getmtime(crash_log)
            if time.time() - mtime < 600:  # Active in last 10 minutes
                log("[WATCHDOG] Bot runner is running correctly [OK]")
                return 0
    
    # Not running, restart it
    if restart_runner():
        log("[WATCHDOG] Runner restarted successfully [OK]")
        return 0
    else:
        log("[WATCHDOG] Failed to restart runner [FAIL]")
        return 1

if __name__ == "__main__":
    sys.exit(main())
