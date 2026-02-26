#!/usr/bin/env python3
"""
The Beast Runner - Wrapper care rulează botul și loghează toate erorile
Folosește: python the_beast_runner.py
"""

import subprocess
import sys
import os
from datetime import datetime
import time
import traceback

# Configuration
BOT_SCRIPT = r"C:\Users\Claw\.openclaw\workspace\mt5_trader\bot_controller.py"
LOG_FILE = r"C:\Users\Claw\.openclaw\workspace\mt5_trader\THE_BEAST\crash_log.txt"

def log(msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}\n"
    print(line.strip())
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(line)

def run_bot():
    """Run the bot and capture all output and errors"""
    log("=" * 60)
    log("Starting The Beast Bot")
    log("=" * 60)
    
    try:
        # Change to working directory
        work_dir = os.path.dirname(BOT_SCRIPT)
        os.chdir(work_dir)
        
        # Run bot with full output capture
        process = subprocess.Popen(
            [sys.executable, '-u', BOT_SCRIPT, '--continuous'],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,  # Merge stderr into stdout
            text=True,
            bufsize=1,  # Line buffered
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
        )
        
        log(f"Bot started with PID: {process.pid}")
        
        # Read output line by line and log it
        for line in process.stdout:
            line = line.strip()
            if line:
                print(line)  # Show in console
                # Also log important lines
                if any(keyword in line for keyword in ['ERROR', 'CRASH', 'FATAL', 'TRADE', 'EXECUTED', 'REPORT']):
                    with open(LOG_FILE, 'a', encoding='utf-8') as f:
                        f.write(f"[{datetime.now().strftime('%H:%M:%S')}] {line}\n")
        
        # Wait for process to finish
        return_code = process.wait()
        log(f"Bot exited with code: {return_code}")
        return return_code
        
    except Exception as e:
        log(f"RUNNER ERROR: {e}")
        log(traceback.format_exc())
        return 1

def main():
    """Main loop - restart bot if it crashes"""
    restart_count = 0
    max_restarts = 10
    
    while restart_count < max_restarts:
        exit_code = run_bot()
        restart_count += 1
        
        if exit_code == 0:
            log("Bot exited normally")
            break
        else:
            log(f"Bot crashed (exit code: {exit_code}). Restart #{restart_count} in 10 seconds...")
            time.sleep(10)
    
    if restart_count >= max_restarts:
        log(f"Max restarts ({max_restarts}) reached. Giving up.")
        return 1
    
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        log("Runner stopped by user")
        sys.exit(0)
