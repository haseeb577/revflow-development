#!/usr/bin/env python3
"""
RevCORE Layer 8 API - Essential Management Endpoints
Port: 8951
"""
import subprocess
import json
from datetime import datetime
from fastapi import FastAPI
from fastapi.responses import JSONResponse
import uvicorn

app = FastAPI(title="RevCORE Layer 8 API", version="1.0")

@app.get("/")
async def root():
    return {"status": "online", "service": "RevCORE Layer 8 API", "port": 8951}

@app.get("/services/all")
async def get_all_services():
    """Get status of all systemd services"""
    try:
        result = subprocess.run(
            ["systemctl", "list-units", "--type=service", "--all", "--no-pager"],
            capture_output=True, text=True
        )
        lines = result.stdout.split('\n')
        services = []
        for line in lines:
            if '.service' in line:
                parts = line.split()
                if len(parts) >= 4:
                    services.append({
                        "name": parts[0],
                        "loaded": parts[1],
                        "active": parts[2],
                        "status": parts[3]
                    })
        return {"count": len(services), "services": services}
    except Exception as e:
        return {"error": str(e)}

@app.get("/services/dead")
async def get_dead_services():
    """Get services that are dead/failed"""
    try:
        result = subprocess.run(
            ["systemctl", "list-units", "--type=service", "--state=failed,dead", "--no-pager"],
            capture_output=True, text=True
        )
        lines = result.stdout.split('\n')
        services = []
        for line in lines:
            if '.service' in line:
                parts = line.split()
                if len(parts) >= 4:
                    services.append({
                        "name": parts[0],
                        "loaded": parts[1],
                        "active": parts[2],
                        "status": parts[3]
                    })
        return {"count": len(services), "services": services}
    except Exception as e:
        return {"error": str(e)}

@app.get("/services/stuck")
async def get_stuck_services():
    """Get services stuck in activating state"""
    try:
        result = subprocess.run(
            ["systemctl", "list-units", "--type=service", "--state=activating", "--no-pager"],
            capture_output=True, text=True
        )
        lines = result.stdout.split('\n')
        services = []
        for line in lines:
            if '.service' in line:
                parts = line.split()
                if len(parts) >= 4:
                    services.append({
                        "name": parts[0],
                        "loaded": parts[1],
                        "active": parts[2],
                        "status": parts[3]
                    })
        return {"count": len(services), "services": services}
    except Exception as e:
        return {"error": str(e)}

@app.get("/ports/listening")
async def get_listening_ports():
    """Get all listening ports"""
    try:
        result = subprocess.run(
            ["ss", "-tlnp"],
            capture_output=True, text=True
        )
        ports = []
        for line in result.stdout.split('\n')[1:]:
            if 'LISTEN' in line:
                parts = line.split()
                if len(parts) >= 4:
                    ports.append({
                        "port": parts[3],
                        "process": parts[-1] if len(parts) > 5 else "unknown"
                    })
        return {"count": len(ports), "ports": ports}
    except Exception as e:
        return {"error": str(e)}

@app.get("/nginx/status")
async def nginx_status():
    """Get NGINX status"""
    try:
        result = subprocess.run(
            ["systemctl", "is-active", "nginx"],
            capture_output=True, text=True
        )
        active = result.stdout.strip() == "active"
        
        # Test config
        test_result = subprocess.run(
            ["nginx", "-t"],
            capture_output=True, text=True
        )
        config_valid = test_result.returncode == 0
        
        return {
            "active": active,
            "config_valid": config_valid,
            "config_test_output": test_result.stderr
        }
    except Exception as e:
        return {"error": str(e)}

@app.post("/services/restart/{service_name}")
async def restart_service(service_name: str):
    """Restart a systemd service"""
    try:
        result = subprocess.run(
            ["systemctl", "restart", service_name],
            capture_output=True, text=True
        )
        success = result.returncode == 0
        return {
            "service": service_name,
            "action": "restart",
            "success": success,
            "output": result.stderr if not success else "Service restarted"
        }
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8951)
