import json
path = r'C:\Users\Claw\AppData\Roaming\MetaQuotes\Terminal\Common\Files\ZevBot_Status.json'
try:
    with open(path, 'rb') as f:
        data = json.loads(f.read().decode('utf-16'))
    print(f'Account in status file: {data.get("account", "unknown")}')
    print(f'Server: {data.get("server", "unknown")}')
    print(f'Balance: {data.get("balance")}')
    print(f'Timestamp: {data.get("timestamp")}')
except Exception as e:
    print(f'Error: {e}')
