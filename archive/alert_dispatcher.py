#!/usr/bin/env python3
"""
Smart Alert Dispatcher - Only sends notifications for actual errors
"""

import subprocess
import sys
from pathlib import Path
import json
from datetime import datetime

def main():
    # Run the actual checker
    checker_path = Path(__file__).parent / "critical_checker.py"
    result = subprocess.run(
        [sys.executable, str(checker_path)],
        capture_output=True,
        text=True
    )
    
    # Check if alert file was created
    alert_file = Path(__file__).parent / "critical_alert_pending.json"
    
    if alert_file.exists() and result.returncode == 1:
        # Read and display the alert
        with open(alert_file, 'r') as f:
            data = json.load(f)
        
        print(data["alert"])
        
        # Remove the alert file
        alert_file.unlink()
        
        return 1  # Signal that alert was sent
    else:
        # No alert - silent
        return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
