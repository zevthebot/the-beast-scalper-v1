import subprocess
import json
import sys

def run_ps_command(command):
    """Run PowerShell command and return clean output"""
    try:
        result = subprocess.run(
            ['powershell', '-Command', command],
            capture_output=True,
            text=True,
            timeout=30
        )
        return {
            'stdout': result.stdout,
            'stderr': result.stderr,
            'returncode': result.returncode
        }
    except Exception as e:
        return {'error': str(e)}

if __name__ == "__main__":
    # Default command: list python processes
    cmd = "Get-Process python -ErrorAction SilentlyContinue | Select-Object Id, StartTime | ConvertTo-Json"
    
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
    
    result = run_ps_command(cmd)
    print(json.dumps(result, indent=2, default=str))
