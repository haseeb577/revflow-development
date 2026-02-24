"""
Admin API Endpoints
Manage review queue, view stats, audit logs
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from datetime import datetime, timedelta

from ..database import get_db_session
from ..models.db_models import ReviewQueueItem, AuditLog, WebhookLog
from ..models.pydantic_models import ManualReviewRequest, ManualReviewResponse

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])

# ============================================================================
# REVIEW QUEUE
# ============================================================================

@router.get("/queue")
async def get_review_queue(
    status: Optional[str] = "pending",
    limit: int = 50,
    db: Session = Depends(get_db_session)
):
    """Get items from review queue"""
    query = db.query(ReviewQueueItem)
    
    if status:
        query = query.filter(ReviewQueueItem.status == status)
    
    items = query.order_by(ReviewQueueItem.created_at.desc()).limit(limit).all()
    
    return {
        "total": len(items),
        "items": [
            {
                "id": item.id,
                "content_id": item.content_id,
                "title": item.title,
                "qa_score": item.qa_score,
                "voice_score": item.voice_consistency_score,
                "ymyl_score": item.ymyl_verification_score,
                "ai_probability": item.ai_probability,
                "status": item.status,
                "created_at": item.created_at.isoformat() if item.created_at else None,
                "tier1_count": len(item.tier1_issues) if item.tier1_issues else 0,
                "tier2_count": len(item.tier2_issues) if item.tier2_issues else 0,
                "tier3_count": len(item.tier3_issues) if item.tier3_issues else 0
            }
            for item in items
        ]
    }

@router.get("/queue/{content_id}")
async def get_queue_item(
    content_id: str,
    db: Session = Depends(get_db_session)
):
    """Get specific queue item details"""
    item = db.query(ReviewQueueItem).filter(
        ReviewQueueItem.content_id == content_id
    ).first()
    
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    return {
        "content_id": item.content_id,
        "title": item.title,
        "content": item.content,
        "qa_score": item.qa_score,
        "voice_consistency_score": item.voice_consistency_score,
        "ymyl_verification_score": item.ymyl_verification_score,
        "ai_probability": item.ai_probability,
        "tier1_issues": item.tier1_issues,
        "tier2_issues": item.tier2_issues,
        "tier3_issues": item.tier3_issues,
        "voice_violations": item.voice_violations,
        "ymyl_failures": item.ymyl_failures,
        "status": item.status,
        "created_at": item.created_at.isoformat() if item.created_at else None
    }

@router.post("/queue/{content_id}/review", response_model=ManualReviewResponse)
async def review_item(
    content_id: str,
    request: ManualReviewRequest,
    db: Session = Depends(get_db_session)
):
    """Submit manual review decision"""
    item = db.query(ReviewQueueItem).filter(
        ReviewQueueItem.content_id == content_id
    ).first()
    
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    # Update item
    item.status = request.action
    item.reviewer_notes = request.notes
    item.reviewer_action = request.action
    item.reviewed_at = datetime.utcnow()
    
    # Log the action
    log = AuditLog(
        user="admin",
        action=f"review_{request.action}",
        entity_type="review_queue_item",
        entity_id=content_id,
        changes={"action": request.action, "notes": request.notes}
    )
    db.add(log)
    db.commit()
    
    return ManualReviewResponse(
        success=True,
        message=f"Item {request.action}",
        status=item.status
    )

# ============================================================================
# STATISTICS
# ============================================================================

@router.get("/stats")
async def get_stats(db: Session = Depends(get_db_session)):
    """Get system statistics"""
    
    # Queue stats
    pending = db.query(func.count(ReviewQueueItem.id)).filter(
        ReviewQueueItem.status == "pending"
    ).scalar()
    
    approved = db.query(func.count(ReviewQueueItem.id)).filter(
        ReviewQueueItem.status == "approve"
    ).scalar()
    
    rejected = db.query(func.count(ReviewQueueItem.id)).filter(
        ReviewQueueItem.status == "reject"
    ).scalar()
    
    # Average queue time
    avg_queue_time = db.query(
        func.avg(
            func.julianday(ReviewQueueItem.reviewed_at) - 
            func.julianday(ReviewQueueItem.created_at)
        )
    ).filter(
        ReviewQueueItem.reviewed_at.isnot(None)
    ).scalar()
    
    return {
        "queue": {
            "pending": pending or 0,
            "approved": approved or 0,
            "rejected": rejected or 0,
            "total": (pending or 0) + (approved or 0) + (rejected or 0)
        },
        "performance": {
            "avg_queue_time_hours": round((avg_queue_time or 0) * 24, 1)
        }
    }

# ============================================================================
# AUDIT LOG
# ============================================================================

@router.get("/audit")
async def get_audit_log(
    limit: int = 100,
    db: Session = Depends(get_db_session)
):
    """Get audit log entries"""
    entries = db.query(AuditLog).order_by(
        AuditLog.timestamp.desc()
    ).limit(limit).all()
    
    return {
        "total": len(entries),
        "entries": [
            {
                "id": e.id,
                "timestamp": e.timestamp.isoformat() if e.timestamp else None,
                "user": e.user,
                "action": e.action,
                "entity_type": e.entity_type,
                "entity_id": e.entity_id,
                "success": e.success
            }
            for e in entries
        ]
    }
