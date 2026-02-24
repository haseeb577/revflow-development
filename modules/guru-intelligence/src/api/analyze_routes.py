"""Content analysis API routes"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

class AnalyzeRequest(BaseModel):
    content: str
    domain: str = "seo"
    source_type: str = "manual"
    expert: str = "Unknown"

class AnalyzeResponse(BaseModel):
    rules_found: int
    unique_rules: int
    rules: List[Dict]

@router.post("/analyze", response_model=AnalyzeResponse)
def analyze_content(request: AnalyzeRequest):
    """Extract SEO rules from content using Claude"""
    try:
        import sys
        sys.path.insert(0, '/opt/guru-intelligence/src')
        from analyzers.rule_extractor import extract_rules_from_content_sync
        
        # Call with CORRECT parameter order: content, source_type, expert, domain
        result = extract_rules_from_content_sync(
            content=request.content,
            source_type=request.source_type,
            expert=request.expert,
            domain=request.domain
        )
        
        return AnalyzeResponse(
            rules_found=result.get('rules_found', 0),
            unique_rules=result.get('unique_rules', 0),
            rules=result.get('rules', [])
        )
        
    except Exception as e:
        logger.error(f"Analysis failed: {e}", exc_info=True)
        return AnalyzeResponse(rules_found=0, unique_rules=0, rules=[])
