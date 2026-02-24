from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

class DeploymentRequest(BaseModel):
    content_html: str
    title: str
    excerpt: Optional[str] = ""
    target_sites: List[str]
    status: str = "draft"

@router.post("/deploy")
async def deploy_content(request: DeploymentRequest):
    """Deploy content to WordPress sites"""
    logger.info(f"Deployment request: {request.title} → {request.target_sites}")
    
    # For now, just log and return success
    # Later we'll add actual WordPress/Elementor deployment
    return {
        "success": True,
        "message": f"Queued deployment: {request.title}",
        "target_sites": request.target_sites,
        "status": "queued"
    }

@router.get("/status")
async def deployment_status():
    """Get deployment system status"""
    return {
        "status": "ready",
        "configured_sites": 0,
        "active_deployments": 0
    }
