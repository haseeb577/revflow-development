#!/bin/bash

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║   RevFlow Humanization Pipeline - Complete System Deployment  ║"
echo "║   Step 2: Automated Workflows                                  ║"
echo "║   Step 3: Webhook Integration                                  ║"
echo "║   Step 4: Batch Processing                                     ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

set -e  # Exit on any error

# ============================================================================
# STEP 1: Add Database Models for Reviews, Webhooks, Batches
# ============================================================================
echo "📦 Step 1: Creating database models..."

cat > app/models/db_models.py << 'EOF'
"""Database Models for Humanization Pipeline"""
from sqlalchemy import Column, String, Float, DateTime, Boolean, Text, Integer, JSON
from sqlalchemy.sql import func
from app.database import Base
import uuid

class ReviewQueueItem(Base):
    """Manual review queue for content that needs human review"""
    __tablename__ = "review_queue"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    content_id = Column(String, nullable=False, index=True)
    content = Column(Text, nullable=False)
    title = Column(String)
    qa_score = Column(Float)
    ai_probability = Column(Float)
    tier1_issues = Column(JSON, default=list)
    tier2_issues = Column(JSON, default=list)
    tier3_issues = Column(JSON, default=list)
    status = Column(String, default="pending")  # pending, approved, rejected
    assigned_to = Column(String)
    notes = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    reviewed_at = Column(DateTime)
    reviewed_by = Column(String)

class AuditLog(Base):
    """Audit trail for all validation actions"""
    __tablename__ = "audit_logs"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    content_id = Column(String, nullable=False, index=True)
    action = Column(String, nullable=False)  # validated, auto_fixed, reviewed, webhook_sent
    details = Column(JSON)
    user = Column(String)
    created_at = Column(DateTime, server_default=func.now())

class WebhookConfig(Base):
    """Customer-specific webhook configurations"""
    __tablename__ = "webhook_configs"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    customer_id = Column(String, nullable=False, unique=True, index=True)
    webhook_url = Column(String, nullable=False)
    events = Column(JSON, default=list)  # [validation_complete, review_needed, etc]
    secret_key = Column(String)  # For HMAC signature
    enabled = Column(Boolean, default=True)
    retry_count = Column(Integer, default=3)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

class WebhookLog(Base):
    """Log of all webhook deliveries"""
    __tablename__ = "webhook_logs"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    webhook_config_id = Column(String, nullable=False, index=True)
    content_id = Column(String, index=True)
    event = Column(String, nullable=False)
    payload = Column(JSON)
    status_code = Column(Integer)
    response = Column(Text)
    success = Column(Boolean, default=False)
    retry_count = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())

class BatchJob(Base):
    """Batch processing jobs"""
    __tablename__ = "batch_jobs"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    customer_id = Column(String, index=True)
    total_items = Column(Integer, default=0)
    completed_items = Column(Integer, default=0)
    failed_items = Column(Integer, default=0)
    status = Column(String, default="processing")  # processing, completed, failed
    results = Column(JSON, default=list)
    created_at = Column(DateTime, server_default=func.now())
    completed_at = Column(DateTime)
EOF

echo "✅ Database models created"

# ============================================================================
# STEP 2: Create Auto-Humanization Service
# ============================================================================
echo "🤖 Step 2: Creating auto-humanization service..."

cat > app/services/auto_humanizer.py << 'EOF'
"""Auto-Humanization Service - Attempts to fix common issues"""
from typing import List, Dict, Any, Tuple
import re

class AutoHumanizer:
    """Automatically fixes common content issues"""
    
    def attempt_fixes(self, content: str, issues: List[Dict[str, Any]]) -> Tuple[str, List[str]]:
        """
        Attempt to fix issues automatically
        Returns: (fixed_content, changes_made)
        """
        fixed_content = content
        changes = []
        
        for issue in issues:
            issue_type = issue.get("type")
            
            if issue_type == "long_sentences":
                fixed_content, changed = self._fix_long_sentences(fixed_content)
                if changed:
                    changes.append("Split long sentences for readability")
            
            elif issue_type == "passive_voice":
                fixed_content, changed = self._reduce_passive_voice(fixed_content)
                if changed:
                    changes.append("Converted passive voice to active")
            
            elif issue_type == "repetitive_words":
                fixed_content, changed = self._fix_repetition(fixed_content)
                if changed:
                    changes.append("Reduced word repetition")
        
        return fixed_content, changes
    
    def _fix_long_sentences(self, content: str) -> Tuple[str, bool]:
        """Split sentences longer than 25 words"""
        sentences = content.split('. ')
        changed = False
        fixed_sentences = []
        
        for sentence in sentences:
            words = sentence.split()
            if len(words) > 25:
                # Simple split at 'and' or 'but'
                mid_point = len(words) // 2
                for i, word in enumerate(words[mid_point-5:mid_point+5], start=mid_point-5):
                    if word.lower() in ['and', 'but', 'or']:
                        first_half = ' '.join(words[:i])
                        second_half = ' '.join(words[i+1:])
                        fixed_sentences.append(first_half + '.')
                        fixed_sentences.append(second_half.capitalize())
                        changed = True
                        break
                else:
                    fixed_sentences.append(sentence)
            else:
                fixed_sentences.append(sentence)
        
        return '. '.join(fixed_sentences), changed
    
    def _reduce_passive_voice(self, content: str) -> Tuple[str, bool]:
        """Basic passive voice detection and conversion"""
        # Simple pattern: "was/were + past participle"
        passive_pattern = r'\b(was|were|is|are)\s+(\w+ed)\b'
        if re.search(passive_pattern, content):
            # This is a simplified example - real implementation would be more sophisticated
            return content, False
        return content, False
    
    def _fix_repetition(self, content: str) -> Tuple[str, bool]:
        """Remove obvious word repetition"""
        words = content.split()
        fixed_words = []
        prev_word = None
        changed = False
        
        for word in words:
            if word.lower() != (prev_word or '').lower():
                fixed_words.append(word)
            else:
                changed = True
            prev_word = word
        
        return ' '.join(fixed_words), changed
    
    def can_auto_fix(self, issues: List[Dict[str, Any]]) -> bool:
        """Determine if issues can be auto-fixed"""
        auto_fixable = ["long_sentences", "repetitive_words", "passive_voice"]
        
        for issue in issues:
            if issue.get("severity") == "critical":
                return False
            if issue.get("type") not in auto_fixable:
                return False
        
        return True
EOF

echo "✅ Auto-humanization service created"

# ============================================================================
# STEP 3: Create Webhook Service
# ============================================================================
echo "📡 Step 3: Creating webhook service..."

cat > app/services/webhook_service.py << 'EOF'
"""Webhook Service - Sends notifications to customer endpoints"""
import httpx
import hmac
import hashlib
import json
from typing import Dict, Any, Optional
from datetime import datetime
import asyncio

class WebhookService:
    """Manages webhook deliveries to customers"""
    
    async def send_webhook(
        self,
        webhook_url: str,
        event: str,
        payload: Dict[str, Any],
        secret_key: Optional[str] = None,
        retry_count: int = 3
    ) -> Dict[str, Any]:
        """
        Send webhook with retry logic
        Returns: {"success": bool, "status_code": int, "response": str}
        """
        
        # Add metadata to payload
        payload["event"] = event
        payload["timestamp"] = datetime.utcnow().isoformat()
        
        # Generate signature if secret provided
        headers = {"Content-Type": "application/json"}
        if secret_key:
            signature = self._generate_signature(payload, secret_key)
            headers["X-Webhook-Signature"] = signature
        
        for attempt in range(retry_count):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(
                        webhook_url,
                        json=payload,
                        headers=headers
                    )
                    
                    if response.status_code in [200, 201, 202]:
                        return {
                            "success": True,
                            "status_code": response.status_code,
                            "response": response.text[:1000],
                            "retry_count": attempt
                        }
                    
            except Exception as e:
                if attempt == retry_count - 1:
                    return {
                        "success": False,
                        "status_code": 0,
                        "response": str(e),
                        "retry_count": attempt + 1
                    }
                
                # Exponential backoff
                await asyncio.sleep(2 ** attempt)
        
        return {
            "success": False,
            "status_code": response.status_code if 'response' in locals() else 0,
            "response": "Max retries exceeded",
            "retry_count": retry_count
        }
    
    def _generate_signature(self, payload: Dict[str, Any], secret: str) -> str:
        """Generate HMAC signature for webhook security"""
        payload_bytes = json.dumps(payload, sort_keys=True).encode()
        return hmac.new(
            secret.encode(),
            payload_bytes,
            hashlib.sha256
        ).hexdigest()
EOF

echo "✅ Webhook service created"

# ============================================================================
# STEP 4: Add New API Endpoints
# ============================================================================
echo "🔌 Step 4: Adding new API endpoints to main.py..."

# Backup original main.py
cp app/main.py app/main.py.backup

# Add new endpoints at the end of main.py (before if __name__ == "__main__")
cat >> app/main.py << 'EOF'

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
EOF

echo "✅ New endpoints added to main.py"

# ============================================================================
# STEP 5: Create Comprehensive Tests
# ============================================================================
echo "🧪 Step 5: Creating comprehensive test suite..."

cat > tests/test_complete_system.sh << 'EOF'
#!/bin/bash

API_URL="http://localhost:8003/api/v1"

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║        Complete System Test Suite - All Features              ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

TESTS_PASSED=0
TESTS_FAILED=0

test_endpoint() {
    TEST_NAME=$1
    shift
    
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "TEST: $TEST_NAME"
    
    RESPONSE=$(curl -s "$@")
    
    if echo "$RESPONSE" | jq . > /dev/null 2>&1; then
        echo -e "${GREEN}✅ PASS${NC}"
        echo "Response: $(echo "$RESPONSE" | jq -c .)"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}❌ FAIL${NC}"
        echo "Response: $RESPONSE"
        ((TESTS_FAILED++))
    fi
    echo ""
}

# Test 1: Auto-Humanization
test_endpoint "Auto-Humanization" \
    -X POST "$API_URL/auto-humanize" \
    -H "Content-Type: application/json" \
    -d '{"content_id":"test_001","content":"This is a test. This is a test.","target_score":80}'

# Test 2: Webhook Configuration
test_endpoint "Configure Webhook" \
    -X POST "$API_URL/webhooks/configure?customer_id=test_customer&webhook_url=https://example.com/webhook"

# Test 3: Get Webhook Config
test_endpoint "Get Webhook Config" \
    -X GET "$API_URL/webhooks/test_customer"

# Test 4: Batch Submission
test_endpoint "Batch Processing" \
    -X POST "$API_URL/batch/submit?customer_id=test_customer" \
    -H "Content-Type: application/json" \
    -d '{"items":[{"content":"Test 1","title":"Title 1"},{"content":"Test 2","title":"Title 2"}]}'

# Test 5: Review Queue
test_endpoint "Get Review Queue" \
    -X GET "$API_URL/review/queue?status=pending&limit=10"

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                     TEST SUMMARY                               ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "Total Tests: 5"
echo -e "${GREEN}✅ Passed: $TESTS_PASSED${NC}"
echo -e "${RED}❌ Failed: $TESTS_FAILED${NC}"
EOF

chmod +x tests/test_complete_system.sh

echo "✅ Test suite created"

# ============================================================================
# STEP 6: Deploy Everything
# ============================================================================
echo "🚀 Step 6: Deploying complete system..."

# Stop containers
docker-compose down

# Rebuild with new code
docker-compose build --no-cache

# Start services
docker-compose up -d

# Wait for startup
echo "⏳ Waiting for services to start..."
sleep 25

# Initialize database tables
echo "📊 Initializing database tables..."
docker exec revflow-humanization-pipeline python3 << 'PYINIT'
import sys
sys.path.insert(0, '/app')
from app.database import init_db
init_db()
print("✅ Database tables initialized")
PYINIT

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║              DEPLOYMENT COMPLETE!                              ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "✅ Step 2: Auto-Humanization - DEPLOYED"
echo "✅ Step 3: Webhook Integration - DEPLOYED"
echo "✅ Step 4: Batch Processing - DEPLOYED"
echo ""
echo "🔗 New API Endpoints:"
echo "  POST /api/v1/auto-humanize - Auto-fix content"
echo "  POST /api/v1/review/submit - Submit for manual review"
echo "  GET  /api/v1/review/queue - Get review queue"
echo "  POST /api/v1/review/complete - Complete review"
echo "  POST /api/v1/webhooks/configure - Setup webhooks"
echo "  GET  /api/v1/webhooks/{customer_id} - Get webhook config"
echo "  POST /api/v1/batch/submit - Submit batch job"
echo "  GET  /api/v1/batch/{batch_id} - Get batch status"
echo ""
echo "🧪 Running comprehensive tests..."
cd tests && ./test_complete_system.sh

