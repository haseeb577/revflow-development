"""
RevPublish v2.0 API Routes
Adds AI extraction, conflict scanning, Google OAuth, and enhanced deployment
"""

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from database import get_db_connection
from extractors.ai_extraction import get_hybrid_extractor, ExtractionCost
from scanners.conflict_scanner import scan_for_conflicts, ConflictReport
from integrations.google_oauth import google_oauth
from converters.elementor_mapper import elementor_mapper
from converters.template_engine import template_engine
from deployers.wordpress_client import WordPressClientManager

router = APIRouter()
wp_manager = WordPressClientManager()


# ===== Request Models =====

class AIExtractionRequest(BaseModel):
    """Request for AI-powered field extraction"""
    content: str = Field(..., description="Raw content to extract from")
    page_type_id: str = Field(..., description="Target page type")
    use_ai: bool = Field(True, description="Enable AI extraction")
    max_cost: float = Field(0.05, description="Maximum cost for AI extraction")


class ConflictScanRequest(BaseModel):
    """Request for conflict scanning"""
    title: str = Field(..., description="Proposed content title")
    content: str = Field("", description="Proposed content body")
    slug: Optional[str] = Field(None, description="Proposed URL slug")
    target_sites: Optional[List[str]] = Field(None, description="Sites to scan (default: all)")


class SmartDeployRequest(BaseModel):
    """Smart deployment with conflict check and AI extraction"""
    content: str = Field(..., description="Raw content to deploy")
    content_type: str = Field("text", description="Content type: text, html, json, markdown")
    page_type_id: str = Field(..., description="Page type to generate")
    target_sites: List[str] = Field(..., description="Site IDs to deploy to")
    status: str = Field("draft", description="Post status: draft or publish")
    use_ai: bool = Field(True, description="Use AI for field extraction")
    skip_conflict_check: bool = Field(False, description="Skip conflict scanning")
    force_deploy: bool = Field(False, description="Deploy despite conflicts")
    color_scheme: str = Field("default", description="Elementor color scheme")


class GoogleDocImportRequest(BaseModel):
    """Import from Google Docs"""
    document_id: str
    page_type_id: str
    use_ai: bool = True


class GoogleSheetImportRequest(BaseModel):
    """Import from Google Sheets"""
    spreadsheet_id: str
    sheet_name: Optional[str] = None
    page_type_id: str
    target_sites: List[str]
    use_ai: bool = True


# ===== AI Extraction Endpoints =====

@router.post("/extract/ai")
async def ai_extract_fields(request: AIExtractionRequest):
    """
    Extract structured fields from content using AI.

    Uses Claude-3-Haiku with cost controls.
    Returns estimated cost before extraction and actual cost after.
    """
    try:
        extractor = get_hybrid_extractor()

        # Get cost estimate first
        if extractor.ai_extractor:
            estimated = extractor.ai_extractor.estimate_cost(
                request.content, request.page_type_id
            )
            if estimated.estimated_cost_usd > request.max_cost:
                return {
                    "success": False,
                    "error": "Cost limit exceeded",
                    "estimated_cost": estimated.estimated_cost_usd,
                    "max_allowed": request.max_cost,
                    "suggestion": "Reduce content size or increase max_cost"
                }

        # Extract fields
        extracted, ai_cost, warnings = extractor.extract(
            request.content,
            request.page_type_id,
            use_ai=request.use_ai,
            ai_max_cost=request.max_cost
        )

        return {
            "success": True,
            "extracted_fields": extracted,
            "ai_used": ai_cost is not None,
            "cost": {
                "input_tokens": ai_cost.input_tokens if ai_cost else 0,
                "output_tokens": ai_cost.output_tokens if ai_cost else 0,
                "usd": ai_cost.estimated_cost_usd if ai_cost else 0
            } if ai_cost else None,
            "warnings": warnings
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/extract/cost-estimate")
async def estimate_extraction_cost(
    content_length: int = Query(..., description="Length of content in characters"),
    page_type_id: str = Query(..., description="Target page type")
):
    """
    Estimate AI extraction cost before running.

    Provides cost estimate based on content length and target fields.
    """
    try:
        extractor = get_hybrid_extractor()
        if not extractor.ai_extractor:
            return {
                "ai_available": False,
                "message": "AI extraction not configured (missing ANTHROPIC_API_KEY)"
            }

        # Create dummy content for estimation
        dummy_content = "x" * content_length
        estimated = extractor.ai_extractor.estimate_cost(dummy_content, page_type_id)

        return {
            "ai_available": True,
            "estimated_cost_usd": estimated.estimated_cost_usd,
            "estimated_input_tokens": estimated.input_tokens,
            "estimated_output_tokens": estimated.output_tokens,
            "model": estimated.model
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/extract/daily-usage")
async def get_daily_ai_usage():
    """Get AI extraction usage for today"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                COUNT(*) as extractions,
                COALESCE(SUM(input_tokens), 0) as total_input_tokens,
                COALESCE(SUM(output_tokens), 0) as total_output_tokens,
                COALESCE(SUM(cost_usd), 0) as total_cost_usd
            FROM revpublish_ai_usage
            WHERE DATE(created_at) = CURRENT_DATE
        """)
        row = cursor.fetchone()
        return dict(row) if row else {
            "extractions": 0,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "total_cost_usd": 0
        }


# ===== Conflict Scanning Endpoints =====

@router.post("/scan/conflicts")
async def scan_content_conflicts(request: ConflictScanRequest):
    """
    Scan all WordPress sites for content conflicts.

    Checks for:
    - Exact title matches
    - Similar titles (>70% match)
    - URL slug conflicts
    - Content overlap (>60% match)

    Returns detailed conflict report with blocking status.
    """
    try:
        report = scan_for_conflicts(
            proposed_title=request.title,
            proposed_content=request.content,
            proposed_slug=request.slug,
            target_sites=request.target_sites
        )

        return {
            "success": True,
            **report.to_dict()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===== Google OAuth Endpoints =====

@router.get("/google/status")
async def google_auth_status():
    """Check Google OAuth status"""
    return {
        "api_available": google_oauth.is_available,
        "configured": google_oauth.is_configured,
        "authenticated": google_oauth.is_authenticated
    }


@router.get("/google/auth")
async def start_google_auth():
    """Start Google OAuth flow. Returns URL for user to visit."""
    try:
        auth_url = google_oauth.get_auth_url()
        return {
            "success": True,
            "auth_url": auth_url,
            "instructions": "Visit the auth_url to grant access, then you'll be redirected back"
        }
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/google/callback")
async def google_auth_callback(code: str, state: str):
    """OAuth callback handler"""
    try:
        result = google_oauth.complete_auth(code, state)
        return {
            "success": True,
            "message": f"Successfully connected Google account: {result['email']}",
            **result
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/google/revoke")
async def revoke_google_auth():
    """Revoke Google OAuth tokens"""
    success = google_oauth.revoke_auth()
    return {
        "success": success,
        "message": "Google access revoked" if success else "No tokens to revoke"
    }


@router.get("/google/docs")
async def list_google_docs(limit: int = 20):
    """List recent Google Docs"""
    try:
        docs = google_oauth.list_recent_docs(limit)
        return {"success": True, "documents": docs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/google/sheets")
async def list_google_sheets(limit: int = 20):
    """List recent Google Sheets"""
    try:
        sheets = google_oauth.list_recent_sheets(limit)
        return {"success": True, "spreadsheets": sheets}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/google/import-doc")
async def import_google_doc(request: GoogleDocImportRequest):
    """
    Import content from Google Docs.

    Fetches document, extracts content, and optionally uses AI for field mapping.
    """
    try:
        # Fetch document
        doc = google_oauth.get_document(request.document_id)

        # Extract fields
        extractor = get_hybrid_extractor()
        extracted, ai_cost, warnings = extractor.extract(
            doc['content'],
            request.page_type_id,
            use_ai=request.use_ai
        )

        return {
            "success": True,
            "document_title": doc['title'],
            "extracted_fields": extracted,
            "ai_cost": ai_cost.estimated_cost_usd if ai_cost else 0,
            "warnings": warnings
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/google/import-sheet")
async def import_google_sheet(request: GoogleSheetImportRequest):
    """
    Import content from Google Sheets.

    Each row becomes a separate page deployment.
    """
    try:
        # Fetch spreadsheet
        sheet = google_oauth.get_spreadsheet(
            request.spreadsheet_id,
            request.sheet_name
        )

        # Process each row
        results = []
        extractor = get_hybrid_extractor()

        for row in sheet['rows']:
            # Convert row to content string for extraction
            row_content = '\n'.join(f"{k}: {v}" for k, v in row.items() if v)

            extracted, ai_cost, warnings = extractor.extract(
                row_content,
                request.page_type_id,
                use_ai=request.use_ai
            )

            results.append({
                "row_data": row,
                "extracted_fields": extracted,
                "warnings": warnings
            })

        return {
            "success": True,
            "sheet_title": sheet['title'],
            "rows_processed": len(results),
            "results": results
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===== Smart Deployment =====

@router.post("/deploy/smart")
async def smart_deploy(request: SmartDeployRequest):
    """
    Smart deployment with full pipeline:

    1. AI extraction (optional)
    2. Conflict scanning (optional)
    3. Elementor mapping
    4. Multi-site deployment

    Returns comprehensive results including conflicts and deployment status.
    """
    results = {
        "extraction": None,
        "conflicts": None,
        "elementor": None,
        "deployment": None,
        "success": False
    }

    try:
        # Step 1: Extract fields
        extractor = get_hybrid_extractor()
        extracted, ai_cost, warnings = extractor.extract(
            request.content,
            request.page_type_id,
            use_ai=request.use_ai
        )

        results["extraction"] = {
            "fields": extracted,
            "ai_cost": ai_cost.estimated_cost_usd if ai_cost else 0,
            "warnings": warnings
        }

        # Get title for conflict check
        title = extracted.get('title') or extracted.get('hero_headline') or 'Untitled'

        # Step 2: Conflict scan
        if not request.skip_conflict_check:
            conflict_report = scan_for_conflicts(
                proposed_title=title,
                proposed_content=request.content,
                target_sites=request.target_sites
            )

            results["conflicts"] = conflict_report.to_dict()

            # Block if conflicts found and force not enabled
            if conflict_report.has_blocking_conflicts and not request.force_deploy:
                results["success"] = False
                results["blocked"] = True
                results["message"] = "Deployment blocked due to conflicts. Set force_deploy=true to override."
                return results

        # Step 3: Generate Elementor JSON
        elementor_data = elementor_mapper.map_to_elementor(
            request.page_type_id,
            extracted,
            request.color_scheme
        )

        results["elementor"] = {
            "sections_generated": len(elementor_data.get('elements', [])),
            "title": elementor_data.get('title')
        }

        # Step 4: Generate page content
        page_content = template_engine.generate_page_content(
            request.page_type_id,
            extracted
        )

        # Step 5: Deploy to sites
        deployment_results = []
        for site_id in request.target_sites:
            try:
                client = wp_manager.get_client(site_id)
                post_data = {
                    'title': page_content['title'],
                    'content_html': page_content['content'],
                    'excerpt': page_content.get('excerpt', ''),
                    'status': request.status
                }

                result = client.deploy_post(post_data, elementor_data)
                deployment_results.append({
                    'site_id': site_id,
                    **result
                })

            except Exception as e:
                deployment_results.append({
                    'site_id': site_id,
                    'success': False,
                    'error': str(e)
                })

        successful = sum(1 for r in deployment_results if r.get('success'))
        results["deployment"] = {
            "total_sites": len(request.target_sites),
            "successful": successful,
            "failed": len(request.target_sites) - successful,
            "results": deployment_results
        }

        results["success"] = successful > 0
        return results

    except Exception as e:
        results["error"] = str(e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/preview/elementor")
async def preview_elementor(
    page_type_id: str,
    field_data: Dict[str, Any],
    color_scheme: str = "default"
):
    """
    Preview Elementor JSON structure without deploying.

    Useful for testing field mapping and layout generation.
    """
    try:
        elementor_data = elementor_mapper.map_to_elementor(
            page_type_id,
            field_data,
            color_scheme
        )

        return {
            "success": True,
            "elementor_json": elementor_data,
            "sections_count": len(elementor_data.get('elements', [])),
            "title": elementor_data.get('title')
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===== Database Migration =====

@router.post("/admin/migrate-v2")
async def run_v2_migration():
    """Run database migrations for v2.0 features"""
    migrations = []

    with get_db_connection() as conn:
        cursor = conn.cursor()

        # AI Usage tracking table
        try:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS revpublish_ai_usage (
                    id SERIAL PRIMARY KEY,
                    page_type_id VARCHAR(50),
                    model VARCHAR(100),
                    input_tokens INTEGER,
                    output_tokens INTEGER,
                    cost_usd DECIMAL(10, 6),
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            migrations.append("Created revpublish_ai_usage table")
        except Exception as e:
            migrations.append(f"AI usage table: {str(e)}")

        # OAuth tokens table
        try:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS revpublish_oauth_tokens (
                    id SERIAL PRIMARY KEY,
                    provider VARCHAR(50) UNIQUE NOT NULL,
                    token_data BYTEA,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """)
            migrations.append("Created revpublish_oauth_tokens table")
        except Exception as e:
            migrations.append(f"OAuth tokens table: {str(e)}")

        # OAuth states table (for CSRF)
        try:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS revpublish_oauth_states (
                    id SERIAL PRIMARY KEY,
                    state VARCHAR(255) UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT NOW(),
                    expires_at TIMESTAMP NOT NULL
                )
            """)
            migrations.append("Created revpublish_oauth_states table")
        except Exception as e:
            migrations.append(f"OAuth states table: {str(e)}")

        # Deployment history table
        try:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS revpublish_deployment_history (
                    id SERIAL PRIMARY KEY,
                    site_id VARCHAR(100),
                    page_type_id VARCHAR(50),
                    post_id INTEGER,
                    post_url TEXT,
                    title TEXT,
                    status VARCHAR(20),
                    ai_cost_usd DECIMAL(10, 6),
                    conflicts_found INTEGER DEFAULT 0,
                    deployed_at TIMESTAMP DEFAULT NOW()
                )
            """)
            migrations.append("Created revpublish_deployment_history table")
        except Exception as e:
            migrations.append(f"Deployment history table: {str(e)}")

        conn.commit()

    return {
        "success": True,
        "migrations": migrations
    }
