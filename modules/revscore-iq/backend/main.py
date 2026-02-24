"""
RevScore IQ™ Backend API
Main FastAPI application for assessment platform
"""
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
import os
import sys
import json
import asyncio
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
env_paths = ['../../.env', '../.env', '.env']
for path in env_paths:
    if os.path.exists(path):
        load_dotenv(path)
        break

# Add shared modules to path
sys.path.insert(0, '/opt/shared-api-engine')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Database imports
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from models import Base, Assessment, Competitor, ModuleScore, ComponentScore, Report, Priority

# Initialize database - use environment variables or defaults
# Docker PostgreSQL runs on port 5433 (mapped from container port 5432)
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5433")  # Docker port
POSTGRES_DB = os.getenv("POSTGRES_DB", "revflow")
POSTGRES_USER = os.getenv("POSTGRES_USER", "revflow")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "revflow2026")

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
)
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create tables
Base.metadata.create_all(bind=engine)

# Initialize FastAPI
app = FastAPI(
    title="RevScore IQ™ API",
    description="Professional website assessment and P0-P3 scoring system",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency for database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ============================================================================
# Request/Response Models
# ============================================================================

class AssessmentCreate(BaseModel):
    """Create new assessment request"""
    prospect_name: str = Field(..., min_length=3)
    prospect_url: str = Field(..., pattern=r'^https?://')
    industry: Optional[str] = None
    business_location: Optional[Dict[str, Any]] = None
    service_area: Optional[List[str]] = None
    contact_info: Optional[Dict[str, Any]] = None
    business_profile: Optional[Dict[str, Any]] = None


class CompetitorCreate(BaseModel):
    """Add competitor request"""
    competitor_name: str
    competitor_url: str = Field(..., pattern=r'^https?://')
    competitor_location: Optional[Dict[str, Any]] = None


class AssessmentConfig(BaseModel):
    """Assessment configuration"""
    assessment_mode: str = Field(default="comprehensive", pattern=r"^(executive|comprehensive|regional|json)$")
    modules_selected: List[str] = Field(default_factory=lambda: ["A", "B", "C", "D", "E", "E1", "E2", "F"])
    depth_level: str = Field(default="standard", pattern=r"^(quick|standard|deep)$")
    ai_model: str = Field(default="auto")
    appendices_selected: Optional[List[str]] = None


# ============================================================================
# Health & Info Endpoints
# ============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "RevScore IQ API",
        "version": "2.0.0",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/")
async def root():
    """API information"""
    return {
        "service": "RevScore IQ™ API",
        "version": "2.0.0",
        "endpoints": {
            "dashboard": "GET /api/assessments/stats",
            "create_assessment": "POST /api/assessments",
            "get_assessment": "GET /api/assessments/{id}",
            "list_assessments": "GET /api/assessments",
            "reports": "GET /api/reports",
            "appendices": "GET /api/appendices"
        }
    }


# ============================================================================
# Dashboard Endpoints
# ============================================================================

@app.get("/api/assessments/stats")
async def get_dashboard_stats(db: Session = Depends(get_db)):
    """Get dashboard statistics"""
    try:
        total_assessments = db.query(Assessment).count()
        completed_assessments = db.query(Assessment).filter(Assessment.status == "completed").count()
        
        # Calculate average P-Score distribution
        p_scores = db.query(Assessment.p_classification).filter(
            Assessment.p_classification.isnot(None)
        ).all()
        p_score_counts = {"P0": 0, "P1": 0, "P2": 0, "P3": 0}
        for (p_score,) in p_scores:
            if p_score in p_score_counts:
                p_score_counts[p_score] += 1
        
        # Calculate average overall score
        avg_score_result = db.query(Assessment.overall_score).filter(
            Assessment.overall_score.isnot(None)
        ).all()
        avg_scores = [s[0] for s in avg_score_result if s[0] is not None]
        avg_overall_score = sum(avg_scores) / len(avg_scores) if avg_scores else 0
        
        # Grade distribution
        grades = db.query(Assessment.letter_grade).filter(
            Assessment.letter_grade.isnot(None)
        ).all()
        grade_counts = {"A": 0, "B": 0, "C": 0, "D": 0}
        for (grade,) in grades:
            if grade in grade_counts:
                grade_counts[grade] += 1
        
        return {
            "total_assessments": total_assessments,
            "completed_assessments": completed_assessments,
            "average_p_score": p_score_counts,
            "average_overall_score": round(avg_overall_score, 1),
            "grade_distribution": grade_counts
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching stats: {str(e)}")


@app.get("/api/assessments/charts")
async def get_charts_data(
    range: str = "30d",
    db: Session = Depends(get_db)
):
    """Get chart data for dashboard"""
    try:
        # Get assessments over time
        assessments = db.query(Assessment).filter(
            Assessment.created_at.isnot(None)
        ).order_by(Assessment.created_at.desc()).limit(100).all()
        
        # Group by date
        assessments_per_day = {}
        for assessment in assessments:
            date_key = assessment.created_at.date().isoformat()
            assessments_per_day[date_key] = assessments_per_day.get(date_key, 0) + 1
        
        # P-Score distribution
        p_scores = db.query(Assessment.p_classification).filter(
            Assessment.p_classification.isnot(None)
        ).all()
        p_score_counts = {"P0": 0, "P1": 0, "P2": 0, "P3": 0}
        for (p_score,) in p_scores:
            if p_score in p_score_counts:
                p_score_counts[p_score] += 1
        
        return {
            "assessments_over_time": assessments_per_day,
            "p_score_distribution": p_score_counts
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching chart data: {str(e)}")


# ============================================================================
# Assessment Endpoints
# ============================================================================

@app.post("/api/assessments")
async def create_assessment(
    assessment: AssessmentCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Create a new assessment (Step 1: Input Form)"""
    try:
        import uuid
        assessment_id = f"ASS-{datetime.now().strftime('%Y')}-{str(uuid.uuid4())[:8].upper()}"
        
        new_assessment = Assessment(
            assessment_id=assessment_id,
            prospect_name=assessment.prospect_name,
            prospect_url=assessment.prospect_url,
            industry=assessment.industry,
            business_location=json.dumps(assessment.business_location) if assessment.business_location else None,
            service_area=json.dumps(assessment.service_area) if assessment.service_area else None,
            contact_info=json.dumps(assessment.contact_info) if assessment.contact_info else None,
            business_profile=json.dumps(assessment.business_profile) if assessment.business_profile else None,
            status="draft"
        )
        
        db.add(new_assessment)
        db.commit()
        db.refresh(new_assessment)
        
        return {
            "status": "success",
            "assessment_id": assessment_id,
            "assessment": new_assessment.to_dict(),
            "message": "Assessment created successfully"
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating assessment: {str(e)}")


@app.get("/api/assessments")
async def list_assessments(
    page: int = 1,
    limit: int = 10,
    search: Optional[str] = None,
    industry: Optional[str] = None,
    p_score: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List assessments with filtering and pagination"""
    try:
        query = db.query(Assessment)
        
        # Apply filters
        if search:
            query = query.filter(
                (Assessment.prospect_name.ilike(f"%{search}%")) |
                (Assessment.prospect_url.ilike(f"%{search}%")) |
                (Assessment.assessment_id.ilike(f"%{search}%"))
            )
        if industry:
            query = query.filter(Assessment.industry == industry)
        if p_score:
            query = query.filter(Assessment.p_classification == p_score)
        if status:
            query = query.filter(Assessment.status == status)
        
        # Get total count
        total = query.count()
        
        # Paginate
        offset = (page - 1) * limit
        assessments = query.order_by(Assessment.created_at.desc()).offset(offset).limit(limit).all()
        
        # Convert to dicts safely
        assessments_list = []
        for a in assessments:
            try:
                assessments_list.append(a.to_dict())
            except Exception as e:
                # Fallback if to_dict fails
                assessments_list.append({
                    "id": a.id,
                    "assessment_id": a.assessment_id,
                    "prospect_name": a.prospect_name,
                    "prospect_url": a.prospect_url,
                    "status": a.status,
                    "overall_score": float(a.overall_score) if a.overall_score else None,
                    "letter_grade": a.letter_grade,
                    "p_classification": a.p_classification,
                    "created_at": a.created_at.isoformat() if a.created_at else None,
                    "completed_at": a.completed_at.isoformat() if a.completed_at else None
                })
        
        return {
            "total": total,
            "page": page,
            "limit": limit,
            "assessments": assessments_list
        }
    except Exception as e:
        import traceback
        error_detail = f"Error listing assessments: {str(e)}\n{traceback.format_exc()}"
        print(f"ERROR in list_assessments: {error_detail}")
        raise HTTPException(status_code=500, detail=f"Error listing assessments: {str(e)}")


@app.get("/api/assessments/{assessment_id}")
async def get_assessment(assessment_id: str, db: Session = Depends(get_db)):
    """Get assessment details"""
    try:
        assessment = db.query(Assessment).filter(Assessment.assessment_id == assessment_id).first()
        if not assessment:
            raise HTTPException(status_code=404, detail="Assessment not found")
        
        # Get related data
        competitors = db.query(Competitor).filter(Competitor.assessment_id == assessment.id).all()
        module_scores = db.query(ModuleScore).filter(ModuleScore.assessment_id == assessment.id).all()
        priorities = db.query(Priority).filter(Priority.assessment_id == assessment.id).order_by(Priority.priority_rank).all()
        
        result = assessment.to_dict()
        result["competitors"] = [{"name": c.competitor_name, "url": c.competitor_url, "score": c.overall_score} for c in competitors]
        result["module_scores"] = [{"module": m.module_letter, "score": m.module_score, "grade": m.module_grade} for m in module_scores]
        result["priorities"] = [{"rank": p.priority_rank, "title": p.priority_title, "impact": p.impact} for p in priorities]
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching assessment: {str(e)}")


@app.post("/api/assessments/{assessment_id}/competitors")
async def add_competitors(
    assessment_id: str,
    competitors: List[CompetitorCreate],
    db: Session = Depends(get_db)
):
    """Add competitors to assessment (Step 2: Competitor Selection)"""
    try:
        assessment = db.query(Assessment).filter(Assessment.assessment_id == assessment_id).first()
        if not assessment:
            raise HTTPException(status_code=404, detail="Assessment not found")
        
        for comp_data in competitors:
            competitor = Competitor(
                assessment_id=assessment.id,
                competitor_name=comp_data.competitor_name,
                competitor_url=comp_data.competitor_url,
                competitor_location=json.dumps(comp_data.competitor_location) if comp_data.competitor_location else None
            )
            db.add(competitor)
        
        db.commit()
        return {"status": "success", "message": f"Added {len(competitors)} competitors"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error adding competitors: {str(e)}")


@app.post("/api/assessments/{assessment_id}/configure")
async def configure_assessment(
    assessment_id: str,
    config: AssessmentConfig,
    db: Session = Depends(get_db)
):
    """Configure assessment (Step 3: Configuration)"""
    try:
        assessment = db.query(Assessment).filter(Assessment.assessment_id == assessment_id).first()
        if not assessment:
            raise HTTPException(status_code=404, detail="Assessment not found")
        
        assessment.assessment_mode = config.assessment_mode
        assessment.modules_selected = json.dumps(config.modules_selected)
        assessment.depth_level = config.depth_level
        assessment.ai_model = config.ai_model
        assessment.appendices_selected = json.dumps(config.appendices_selected) if config.appendices_selected else None
        
        db.commit()
        return {"status": "success", "message": "Assessment configured"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error configuring assessment: {str(e)}")


@app.post("/api/assessments/{assessment_id}/launch")
async def launch_assessment(
    assessment_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Launch assessment (Step 4: Review & Launch)"""
    try:
        assessment = db.query(Assessment).filter(Assessment.assessment_id == assessment_id).first()
        if not assessment:
            raise HTTPException(status_code=404, detail="Assessment not found")
        
        assessment.status = "in_progress"
        assessment.overall_progress = 0
        db.commit()
        
        # Queue background processing
        background_tasks.add_task(process_assessment_pipeline, assessment_id, db)
        
        return {
            "status": "success",
            "message": "Assessment launched",
            "assessment_id": assessment_id
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error launching assessment: {str(e)}")


@app.get("/api/assessments/{assessment_id}/status")
async def get_assessment_status(assessment_id: str, db: Session = Depends(get_db)):
    """Get assessment progress status"""
    try:
        assessment = db.query(Assessment).filter(Assessment.assessment_id == assessment_id).first()
        if not assessment:
            raise HTTPException(status_code=404, detail="Assessment not found")
        
        return {
            "assessment_id": assessment_id,
            "status": assessment.status,
            "progress": assessment.overall_progress,
            "stage_1": assessment.stage_1_status,
            "stage_2": assessment.stage_2_status,
            "stage_3": assessment.stage_3_status,
            "stage_4": assessment.stage_4_status,
            "stage_5": assessment.stage_5_status
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching status: {str(e)}")


# ============================================================================
# Reports Endpoints
# ============================================================================

@app.get("/api/reports")
async def list_reports(
    page: int = 1,
    limit: int = 12,
    report_type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List all reports"""
    try:
        query = db.query(Report)
        if report_type:
            query = query.filter(Report.report_type == report_type)
        
        total = query.count()
        offset = (page - 1) * limit
        reports = query.order_by(Report.generated_at.desc()).offset(offset).limit(limit).all()
        
        return {
            "total": total,
            "page": page,
            "limit": limit,
            "reports": [{
                "id": r.id,
                "assessment_id": r.assessment.assessment_id,
                "report_type": r.report_type,
                "file_url": r.file_url,
                "generated_at": r.generated_at.isoformat() if r.generated_at else None
            } for r in reports]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing reports: {str(e)}")


@app.get("/api/reports/{report_id}")
async def get_report(report_id: int, db: Session = Depends(get_db)):
    """Get report details"""
    try:
        report = db.query(Report).filter(Report.id == report_id).first()
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")
        
        if report.file_path and os.path.exists(report.file_path):
            return FileResponse(report.file_path)
        else:
            raise HTTPException(status_code=404, detail="Report file not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching report: {str(e)}")


# ============================================================================
# Appendices Endpoints
# ============================================================================

@app.get("/api/appendices")
async def list_appendices(
    category: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List all appendices"""
    try:
        from models import Appendix
        query = db.query(Appendix)
        if category:
            query = query.filter(Appendix.category == category)
        
        appendices = query.order_by(Appendix.appendix_letter).all()
        
        return {
            "total": len(appendices),
            "appendices": [{
                "id": a.id,
                "letter": a.appendix_letter,
                "title": a.appendix_title,
                "description": a.appendix_description,
                "category": a.category,
                "page_count": a.page_count
            } for a in appendices]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing appendices: {str(e)}")


# ============================================================================
# Background Processing
# ============================================================================

async def process_assessment_pipeline(assessment_id: str, db: Session):
    """
    5-Stage AI Pipeline for assessment processing
    
    Stage 1: URL Analysis & Scraping
    Stage 2: Competitor Benchmarking
    Stage 3: Gap Identification
    Stage 4: Scoring Algorithm
    Stage 5: Report Generation
    """
    try:
        assessment = db.query(Assessment).filter(Assessment.assessment_id == assessment_id).first()
        if not assessment:
            return
        
        # Stage 1: URL Analysis
        assessment.stage_1_status = "in_progress"
        assessment.overall_progress = 10
        db.commit()
        
        # TODO: Implement actual URL analysis
        await asyncio.sleep(2)  # Simulate processing
        
        assessment.stage_1_status = "complete"
        assessment.overall_progress = 20
        db.commit()
        
        # Stage 2: Competitor Benchmarking
        assessment.stage_2_status = "in_progress"
        db.commit()
        
        # TODO: Implement competitor analysis
        await asyncio.sleep(2)
        
        assessment.stage_2_status = "complete"
        assessment.overall_progress = 40
        db.commit()
        
        # Stage 3: Gap Identification
        assessment.stage_3_status = "in_progress"
        db.commit()
        
        # TODO: Implement gap analysis
        await asyncio.sleep(2)
        
        assessment.stage_3_status = "complete"
        assessment.overall_progress = 60
        db.commit()
        
        # Stage 4: Scoring Algorithm
        assessment.stage_4_status = "in_progress"
        db.commit()
        
        # Calculate module scores (placeholder - implement actual scoring)
        module_scores_data = calculate_module_scores(assessment)
        
        for module_letter, score_data in module_scores_data.items():
            module_score = ModuleScore(
                assessment_id=assessment.id,
                module_letter=module_letter,
                module_name=score_data["name"],
                module_score=score_data["score"],
                module_grade=score_data["grade"],
                status=score_data["status"]
            )
            db.add(module_score)
        
        # Calculate overall score
        overall_score = sum(s["score"] for s in module_scores_data.values()) / len(module_scores_data)
        assessment.overall_score = overall_score
        assessment.letter_grade = get_letter_grade(overall_score)
        assessment.p_classification = get_p_classification(overall_score)
        
        assessment.stage_4_status = "complete"
        assessment.overall_progress = 80
        db.commit()
        
        # Stage 5: Report Generation
        assessment.stage_5_status = "in_progress"
        db.commit()
        
        # TODO: Generate actual reports
        await asyncio.sleep(2)
        
        assessment.stage_5_status = "complete"
        assessment.overall_progress = 100
        assessment.status = "completed"
        assessment.completed_at = datetime.utcnow()
        db.commit()
        
    except Exception as e:
        assessment.status = "failed"
        db.commit()
        print(f"Error processing assessment {assessment_id}: {e}")


def calculate_module_scores(assessment: Assessment) -> Dict[str, Dict]:
    """Calculate module scores (placeholder - implement actual logic)"""
    # This is a placeholder - implement actual scoring logic
    base_score = 75.0
    return {
        "A": {"name": "Visibility & Discoverability", "score": base_score, "grade": "B", "status": "good"},
        "B": {"name": "Reputation & Trust Signals", "score": base_score + 5, "grade": "B", "status": "good"},
        "C": {"name": "On-Site Experience", "score": base_score + 10, "grade": "A", "status": "excellent"},
        "D": {"name": "Conversion Path", "score": base_score - 5, "grade": "B", "status": "good"},
        "E": {"name": "AI SEO Readiness", "score": base_score + 8, "grade": "A", "status": "excellent"},
        "E1": {"name": "Content Gap Analysis", "score": base_score - 10, "grade": "C", "status": "moderate"},
        "E2": {"name": "AI Surface Visibility", "score": base_score - 5, "grade": "B", "status": "good"},
        "F": {"name": "Google Authority Stack", "score": base_score + 12, "grade": "A", "status": "excellent"}
    }


def get_letter_grade(score: float) -> str:
    """Convert score to letter grade"""
    if score >= 90:
        return "A"
    elif score >= 75:
        return "B"
    elif score >= 60:
        return "C"
    else:
        return "D"


def get_p_classification(score: float) -> str:
    """Convert score to P-classification"""
    if score >= 90:
        return "P0"
    elif score >= 75:
        return "P1"
    elif score >= 60:
        return "P2"
    else:
        return "P3"


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8100)

