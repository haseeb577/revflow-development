"""
Hostinger Integration Routes
Fetches websites from Hostinger account dynamically
"""

from fastapi import APIRouter, HTTPException
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

def get_hostinger_api_key() -> Optional[str]:
    """Get Hostinger API key from environment variables"""
    return os.getenv("HOSTINGER_API_KEY") or os.getenv("HOSTINGER_TOKEN")

def get_hostinger_api_url() -> str:
    """Get Hostinger API base URL"""
    # Hostinger API endpoint (update if different)
    return os.getenv("HOSTINGER_API_URL", "https://api.hostinger.com/v1")

@router.get("/hostinger/websites")
async def get_hostinger_websites():
    """
    Fetch all websites from Hostinger account
    Returns list of domains/websites from Hostinger
    
    Note: Hostinger may not have a public API. This endpoint supports:
    1. Hostinger API (if available) - requires HOSTINGER_API_KEY
    2. Fallback to local database - returns sites from wordpress_sites table
    3. Manual configuration via /api/hostinger/sync endpoint
    """
    api_key = get_hostinger_api_key()
    
    # If no API key, fallback to local database
    if not api_key:
        try:
            from routes.dashboard import get_db, ensure_table_exists
            import psycopg2
            
            conn = get_db()
            ensure_table_exists(conn)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, site_id, site_name, site_url, status, created_at
                FROM wordpress_sites
                ORDER BY site_name
            """)
            
            sites = []
            for row in cursor.fetchall():
                sites.append({
                    "id": row[0],
                    "site_id": row[1] or str(row[0]),
                    "site_name": row[2],
                    "site_url": row[3],
                    "status": row[4] or "active",
                    "created_at": row[5].isoformat() if row[5] else None,
                    "provider": "local"
                })
            
            cursor.close()
            conn.close()
            
            return {
                "status": "success",
                "sites": sites,
                "total": len(sites),
                "provider": "local",
                "message": "Using local database. Set HOSTINGER_API_KEY to fetch from Hostinger API."
            }
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error fetching local websites: {str(e)}"
            )
    
    # Try Hostinger API
    try:
        api_url = get_hostinger_api_url()
        
        # Try different authentication methods
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        # Try Bearer token first
        if api_key.startswith("Bearer "):
            headers["Authorization"] = api_key
        else:
            headers["Authorization"] = f"Bearer {api_key}"
        
        # Also try API key in header (some APIs use X-API-Key)
        headers["X-API-Key"] = api_key
        
        # Try multiple possible endpoints
        endpoints_to_try = [
            f"{api_url}/domains",
            f"{api_url}/websites",
            f"{api_url}/v1/domains",
            f"{api_url}/v1/websites",
            f"https://api.hostinger.com/v1/domains",
            f"https://api.hostinger.com/v1/websites",
        ]
        
        last_error = None
        for endpoint in endpoints_to_try:
            try:
                response = requests.get(
                    endpoint,
                    headers=headers,
                    timeout=10
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Transform Hostinger response to our format
                    websites = []
                    if isinstance(data, list):
                        websites = data
                    elif isinstance(data, dict):
                        if "domains" in data:
                            websites = data["domains"]
                        elif "websites" in data:
                            websites = data["websites"]
                        elif "data" in data:
                            websites = data["data"]
                        elif "items" in data:
                            websites = data["items"]
                        else:
                            websites = [data]
                    
                    # Normalize website data
                    normalized_websites = []
                    for site in websites:
                        if isinstance(site, dict):
                            # Extract domain/URL
                            domain = (site.get("domain") or site.get("name") or 
                                     site.get("domain_name") or site.get("url") or 
                                     site.get("fqdn") or "")
                            
                            # Ensure URL has protocol
                            if domain and not domain.startswith(("http://", "https://")):
                                domain = f"https://{domain}"
                            
                            normalized_websites.append({
                                "id": site.get("id") or site.get("domain_id") or site.get("website_id") or domain,
                                "site_name": site.get("name") or site.get("domain") or site.get("domain_name") or domain.replace("https://", "").replace("http://", ""),
                                "site_url": domain,
                                "status": site.get("status") or "active",
                                "created_at": site.get("created_at") or site.get("created"),
                                "expires_at": site.get("expires_at") or site.get("expires"),
                                "provider": "hostinger"
                            })
                        elif isinstance(site, str):
                            # If it's just a domain string
                            domain = site if site.startswith(("http://", "https://")) else f"https://{site}"
                            normalized_websites.append({
                                "id": site,
                                "site_name": site,
                                "site_url": domain,
                                "status": "active",
                                "provider": "hostinger"
                            })
                    
                    return {
                        "status": "success",
                        "sites": normalized_websites,
                        "total": len(normalized_websites),
                        "provider": "hostinger",
                        "endpoint_used": endpoint
                    }
                elif response.status_code == 401:
                    last_error = "Invalid Hostinger API key. Please check your credentials."
                    continue
                elif response.status_code == 404:
                    last_error = f"Endpoint not found: {endpoint}"
                    continue
                else:
                    last_error = f"HTTP {response.status_code}: {response.text[:200]}"
                    continue
                    
            except requests.exceptions.RequestException as e:
                last_error = str(e)
                continue
        
        # If all endpoints failed, raise error
        raise HTTPException(
            status_code=503,
            detail=f"Failed to connect to Hostinger API. Last error: {last_error}. Please check HOSTINGER_API_KEY and HOSTINGER_API_URL in your .env file."
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching Hostinger websites: {str(e)}"
        )

@router.post("/hostinger/sync")
async def sync_hostinger_websites():
    """
    Sync Hostinger websites to local database
    Fetches from Hostinger and stores in wordpress_sites table
    """
    try:
        # Get websites from Hostinger
        websites_response = await get_hostinger_websites()
        websites = websites_response["sites"]
        
        # Import database functions
        from routes.dashboard import get_db, ensure_table_exists
        import psycopg2
        
        conn = get_db()
        ensure_table_exists(conn)
        cursor = conn.cursor()
        
        synced_count = 0
        for website in websites:
            try:
                # Check if site already exists
                cursor.execute("""
                    SELECT id FROM wordpress_sites 
                    WHERE site_url = %s OR site_id = %s
                """, (website["site_url"], str(website["id"])))
                
                if cursor.fetchone():
                    # Update existing
                    cursor.execute("""
                        UPDATE wordpress_sites 
                        SET site_name = %s, updated_at = CURRENT_TIMESTAMP
                        WHERE site_url = %s OR site_id = %s
                    """, (website["site_name"], website["site_url"], str(website["id"])))
                else:
                    # Insert new
                    cursor.execute("""
                        INSERT INTO wordpress_sites 
                        (site_id, site_name, site_url, status, connection_status)
                        VALUES (%s, %s, %s, %s, 'pending')
                    """, (
                        str(website["id"]),
                        website["site_name"],
                        website["site_url"],
                        website.get("status", "active")
                    ))
                synced_count += 1
            except Exception as e:
                print(f"Error syncing website {website.get('site_url')}: {e}", flush=True)
                continue
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return {
            "status": "success",
            "synced": synced_count,
            "total": len(websites),
            "message": f"Successfully synced {synced_count} websites from Hostinger"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error syncing Hostinger websites: {str(e)}"
        )

