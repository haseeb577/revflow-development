"""
Enhanced Deployment Routes with PostgreSQL Storage
RevPublish Module 9 - RevFlow OS
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from converters.elementor_converter import ElementorConverter
from converters.template_engine import template_engine
from deployers.wordpress_client import WordPressClientManager

router = APIRouter()
converter = ElementorConverter()
wp_manager = WordPressClientManager()


class StructuredDeploymentRequest(BaseModel):
    """Deploy content using page type and structured field data"""
    page_type_id: str
    data: Dict
    target_sites: List[str]
    status: str = "draft"
    template_name: Optional[str] = None


class DeploymentRequest(BaseModel):
    content_html: str
    title: str
    excerpt: Optional[str] = ""
    target_sites: List[str]
    status: str = "draft"


class SiteConfiguration(BaseModel):
    site_id: str
    site_url: str
    username: str
    app_password: str


class BulkCredentialsRequest(BaseModel):
    """For setting credentials on multiple sites at once"""
    username: str
    app_password: str
    site_ids: Optional[List[str]] = None  # If None, apply to all pending sites


# ============ SITE MANAGEMENT ============

@router.get("/sites")
async def list_sites(status: Optional[str] = None):
    """List all WordPress sites from database"""
    try:
        sites = wp_manager.list_sites(status=status)
        return {
            "success": True,
            "count": len(sites),
            "sites": sites
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sites/configured")
async def list_configured_sites():
    """List only configured sites (with credentials)"""
    try:
        sites = wp_manager.get_configured_sites()
        return {
            "success": True,
            "count": len(sites),
            "sites": sites
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/configure-site")
async def configure_site(config: SiteConfiguration):
    """Configure a WordPress site with credentials"""
    try:
        result = wp_manager.add_site(
            config.site_id,
            config.site_url,
            config.username,
            config.app_password
        )

        return {
            "success": True,
            "site_id": config.site_id,
            **result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/configure-bulk")
async def configure_bulk_credentials(request: BulkCredentialsRequest):
    """Apply same credentials to multiple sites (for shared WordPress admin)"""
    try:
        from database import get_db_connection

        with get_db_connection() as conn:
            cursor = conn.cursor()

            if request.site_ids:
                # Update specific sites
                cursor.execute("""
                    UPDATE wordpress_sites
                    SET wp_username = %s, app_password = %s, status = 'configured', updated_at = NOW()
                    WHERE site_id = ANY(%s)
                    RETURNING site_id
                """, (request.username, request.app_password, request.site_ids))
            else:
                # Update all pending sites
                cursor.execute("""
                    UPDATE wordpress_sites
                    SET wp_username = %s, app_password = %s, status = 'configured', updated_at = NOW()
                    WHERE status = 'pending'
                    RETURNING site_id
                """, (request.username, request.app_password))

            updated = [row['site_id'] for row in cursor.fetchall()]

        return {
            "success": True,
            "updated_count": len(updated),
            "updated_sites": updated
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/sites/{site_id}")
async def delete_site(site_id: str):
    """Remove a site from the database"""
    try:
        deleted = wp_manager.delete_site(site_id)
        return {
            "success": deleted,
            "site_id": site_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test-connections")
async def test_all_connections():
    """Test connections to all configured sites"""
    try:
        results = wp_manager.test_all_connections()
        successful = sum(1 for r in results if r.get('success'))
        return {
            "success": True,
            "total": len(results),
            "successful": successful,
            "failed": len(results) - successful,
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/test-connection/{site_id}")
async def test_single_connection(site_id: str):
    """Test connection to a single site"""
    try:
        client = wp_manager.get_client(site_id)
        result = client.test_connection()
        return {
            "success": True,
            "site_id": site_id,
            "connection": result
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ DEPLOYMENT ============

@router.post("/deploy")
async def deploy_content(request: DeploymentRequest):
    """Deploy content to WordPress sites"""
    try:
        # Convert HTML to Elementor
        elementor_json = converter.convert_html_to_elementor(request.content_html)

        results = []
        for site_id in request.target_sites:
            try:
                client = wp_manager.get_client(site_id)
                post_data = {
                    'title': request.title,
                    'content_html': request.content_html,
                    'excerpt': request.excerpt,
                    'status': request.status
                }
                result = client.deploy_post(post_data, elementor_json)
                results.append({
                    'site_id': site_id,
                    **result
                })
            except Exception as e:
                results.append({
                    'site_id': site_id,
                    'success': False,
                    'error': str(e)
                })

        successful = sum(1 for r in results if r.get('success'))
        return {
            "success": successful > 0,
            "total_sites": len(request.target_sites),
            "successful": successful,
            "failed": len(request.target_sites) - successful,
            "deployments": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/deploy-all")
async def deploy_to_all_configured_sites(request: DeploymentRequest):
    """Deploy content to ALL configured sites"""
    try:
        sites = wp_manager.get_configured_sites()
        if not sites:
            return {"success": False, "error": "No configured sites found"}

        # Use all configured site IDs
        request.target_sites = [s['site_id'] for s in sites]
        return await deploy_content(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============ PAGE TYPES & TEMPLATES ============

@router.get("/page-types")
async def list_page_types():
    """Get all available page types"""
    try:
        page_types = template_engine.get_page_types()
        return {
            "success": True,
            "count": len(page_types),
            "page_types": page_types
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/page-types/{type_id}/fields")
async def get_page_type_fields(type_id: str):
    """Get fields for a specific page type"""
    try:
        fields = template_engine.get_page_fields(type_id)
        if not fields:
            raise HTTPException(status_code=404, detail=f"Page type '{type_id}' not found or has no fields")
        return {
            "success": True,
            "page_type_id": type_id,
            "count": len(fields),
            "fields": fields
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/deploy-structured")
async def deploy_structured_content(request: StructuredDeploymentRequest):
    """
    Deploy content using page type templates and structured data.

    This generates Elementor-compatible content from a page type template
    and field data, then deploys to the specified WordPress sites.
    """
    try:
        # Generate content from template + data
        page_content = template_engine.generate_page_content(
            request.page_type_id,
            request.data
        )

        results = []
        for site_id in request.target_sites:
            try:
                client = wp_manager.get_client(site_id)
                post_data = {
                    'title': page_content['title'],
                    'content_html': page_content['content'],
                    'excerpt': page_content.get('excerpt', ''),
                    'status': request.status
                }
                # Deploy with Elementor data
                result = client.deploy_post(post_data, page_content['elementor_data'])
                results.append({
                    'site_id': site_id,
                    **result
                })
            except Exception as e:
                results.append({
                    'site_id': site_id,
                    'success': False,
                    'error': str(e)
                })

        successful = sum(1 for r in results if r.get('success'))
        return {
            "success": successful > 0,
            "page_type": request.page_type_id,
            "generated_title": page_content['title'],
            "total_sites": len(request.target_sites),
            "successful": successful,
            "failed": len(request.target_sites) - successful,
            "deployments": results
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/preview-structured")
async def preview_structured_content(page_type_id: str, data: Dict):
    """
    Preview generated content without deploying.
    Useful for testing templates before deployment.
    """
    try:
        page_content = template_engine.generate_page_content(page_type_id, data)
        return {
            "success": True,
            "page_type": page_type_id,
            "preview": {
                "title": page_content['title'],
                "html_content": page_content['content'],
                "excerpt": page_content.get('excerpt', ''),
                "meta": page_content.get('meta', {}),
                "elementor_data": page_content['elementor_data']
            }
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
