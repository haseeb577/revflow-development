"""
RevAudit™ Anti-Hallucination API
Data Provenance & Integrity Endpoints

Port: 8710
"""

from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime

from audit_service import audit_service, HallucinationDetected


app = FastAPI(
    title="RevAudit™ Anti-Hallucination API",
    description="Data provenance, integrity verification, and hallucination detection",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================
# PYDANTIC MODELS
# ============================================

class APICallLog(BaseModel):
    tool: str = Field(..., description="API tool name (DataForSEO, ChatGPT, etc.)")
    endpoint: str = Field(..., description="Full endpoint URL")
    method: str = Field(default="GET")
    request_payload: Optional[Dict] = None
    response_data: Optional[Any] = None
    response_status: int = Field(default=200)
    called_by_module: Optional[str] = None
    assessment_id: Optional[str] = None
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    duration_ms: Optional[int] = None


class ClaimRegistration(BaseModel):
    claim_text: str = Field(..., description="The claim being made")
    source_audit_id: str = Field(..., description="Audit ID of the source API call")
    source_field: str = Field(..., description="JSON path to the source value")
    source_value: Any = Field(..., description="The actual value from the API")
    claim_type: str = Field(default="metric")
    assessment_id: Optional[str] = None
    report_section: Optional[str] = None


class ContentValidation(BaseModel):
    content: str = Field(..., description="Content to validate")
    assessment_id: Optional[str] = None
    module: Optional[str] = None
    strict: bool = Field(default=True, description="Raise exception on BLOCKED issues")


class VerificationGate(BaseModel):
    assessment_id: str
    data_type: str = Field(..., description="Type of data (api_responses, scores, report)")
    data_snapshot: Dict = Field(..., description="Snapshot of data for user to verify")


class VerificationApproval(BaseModel):
    verification_id: str
    user_id: str
    notes: Optional[str] = None


# ============================================
# HEALTH & STATUS
# ============================================

@app.get("/health")
async def health_check():
    """Check RevAudit service health"""
    return audit_service.health_check()


@app.get("/")
async def root():
    """RevAudit API root"""
    return {
        "service": "RevAudit™ Anti-Hallucination Framework",
        "version": "1.0.0",
        "status": "operational",
        "features": [
            "API Call Logging",
            "Claim Source Attribution",
            "Hallucination Detection",
            "User Verification Gates",
            "Audit Trail Generation"
        ]
    }


# ============================================
# API CALL LOGGING
# ============================================

@app.post("/api/audit/log-call")
async def log_api_call(log: APICallLog):
    """
    Log an API call with full audit trail.

    Every external API call should be logged here for provenance tracking.
    """
    result = audit_service.log_api_call(
        tool=log.tool,
        endpoint=log.endpoint,
        method=log.method,
        request_payload=log.request_payload,
        response_data=log.response_data,
        response_status=log.response_status,
        called_by_module=log.called_by_module,
        assessment_id=log.assessment_id,
        session_id=log.session_id,
        user_id=log.user_id,
        duration_ms=log.duration_ms
    )

    if not result.get('logged'):
        raise HTTPException(status_code=500, detail=result.get('error', 'Failed to log'))

    return result


@app.get("/api/audit/raw-response/{audit_id}")
async def get_raw_response(audit_id: str):
    """
    Retrieve the raw API response for an audit record.

    This proves what the actual API returned.
    """
    response = audit_service.get_raw_response(audit_id)
    if not response:
        raise HTTPException(status_code=404, detail="Raw response not found")
    return response


# ============================================
# CLAIM REGISTRATION
# ============================================

@app.post("/api/audit/register-claim")
async def register_claim(claim: ClaimRegistration):
    """
    Register a claim with its source attribution.

    Every claim in a report must be registered to prove it has a data source.
    """
    result = audit_service.register_claim(
        claim_text=claim.claim_text,
        source_audit_id=claim.source_audit_id,
        source_field=claim.source_field,
        source_value=claim.source_value,
        claim_type=claim.claim_type,
        assessment_id=claim.assessment_id,
        report_section=claim.report_section
    )

    if not result.get('verified'):
        raise HTTPException(status_code=400, detail=result.get('error', 'Failed to register'))

    return result


# ============================================
# HALLUCINATION DETECTION
# ============================================

@app.post("/api/audit/validate-content")
async def validate_content(validation: ContentValidation):
    """
    Validate content for potential hallucinations.

    Checks for:
    - Forbidden phrases (vague claims without sources)
    - Missing citations on numeric claims
    - Unverifiable statements
    """
    try:
        result = audit_service.validate_report_content(
            report_text=validation.content,
            assessment_id=validation.assessment_id,
            strict=validation.strict
        )
        return result
    except HallucinationDetected as e:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "HALLUCINATION_DETECTED",
                "severity": e.severity.value,
                "reason": e.reason,
                "content": e.content[:200]
            }
        )


@app.post("/api/audit/check-text")
async def check_text(content: str = Body(..., embed=True)):
    """
    Quick check for hallucination indicators in text.

    Non-blocking - returns findings but doesn't raise exceptions.
    """
    is_clean, detections = audit_service.check_for_hallucination(content)
    return {
        "is_clean": is_clean,
        "can_proceed": is_clean,
        "detection_count": len(detections),
        "detections": detections
    }


# ============================================
# VERIFICATION GATES
# ============================================

@app.post("/api/audit/verification/create")
async def create_verification_gate(gate: VerificationGate):
    """
    Create a verification gate that user must approve.

    Users must verify raw data before report generation.
    """
    verification_id = audit_service.create_verification_gate(
        assessment_id=gate.assessment_id,
        data_type=gate.data_type,
        data_snapshot=gate.data_snapshot
    )

    if not verification_id:
        raise HTTPException(status_code=500, detail="Failed to create verification gate")

    return {
        "verification_id": verification_id,
        "status": "pending",
        "message": "User approval required before proceeding"
    }


@app.post("/api/audit/verification/approve")
async def approve_verification(approval: VerificationApproval):
    """
    User approves verification gate, allowing report generation.
    """
    success = audit_service.approve_verification(
        verification_id=approval.verification_id,
        user_id=approval.user_id,
        notes=approval.notes
    )

    if not success:
        raise HTTPException(status_code=400, detail="Failed to approve verification")

    return {
        "verification_id": approval.verification_id,
        "status": "approved",
        "approved_by": approval.user_id,
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/api/audit/verification/status/{assessment_id}")
async def get_verification_status(assessment_id: str):
    """
    Check verification status for an assessment.

    Reports can only be generated when all verifications are approved.
    """
    return audit_service.check_verification_status(assessment_id)


# ============================================
# AUDIT TRAIL
# ============================================

@app.get("/api/audit/trail/{assessment_id}")
async def get_audit_trail(assessment_id: str):
    """
    Get complete audit trail for an assessment.

    Shows all API calls, registered claims, and detections.
    """
    trail = audit_service.get_audit_trail(assessment_id)
    if 'error' in trail:
        raise HTTPException(status_code=500, detail=trail['error'])
    return trail


# ============================================
# REPORT GENERATION GATE
# ============================================

@app.get("/api/audit/can-generate-report/{assessment_id}")
async def can_generate_report(assessment_id: str):
    """
    Check if report generation is allowed for an assessment.

    Requirements:
    1. All verifications approved
    2. No unresolved BLOCKED detections
    """
    verification_status = audit_service.check_verification_status(assessment_id)
    trail = audit_service.get_audit_trail(assessment_id)

    unresolved_blocked = len([
        d for d in trail.get('detections', [])
        if d.get('severity') == 'BLOCKED' and not d.get('resolved')
    ])

    can_generate = (
        verification_status.get('can_generate_report', False) and
        unresolved_blocked == 0
    )

    return {
        "assessment_id": assessment_id,
        "can_generate": can_generate,
        "verification_status": verification_status,
        "unresolved_blocked_issues": unresolved_blocked,
        "blockers": [] if can_generate else [
            "Pending verifications" if not verification_status.get('can_generate_report') else None,
            f"{unresolved_blocked} blocked issues" if unresolved_blocked > 0 else None
        ]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8710)
