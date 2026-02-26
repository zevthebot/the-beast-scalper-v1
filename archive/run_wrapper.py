import sys
import os
import datetime

# Setup logging
log_file = open('C:\\Users\\Claw\\.openclaw\\workspace\\mt5_trader\\bot_wrapper.log', 'w')
original_stdout = sys.stdout
original_stderr = sys.stderr
sys.stdout = log_file
sys.stderr = log_file

def log(msg):
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {msg}")
    log_file.flush()

log("=== BOT WRAPPER STARTED ===")
log(f"Python executable: {sys.executable}")
log(f"Working directory: {os.getcwd()}")
log(f"Command line args: {sys.argv}")

try:
    log("Importing bot_controller...")
    import importlib.util
    spec = importlib.util.spec_from_file_location("bot_controller", "C:\\Users\\Claw\\.openclaw\\workspace\\mt5_trader\\bot_controller.py")
    bot_module = importlib.util.module_from_spec(spec)
    
    log("Executing bot_controller module...")
    spec.loader.exec_module(bot_module)
    
    log("=== BOT EXECUTION COMPLETE ===")
    
except Exception as e:
    import traceback
    log(f"ERROR: {e}")
    log("Traceback:")
    log(traceback.format_exc())
    log("=== BOT EXECUTION FAILED ===")

finally:
    log_file.close()
    sys.stdout = original_stdout
    sys.stderr = original_stderr
    print("Bot wrapper completed. Check bot_wrapper.log")
