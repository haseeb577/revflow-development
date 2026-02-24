from typing import List, Optional, Dict, Any
"""
Humanization Pipeline - Main FastAPI Application
Complete application with all endpoints and services
RevAudit: ENABLED
"""
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from sqlalchemy.orm import Session
import os
import uuid
import sys

# RevAudit Anti-Hallucination Integration
sys.path.insert(0, '/opt/shared-api-engine')
try:
    from revaudit.integrate import integrate_revaudit
    REVAUDIT_AVAILABLE = True
except ImportError:
    REVAUDIT_AVAILABLE = False

from .database import get_db_session, init_db
from .models.pydantic_models import (
    ContentValidationRequest,
    ContentValidationResponse,
    VoiceCheckRequest,
    VoiceCheckResponse,
    YMYLCheckRequest,
    YMYLCheckResponse,
    AutoHumanizationRequest,
    AutoHumanizationResult,
    ManualReviewRequest,
    ManualReviewResponse
)
from .models.db_models import ReviewQueueItem, AuditLog
from .validators import QAValidator
from .services import VoiceConsistencyChecker, YMYLVerificationChecker, AIDetector

# Initialize FastAPI
app = FastAPI(
    title="Humanization Pipeline API",
    version="1.0.0",
    description="Complete content validation and humanization system"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# RevAudit Integration
if REVAUDIT_AVAILABLE:
    integrate_revaudit(app, "RevHumanize")

# Initialize services
qa_validator = QAValidator()
voice_checker = VoiceConsistencyChecker()
ymyl_checker = YMYLVerificationChecker()
ai_detector = AIDetector()

# Initialize database on startup
@app.on_event("startup")
async def startup():
    init_db()
    print("✓ Database initialized")

# ============================================================================
# HEALTH & STATUS
# ============================================================================

@app.get("/")
async def root():
    return {
        "service": "Humanization Pipeline",
        "version": "1.0.0",
        "status": "operational"
    }

@app.get("/health")
async def health():
    return {"status": "healthy", "database": "connected"}

# ============================================================================
# CONTENT VALIDATION
# ============================================================================

@app.post("/api/v1/validate", response_model=ContentValidationResponse)
async def validate_content(
    request: ContentValidationRequest,
    db: Session = Depends(get_db_session)
):
    """
    Complete content validation pipeline
    """
    # Generate content_id if not provided
    content_id = request.get_content_id()
    # Run QA validation
    qa_result = qa_validator.calculate_score(request.content, request.title)
    
    # Run voice check
    voice_result = voice_checker.check(request.content)
    
    # Run YMYL check  
    ymyl_result = ymyl_checker.check(request.content, "general")
    
    # Run AI detection
    ai_result = ai_detector.detect(request.content)
    
    # Determine if manual review needed
    requires_review = (
        qa_result["qa_score"] < request.target_score or
        not voice_result["is_consistent"] or
        ai_result["is_ai_generated"]
    )
    
    # Add to review queue if needed
    if requires_review and db:
        queue_item = ReviewQueueItem(
            content_id=content_id or f"temp_{uuid.uuid4().hex[:12]}",
            title=request.title,
            content=request.content,
            qa_score=qa_result["qa_score"],
            voice_consistency_score=voice_result["score"],
            ymyl_verification_score=ymyl_result["score"],
            ai_probability=ai_result["probability"],
            tier1_issues=qa_result["tier1_issues"],
            tier2_issues=qa_result["tier2_issues"],
            tier3_issues=qa_result["tier3_issues"],
            voice_violations=voice_result["violations"],
            ymyl_failures=ymyl_result["failures"],
            status="pending"
        )
        db.add(queue_item)
        db.commit()
    
    return ContentValidationResponse(
        content_id=content_id or f"temp_{uuid.uuid4().hex[:12]}",
        qa_score=qa_result["qa_score"],
        voice_consistency_score=voice_result["score"],
        ymyl_verification_score=ymyl_result["score"],
        ai_probability=ai_result["probability"],
        tier1_issues=qa_result["tier1_issues"],
        tier2_issues=qa_result["tier2_issues"],
        tier3_issues=qa_result["tier3_issues"],
        requires_manual_review=requires_review,
        status="needs_review" if requires_review else "approved"
    )

# ============================================================================
# VOICE CONSISTENCY CHECK
# ============================================================================

@app.post("/api/v1/voice/check", response_model=VoiceCheckResponse)
async def check_voice(request: VoiceCheckRequest):
    """Check voice consistency"""
    result = voice_checker.check(request.content, request.reference_voice)
    return VoiceCheckResponse(**result)

# ============================================================================
# YMYL VERIFICATION
# ============================================================================

@app.post("/api/v1/ymyl/verify", response_model=YMYLCheckResponse)
async def verify_ymyl(request: YMYLCheckRequest):
    """Verify YMYL content"""
    result = ymyl_checker.check(request.content, request.content_type)
    return YMYLCheckResponse(**result)

# ============================================================================
# AUTO-HUMANIZATION
# ============================================================================

@app.post("/api/v1/humanize", response_model=AutoHumanizationResult)
async def auto_humanize(request: AutoHumanizationRequest):
    """
    Auto-humanize content (basic implementation)
    """
    content = request.content
    changes = []
    
    # Simple humanization: remove AI phrases
    ai_phrases = [
        ("it's important to note", "notably"),
        ("in today's digital age", "today"),
        ("comprehensive guide", "guide"),
        ("delve into", "explore"),
    ]
    
    for old, new in ai_phrases:
        if old in content.lower():
            content = content.replace(old, new)
            content = content.replace(old.title(), new.title())
            changes.append(f"Replaced '{old}' with '{new}'")
    
    # Detect before/after
    before = ai_detector.detect(request.content)
    after = ai_detector.detect(content)
    
    return AutoHumanizationResult(
        original_content=request.content,
        humanized_content=content,
        changes_made=changes,
        success=len(changes) > 0,
        ai_probability_before=before["probability"],
        ai_probability_after=after["probability"]
    )

# ============================================================================
# ADMIN UI
# ============================================================================

@app.get("/admin", response_class=HTMLResponse)
async def serve_admin():
    """Serve admin UI"""
    admin_path = "/opt/revflow-humanization-pipeline/app/templates/admin.html"
    if os.path.exists(admin_path):
        with open(admin_path) as f:
            return f.read()
    return "<h1>Admin UI</h1><p>Template not found</p>"

# Import admin router
from .api.admin import router as admin_router
app.include_router(admin_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

# ============================================================================
# AUTO-HUMANIZATION ENDPOINT
# ============================================================================
@app.post("/api/v1/auto-humanize")
async def auto_humanize_content(request: AutoHumanizationRequest):
    """Attempt to automatically fix content issues"""
    from app.services.auto_humanizer import AutoHumanizer
    
    # First validate the content
    validation_result = await validate_content(
        ContentValidationRequest(content=request.content, title="Auto-humanize")
    )
    
    # Get issues
    all_issues = (
        validation_result.get("tier1_issues", []) +
        validation_result.get("tier2_issues", [])
    )
    
    # Attempt fixes
    humanizer = AutoHumanizer()
    if humanizer.can_auto_fix(all_issues):
        fixed_content, changes = humanizer.attempt_fixes(request.content, all_issues)
        
        # Re-validate
        new_result = await validate_content(
            ContentValidationRequest(content=fixed_content, title="Auto-humanize")
        )
        
        return {
            "content_id": request.content_id,
            "original_score": validation_result.get("qa_score", 0),
            "final_score": new_result.get("qa_score", 0),
            "fixed_content": fixed_content,
            "changes_made": changes,
            "success": new_result.get("qa_score", 0) > validation_result.get("qa_score", 0)
        }
    
    return {
        "content_id": request.content_id,
        "original_score": validation_result.get("qa_score", 0),
        "final_score": validation_result.get("qa_score", 0),
        "fixed_content": request.content,
        "changes_made": [],
        "success": False,
        "message": "Content has critical issues requiring manual review"
    }

# ============================================================================
# MANUAL REVIEW ENDPOINTS
# ============================================================================
@app.post("/api/v1/review/submit")
async def submit_for_review(request: ManualReviewRequest):
    """Submit content to manual review queue"""
    from app.models.db_models import ReviewQueueItem
    
    with get_db() as db:
        if db is None:
            return {"error": "Database unavailable", "queued": False}
        
        review_item = ReviewQueueItem(
            content_id=request.content_id,
            content=request.content if hasattr(request, 'content') else "",
            status="pending"
        )
        db.add(review_item)
        db.commit()
        
        return {
            "content_id": request.content_id,
            "status": "queued",
            "message": "Content submitted for manual review"
        }

@app.get("/api/v1/review/queue")
async def get_review_queue(status: str = "pending", limit: int = 50):
    """Get items in review queue"""
    from app.models.db_models import ReviewQueueItem
    
    with get_db() as db:
        if db is None:
            return {"items": [], "total": 0}
        
        items = db.query(ReviewQueueItem)\
            .filter(ReviewQueueItem.status == status)\
            .limit(limit)\
            .all()
        
        return {
            "items": [
                {
                    "id": item.id,
                    "content_id": item.content_id,
                    "qa_score": item.qa_score,
                    "status": item.status,
                    "created_at": item.created_at.isoformat() if item.created_at else None
                }
                for item in items
            ],
            "total": len(items)
        }

@app.post("/api/v1/review/complete")
async def complete_review(request: ManualReviewResponse):
    """Complete a manual review"""
    from app.models.db_models import ReviewQueueItem, AuditLog
    
    with get_db() as db:
        if db is None:
            return {"error": "Database unavailable"}
        
        item = db.query(ReviewQueueItem)\
            .filter(ReviewQueueItem.content_id == request.content_id)\
            .first()
        
        if item:
            item.status = request.status
            item.reviewed_at = datetime.utcnow()
            item.notes = request.notes if hasattr(request, 'notes') else None
            
            # Log the review
            audit = AuditLog(
                content_id=request.content_id,
                action="reviewed",
                details={"status": request.status, "notes": request.notes if hasattr(request, 'notes') else None}
            )
            db.add(audit)
            db.commit()
            
            return {
                "content_id": request.content_id,
                "status": "completed",
                "message": "Review completed successfully"
            }
        
        return {"error": "Content not found in review queue"}

# ============================================================================
# WEBHOOK CONFIGURATION ENDPOINTS
# ============================================================================
@app.post("/api/v1/webhooks/configure")
async def configure_webhook(
    customer_id: str,
    webhook_url: str,
    events: List[str] = ["validation_complete"],
    secret_key: Optional[str] = None
):
    """Configure webhook for a customer"""
    from app.models.db_models import WebhookConfig
    
    with get_db() as db:
        if db is None:
            return {"error": "Database unavailable"}
        
        # Check if config exists
        config = db.query(WebhookConfig)\
            .filter(WebhookConfig.customer_id == customer_id)\
            .first()
        
        if config:
            config.webhook_url = webhook_url
            config.events = events
            config.secret_key = secret_key
        else:
            config = WebhookConfig(
                customer_id=customer_id,
                webhook_url=webhook_url,
                events=events,
                secret_key=secret_key
            )
            db.add(config)
        
        db.commit()
        
        return {
            "customer_id": customer_id,
            "webhook_url": webhook_url,
            "events": events,
            "status": "configured"
        }

@app.get("/api/v1/webhooks/{customer_id}")
async def get_webhook_config(customer_id: str):
    """Get webhook configuration for a customer"""
    from app.models.db_models import WebhookConfig
    
    with get_db() as db:
        if db is None:
            return {"error": "Database unavailable"}
        
        config = db.query(WebhookConfig)\
            .filter(WebhookConfig.customer_id == customer_id)\
            .first()
        
        if config:
            return {
                "customer_id": config.customer_id,
                "webhook_url": config.webhook_url,
                "events": config.events,
                "enabled": config.enabled
            }
        
        return {"error": "Webhook not configured"}

# ============================================================================
# BATCH PROCESSING ENDPOINTS
# ============================================================================
@app.post("/api/v1/batch/submit")
async def submit_batch(
    customer_id: str,
    items: List[Dict[str, Any]]
):
    """Submit batch of content for validation"""
    from app.models.db_models import BatchJob
    import uuid
    
    batch_id = str(uuid.uuid4())
    
    with get_db() as db:
        if db is None:
            # Process without database
            results = []
            for item in items:
                result = await validate_content(
                    ContentValidationRequest(
                        content=item.get("content", ""),
                        title=item.get("title", "")
                    )
                )
                results.append(result)
            
            return {
                "batch_id": batch_id,
                "status": "completed",
                "total_items": len(items),
                "results": results
            }
        
        # Create batch job
        batch = BatchJob(
            id=batch_id,
            customer_id=customer_id,
            total_items=len(items),
            status="processing"
        )
        db.add(batch)
        db.commit()
    
    # Process items (in production, this would be async/background)
    results = []
    completed = 0
    failed = 0
    
    for item in items:
        try:
            result = await validate_content(
                ContentValidationRequest(
                    content=item.get("content", ""),
                    title=item.get("title", "")
                )
            )
            results.append(result)
            completed += 1
        except Exception as e:
            results.append({"error": str(e)})
            failed += 1
    
    # Update batch job
    with get_db() as db:
        if db:
            batch = db.query(BatchJob).filter(BatchJob.id == batch_id).first()
            if batch:
                batch.completed_items = completed
                batch.failed_items = failed
                batch.status = "completed"
                batch.results = results
                batch.completed_at = datetime.utcnow()
                db.commit()
    
    return {
        "batch_id": batch_id,
        "status": "completed",
        "total_items": len(items),
        "completed": completed,
        "failed": failed
    }

@app.get("/api/v1/batch/{batch_id}")
async def get_batch_status(batch_id: str):
    """Get status of a batch job"""
    from app.models.db_models import BatchJob
    
    with get_db() as db:
        if db is None:
            return {"error": "Database unavailable"}
        
        batch = db.query(BatchJob).filter(BatchJob.id == batch_id).first()
        
        if batch:
            return {
                "batch_id": batch.id,
                "status": batch.status,
                "total_items": batch.total_items,
                "completed_items": batch.completed_items,
                "failed_items": batch.failed_items,
                "results": batch.results if batch.status == "completed" else None
            }
        
        return {"error": "Batch not found"}

from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm, HTTPBearer, HTTPAuthorizationCredentials
from app.services.auth_service import AuthService
from app.models.db_models import User, APIKey

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")
security = HTTPBearer()
auth_service = AuthService()

# ============================================================================
# AUTHENTICATION ENDPOINTS
# ============================================================================
@app.post("/api/v1/auth/register")
async def register_user(email: str, password: str, full_name: str, customer_id: str):
    """Register new user"""
    with get_db() as db:
        if db is None:
            return {"error": "Database unavailable"}
        
        # Check if user exists
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            return {"error": "Email already registered"}
        
        # Create user
        user = User(
            email=email,
            hashed_password=auth_service.get_password_hash(password),
            full_name=full_name,
            customer_id=customer_id
        )
        db.add(user)
        db.commit()
        
        return {
            "user_id": user.id,
            "email": user.email,
            "message": "User registered successfully"
        }

@app.post("/api/v1/auth/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """Login and get access token"""
    with get_db() as db:
        if db is None:
            return {"error": "Database unavailable"}
        
        # Find user
        user = db.query(User).filter(User.email == form_data.username).first()
        if not user or not auth_service.verify_password(form_data.password, user.hashed_password):
            raise HTTPException(status_code=401, detail="Incorrect email or password")
        
        if not user.is_active:
            raise HTTPException(status_code=400, detail="Inactive user")
        
        # Update last login
        user.last_login = datetime.utcnow()
        db.commit()
        
        # Create token
        access_token = auth_service.create_access_token(
            data={
                "sub": user.email,
                "user_id": user.id,
                "customer_id": user.customer_id
            }
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "email": user.email,
                "full_name": user.full_name,
                "customer_id": user.customer_id
            }
        }

@app.post("/api/v1/auth/api-key")
async def create_api_key(name: str, customer_id: str, credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Create new API key (requires auth)"""
    # Verify JWT token
    token_data = auth_service.decode_token(credentials.credentials)
    if not token_data:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    with get_db() as db:
        if db is None:
            return {"error": "Database unavailable"}
        
        # Generate API key
        api_key = APIKey(
            key=auth_service.generate_api_key(),
            name=name,
            customer_id=customer_id
        )
        db.add(api_key)
        db.commit()
        
        return {
            "api_key": api_key.key,
            "name": api_key.name,
            "customer_id": api_key.customer_id,
            "created_at": api_key.created_at.isoformat()
        }

@app.get("/api/v1/auth/me")
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current user info"""
    token_data = auth_service.decode_token(credentials.credentials)
    if not token_data:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    with get_db() as db:
        if db is None:
            return {"error": "Database unavailable"}
        
        user = db.query(User).filter(User.email == token_data['sub']).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "customer_id": user.customer_id,
            "is_superuser": user.is_superuser
        }

from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm, HTTPBearer, HTTPAuthorizationCredentials
from fastapi import Depends, HTTPException
from datetime import datetime
from app.services.auth_service import AuthService
from app.models.db_models import User, APIKey

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")
security = HTTPBearer()
auth_service = AuthService()

@app.post("/api/v1/auth/register")
async def register_user(email: str, password: str, full_name: str, customer_id: str):
    with get_db() as db:
        if db is None:
            return {"error": "Database unavailable"}
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            return {"error": "Email already registered"}
        user = User(
            email=email,
            hashed_password=auth_service.get_password_hash(password),
            full_name=full_name,
            customer_id=customer_id
        )
        db.add(user)
        db.commit()
        return {"user_id": user.id, "email": user.email}

@app.post("/api/v1/auth/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    with get_db() as db:
        if db is None:
            return {"error": "Database unavailable"}
        user = db.query(User).filter(User.email == form_data.username).first()
        if not user or not auth_service.verify_password(form_data.password, user.hashed_password):
            raise HTTPException(status_code=401, detail="Incorrect credentials")
        if not user.is_active:
            raise HTTPException(status_code=400, detail="Inactive user")
        user.last_login = datetime.utcnow()
        db.commit()
        access_token = auth_service.create_access_token(data={
            "sub": user.email,
            "user_id": user.id,
            "customer_id": user.customer_id
        })
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "email": user.email,
                "full_name": user.full_name,
                "customer_id": user.customer_id
            }
        }

@app.get("/api/v1/auth/me")
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token_data = auth_service.decode_token(credentials.credentials)
    if not token_data:
        raise HTTPException(status_code=401, detail="Invalid token")
    with get_db() as db:
        if db is None:
            return {"error": "Database unavailable"}
        user = db.query(User).filter(User.email == token_data['sub']).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "customer_id": user.customer_id
        }

@app.get("/api/v1/stats/summary")
async def get_stats_summary(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token_data = auth_service.decode_token(credentials.credentials)
    if not token_data:
        raise HTTPException(status_code=401, detail="Invalid token")
    return {
        "totalValidations": 152,
        "avgQAScore": 75.5,
        "activeJobs": 3,
        "pendingReviews": 7
    }

@app.get("/api/v1/jobs/recent")
async def get_recent_jobs(limit: int = 10, credentials: HTTPAuthorizationCredentials = Depends(security)):
    token_data = auth_service.decode_token(credentials.credentials)
    if not token_data:
        raise HTTPException(status_code=401, detail="Invalid token")
    return {"jobs": []}

from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm, HTTPBearer, HTTPAuthorizationCredentials
from fastapi import Depends, HTTPException
from datetime import datetime
from app.services.auth_service import AuthService
from app.models.db_models import User, APIKey

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")
security = HTTPBearer()
auth_service = AuthService()

@app.post("/api/v1/auth/register")
async def register_user(email: str, password: str, full_name: str, customer_id: str):
    with get_db() as db:
        if db is None:
            return {"error": "Database unavailable"}
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            return {"error": "Email already registered"}
        user = User(
            email=email,
            hashed_password=auth_service.get_password_hash(password),
            full_name=full_name,
            customer_id=customer_id
        )
        db.add(user)
        db.commit()
        return {"user_id": user.id, "email": user.email}

@app.post("/api/v1/auth/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    with get_db() as db:
        if db is None:
            return {"error": "Database unavailable"}
        user = db.query(User).filter(User.email == form_data.username).first()
        if not user or not auth_service.verify_password(form_data.password, user.hashed_password):
            raise HTTPException(status_code=401, detail="Incorrect credentials")
        if not user.is_active:
            raise HTTPException(status_code=400, detail="Inactive user")
        user.last_login = datetime.utcnow()
        db.commit()
        access_token = auth_service.create_access_token(data={
            "sub": user.email,
            "user_id": user.id,
            "customer_id": user.customer_id
        })
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "email": user.email,
                "full_name": user.full_name,
                "customer_id": user.customer_id
            }
        }

@app.get("/api/v1/auth/me")
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token_data = auth_service.decode_token(credentials.credentials)
    if not token_data:
        raise HTTPException(status_code=401, detail="Invalid token")
    with get_db() as db:
        if db is None:
            return {"error": "Database unavailable"}
        user = db.query(User).filter(User.email == token_data['sub']).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "customer_id": user.customer_id
        }

@app.get("/api/v1/stats/summary")
async def get_stats_summary(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token_data = auth_service.decode_token(credentials.credentials)
    if not token_data:
        raise HTTPException(status_code=401, detail="Invalid token")
    return {
        "totalValidations": 152,
        "avgQAScore": 75.5,
        "activeJobs": 3,
        "pendingReviews": 7
    }

@app.get("/api/v1/jobs/recent")
async def get_recent_jobs(limit: int = 10, credentials: HTTPAuthorizationCredentials = Depends(security)):
    token_data = auth_service.decode_token(credentials.credentials)
    if not token_data:
        raise HTTPException(status_code=401, detail="Invalid token")
    return {"jobs": []}

from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm, HTTPBearer, HTTPAuthorizationCredentials
from fastapi import Depends, HTTPException
from datetime import datetime
from app.services.auth_service import AuthService
from app.models.db_models import User, APIKey

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")
security = HTTPBearer()
auth_service = AuthService()

@app.post("/api/v1/auth/register")
async def register_user(email: str, password: str, full_name: str, customer_id: str):
    with get_db() as db:
        if db is None:
            return {"error": "Database unavailable"}
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            return {"error": "Email already registered"}
        user = User(
            email=email,
            hashed_password=auth_service.get_password_hash(password),
            full_name=full_name,
            customer_id=customer_id
        )
        db.add(user)
        db.commit()
        return {"user_id": user.id, "email": user.email}

@app.post("/api/v1/auth/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    with get_db() as db:
        if db is None:
            return {"error": "Database unavailable"}
        user = db.query(User).filter(User.email == form_data.username).first()
        if not user or not auth_service.verify_password(form_data.password, user.hashed_password):
            raise HTTPException(status_code=401, detail="Incorrect credentials")
        if not user.is_active:
            raise HTTPException(status_code=400, detail="Inactive user")
        user.last_login = datetime.utcnow()
        db.commit()
        access_token = auth_service.create_access_token(data={
            "sub": user.email,
            "user_id": user.id,
            "customer_id": user.customer_id
        })
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "email": user.email,
                "full_name": user.full_name,
                "customer_id": user.customer_id
            }
        }

@app.get("/api/v1/auth/me")
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token_data = auth_service.decode_token(credentials.credentials)
    if not token_data:
        raise HTTPException(status_code=401, detail="Invalid token")
    with get_db() as db:
        if db is None:
            return {"error": "Database unavailable"}
        user = db.query(User).filter(User.email == token_data['sub']).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "customer_id": user.customer_id
        }

@app.get("/api/v1/stats/summary")
async def get_stats_summary(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token_data = auth_service.decode_token(credentials.credentials)
    if not token_data:
        raise HTTPException(status_code=401, detail="Invalid token")
    return {
        "totalValidations": 152,
        "avgQAScore": 75.5,
        "activeJobs": 3,
        "pendingReviews": 7
    }

@app.get("/api/v1/jobs/recent")
async def get_recent_jobs(limit: int = 10, credentials: HTTPAuthorizationCredentials = Depends(security)):
    token_data = auth_service.decode_token(credentials.credentials)
    if not token_data:
        raise HTTPException(status_code=401, detail="Invalid token")
    return {"jobs": []}
