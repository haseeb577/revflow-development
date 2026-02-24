"""Deployment management routes"""
from fastapi import APIRouter

router = APIRouter()

@router.get("/queue")
async def get_deployment_queue():
    """Get current deployment queue"""
    return {"queue": []}

@router.post("/create")
async def create_deployment(content_id: str, target_sites: list):
    """Create new deployment job"""
    return {"status": "queued"}
