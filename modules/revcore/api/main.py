"""
RevCore™ MODULE 12: Unified Intelligence Platform API - ENHANCED
Integrated with RevFlow OS 18-Module Architecture
Multi-Database Support, Restart Mechanism Management, Memory Monitoring
Port: 8950
Database: PostgreSQL localhost:5432/revflow_db

RevAudit Integration: ENABLED - Zero tolerance for hallucination
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import subprocess
import os
import json
import psycopg2
from datetime import datetime
import re
import sys

# RevAudit Anti-Hallucination Integration
sys.path.insert(0, '/opt/shared-api-engine')
try:
    from revaudit.integrate import integrate_revaudit
    REVAUDIT_AVAILABLE = True
except ImportError:
    REVAUDIT_AVAILABLE = False

app = FastAPI(
    title="RevCore™ MODULE 12 - Unified Intelligence Platform",
    description="Service Orchestration, Database Management, Port Control, Restart Detection",
    version="2.0.0 ENHANCED"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# RevAudit Integration
if REVAUDIT_AVAILABLE:
    integrate_revaudit(app, "RevCore_API")

# SINGLE SOURCE OF TRUTH
SHARED_ENV = "/opt/shared-api-engine/.env"
POSTGRES_DB = "revflow_db"
POSTGRES_HOST = "localhost"
POSTGRES_PORT = "5432"

################################################################################
# Helper Functions
################################################################################

def load_env():
    """Load environment from SINGLE SOURCE OF TRUTH"""
    env = {}
    if os.path.exists(SHARED_ENV):
        with open(SHARED_ENV) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env[key.strip()] = value.strip()
    return env

def get_db_connection():
    """Get PostgreSQL connection using shared .env"""
    env = load_env()
    try:
        conn = psycopg2.connect(
            host=env.get('POSTGRES_HOST', POSTGRES_HOST),
            port=env.get('POSTGRES_PORT', POSTGRES_PORT),
            database=env.get('POSTGRES_DB', POSTGRES_DB),
            user=env.get('POSTGRES_USER', 'postgres'),
            password=env.get('POSTGRES_PASSWORD', '')
        )
        return conn
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database connection failed: {str(e)}")

def execute_query(query, params=None, fetch=True):
    """Execute SQL query safely"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        if params:
            cur.execute(query, params)
        else:
            cur.execute(query)
        
        result = None
        if fetch:
            result = cur.fetchall()
        
        conn.commit()
        cur.close()
        conn.close()
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")

################################################################################
# Models
################################################################################

class ServiceAction(BaseModel):
    action: str  # "start", "stop", "restart", "kill"
    service_names: List[str]

class PortCheck(BaseModel):
    port: int

class RestartMechanismAction(BaseModel):
    mechanism_type: str  # "systemd", "docker", "cron", "tmux", "startup_script"
    action: str  # "disable", "enable", "kill"

################################################################################
# API Endpoints
################################################################################

@app.get("/health")
@app.get("/api/v1/health")
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "module": "RevCore Module 17",
        "version": "2.0.0",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/v1/modules/all")
def get_all_modules():
    """Get all 18 RevFlow OS modules"""
    query = """
        SELECT module_number, module_name, service_name, category, 
               port, directory_path, auto_heal, status
        FROM revcore_service_registry
        ORDER BY module_number
    """
    
    try:
        results = execute_query(query)
        modules = []
        for row in results:
            modules.append({
                "module_number": row[0],
                "module_name": row[1],
                "service_name": row[2],
                "category": row[3],
                "port": row[4],
                "directory_path": row[5],
                "auto_heal": row[6],
                "status": row[7]
            })
        
        return {
            "total_modules": len(modules),
            "modules": modules,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/restart-mechanisms/all")
def get_restart_mechanisms():
    """Get all detected restart mechanisms"""
    try:
        # Read from JSON file created by restart-detector.py
        if os.path.exists('/opt/revcore/logs/restart-mechanisms.json'):
            with open('/opt/revcore/logs/restart-mechanisms.json') as f:
                report = json.load(f)
            return report
        else:
            return {
                "error": "No restart mechanisms scanned yet",
                "message": "Run: POST /api/v1/restart-mechanisms/scan"
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/restart-mechanisms/scan")
def scan_restart_mechanisms(background_tasks: BackgroundTasks):
    """Trigger restart mechanism scan"""
    def run_scan():
        subprocess.run(['/usr/bin/python3', '/opt/revcore/scripts/restart-detector.py'])
    
    background_tasks.add_task(run_scan)
    return {
        "status": "scan_initiated",
        "message": "Restart mechanism scan running in background"
    }

@app.post("/api/v1/restart-mechanisms/disable")
def disable_restart_mechanism(action: RestartMechanismAction):
    """Disable a restart mechanism"""
    results = []
    
    if action.mechanism_type == "systemd":
        # Stop and disable systemd services
        try:
            result = subprocess.run(
                ['systemctl', 'stop', action.service_names[0]],
                capture_output=True, text=True
            )
            subprocess.run(['systemctl', 'disable', action.service_names[0]])
            results.append({
                "mechanism": "systemd",
                "service": action.service_names[0],
                "action": "disabled",
                "success": True
            })
        except Exception as e:
            results.append({"error": str(e)})
    
    elif action.mechanism_type == "docker":
        # Stop docker container and disable restart
        try:
            subprocess.run(['docker', 'stop', action.service_names[0]])
            subprocess.run(['docker', 'update', '--restart=no', action.service_names[0]])
            results.append({
                "mechanism": "docker",
                "container": action.service_names[0],
                "action": "stopped_and_no_restart",
                "success": True
            })
        except Exception as e:
            results.append({"error": str(e)})
    
    elif action.mechanism_type == "cron":
        # Remove cron job
        results.append({
            "mechanism": "cron",
            "action": "manual_removal_required",
            "message": "Use: crontab -e to remove manually"
        })
    
    return {"results": results}

@app.get("/api/v1/services/memory-hogs")
def get_memory_hogs():
    """Get services using excessive memory"""
    try:
        result = subprocess.run(
            ['ps', 'aux', '--sort=-%mem'],
            capture_output=True, text=True
        )
        
        hogs = []
        for line in result.stdout.split('\n')[1:11]:  # Top 10
            if line.strip():
                parts = line.split()
                if len(parts) >= 11:
                    mem_mb = float(parts[3]) * 80  # Approximate MB (75% = ~6GB)
                    if mem_mb > 100:  # Over 100MB
                        hogs.append({
                            "user": parts[0],
                            "pid": parts[1],
                            "cpu_percent": parts[2],
                            "mem_percent": parts[3],
                            "mem_mb_approx": round(mem_mb, 2),
                            "command": ' '.join(parts[10:])
                        })
        
        return {
            "memory_hogs": hogs,
            "total_found": len(hogs),
            "threshold_mb": 100
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/services/kill-by-path")
def kill_service_by_path(path: str):
    """Kill all processes running from a specific directory"""
    try:
        subprocess.run(['pkill', '-9', '-f', path])
        return {
            "status": "killed",
            "path": path,
            "message": f"All processes matching {path} terminated"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/ports/status")
def get_ports_status():
    """Get all listening ports"""
    try:
        result = subprocess.run(['ss', '-tlnp'], capture_output=True, text=True)
        ports = []
        
        for line in result.stdout.split('\n'):
            if 'LISTEN' in line and ':' in line:
                port_match = re.search(r':(\d+)\s', line)
                if port_match:
                    port = int(port_match.group(1))
                    process_match = re.search(r'users:\(\("([^"]+)"', line)
                    process = process_match.group(1) if process_match else "unknown"
                    
                    ports.append({
                        "port": port,
                        "process": process
                    })
        
        return {
            "ports": sorted(ports, key=lambda x: x['port']),
            "total": len(ports),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/ports/check")
def check_port(port_check: PortCheck):
    """Check if a port is available"""
    try:
        result = subprocess.run(
            ['/usr/bin/python3', '/opt/revcore/scripts/port-manager.py', 'check', str(port_check.port)],
            capture_output=True, text=True
        )
        
        return {
            "port": port_check.port,
            "available": result.returncode == 0
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/ports/suggest")
def suggest_port():
    """Suggest next available port"""
    try:
        result = subprocess.run(
            ['/usr/bin/python3', '/opt/revcore/scripts/port-manager.py', 'suggest'],
            capture_output=True, text=True
        )
        
        if result.returncode == 0 and result.stdout.strip():
            return {"suggested_port": int(result.stdout.strip())}
        else:
            raise HTTPException(status_code=500, detail="No available ports found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/system/status")
def get_system_status():
    """Get overall system status"""
    try:
        # Load average
        with open('/proc/loadavg') as f:
            load = f.read().split()[:3]
        
        # Memory
        with open('/proc/meminfo') as f:
            meminfo = {}
            for line in f:
                if ':' in line:
                    key, value = line.split(':')
                    meminfo[key.strip()] = value.strip()
        
        total_mem = int(meminfo['MemTotal'].split()[0])
        avail_mem = int(meminfo['MemAvailable'].split()[0])
        used_mem = total_mem - avail_mem
        
        # Uptime
        with open('/proc/uptime') as f:
            uptime_seconds = float(f.read().split()[0])
        
        # CPU count
        cpu_count = os.cpu_count()
        
        return {
            "load_average": {
                "1min": float(load[0]),
                "5min": float(load[1]),
                "15min": float(load[2]),
                "cpu_cores": cpu_count,
                "load_per_core": round(float(load[0]) / cpu_count, 2)
            },
            "memory": {
                "total_mb": total_mem // 1024,
                "used_mb": used_mem // 1024,
                "available_mb": avail_mem // 1024,
                "percent_used": round((used_mem / total_mem) * 100, 2)
            },
            "uptime_hours": round(uptime_seconds / 3600, 2),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/databases/status")
def get_databases_status():
    """Get PostgreSQL database status"""
    try:
        conn = get_db_connection()
        
        # Get database size
        cur = conn.cursor()
        cur.execute("SELECT pg_database_size(current_database());")
        size_bytes = cur.fetchone()[0]
        
        # Get table count
        cur.execute("""
            SELECT COUNT(*) 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        table_count = cur.fetchone()[0]
        
        cur.close()
        conn.close()
        
        return {
            "postgresql": {
                "status": "connected",
                "host": POSTGRES_HOST,
                "port": POSTGRES_PORT,
                "database": POSTGRES_DB,
                "size_mb": round(size_bytes / 1024 / 1024, 2),
                "table_count": table_count
            },
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "postgresql": {
                "status": "error",
                "error": str(e)
            }
        }

@app.post("/api/v1/services/action")
def execute_service_action(action: ServiceAction):
    """Execute action on services (start/stop/restart/kill)"""
    results = []
    
    for service_name in action.service_names:
        try:
            if action.action in ['start', 'stop', 'restart']:
                result = subprocess.run(
                    ['systemctl', action.action, service_name],
                    capture_output=True, text=True
                )
                results.append({
                    "service": service_name,
                    "action": action.action,
                    "success": result.returncode == 0,
                    "output": result.stdout if result.returncode == 0 else result.stderr
                })
            elif action.action == 'kill':
                # Kill by process name
                subprocess.run(['pkill', '-9', '-f', service_name])
                results.append({
                    "service": service_name,
                    "action": "kill",
                    "success": True,
                    "message": f"Killed all processes matching {service_name}"
                })
            else:
                results.append({
                    "service": service_name,
                    "action": action.action,
                    "success": False,
                    "error": "Invalid action"
                })
        except Exception as e:
            results.append({
                "service": service_name,
                "action": action.action,
                "success": False,
                "error": str(e)
            })
    
    return {"results": results, "total": len(results)}

@app.get("/api/v1/config/validate")
def validate_shared_env():
    """Validate shared .env file integrity"""
    issues = []
    
    # Check if file exists
    if not os.path.exists(SHARED_ENV):
        issues.append(f"Shared .env file does not exist: {SHARED_ENV}")
        return {"valid": False, "issues": issues}
    
    # Check permissions
    stat_info = os.stat(SHARED_ENV)
    if stat_info.st_mode & 0o777 != 0o600:
        issues.append(f"Incorrect permissions on {SHARED_ENV} - should be 600")
    
    # Check for required variables
    env = load_env()
    required_vars = ['POSTGRES_HOST', 'POSTGRES_PORT', 'POSTGRES_DB']
    for var in required_vars:
        if var not in env:
            issues.append(f"Missing required variable: {var}")
    
    # Check for duplicate .env files
    try:
        result = subprocess.run(
            ['find', '/opt', '-name', '.env', '-type', 'f'],
            capture_output=True, text=True, timeout=10
        )
        duplicate_envs = [
            line for line in result.stdout.split('\n') 
            if line and line != SHARED_ENV and '/node_modules/' not in line
        ]
        if duplicate_envs:
            issues.append(f"Duplicate .env files found: {', '.join(duplicate_envs)}")
    except:
        pass
    
    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "shared_env": SHARED_ENV,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/v1/modules/suite/{suite_name}")
def get_modules_by_suite(suite_name: str):
    """Get modules by suite (lead-gen, digital-landlord, tech-efficiency)"""
    suite_map = {
        "lead-gen": list(range(1, 12)),
        "digital-landlord": [13, 14],
        "tech-efficiency": [12, 15, 18]
    }
    
    if suite_name not in suite_map:
        raise HTTPException(status_code=404, detail="Suite not found")
    
    module_numbers = suite_map[suite_name]
    
    query = """
        SELECT module_number, module_name, service_name, category, 
               port, status
        FROM revcore_service_registry
        WHERE module_number = ANY(%s)
        ORDER BY module_number
    """
    
    try:
        results = execute_query(query, (module_numbers,))
        modules = []
        for row in results:
            modules.append({
                "module_number": row[0],
                "module_name": row[1],
                "service_name": row[2],
                "category": row[3],
                "port": row[4],
                "status": row[5]
            })
        
        return {
            "suite": suite_name,
            "modules": modules,
            "total": len(modules)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8950)
