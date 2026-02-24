"""
RevCore - Consul Management API
Exposes Consul port validation and service management endpoints.
"""
from fastapi import APIRouter, HTTPException
from typing import Dict, List, Optional
import subprocess
import json
import requests as http_requests

router = APIRouter(prefix="/api/consul", tags=["consul"])

CONSUL_URL = "http://127.0.0.1:8500"

# Reserved Consul ports
RESERVED_PORTS = {8300, 8301, 8302, 8500, 8503, 8600}


def get_consul_services() -> Dict:
    """Get all registered Consul services."""
    try:
        resp = http_requests.get(f"{CONSUL_URL}/v1/agent/services", timeout=5)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Consul unavailable: {str(e)}")


def get_consul_health() -> Dict[str, str]:
    """Get health status of all services."""
    health = {}
    for state in ["passing", "warning", "critical"]:
        try:
            resp = http_requests.get(f"{CONSUL_URL}/v1/health/state/{state}", timeout=5)
            for check in resp.json():
                svc_id = check.get("ServiceID", "")
                if svc_id:
                    health[svc_id] = state
        except:
            pass
    return health


@router.get("/status")
async def consul_status():
    """Get Consul cluster status and service overview."""
    try:
        # Get leader
        leader_resp = http_requests.get(f"{CONSUL_URL}/v1/status/leader", timeout=5)
        leader = leader_resp.json() if leader_resp.ok else "unknown"

        # Get services
        services = get_consul_services()
        health = get_consul_health()

        # Count by health status
        passing = sum(1 for s in services if health.get(s) == "passing")
        warning = sum(1 for s in services if health.get(s) == "warning")
        critical = sum(1 for s in services if health.get(s) == "critical")
        unknown = len(services) - passing - warning - critical

        return {
            "status": "healthy" if critical == 0 else "degraded",
            "leader": leader,
            "services": {
                "total": len(services),
                "passing": passing,
                "warning": warning,
                "critical": critical,
                "unknown": unknown
            },
            "ui_url": "http://217.15.168.106:8500/ui"
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/services")
async def list_services():
    """List all registered Consul services with health status."""
    services = get_consul_services()
    health = get_consul_health()

    result = []
    for svc_id, svc_data in services.items():
        result.append({
            "id": svc_id,
            "name": svc_data.get("Service"),
            "port": svc_data.get("Port"),
            "tags": svc_data.get("Tags", []),
            "health": health.get(svc_id, "unknown")
        })

    return {"services": sorted(result, key=lambda x: x["port"])}


@router.get("/validate")
async def validate_registrations():
    """Validate all Consul service registrations."""
    services = get_consul_services()
    health = get_consul_health()

    issues = []

    for svc_id, svc_data in services.items():
        port = svc_data.get("Port", 0)
        name = svc_data.get("Service", svc_id)

        # Check reserved ports
        if port in RESERVED_PORTS and svc_id != "consul":
            issues.append({
                "service": name,
                "port": port,
                "issue": "Using reserved Consul port",
                "severity": "critical"
            })

        # Check health
        svc_health = health.get(svc_id, "unknown")
        if svc_health == "critical":
            issues.append({
                "service": name,
                "port": port,
                "issue": "Health check failing",
                "severity": "critical"
            })
        elif svc_health == "warning":
            issues.append({
                "service": name,
                "port": port,
                "issue": "Health check warning",
                "severity": "warning"
            })

    return {
        "valid": len(issues) == 0,
        "total_services": len(services),
        "issues_found": len(issues),
        "issues": issues
    }


@router.post("/fix")
async def fix_registrations():
    """Run auto-fix for misconfigured Consul registrations."""
    try:
        result = subprocess.run(
            ["/opt/shared-api-engine/consul_port_validator.py", "--fix"],
            capture_output=True,
            text=True,
            timeout=60
        )

        return {
            "status": "completed",
            "exit_code": result.returncode,
            "output": result.stdout[-2000:] if result.stdout else "",
            "errors": result.stderr[-500:] if result.stderr else ""
        }
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Fix operation timed out")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/register")
async def register_service(
    service_id: str,
    name: str,
    port: int,
    check_type: str = "http",
    health_endpoint: Optional[str] = None,
    tags: Optional[List[str]] = None
):
    """Register a new service with Consul."""

    # Validate port
    if port in RESERVED_PORTS:
        raise HTTPException(
            status_code=400,
            detail=f"Port {port} is reserved for Consul"
        )

    # Build check config
    if check_type == "tcp":
        check = {
            "TCP": f"localhost:{port}",
            "Interval": "30s",
            "Timeout": "5s"
        }
    else:
        endpoint = health_endpoint or f"http://localhost:{port}/health"
        check = {
            "HTTP": endpoint,
            "Interval": "30s",
            "Timeout": "10s"
        }

    # Build registration
    registration = {
        "ID": service_id,
        "Name": name,
        "Port": port,
        "Tags": tags or ["revflow"],
        "Check": check
    }

    try:
        resp = http_requests.put(
            f"{CONSUL_URL}/v1/agent/service/register",
            json=registration,
            timeout=5
        )

        if resp.status_code == 200:
            return {"status": "registered", "service": registration}
        else:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
    except http_requests.exceptions.RequestException as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.delete("/deregister/{service_id}")
async def deregister_service(service_id: str):
    """Deregister a service from Consul."""
    try:
        resp = http_requests.put(
            f"{CONSUL_URL}/v1/agent/service/deregister/{service_id}",
            timeout=5
        )

        if resp.status_code == 200:
            return {"status": "deregistered", "service_id": service_id}
        else:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
    except http_requests.exceptions.RequestException as e:
        raise HTTPException(status_code=503, detail=str(e))
