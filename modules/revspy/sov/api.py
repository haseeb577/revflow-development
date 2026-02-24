
"""
RevInsight™ SOV API - Share of Voice endpoints
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, date, timedelta
import os

from dotenv import load_dotenv
load_dotenv('/opt/shared-api-engine/.env')

from sov_calculator import (
    ShareOfVoiceCalculator, get_sov_history
)

app = FastAPI(
    title="RevInsight™ SOV API",
    description="Share of Voice analysis for AI citations",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SOVRequest(BaseModel):
    site_id: int
    client_domains: List[str]
    competitor_domains: List[str]
    days: int = 30


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "RevInsight SOV",
        "timestamp": datetime.now().isoformat()
    }


@app.post("/api/v1/sov/calculate")
async def calculate_sov(request: SOVRequest):
    """Calculate Share of Voice for a site"""
    calculator = ShareOfVoiceCalculator(
        site_id=request.site_id,
        client_domains=request.client_domains,
        competitor_domains=request.competitor_domains
    )
    
    end_date = date.today()
    start_date = end_date - timedelta(days=request.days)
    
    sov_data = calculator.calculate_from_results(start_date, end_date)
    
    return {
        "site_id": request.site_id,
        "period": {
            "start": str(start_date),
            "end": str(end_date),
            "days": request.days
        },
        "sov": sov_data
    }


@app.get("/api/v1/sov/{site_id}/gaps")
async def get_citation_gaps(
    site_id: int,
    client_domains: str = Query(..., description="Comma-separated client domains"),
    competitor_domains: str = Query("", description="Comma-separated competitor domains"),
    limit: int = Query(50, ge=1, le=200)
):
    """Get citation gaps (where competitors appear but client doesn't)"""
    calculator = ShareOfVoiceCalculator(
        site_id=site_id,
        client_domains=client_domains.split(','),
        competitor_domains=competitor_domains.split(',') if competitor_domains else []
    )
    
    gaps = calculator.identify_citation_gaps(limit=limit)
    
    return {
        "site_id": site_id,
        "count": len(gaps),
        "gaps": gaps
    }


@app.get("/api/v1/sov/{site_id}/history")
async def get_sov_history_endpoint(
    site_id: int,
    days: int = Query(30, ge=1, le=365)
):
    """Get SOV history for a site"""
    history = get_sov_history(site_id, days)
    
    return {
        "site_id": site_id,
        "days": days,
        "count": len(history),
        "history": [
            {
                "date": str(h['measurement_date']),
                "competitor": h['competitor_domain'],
                "platform": h['ai_platform'],
                "client_sov": float(h['client_sov_percent'] or 0),
                "competitor_sov": float(h['competitor_sov_percent'] or 0),
                "gap": float(h['gap_percent'] or 0)
            }
            for h in history
        ]
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv('SOV_PORT', 8402))
    uvicorn.run(app, host="0.0.0.0", port=port)
