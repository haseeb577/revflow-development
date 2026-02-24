#!/usr/bin/env python3
"""RevCore™ - Port Conflict Detection"""

import subprocess
import re
import sys

def get_listening_ports():
    try:
        result = subprocess.run(['ss', '-tlnp'], capture_output=True, text=True)
        ports = set()
        for line in result.stdout.split('\n'):
            match = re.search(r':(\d+)\s', line)
            if match:
                ports.add(int(match.group(1)))
        return ports
    except:
        return set()

def check_port(port):
    used = get_listening_ports()
    if port in used:
        print(f"❌ Port {port} is in use")
        return False
    else:
        print(f"✅ Port {port} is available")
        return True

def suggest_port(start=8000):
    used = get_listening_ports()
    for port in range(start, 9000):
        if port not in used:
            print(port)
            return port
    return None

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: port-manager.py [check|suggest] [port]")
        sys.exit(1)
    
    cmd = sys.argv[1]
    if cmd == "check" and len(sys.argv) == 3:
        port = int(sys.argv[2])
        available = check_port(port)
        sys.exit(0 if available else 1)
    elif cmd == "suggest":
        suggest_port()
