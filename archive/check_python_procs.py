import psutil
import json
import sys

def get_python_processes():
    processes = []
    for proc in psutil.process_iter(['pid', 'name', 'create_time']):
        if 'python' in proc.info['name'].lower():
            processes.append({
                'pid': proc.info['pid'],
                'name': proc.info['name'],
                'start_time': str(proc.info['create_time'])
            })
    return processes

if __name__ == "__main__":
    try:
        procs = get_python_processes()
        print(json.dumps(procs, indent=2))
    except Exception as e:
        print(json.dumps({'error': str(e)}))
