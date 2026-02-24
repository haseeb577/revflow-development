#!/usr/bin/env python3
"""
Guru Intelligence - Unified Knowledge Layer API Routes
FastAPI endpoints for Multi-Tiered Assessment, Prompt Library, and Scoring Frameworks

Routes:
    /knowledge/assess - Multi-Tiered content assessment
    /knowledge/rules - Query rules by filters
    /knowledge/stats - System statistics
    /prompts/* - Prompt library endpoints
    /scoring/* - Scoring framework endpoints
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import psycopg2
from datetime import datetime
import os

# Import the Multi-Tiered Assessor
from multi_tiered_assessor import MultiTieredAssessor

# Router setup
knowledge_router = APIRouter(prefix="/knowledge", tags=["knowledge"])
prompts_router = APIRouter(prefix="/prompts", tags=["prompts"])
scoring_router = APIRouter(prefix="/scoring", tags=["scoring"])

# Database configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', '172.23.0.2'),
    'port': int(os.getenv('DB_PORT', 5432)),
    'database': os.getenv('DB_NAME', 'knowledge_graph_db'),
    'user': os.getenv('DB_USER', 'knowledge_admin'),
    'password': os.getenv('DB_PASSWORD', 'ZYsCjjdy2dzIwrKKM4TY7Vc0Z8ryoR1V')
}

# Initialize assessor (will be configured with API key from environment)
CLAUDE_API_KEY = os.getenv('ANTHROPIC_API_KEY', '')
assessor = MultiTieredAssessor(claude_api_key=CLAUDE_API_KEY if CLAUDE_API_KEY else None)

# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class AssessRequest(BaseModel):
    """Request model for /assess endpoint"""
    content: str = Field(..., description="Content to assess")
    page_type: str = Field(default="service", description="Page type (service, location, homepage, etc.)")
    industry: str = Field(default="general", description="Industry (plumbing, hvac, legal, etc.)")
    options: Optional[Dict[str, Any]] = Field(default=None, description="Assessment options")

class RulesQueryRequest(BaseModel):
    """Request model for /rules endpoint"""
    category: Optional[str] = None
    complexity_level: Optional[int] = None
    page_type: Optional[str] = None
    enforcement_level: Optional[str] = None
    limit: int = Field(default=50, le=200)

class PromptRenderRequest(BaseModel):
    """Request model for /prompts/render"""
    prompt_id: str
    variables: Dict[str, str]

class ScoringRequest(BaseModel):
    """Request model for /scoring/score"""
    framework_id: str
    content: str
    context: Optional[Dict[str, str]] = None

# ============================================================================
# KNOWLEDGE ENDPOINTS
# ============================================================================

@knowledge_router.post("/assess")
async def assess_content(request: AssessRequest):
    """
    Multi-Tiered content assessment
    
    Uses Tier 1/2/3 architecture with short-circuit logic:
    - Tier 1: Regex/deterministic checks (free, ~100ms)
    - Tier 2: NLP/spaCy checks (free, ~500ms)
    - Tier 3: LLM/Claude checks (paid, ~3s, batched)
    
    Returns assessment result with violations, score, and cost tracking.
    """
    try:
        # Run assessment
        result = assessor.assess(
            content=request.content,
            page_type=request.page_type,
            industry=request.industry,
            options=request.options or {}
        )
        
        # Convert to dict for JSON response
        response_data = assessor.to_dict(result)
        
        # Log to validation_history table
        _log_validation(request, response_data)
        
        return response_data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Assessment failed: {str(e)}")

@knowledge_router.post("/rules")
async def query_rules(request: RulesQueryRequest):
    """
    Query rules by filters
    
    Filters:
    - category: Rule category (e.g., "BLUF", "Local Proof")
    - complexity_level: Tier (1, 2, or 3)
    - page_type: Applicable page type
    - enforcement_level: "required", "recommended", or "optional"
    """
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # Build query
        query = """
            SELECT rule_id, rule_name, rule_category, rule_description,
                   complexity_level, validation_type, enforcement_level,
                   priority_score, applies_to_page_types
            FROM extracted_rules
            WHERE is_active = TRUE
        """
        params = []
        
        if request.category:
            query += " AND rule_category ILIKE %s"
            params.append(f"%{request.category}%")
        
        if request.complexity_level:
            query += " AND complexity_level = %s"
            params.append(request.complexity_level)
        
        if request.page_type:
            query += " AND (%s = ANY(applies_to_page_types) OR applies_to_page_types IS NULL)"
            params.append(request.page_type)
        
        if request.enforcement_level:
            query += " AND enforcement_level = %s"
            params.append(request.enforcement_level)
        
        query += " ORDER BY priority_score DESC, rule_id LIMIT %s"
        params.append(request.limit)
        
        cursor.execute(query, params)
        
        columns = [desc[0] for desc in cursor.description]
        rules = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        cursor.close()
        conn.close()
        
        return {
            "count": len(rules),
            "rules": rules
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")

@knowledge_router.get("/stats")
async def get_stats():
    """
    Get system statistics
    
    Returns counts for rules, prompts, frameworks, and recent validation metrics.
    """
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # Rule counts by tier
        cursor.execute("""
            SELECT complexity_level, COUNT(*)
            FROM extracted_rules
            WHERE is_active = TRUE
            GROUP BY complexity_level
            ORDER BY complexity_level
        """)
        tier_counts = dict(cursor.fetchall())
        
        # Rule counts by category
        cursor.execute("""
            SELECT rule_category, COUNT(*)
            FROM extracted_rules
            WHERE is_active = TRUE
            GROUP BY rule_category
            ORDER BY COUNT(*) DESC
            LIMIT 10
        """)
        category_counts = dict(cursor.fetchall())
        
        # Total rules
        cursor.execute("SELECT COUNT(*) FROM extracted_rules WHERE is_active = TRUE")
        total_rules = cursor.fetchone()[0]
        
        # Prompt counts
        cursor.execute("SELECT COUNT(*) FROM prompt_templates WHERE is_active = TRUE")
        total_prompts = cursor.fetchone()[0] if cursor.rowcount > 0 else 0
        
        # Framework counts
        cursor.execute("SELECT COUNT(*) FROM scoring_frameworks WHERE is_active = TRUE")
        total_frameworks = cursor.fetchone()[0] if cursor.rowcount > 0 else 0
        
        # Recent validation stats (last 7 days)
        cursor.execute("""
            SELECT 
                COUNT(*) as total_validations,
                SUM(CASE WHEN passed THEN 1 ELSE 0 END) as passed_count,
                ROUND(AVG(overall_score), 2) as avg_score,
                SUM(api_cost) as total_cost
            FROM validation_history
            WHERE assessed_at >= NOW() - INTERVAL '7 days'
        """)
        validation_stats = cursor.fetchone() if cursor.rowcount > 0 else (0, 0, 0, 0)
        
        cursor.close()
        conn.close()
        
        return {
            "rules": {
                "total": total_rules,
                "by_tier": tier_counts,
                "by_category": category_counts
            },
            "prompts": {
                "total": total_prompts
            },
            "frameworks": {
                "total": total_frameworks
            },
            "recent_validations": {
                "total": validation_stats[0],
                "passed": validation_stats[1],
                "avg_score": float(validation_stats[2]) if validation_stats[2] else 0,
                "total_cost": float(validation_stats[3]) if validation_stats[3] else 0
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Stats query failed: {str(e)}")

# ============================================================================
# PROMPT LIBRARY ENDPOINTS
# ============================================================================

@prompts_router.get("/")
async def list_prompts(
    prompt_type: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = Query(default=50, le=200)
):
    """
    List all prompts with optional filters
    
    Filters:
    - prompt_type: generation, validation, meta, analysis, extraction
    - category: AI-SEO, AI-PPC, QA, etc.
    """
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        query = """
            SELECT prompt_id, name, prompt_type, category, description,
                   preferred_model, usage_count, last_used_at, is_active
            FROM prompt_templates
            WHERE is_active = TRUE
        """
        params = []
        
        if prompt_type:
            query += " AND prompt_type = %s"
            params.append(prompt_type)
        
        if category:
            query += " AND category = %s"
            params.append(category)
        
        query += " ORDER BY prompt_type, category, name LIMIT %s"
        params.append(limit)
        
        cursor.execute(query, params)
        
        columns = [desc[0] for desc in cursor.description]
        prompts = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        cursor.close()
        conn.close()
        
        return {
            "count": len(prompts),
            "prompts": prompts
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prompt query failed: {str(e)}")

@prompts_router.get("/{prompt_id}")
async def get_prompt(prompt_id: str):
    """
    Get specific prompt by ID
    
    Returns complete prompt details including templates, variables, and examples.
    """
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT prompt_id, name, prompt_type, category, description,
                   system_prompt, user_prompt_template,
                   required_variables, optional_variables, variable_descriptions,
                   preferred_model, max_tokens, temperature,
                   applies_to_modules, applies_to_page_types,
                   example_input, example_output, usage_count
            FROM prompt_templates
            WHERE prompt_id = %s AND is_active = TRUE
        """, (prompt_id,))
        
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail=f"Prompt {prompt_id} not found")
        
        columns = [desc[0] for desc in cursor.description]
        prompt = dict(zip(columns, cursor.fetchone()))
        
        cursor.close()
        conn.close()
        
        return prompt
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")

@prompts_router.post("/render")
async def render_prompt(request: PromptRenderRequest):
    """
    Render a prompt template with variables
    
    Takes a prompt_id and variables dict, returns the rendered prompt ready for LLM.
    """
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # Get prompt template
        cursor.execute("""
            SELECT system_prompt, user_prompt_template, required_variables,
                   preferred_model, max_tokens, temperature
            FROM prompt_templates
            WHERE prompt_id = %s AND is_active = TRUE
        """, (request.prompt_id,))
        
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail=f"Prompt {request.prompt_id} not found")
        
        row = cursor.fetchone()
        system_prompt = row[0]
        user_prompt_template = row[1]
        required_variables = row[2] or []
        preferred_model = row[3]
        max_tokens = row[4]
        temperature = row[5]
        
        # Validate required variables
        missing_vars = [v for v in required_variables if v not in request.variables]
        if missing_vars:
            raise HTTPException(status_code=400, detail=f"Missing required variables: {missing_vars}")
        
        # Render templates
        rendered_system = system_prompt
        rendered_user = user_prompt_template
        
        for var_name, var_value in request.variables.items():
            placeholder = "{" + var_name + "}"
            if rendered_system:
                rendered_system = rendered_system.replace(placeholder, var_value)
            rendered_user = rendered_user.replace(placeholder, var_value)
        
        cursor.close()
        conn.close()
        
        return {
            "prompt_id": request.prompt_id,
            "rendered_system_prompt": rendered_system,
            "rendered_user_prompt": rendered_user,
            "model": preferred_model,
            "max_tokens": max_tokens,
            "temperature": float(temperature)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Render failed: {str(e)}")

# ============================================================================
# SCORING FRAMEWORK ENDPOINTS
# ============================================================================

@scoring_router.get("/frameworks")
async def list_frameworks():
    """
    List all scoring frameworks
    
    Returns available frameworks like E-E-A-T, GEO, Tier Scanner, etc.
    """
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT framework_id, name, description, max_score, passing_threshold,
                   components, applies_to_modules, is_active
            FROM scoring_frameworks
            WHERE is_active = TRUE
            ORDER BY name
        """)
        
        columns = [desc[0] for desc in cursor.description]
        frameworks = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        cursor.close()
        conn.close()
        
        return {
            "count": len(frameworks),
            "frameworks": frameworks
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")

@scoring_router.post("/score")
async def score_content(request: ScoringRequest):
    """
    Apply a scoring framework to content
    
    Uses the specified framework to score content and return component breakdowns.
    """
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # Get framework
        cursor.execute("""
            SELECT framework_id, name, max_score, passing_threshold, components,
                   tier1_rules, tier2_rules, tier3_rules
            FROM scoring_frameworks
            WHERE framework_id = %s AND is_active = TRUE
        """, (request.framework_id,))
        
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail=f"Framework {request.framework_id} not found")
        
        framework = dict(zip([desc[0] for desc in cursor.description], cursor.fetchone()))
        
        cursor.close()
        conn.close()
        
        # Run assessment using framework's rules
        # This is a placeholder - full implementation would use the assessor
        # with framework-specific rule filtering
        
        return {
            "framework_id": request.framework_id,
            "overall_score": 85,  # Placeholder
            "passed": True,
            "component_scores": framework['components'],
            "details": {
                "message": "Framework scoring not yet fully implemented"
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scoring failed: {str(e)}")

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _log_validation(request: AssessRequest, response_data: Dict):
    """Log validation to validation_history table"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # Extract key metrics
        tiers_run = response_data.get('tiers_run', [])
        tier_results = response_data.get('tier_results', {})
        
        tier1 = tier_results.get('1', {})
        tier2 = tier_results.get('2', {})
        tier3 = tier_results.get('3', {})
        
        cursor.execute("""
            INSERT INTO validation_history (
                content_id, page_type, industry, module,
                overall_score, passed, tiers_run,
                tier1_checked, tier1_passed,
                tier2_checked, tier2_passed,
                tier3_checked, tier3_passed,
                violations_count, violations,
                api_cost, tokens_used, processing_time_ms
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s
            )
        """, (
            None,  # content_id - could hash content for tracking
            request.page_type,
            request.industry,
            'api',
            response_data['overall_score'],
            response_data['passed'],
            tiers_run,
            tier1.get('rules_checked', 0),
            tier1.get('rules_passed', 0),
            tier2.get('rules_checked', 0),
            tier2.get('rules_passed', 0),
            tier3.get('rules_checked', 0),
            tier3.get('rules_passed', 0),
            len(response_data.get('violations', [])),
            psycopg2.extras.Json(response_data.get('violations', [])),
            response_data.get('api_cost', 0),
            response_data.get('tokens_used', 0),
            response_data.get('total_processing_time_ms', 0)
        ))
        
        conn.commit()
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"⚠️  Failed to log validation: {e}")

# Export routers for FastAPI app
__all__ = ['knowledge_router', 'prompts_router', 'scoring_router']
