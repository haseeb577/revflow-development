"""
WordPress Site Discovery Routes
Discovers and connects to WordPress sites via custom plugin
"""

from fastapi import APIRouter, HTTPException, Form
from pydantic import BaseModel
from typing import List, Dict, Optional
import requests
import os
from dotenv import load_dotenv

# Load environment variables
env_paths = [
    '/opt/shared-api-engine/.env',
    '../../../.env',
    '../../.env',
    '../.env',
    '.env'
]
for path in env_paths:
    if os.path.exists(path):
        load_dotenv(path)
        break

router = APIRouter()

class WordPressSiteRequest(BaseModel):
    site_url: str
    site_secret: Optional[str] = None
    wp_username: Optional[str] = None
    app_password: Optional[str] = None

@router.post("/wordpress/discover")
async def discover_wordpress_site(request: WordPressSiteRequest):
    """
    Discover a WordPress site by connecting to it via RevPublish plugin
    Requires: site_url (and optionally site_secret or wp_username/app_password)
    """
    site_url = request.site_url.strip().rstrip('/')
    
    # Normalize URL
    if not site_url.startswith(('http://', 'https://')):
        site_url = f"https://{site_url}"
    
    try:
        # Try to connect via RevPublish plugin first
        plugin_endpoint = f"{site_url}/wp-json/revpublish/v1/site-info"
        
        headers = {}
        if request.site_secret:
            headers['X-RevPublish-Secret'] = request.site_secret
        
        # Try plugin endpoint
        try:
            response = requests.get(
                plugin_endpoint,
                headers=headers,
                timeout=5,
                verify=False  # Allow self-signed certificates
            )
            
            if response.status_code == 200:
                site_info = response.json()
                return {
                    "status": "success",
                    "discovery_method": "plugin",
                    "site": {
                        "site_id": site_info.get("site_id"),
                        "site_name": site_info.get("site_name"),
                        "site_url": site_info.get("site_url"),
                        "wp_version": site_info.get("wp_version"),
                        "status": site_info.get("status", "active"),
                        "registered_at": site_info.get("registered_at"),
                    },
                    "message": "Site discovered via RevPublish plugin"
                }
        except requests.exceptions.RequestException:
            pass  # Plugin not available, try WordPress REST API
        
        # Fallback: Try WordPress REST API with Application Password
        if request.wp_username and request.app_password:
            wp_api_endpoint = f"{site_url}/wp-json/wp/v2"
            
            # Test connection with Application Password
            auth = (request.wp_username, request.app_password)
            
            try:
                # Try to get site info from WordPress REST API
                response = requests.get(
                    f"{wp_api_endpoint}/",
                    auth=auth,
                    timeout=5,
                    verify=False
                )
                
                if response.status_code == 200:
                    wp_info = response.json()
                    return {
                        "status": "success",
                        "discovery_method": "wordpress_api",
                        "site": {
                            "site_id": None,  # Will be generated
                            "site_name": wp_info.get("name", site_url),
                            "site_url": site_url,
                            "wp_version": wp_info.get("version", "unknown"),
                            "status": "active",
                        },
                        "message": "Site discovered via WordPress REST API"
                    }
            except requests.exceptions.RequestException as e:
                raise HTTPException(
                    status_code=400,
                    detail=f"Failed to connect to WordPress site: {str(e)}"
                )
        
        # If both methods fail
        raise HTTPException(
            status_code=404,
            detail="WordPress site not found or RevPublish plugin not installed. Please install the plugin or provide WordPress credentials."
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error discovering WordPress site: {str(e)}"
        )

@router.post("/wordpress/register")
async def register_wordpress_site(
    site_url: str = Form(...),
    site_secret: Optional[str] = Form(None),
    wp_username: Optional[str] = Form(None),
    app_password: Optional[str] = Form(None)
):
    """
    Register a WordPress site in the database
    First discovers the site, then stores it locally
    """
    try:
        # Discover the site first
        discovery_request = WordPressSiteRequest(
            site_url=site_url,
            site_secret=site_secret,
            wp_username=wp_username,
            app_password=app_password
        )
        
        discovery_result = await discover_wordpress_site(discovery_request)
        site_data = discovery_result["site"]
        
        # Store in database
        from routes.dashboard import get_db, ensure_table_exists
        import psycopg2
        
        conn = get_db()
        ensure_table_exists(conn)
        cursor = conn.cursor()
        
        # Check if site already exists
        cursor.execute("""
            SELECT id FROM wordpress_sites 
            WHERE site_url = %s OR site_id = %s
        """, (site_data["site_url"], site_data.get("site_id") or ""))
        
        existing = cursor.fetchone()
        
        if existing:
            # Update existing
            cursor.execute("""
                UPDATE wordpress_sites 
                SET site_name = %s, 
                    wp_username = %s,
                    app_password = %s,
                    status = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (
                site_data["site_name"],
                wp_username,
                app_password,
                site_data.get("status", "active"),
                existing[0]
            ))
            site_id = existing[0]
        else:
            # Insert new
            cursor.execute("""
                INSERT INTO wordpress_sites 
                (site_id, site_name, site_url, wp_username, app_password, status, connection_status)
                VALUES (%s, %s, %s, %s, %s, %s, 'pending')
                RETURNING id
            """, (
                site_data.get("site_id") or f"wp_{site_data['site_url'].replace('https://', '').replace('http://', '').replace('/', '_')}",
                site_data["site_name"],
                site_data["site_url"],
                wp_username,
                app_password,
                site_data.get("status", "active")
            ))
            site_id = cursor.fetchone()[0]
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return {
            "status": "success",
            "message": "WordPress site registered successfully",
            "site_id": site_id,
            "site": site_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error registering WordPress site: {str(e)}"
        )

@router.get("/wordpress/discover-bulk")
async def discover_bulk_sites(urls: str):
    """
    Discover multiple WordPress sites at once
    URLs should be comma-separated
    """
    url_list = [url.strip() for url in urls.split(',') if url.strip()]
    
    results = []
    for url in url_list:
        try:
            request = WordPressSiteRequest(site_url=url)
            result = await discover_wordpress_site(request)
            results.append({
                "url": url,
                "status": "success",
                "site": result["site"]
            })
        except Exception as e:
            results.append({
                "url": url,
                "status": "error",
                "error": str(e)
            })
    
    return {
        "status": "success",
        "total": len(url_list),
        "successful": len([r for r in results if r["status"] == "success"]),
        "results": results
    }

