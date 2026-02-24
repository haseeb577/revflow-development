"""Content ingestion API routes"""
from fastapi import APIRouter, HTTPException

router = APIRouter()

@router.get("/revrank/pending")
async def get_revrank_content(min_score: int = 70):
    """Get pending content from RevRank Engine"""
    return {"count": 0, "content": [], "message": "Integration pending"}

@router.post("/google-docs/scan")
async def scan_google_docs(folder_id: str):
    """Scan Google Drive folder for docs"""
    return {"count": 0, "content": [], "message": "Integration pending"}

@router.post("/google-sheets/import")
async def import_google_sheet(spreadsheet_id: str, range_name: str = "Sheet1"):
    """Import content from Google Sheet"""
    return {"count": 0, "content": [], "message": "Integration pending"}
