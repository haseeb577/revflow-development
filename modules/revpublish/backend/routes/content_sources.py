"""
Content Sources Routes
Integrates with EXISTING RevFlow services
"""

from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import List, Optional, Dict
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from integrations.csv_import_client import CSVImportEngineClient
from integrations.data_provider_client import DataProviderClient
from integrations.revrank_client import RevRankEngineClient
from integrations.google_integrations import GoogleSheetsClient, GoogleDocsClient
from revflow_client import get_revflow_client

router = APIRouter()

# Initialize clients for existing services
csv_import = get_revflow_client().get_service("csv_import")
data_provider = get_revflow_client().get_service("data_provider")
revrank = get_revflow_client().get_service("revrank_engine")
google_sheets = GoogleSheetsClient()
google_docs = GoogleDocsClient()

class CSVImportRequest(BaseModel):
    csv_content: str
    mapping: Optional[Dict] = None

class JSONImportRequest(BaseModel):
    json_content: str

class GoogleSheetsRequest(BaseModel):
    sheet_url: str

class GoogleDocsRequest(BaseModel):
    doc_url: str

class RevRankRequest(BaseModel):
    business_name: str
    page_type: str
    location: Optional[str] = None
    keywords: Optional[List[str]] = []

@router.post("/import/csv")
async def import_csv(request: CSVImportRequest):
    """Import CSV using EXISTING CSV Import Engine (port 8766)"""
    try:
        items = csv_import.import_csv(request.csv_content, request.mapping)
        
        return {
            "success": True,
            "source": "csv_import_engine",
            "port": 8766,
            "items_count": len(items),
            "items": items
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/import/csv/upload")
async def upload_csv(file: UploadFile = File(...)):
    """Upload CSV file to EXISTING CSV Import Engine"""
    try:
        content = await file.read()
        csv_content = content.decode('utf-8')
        
        items = csv_import.import_csv(csv_content)
        
        return {
            "success": True,
            "source": "csv_import_engine",
            "port": 8766,
            "filename": file.filename,
            "items_count": len(items),
            "items": items
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/import/json")
async def import_json(request: JSONImportRequest):
    """Import JSON content"""
    try:
        import json
        data = json.loads(request.json_content)
        
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            items = data.get('items', [data])
        else:
            items = [{'content': str(data)}]
        
        return {
            "success": True,
            "source": "json",
            "items_count": len(items),
            "items": items
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/import/google-sheets")
async def import_google_sheets(request: GoogleSheetsRequest):
    """Import from Google Sheets"""
    try:
        items = google_sheets.extract_from_url(request.sheet_url)
        
        return {
            "success": True,
            "source": "google_sheets",
            "items_count": len(items),
            "items": items
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/import/google-docs")
async def import_google_docs(request: GoogleDocsRequest):
    """Import from Google Docs"""
    try:
        item = google_docs.extract_from_url(request.doc_url)
        
        return {
            "success": True,
            "source": "google_docs",
            "item": item
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/generate/revrank")
async def generate_revrank(request: RevRankRequest):
    """Generate content using EXISTING RevRank Engine (port 8200)"""
    try:
        item = revrank.generate_content({
            'business_name': request.business_name,
            'page_type': request.page_type,
            'location': request.location,
            'keywords': request.keywords
        })
        
        return {
            "success": True,
            "source": "revrank_engine",
            "port": 8200,
            "item": item
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sources/status")
async def check_sources_status():
    """Check status of all existing RevFlow services"""
    return {
        "sources": {
            "csv_import_engine": {
                "port": 8766,
                "status": "available" if csv_import.health_check() else "unavailable",
                "description": "Existing CSV Import Engine with dynamic field mapping"
            },
            "revrank_engine": {
                "port": 8200,
                "status": "available" if revrank.health_check() else "unavailable",
                "description": "Existing RevRank content generation engine"
            },
            "data_provider": {
                "port": 8100,
                "status": "available" if data_provider.health_check() else "unavailable",
                "description": "Existing Data Provider system"
            },
            "google_sheets": {
                "status": "available",
                "description": "Google Sheets integration (public sheets)"
            },
            "google_docs": {
                "status": "available",
                "description": "Google Docs integration (public docs)"
            },
            "json": {
                "status": "available",
                "description": "Direct JSON import"
            }
        }
    }

@router.get("/sources/list")
async def list_sources():
    """List all 5 content sources"""
    return {
        "sources": [
            {
                "id": "revrank_engine",
                "name": "RevRank Engine",
                "port": 8200,
                "type": "EXISTING SERVICE",
                "endpoint": "/api/sources/generate/revrank"
            },
            {
                "id": "csv",
                "name": "CSV Import",
                "port": 8766,
                "type": "EXISTING SERVICE",
                "endpoint": "/api/sources/import/csv"
            },
            {
                "id": "json",
                "name": "JSON Import",
                "type": "NATIVE",
                "endpoint": "/api/sources/import/json"
            },
            {
                "id": "google_sheets",
                "name": "Google Sheets",
                "type": "NATIVE",
                "endpoint": "/api/sources/import/google-sheets"
            },
            {
                "id": "google_docs",
                "name": "Google Docs",
                "type": "NATIVE",
                "endpoint": "/api/sources/import/google-docs"
            }
        ]
    }
