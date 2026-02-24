"""
RevFlow OS™ - Standard Health Check Module
Can be imported into any FastAPI application
"""

from fastapi import APIRouter, Response, status
from datetime import datetime
import psycopg2
import os
import sys

router = APIRouter()

@router.get("/health")
async def health_check():
    """
    Standard RevFlow module health check endpoint
    
    Returns:
        - status: "healthy" | "degraded" | "unhealthy"  
        - timestamp: ISO 8601 timestamp
        - checks: Individual component health
    """
    health_data = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "module": os.getenv("MODULE_NAME", os.path.basename(os.getcwd())),
        "version": os.getenv("MODULE_VERSION", "1.0.0"),
        "checks": {},
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    }
    
    # Check database connectivity
    try:
        conn = psycopg2.connect(
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=int(os.getenv("POSTGRES_PORT", "5432")),
            database=os.getenv("POSTGRES_DB", "revflow"),
            user=os.getenv("POSTGRES_USER", "postgres"),
            password=os.getenv("POSTGRES_PASSWORD", ""),
            connect_timeout=3
        )
        conn.close()
        health_data["checks"]["database"] = "healthy"
    except Exception as e:
        health_data["checks"]["database"] = f"unhealthy: {str(e)[:50]}"
        health_data["status"] = "degraded"
    
    # Check disk space
    try:
        import shutil
        total, used, free = shutil.disk_usage("/")
        free_percent = (free / total) * 100
        
        if free_percent < 10:
            health_data["checks"]["disk"] = "critical"
            health_data["status"] = "degraded"
        elif free_percent < 20:
            health_data["checks"]["disk"] = "warning"
        else:
            health_data["checks"]["disk"] = "healthy"
            
        health_data["checks"]["disk_free_gb"] = round(free / (1024**3), 2)
    except Exception:
        health_data["checks"]["disk"] = "unknown"
    
    # Check memory
    try:
        with open('/proc/meminfo', 'r') as f:
            meminfo = f.read()
            mem_total = int([line for line in meminfo.split('\n') if 'MemTotal' in line][0].split()[1])
            mem_available = int([line for line in meminfo.split('\n') if 'MemAvailable' in line][0].split()[1])
            mem_percent = ((mem_total - mem_available) / mem_total) * 100
            
            if mem_percent > 90:
                health_data["checks"]["memory"] = "critical"
                health_data["status"] = "degraded"
            elif mem_percent > 80:
                health_data["checks"]["memory"] = "warning"
            else:
                health_data["checks"]["memory"] = "healthy"
                
            health_data["checks"]["memory_used_percent"] = round(mem_percent, 1)
    except Exception:
        health_data["checks"]["memory"] = "unknown"
    
    # Set HTTP status code based on health
    response_status = status.HTTP_200_OK
    if health_data["status"] == "degraded":
        response_status = status.HTTP_503_SERVICE_UNAVAILABLE
    elif health_data["status"] == "unhealthy":
        response_status = status.HTTP_503_SERVICE_UNAVAILABLE
    
    return health_data

@router.get("/health/detailed")
async def health_check_detailed():
    """
    Detailed health check with more diagnostic information
    """
    basic_health = await health_check()
    
    # Add more detailed checks
    detailed_data = basic_health.copy()
    detailed_data["environment"] = {
        "module_name": os.getenv("MODULE_NAME", "unknown"),
        "module_version": os.getenv("MODULE_VERSION", "unknown"),
        "python_path": sys.executable,
        "working_directory": os.getcwd()
    }
    
    return detailed_data
