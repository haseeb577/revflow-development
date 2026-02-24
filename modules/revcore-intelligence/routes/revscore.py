"""
RevScore IQ Gateway Routes
Auto-generated: 2026-01-26 20:00:00

Add these routes to your RevCore Gateway configuration
to enable routing of RevScore IQ through the central gateway.
"""

from fastapi import APIRouter, Request
import httpx

router = APIRouter(prefix="/revscore", tags=["RevScore IQ"])

# RevScore IQ backend URL
REVSCORE_BACKEND_URL = "http://localhost:8500"

@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_revscore(path: str, request: Request):
    """
    Proxy all requests to RevScore IQ backend
    Routes: /revscore/* → http://localhost:8500/*
    """
    # Build target URL
    target_url = f"{REVSCORE_BACKEND_URL}/{path}"
    
    # Get request body if present
    body = await request.body()
    
    # Forward request to RevScore IQ
    async with httpx.AsyncClient() as client:
        response = await client.request(
            method=request.method,
            url=target_url,
            headers=dict(request.headers),
            params=request.query_params,
            content=body,
            timeout=300.0  # 5 minute timeout for long assessments
        )
    
    return response.json() if response.headers.get("content-type") == "application/json" else response.text


# Specific endpoint mappings (optional - for explicit routing)
@router.post("/assess")
async def assess_website(request: Request):
    """Submit website assessment request"""
    return await proxy_revscore("assess", request)

@router.post("/assessment")
async def create_assessment(request: Request):
    """Create full assessment"""
    return await proxy_revscore("assessment", request)

@router.get("/health")
async def health_check():
    """Check RevScore IQ health via gateway"""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{REVSCORE_BACKEND_URL}/health")
        return response.json()
