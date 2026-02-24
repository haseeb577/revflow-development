"""Pydantic Models for Humanization Pipeline"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
import uuid

class ContentStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_REVIEW = "needs_review"
    IN_PROGRESS = "in_progress"

class ValidationTier(int, Enum):
    TIER_1 = 1
    TIER_2 = 2
    TIER_3 = 3

class ContentValidationRequest(BaseModel):
    content_id: Optional[str] = Field(None, description="Optional unique content identifier")
    title: Optional[str] = Field(None, description="Content title")
    content: str = Field(..., description="Content to validate")
    target_score: Optional[float] = Field(70.0, ge=0, le=100)

    def get_content_id(self) -> str:
        if self.content_id is None:
            return f"temp_{uuid.uuid4().hex[:12]}"
        return self.content_id

class ContentValidationResponse(BaseModel):
    content_id: str
    qa_score: float
    voice_consistency_score: Optional[float] = None
    ymyl_verification_score: Optional[float] = None
    ai_probability: Optional[float] = None
    tier1_issues: List[Dict[str, Any]] = []
    tier2_issues: List[Dict[str, Any]] = []
    tier3_issues: List[Dict[str, Any]] = []
    requires_manual_review: bool
    status: str

class VoiceCheckRequest(BaseModel):
    content: str
    reference_voice: Optional[str] = None

class VoiceCheckResponse(BaseModel):
    score: float = Field(..., ge=0, le=100)
    violations: List[Dict[str, Any]] = []
    is_consistent: bool
    details: Optional[Dict[str, Any]] = None

class YMYLCheckRequest(BaseModel):
    content: str
    content_type: str = "general"

class YMYLCheckResponse(BaseModel):
    score: float
    facts_found: List[Dict[str, Any]] = []
    failures: List[str] = []

class AutoHumanizationRequest(BaseModel):
    content_id: str
    content: str
    target_score: float = 70.0

class AutoHumanizationResult(BaseModel):
    content_id: str
    original_score: float
    final_score: float
    changes_made: List[str] = []

class ManualReviewRequest(BaseModel):
    content_id: str
    action: str
    notes: Optional[str] = None

class ManualReviewResponse(BaseModel):
    content_id: str
    status: str
    message: str

class HumanizerValidationResult(BaseModel):
    tier1_issues: List[Dict[str, Any]] = []
    tier2_issues: List[Dict[str, Any]] = []
    tier3_issues: List[Dict[str, Any]] = []
    eeat_score: float = 0.0
    geo_score: float = 0.0
    structural_score: float = 0.0
    final_score: float = 0.0
    status: str = "pending"
    can_auto_fix: bool = False
    needs_manual_review: bool = False

class AIDetectionResult(BaseModel):
    ai_probability: float
    confidence: float
    transformer_score: float = 0.0
    perplexity_score: float = 0.0
    burstiness_score: float = 0.0
    pattern_score: float = 0.0
    statistical_score: float = 0.0
    verdict: str = "UNKNOWN"
    model_used: str = "unknown"

class QAValidationResult(BaseModel):
    score: float = 0.0
    passed: bool = False
    issues: List[str] = []
