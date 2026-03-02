#!/usr/bin/env python3
"""
THE BEAST 4.0 - Standalone Runner
Runs independently of OpenClaw via Windows Task Scheduler or pythonw.
Includes its own watchdog loop + crash recovery.
"""

import subprocess
import sys
import os
import time
import logging
from datetime import datetime
from pathlib import Path

BOT_SCRIPT = Path(r"C:\Users\Claw\.openclaw\workspace\mt5_trader\the_beast_v4_price_action.py")
LOG_DIR = Path(r"C:\Users\Claw\.openclaw\workspace\mt5_trader\logs")
LOG_DIR.mkdir(exist_ok=True)

# Setup file logging (survives terminal close)
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler(LOG_DIR / 'standalone_bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
log = logging.getLogger('standalone')

# Lock file to prevent multiple instances
LOCK_FILE = LOG_DIR / 'standalone.lock'

def is_running():
    """Check if another instance is running via lock file"""
    if LOCK_FILE.exists():
        try:
            pid = int(LOCK_FILE.read_text().strip())
            # Check if PID is alive on Windows
            import ctypes
            kernel32 = ctypes.windll.kernel32
            handle = kernel32.OpenProcess(0x100000, False, pid)  # SYNCHRONIZE
            if handle:
                kernel32.CloseHandle(handle)
                return True
        except:
            pass
        # Stale lock file
        LOCK_FILE.unlink(missing_ok=True)
    return False

def acquire_lock():
    LOCK_FILE.write_text(str(os.getpid()))

def release_lock():
    LOCK_FILE.unlink(missing_ok=True)

def run_bot():
    """Run bot as subprocess, return exit code"""
    log.info(f'Starting bot: {BOT_SCRIPT.name}')
    
    try:
        process = subprocess.Popen(
            [sys.executable, '-u', str(BOT_SCRIPT)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
        )
        
        log.info(f'Bot PID: {process.pid}')
        
        for line in process.stdout:
            line = line.rstrip()
            if line:
                # Log important events to file
                if any(k in line for k in ['[EXECUTED]', '[CLOSED]', '[ERROR]', '[SIGNAL]', 'Traceback', 'Error']):
                    log.info(line)
                # Always print to console if visible
                print(line, flush=True)
        
        code = process.wait()
        log.info(f'Bot exited with code {code}')
        return code
        
    except Exception as e:
        log.error(f'Failed to run bot: {e}', exc_info=True)
        return -1

def main():
    if is_running():
        print('Standalone bot already running. Exiting.')
        sys.exit(0)
    
    acquire_lock()
    
    try:
        log.info('=' * 60)
        log.info('STANDALONE BOT RUNNER - Independent of OpenClaw')
        log.info(f'Bot: {BOT_SCRIPT.name}')
        log.info(f'PID: {os.getpid()}')
        log.info('=' * 60)
        
        consecutive_crashes = 0
        MAX_RAPID_CRASHES = 5
        
        while True:
            start_time = time.time()
            exit_code = run_bot()
            run_duration = time.time() - start_time
            
            if run_duration < 30:
                # Crashed within 30 seconds - likely a code bug
                consecutive_crashes += 1
                log.warning(f'Rapid crash #{consecutive_crashes} (ran {run_duration:.0f}s)')
                
                if consecutive_crashes >= MAX_RAPID_CRASHES:
                    log.error(f'Too many rapid crashes ({MAX_RAPID_CRASHES}). Stopping.')
                    break
                
                # Exponential backoff: 10s, 20s, 40s, 80s, 160s
                wait = min(10 * (2 ** (consecutive_crashes - 1)), 300)
                log.info(f'Waiting {wait}s before retry (backoff)')
                time.sleep(wait)
            else:
                # Ran for a while, normal restart
                consecutive_crashes = 0
                log.info('Restarting in 10s...')
                time.sleep(10)
    
    except KeyboardInterrupt:
        log.info('Stopped by user')
    finally:
        release_lock()

if __name__ == '__main__':
    main()
