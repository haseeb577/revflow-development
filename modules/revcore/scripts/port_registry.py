#!/usr/bin/env python3
"""
RevCORE™ Port Registry & Conflict Detection v2
Fixed: Process name matching logic
"""

import subprocess
import json
import os
from datetime import datetime
from pathlib import Path

# MASTER PORT REGISTRY
# "process" field lists ACCEPTABLE process names for each port
PORT_REGISTRY = {
    # Core Infrastructure
    22: {"service": "ssh", "process": ["sshd"], "type": "system", "critical": True},
    25: {"service": "postfix", "process": ["master", "postfix"], "type": "system", "critical": False},
    53: {"service": "systemd-resolved", "process": ["systemd-resolve", "systemd-resolved"], "type": "system", "critical": True},
    80: {"service": "nginx", "process": ["nginx"], "type": "system", "critical": True},
    443: {"service": "nginx-ssl", "process": ["nginx"], "type": "system", "critical": True},
    5432: {"service": "postgresql", "process": ["postgres", "postgresql"], "type": "database", "critical": True},
    6379: {"service": "redis", "process": ["redis-server", "redis"], "type": "database", "critical": True},
    
    # RevFlow Frontend UIs (3000-3999 range) - node/npx for React apps, python for static
    3100: {"service": "revaudit-frontend", "process": ["node", "npx", "python3", "python", "vite"], "type": "ui", "module": "RevAudit", "critical": False},
    3200: {"service": "revflow-platform-frontend", "process": ["node", "npx"], "type": "ui", "module": "RevFlow Platform", "critical": False},
    3401: {"service": "revdispatch-frontend", "process": ["python3", "python", "node"], "type": "ui", "module": "RevDispatch", "critical": False},
    3550: {"service": "revpublish-frontend", "process": ["node", "npm", "vite"], "type": "ui", "module": "RevPublish", "critical": False},
    3960: {"service": "revcore-ui", "process": ["python3", "python", "node"], "type": "ui", "module": "RevCORE", "critical": False},
    
    # RevFlow Backend APIs (8000-8999 range) - Python services
    8000: {"service": "smarketsherpa-platform", "process": ["python3", "python", "uvicorn", "gunicorn"], "type": "api", "module": "Platform", "critical": False},
    8001: {"service": "revrank-queue", "process": ["python3", "python", "uvicorn"], "type": "api", "module": "RevRank Engine", "critical": False},
    8100: {"service": "revscore-iq", "process": ["python3", "python", "uvicorn"], "type": "api", "module": "RevScore IQ", "critical": False},
    8103: {"service": "revrank-api", "process": ["python3", "python", "uvicorn"], "type": "api", "module": "RevRank Engine", "critical": False},
    8160: {"service": "revflow-charts", "process": ["python3", "python", "uvicorn"], "type": "api", "module": "RevFlow Charts", "critical": False},
    8162: {"service": "revflow-charts-api", "process": ["python3", "python", "uvicorn"], "type": "api", "module": "RevFlow Charts", "critical": False},
    8201: {"service": "revrank-orchestrator", "process": ["python3", "python", "uvicorn"], "type": "api", "module": "RevRank Engine", "critical": False},
    8202: {"service": "revflow-real-ui", "process": ["python3", "python", "node", "npx"], "type": "ui", "module": "RevFlow UI", "critical": False},
    8203: {"service": "revflow-ui-backend", "process": ["python3", "python", "uvicorn"], "type": "api", "module": "RevFlow UI", "critical": False},
    8210: {"service": "revrank-generator", "process": ["python3", "python", "uvicorn"], "type": "api", "module": "RevRank Engine", "critical": False},
    8220: {"service": "revrank-validator", "process": ["python3", "python", "uvicorn"], "type": "api", "module": "RevRank Engine", "critical": False},
    8299: {"service": "revrank-monitor", "process": ["python3", "python", "uvicorn"], "type": "api", "module": "RevRank Engine", "critical": False},
    8300: {"service": "revrank-publisher", "process": ["python3", "python", "uvicorn"], "type": "api", "module": "RevRank Engine", "critical": False},
    8310: {"service": "revrank-scheduler", "process": ["python3", "python", "uvicorn"], "type": "api", "module": "RevRank Engine", "critical": False},
    8320: {"service": "revrank-analytics", "process": ["python3", "python", "uvicorn"], "type": "api", "module": "RevRank Engine", "critical": False},
    8400: {"service": "revflow-ai-visibility", "process": ["python3", "python", "uvicorn"], "type": "api", "module": "AI Visibility", "critical": False},
    8401: {"service": "revdispatch-backend", "process": ["python3", "python", "uvicorn"], "type": "api", "module": "RevDispatch", "critical": False},
    8402: {"service": "revdispatch-worker", "process": ["python3", "python", "uvicorn"], "type": "api", "module": "RevDispatch", "critical": False},
    8500: {"service": "revflow-scoring-api", "process": ["python3", "python", "uvicorn"], "type": "api", "module": "RevScore", "critical": False},
    8501: {"service": "revdispatch-real-backend", "process": ["python3", "python", "uvicorn"], "type": "api", "module": "RevDispatch", "critical": False},
    8550: {"service": "revsignal-api", "process": ["python3", "python", "uvicorn"], "type": "api", "module": "RevSignal", "critical": False},
    8600: {"service": "revimage-backend", "process": ["python3", "python", "uvicorn"], "type": "api", "module": "RevImage", "critical": False},
    8601: {"service": "revimage-ui", "process": ["python3", "python", "node"], "type": "ui", "module": "RevImage", "critical": False},
    8750: {"service": "revvest-api", "process": ["python3", "python", "uvicorn", "node"], "type": "api", "module": "RevVest", "critical": False},
    8765: {"service": "guru-intelligence", "process": ["python3", "python", "uvicorn"], "type": "api", "module": "Guru Intelligence", "critical": False},
    8766: {"service": "revflow-unknown-8766", "process": ["python3", "python", "uvicorn"], "type": "api", "module": "Unknown", "critical": False},
    8767: {"service": "revflow-heatmap", "process": ["python3", "python", "uvicorn"], "type": "api", "module": "Heatmap", "critical": False},
    8800: {"service": "revprompt-api", "process": ["python3", "python", "uvicorn"], "type": "api", "module": "RevPrompt", "critical": False},
    8900: {"service": "revcite-main", "process": ["python3", "python", "uvicorn"], "type": "api", "module": "RevCite Pro", "critical": False},
    8901: {"service": "revcite-tracker", "process": ["python3", "python", "uvicorn"], "type": "api", "module": "RevCite Pro", "critical": False},
    8902: {"service": "revcite-builder", "process": ["python3", "python", "uvicorn"], "type": "api", "module": "RevCite Pro", "critical": False},
    8903: {"service": "revcite-analyzer", "process": ["python3", "python", "uvicorn"], "type": "api", "module": "RevCite Pro", "critical": False},
    8950: {"service": "revcore-api", "process": ["python3", "python", "uvicorn"], "type": "api", "module": "RevCORE", "critical": True},
    8960: {"service": "revguard-v3", "process": ["python3", "python", "uvicorn"], "type": "api", "module": "RevGuard", "critical": True},
    
    # Management UIs (9000-9999 range)
    9000: {"service": "dev-agent-dashboard", "process": ["python3", "python", "node"], "type": "ui", "module": "Dev Tools", "critical": False},
    9010: {"service": "minio-api", "process": ["minio"], "type": "storage", "module": "MinIO", "critical": False},
    9011: {"service": "minio-console", "process": ["minio"], "type": "ui", "module": "MinIO", "critical": False},
}

class PortConflictDetector:
    def __init__(self):
        self.registry = PORT_REGISTRY
        
    def get_active_ports(self):
        """Get all currently listening ports"""
        result = subprocess.run(['ss', '-tlnp'], capture_output=True, text=True)
        active = {}
        
        for line in result.stdout.split('\n'):
            if 'LISTEN' in line:
                parts = line.split()
                if len(parts) >= 4:
                    addr = parts[3]
                    try:
                        port = int(addr.split(':')[-1])
                    except:
                        continue
                    
                    # Extract process name
                    process = "unknown"
                    if 'users:' in line:
                        try:
                            process = line.split('users:((')[1].split('"')[1]
                        except:
                            pass
                    
                    active[port] = {
                        "process": process,
                        "address": addr,
                    }
        
        return active
    
    def detect_conflicts(self):
        """Detect REAL port conflicts (not false positives)"""
        active = self.get_active_ports()
        conflicts = []
        healthy = []
        missing_critical = []
        unregistered = []
        
        # Check registered ports
        for port, info in self.registry.items():
            if port in active:
                actual_process = active[port]["process"]
                allowed_processes = info.get("process", [])
                
                # Check if actual process is in allowed list
                if actual_process in allowed_processes or actual_process == "unknown":
                    healthy.append({
                        "port": port,
                        "service": info["service"],
                        "module": info.get("module", "Unknown"),
                        "process": actual_process,
                        "status": "OK"
                    })
                else:
                    # REAL conflict - wrong process on this port
                    conflicts.append({
                        "port": port,
                        "expected_service": info["service"],
                        "expected_processes": allowed_processes,
                        "actual_process": actual_process,
                        "module": info.get("module", "Unknown"),
                        "severity": "CRITICAL" if info.get("critical") else "WARNING"
                    })
            else:
                # Port not listening
                if info.get("critical"):
                    missing_critical.append({
                        "port": port,
                        "service": info["service"],
                        "module": info.get("module", "Unknown"),
                        "status": "NOT RUNNING"
                    })
        
        # Check for unregistered ports
        for port, info in active.items():
            if port not in self.registry and port > 1024:
                unregistered.append({
                    "port": port,
                    "process": info["process"],
                    "status": "UNREGISTERED"
                })
        
        return {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "healthy": len(healthy),
                "conflicts": len(conflicts),
                "missing_critical": len(missing_critical),
                "unregistered": len(unregistered)
            },
            "conflicts": conflicts,
            "missing_critical": missing_critical,
            "unregistered": unregistered,
            "healthy": healthy
        }
    
    def check_port_available(self, port):
        """Check if a specific port is available"""
        active = self.get_active_ports()
        
        if port in active:
            return {
                "available": False,
                "in_use_by": active[port]["process"],
                "registered_for": self.registry.get(port, {}).get("service", "Unregistered")
            }
        
        return {
            "available": True,
            "registered_for": self.registry.get(port, {}).get("service", "Unregistered")
        }
    
    def generate_report(self):
        """Generate comprehensive port report"""
        active = self.get_active_ports()
        detection = self.detect_conflicts()
        
        return {
            "timestamp": datetime.now().isoformat(),
            "summary": detection["summary"],
            "details": detection,
            "total_listening": len(active),
            "total_registered": len(self.registry)
        }


if __name__ == "__main__":
    import sys
    
    detector = PortConflictDetector()
    result = detector.detect_conflicts()
    
    print(f"\n{'='*60}")
    print(f"  RevCORE™ Port Health Report")
    print(f"{'='*60}")
    print(f"\n📊 Summary:")
    print(f"   ✅ Healthy ports: {result['summary']['healthy']}")
    print(f"   ⚠️  Conflicts: {result['summary']['conflicts']}")
    print(f"   ❌ Missing Critical: {result['summary']['missing_critical']}")
    print(f"   ❓ Unregistered: {result['summary']['unregistered']}")
    
    if result["conflicts"]:
        print(f"\n⚠️  REAL Conflicts (wrong process on port):")
        for c in result["conflicts"]:
            print(f"   Port {c['port']}: Expected {c['expected_processes']}, Found '{c['actual_process']}'")
    
    if result["missing_critical"]:
        print(f"\n❌ Missing CRITICAL Services:")
        for m in result["missing_critical"]:
            print(f"   Port {m['port']}: {m['service']} ({m['module']}) - NOT RUNNING")
    
    if not result["conflicts"] and not result["missing_critical"]:
        print(f"\n✅ All registered services are healthy!")
