"""Template management routes"""
from fastapi import APIRouter

router = APIRouter()

@router.get("/list")
async def list_templates():
    """List available Elementor templates"""
    return {"templates": []}
