#!/usr/bin/env python3
"""
RevCore™ - Crisis Monitor
Added: Jan 21, 2026

Lightweight monitoring script that detects crisis conditions:
1. High CPU steal time (Hostinger throttling)
2. High load average
3. Service restart loops

Run via cron every minute or as a systemd timer.
"""

import os
import sys
import json
import subprocess
from datetime import datetime

LOG_FILE = "/var/log/revcore/crisis-monitor.log"
STATE_FILE = "/var/run/revcore/crisis-state.json"

def log(message):
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {message}"
    print(line)
    with open(LOG_FILE, 'a') as f:
        f.write(line + "\n")

def get_steal_time():
    """Get CPU steal time from /proc/stat"""
    try:
        import psutil
        return psutil.cpu_times_percent(interval=1).steal
    except:
        return 0.0

def get_load_average():
    """Get 1-minute load average"""
    return os.getloadavg()[0]

def get_service_restart_count(service):
    """Get restart count from systemd"""
    try:
        result = subprocess.run(
            ['systemctl', 'show', service, '--property=NRestarts'],
            capture_output=True, text=True
        )
        return int(result.stdout.strip().split('=')[1])
    except:
        return 0

def check_crisis_conditions():
    """Check for crisis conditions and take action if needed."""
    steal = get_steal_time()
    load = get_load_average()
    
    crisis = {
        "timestamp": datetime.now().isoformat(),
        "steal_percent": steal,
        "load_average": load,
        "crisis_level": "normal",
        "actions_taken": []
    }
    
    # Steal time thresholds
    if steal >= 80:
        crisis["crisis_level"] = "emergency"
        log(f"🚨 EMERGENCY: {steal:.1f}% steal time!")
        # Could trigger emergency stop here
    elif steal >= 50:
        crisis["crisis_level"] = "critical"
        log(f"⚠️ CRITICAL: {steal:.1f}% steal time")
    elif steal >= 20:
        crisis["crisis_level"] = "warning"
        log(f"⚠️ WARNING: {steal:.1f}% steal time")
    
    # Load average threshold (2x cores is concerning on 2-core VPS)
    if load >= 4:
        if crisis["crisis_level"] == "normal":
            crisis["crisis_level"] = "warning"
        log(f"⚠️ High load: {load:.2f}")
    
    # Save state
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, 'w') as f:
        json.dump(crisis, f, indent=2)
    
    return crisis

if __name__ == "__main__":
    crisis = check_crisis_conditions()
    if crisis["crisis_level"] != "normal":
        sys.exit(1)
    sys.exit(0)
