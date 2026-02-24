"""
RevCore Gateway Router - Database-Driven Architecture
Queries PostgreSQL revflow_service_registry at startup and caches results
NO HARDCODING - Single source of truth is the database
"""
from fastapi import APIRouter, Request, HTTPException
from typing import Optional, Dict, List
import requests
import logging
import psycopg2
import os
from functools import lru_cache

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/gateway", tags=["gateway"])

# Service registry cache (loaded at startup)
SERVICE_REGISTRY = {}
REGISTRY_LOADED = False


def get_db_connection():
    """Get PostgreSQL connection from environment variables"""
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        database=os.getenv("POSTGRES_DB", "revflow"),
        user=os.getenv("POSTGRES_USER", "postgres"),
        password=os.getenv("POSTGRES_PASSWORD", "")
    )


def load_service_registry():
    """
    Load module endpoints from PostgreSQL at startup
    This is the ONLY place ports are defined
    """
    global SERVICE_REGISTRY, REGISTRY_LOADED
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Query the canonical service registry
        cursor.execute("""
            SELECT module_number, module_name, port, status
            FROM revflow_service_registry
            WHERE status = 'deployed'
            ORDER BY module_number
        """)
        
        results = cursor.fetchall()
        cursor.close()
        conn.close()
        
        # Build service map: module_name -> port
        for module_number, module_name, port, status in results:
            if port:  # Only include modules with ports
                SERVICE_REGISTRY[module_name.lower()] = {
                    "number": module_number,
                    "name": module_name,
                    "port": port,
                    "url": f"http://localhost:{port}/api",
                    "status": status
                }
        
        REGISTRY_LOADED = True
        logger.info(f"✓ Loaded {len(SERVICE_REGISTRY)} modules from PostgreSQL")
        
        # Log loaded modules
        for name, info in SERVICE_REGISTRY.items():
            logger.info(f"  - Module {info['number']:2d}: {name:20s} → port {info['port']}")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Failed to load service registry: {str(e)}")
        logger.warning("! Gateway will operate without service registry")
        return False


def get_module_endpoint(module_name: str) -> Optional[Dict]:
    """
    Get module endpoint from cached registry
    Returns None if not found
    """
    module_name = module_name.lower().strip()
    
    if module_name not in SERVICE_REGISTRY:
        return None
    
    return SERVICE_REGISTRY[module_name]


@router.api_route("/{module_name}/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def gateway_route(
    module_name: str,
    path: str,
    request: Request
):
    """
    Route request through gateway to appropriate module
    Module location is determined by PostgreSQL registry, not hardcoding
    
    Example:
        POST /api/gateway/revspy/serp-analysis
        → Looks up revspy in database
        → Gets port from database
        → Routes to http://localhost:[port]/api/serp-analysis
    """
    
    # Ensure registry is loaded
    if not REGISTRY_LOADED:
        raise HTTPException(
            status_code=503,
            detail="Service registry not loaded. Gateway is initializing."
        )
    
    # Look up module in cached registry
    module_info = get_module_endpoint(module_name)
    
    if not module_info:
        raise HTTPException(
            status_code=404,
            detail=f"Module '{module_name}' not found in service registry"
        )
    
    # Build target URL from database info
    target_url = f"{module_info['url']}/{path}"
    
    # Log routing
    logger.info(
        f"[GATEWAY] {request.method} {module_name} "
        f"(Module {module_info['number']}) → {target_url}"
    )
    
    try:
        # Forward request to target module
        if request.method == "GET":
            response = requests.get(
                target_url,
                params=dict(request.query_params),
                timeout=30
            )
        elif request.method == "POST":
            try:
                body = await request.json() if request.headers.get("content-length") else {}
            except:
                body = {}
            response = requests.post(target_url, json=body, timeout=30)
        elif request.method == "PUT":
            try:
                body = await request.json() if request.headers.get("content-length") else {}
            except:
                body = {}
            response = requests.put(target_url, json=body, timeout=30)
        elif request.method == "DELETE":
            response = requests.delete(target_url, timeout=30)
        
        response.raise_for_status()
        
        # Log success
        logger.info(f"[GATEWAY] ✓ Response {response.status_code}")
        
        return response.json()
        
    except requests.exceptions.Timeout:
        logger.error(f"[GATEWAY] ✗ Timeout: {module_name}")
        raise HTTPException(
            status_code=504,
            detail=f"Module '{module_name}' request timed out"
        )
    except requests.exceptions.ConnectionError:
        logger.error(f"[GATEWAY] ✗ Connection failed: {module_name}")
        raise HTTPException(
            status_code=503,
            detail=f"Module '{module_name}' is unavailable at {module_info['url']}"
        )
    except Exception as e:
        logger.error(f"[GATEWAY] ✗ Error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error routing to {module_name}: {str(e)}"
        )


@router.get("/health")
async def gateway_health():
    """Health check endpoint - shows registry status"""
    return {
        "status": "healthy" if REGISTRY_LOADED else "initializing",
        "modules_loaded": len(SERVICE_REGISTRY),
        "registry": SERVICE_REGISTRY if REGISTRY_LOADED else {}
    }


@router.get("/registry")
async def get_registry():
    """Return the cached service registry (for debugging)"""
    if not REGISTRY_LOADED:
        raise HTTPException(status_code=503, detail="Registry not loaded")
    
    return {
        "status": "loaded",
        "module_count": len(SERVICE_REGISTRY),
        "modules": SERVICE_REGISTRY
    }


# Load registry when module is imported
# This happens at FastAPI startup
try:
    load_service_registry()
except Exception as e:
    logger.warning(f"Warning: Service registry loading failed at startup: {e}")
