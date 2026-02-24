from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime

class ValidationRequest(BaseModel):
    content_id: Optional[str] = Field(default=None, description="Optional unique identifier for the content")
    content: str = Field(..., description="The content text to validate")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")
    checks: Optional[Dict[str, bool]] = Field(
        default_factory=lambda: {
            "voice_consistency": False,
            "ymyl_verification": False,
            "ai_detection": False
        },
        description="Which checks to run"
    )

class ValidationResponse(BaseModel):
    content_id: Optional[str] = None
    overall_score: float
    tier_scores: Dict[str, float]
    validation_results: Dict[str, Any]
    issues: List[str]
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class VoiceCheckRequest(BaseModel):
    content: str

class VoiceCheckResponse(BaseModel):
    consistency_score: float
    assessment: str
    issues: List[str]

class YMYLVerificationRequest(BaseModel):
    content: str
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

class YMYLVerificationResponse(BaseModel):
    verified_count: int
    verified_facts: List[Dict[str, Any]]
    issues: List[str]

class HumanizationRequest(BaseModel):
    content_id: str
    content: str
    auto_fix: bool = False

class HumanizationResponse(BaseModel):
    content_id: str
    original_score: float
    humanized_score: float
    humanized_content: Optional[str] = None
    changes_made: List[str]
    success: bool

class QueueItem(BaseModel):
    content_id: str
    title: str
    score: float
    issues: List[str]
    status: str
    created_at: datetime
    updated_at: datetime
