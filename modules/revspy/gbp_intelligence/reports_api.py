"""
RevSPY™ GBP Intelligence - Enhanced Reports API
Now includes: Health scores, Email templates, PDF export
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from reports.generator import ReportGenerator
from reports.email_templates import generate_prospect_email, generate_client_email
from reports.pdf_export import export_to_pdf

router = APIRouter(prefix="/api/v1/revspy/reports", tags=["RevSPY Reports"])
generator = ReportGenerator()

class ProspectReportRequest(BaseModel):
    place_id: str
    market: str
    recipient_name: Optional[str] = None

class ClientReportRequest(BaseModel):
    place_id: str
    market: str
    recipient_name: Optional[str] = None

@router.post("/prospect")
async def generate_prospect_report(request: ProspectReportRequest):
    """Generate competitive analysis report for prospect"""
    try:
        report = generator.generate_prospect_report(request.place_id, request.market)
        if "error" in report:
            raise HTTPException(status_code=404, detail=report["error"])
        return report
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/prospect/email")
async def generate_prospect_email_template(request: ProspectReportRequest):
    """Generate sales email template for prospect"""
    try:
        report = generator.generate_prospect_report(request.place_id, request.market)
        if "error" in report:
            raise HTTPException(status_code=404, detail=report["error"])
        
        email = generate_prospect_email(report, request.recipient_name)
        return email
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/prospect/pdf")
async def generate_prospect_pdf(request: ProspectReportRequest):
    """Generate PDF report for prospect"""
    try:
        report = generator.generate_prospect_report(request.place_id, request.market)
        if "error" in report:
            raise HTTPException(status_code=404, detail=report["error"])
        
        # Generate PDF
        pdf_path = export_to_pdf(report, output_dir="/tmp")
        
        # Return file
        return FileResponse(
            pdf_path,
            media_type="application/pdf",
            filename=f"competitive_analysis_{request.place_id[:8]}.pdf"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/client/monthly")
async def generate_monthly_client_report(request: ClientReportRequest):
    """Generate monthly progress report for existing client"""
    try:
        report = generator.generate_monthly_client_report(request.place_id, request.market)
        if "error" in report:
            raise HTTPException(status_code=404, detail=report["error"])
        return report
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/client/monthly/email")
async def generate_client_email_template(request: ClientReportRequest):
    """Generate monthly email template for client"""
    try:
        report = generator.generate_monthly_client_report(request.place_id, request.market)
        if "error" in report:
            raise HTTPException(status_code=404, detail=report["error"])
        
        email = generate_client_email(report, request.recipient_name)
        return email
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/markets/{market}/summary")
async def get_market_summary(market: str):
    """Get summary statistics for a market"""
    try:
        conn = generator.get_connection()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT 
                COUNT(*) as total_competitors,
                AVG(rating) as avg_rating,
                AVG(review_count) as avg_reviews,
                AVG(gbp_health_score) as avg_health_score
            FROM revspy_gbp_profiles
            WHERE market = %s
        """, (market,))
        
        result = cur.fetchone()
        cur.close()
        conn.close()
        
        return {
            "market": market,
            "total_competitors": result[0],
            "avg_rating": round(float(result[1] or 0), 2),
            "avg_reviews": int(result[2] or 0),
            "avg_health_score": int(result[3] or 0)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def health_check():
    """API health check"""
    return {
        "status": "healthy",
        "features": [
            "competitive_analysis",
            "health_scores",
            "email_templates",
            "pdf_export"
        ]
    }
