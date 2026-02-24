"""
RevCore Gateway Router
Routes requests from modules to other modules via service registry
"""
from fastapi import APIRouter, Request, HTTPException
from typing import Optional
import requests
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/gateway", tags=["gateway"])

def get_module_endpoint(module_name: str) -> Optional[str]:
    """Look up module endpoint in service registry"""
    
    # Service registry mapping
    module_map = {
        "revprompt": "http://localhost:8700/api",
        "revscore": "http://localhost:8100/api",
        "revrank": "http://localhost:8103/api",
        "revseo": "http://localhost:8765/api",
        "revcite": "http://localhost:8900/api",
        "revhumanize": "http://localhost:8500/api",
        "revwins": "http://localhost:8150/api",
        "revimage": "http://localhost:8610/api",
        "revpublish": "http://localhost:8550/api",
        "revmetrics": "http://localhost:8220/api",
        "revsignal": "http://localhost:8006/api",
        "revintel": "http://localhost:8011/api",
        "revdispatch": "http://localhost:8501/api",
        "revvest": "http://localhost:8003/api",
        "revspy": "http://localhost:8160/api",
        "revspend": "http://localhost:8105/api",
        "revcore": "http://localhost:8004/api",
        "revassist": "http://localhost:8100/api",
    }
    
    return module_map.get(module_name.lower())


@router.api_route("/{module_name}/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def gateway_route(
    module_name: str,
    path: str,
    request: Request
):
    """
    Route request through gateway to appropriate module
    
    Example:
        POST /api/gateway/revspy/serp-analysis
        → Routes to http://localhost:8160/api/serp-analysis
    """
    
    # Look up module endpoint
    target_base = get_module_endpoint(module_name)
    
    if not target_base:
        raise HTTPException(
            status_code=404,
            detail=f"Module '{module_name}' not found in registry"
        )
    
    # Build target URL
    target_url = f"{target_base}/{path}"
    
    # Log routing
    logger.info(f"[GATEWAY] {request.method} {module_name} → {target_url}")
    
    try:
        # Forward request to target module
        if request.method == "GET":
            response = requests.get(
                target_url,
                params=dict(request.query_params),
                timeout=30
            )
        elif request.method == "POST":
            body = await request.json() if request.headers.get("content-length") else {}
            response = requests.post(target_url, json=body, timeout=30)
        elif request.method == "PUT":
            body = await request.json() if request.headers.get("content-length") else {}
            response = requests.put(target_url, json=body, timeout=30)
        elif request.method == "DELETE":
            response = requests.delete(target_url, timeout=30)
        
        response.raise_for_status()
        return response.json()
        
    except requests.exceptions.Timeout:
        raise HTTPException(
            status_code=504,
            detail=f"Module '{module_name}' request timed out"
        )
    except requests.exceptions.ConnectionError:
        raise HTTPException(
            status_code=503,
            detail=f"Module '{module_name}' is unavailable"
        )
    except Exception as e:
        logger.error(f"Gateway routing error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error routing to {module_name}: {str(e)}"
        )
