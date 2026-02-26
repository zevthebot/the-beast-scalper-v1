import json, time, os

time.sleep(20)

path = r'C:\Users\Claw\AppData\Roaming\MetaQuotes\Terminal\Common\Files\ZevBot_Status.json'
if os.path.exists(path):
    with open(path, 'rb') as f:
        data = json.loads(f.read().decode('utf-16'))
    
    ts = data.get('timestamp', 'unknown')
    print(f"EA Status timestamp: {ts}")
    print(f"Session active: {data.get('session_active')}")
    print(f"Positions: {data.get('positions_count', 0)}")
    print(f"Balance: {data.get('balance')}")
    print(f"Equity: {data.get('equity')}")
    print(f"Profit %: {data.get('profit_pct')}")
else:
    print("Status file not found - EA may not be loaded on chart")
    print("You may need to manually drag EA onto chart in MT5")
