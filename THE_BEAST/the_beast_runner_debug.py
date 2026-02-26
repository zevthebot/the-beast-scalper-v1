#!/usr/bin/env python3
"""
The Beast Runner - Debug version with full error capture
"""

import subprocess
import sys
import os
from datetime import datetime
import time
import traceback

BOT_SCRIPT = r"C:\Users\Claw\.openclaw\workspace\mt5_trader\bot_controller.py"
LOG_FILE = r"C:\Users\Claw\.openclaw\workspace\mt5_trader\THE_BEAST\debug_crash.log"

def log(msg, error=False):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    prefix = "[ERROR]" if error else "[INFO]"
    line = f"{timestamp} {prefix} {msg}\n"
    print(line.strip())
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(line)

def run_bot():
    log("=" * 70)
    log("STARTING THE BEAST BOT - DEBUG MODE")
    log("=" * 70)
    
    try:
        work_dir = os.path.dirname(BOT_SCRIPT)
        os.chdir(work_dir)
        
        # Run bot and capture ALL output including errors
        process = subprocess.Popen(
            [sys.executable, '-u', BOT_SCRIPT, '--continuous'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,  # Capture stderr separately
            text=True,
            bufsize=1,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
        )
        
        log(f"Bot PID: {process.pid}")
        
        # Read both stdout and stderr
        while True:
            stdout_line = process.stdout.readline()
            stderr_line = process.stderr.readline()
            
            if stdout_line:
                stdout_line = stdout_line.strip()
                print(f"[OUT] {stdout_line}")
                if any(k in stdout_line for k in ['ERROR', 'CRASH', 'TRADE', 'EXECUTED']):
                    log(f"BOT: {stdout_line}")
            
            if stderr_line:
                stderr_line = stderr_line.strip()
                print(f"[ERR] {stderr_line}", file=sys.stderr)
                log(f"STDERR: {stderr_line}", error=True)
            
            # Check if process ended
            if process.poll() is not None and not stdout_line and not stderr_line:
                break
        
        return_code = process.wait()
        log(f"Bot exited with code: {return_code}")
        
        # Get any remaining stderr
        remaining_err = process.stderr.read()
        if remaining_err:
            log(f"REMAINING STDERR: {remaining_err}", error=True)
        
        return return_code
        
    except Exception as e:
        log(f"RUNNER EXCEPTION: {e}", error=True)
        log(traceback.format_exc(), error=True)
        return 1

def main():
    restart_count = 0
    max_restarts = 10
    
    while restart_count < max_restarts:
        exit_code = run_bot()
        restart_count += 1
        
        if exit_code == 0:
            log("Bot exited normally")
            break
        else:
            log(f"CRASH #{restart_count} - Exit code: {exit_code}", error=True)
            log("Waiting 10 seconds before restart...")
            time.sleep(10)
    
    if restart_count >= max_restarts:
        log(f"MAX RESTARTS ({max_restarts}) REACHED", error=True)
        return 1
    
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        log("Runner stopped by user")
        sys.exit(0)
