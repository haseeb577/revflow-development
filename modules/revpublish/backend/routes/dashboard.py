"""
Dashboard Routes - Top-Level API Endpoints
Provides /api/sites, /api/dashboard-stats, /api/queue, /api/deployments
"""

from fastapi import APIRouter, HTTPException, Form
from pydantic import BaseModel
from typing import List, Optional
import psycopg2
import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
# Try multiple locations for .env file
env_paths = [
    '/opt/shared-api-engine/.env',  # Docker shared location
    '../../../.env',  # Project root
    '../../.env',     # Module root
    '../.env',        # Backend folder
    '.env'            # Current folder
]
for path in env_paths:
    if os.path.exists(path):
        load_dotenv(path)
        break

router = APIRouter()

# Auto-create table if it doesn't exist
def ensure_table_exists(conn):
    """Create wordpress_sites table if it doesn't exist"""
    cursor = conn.cursor()
    try:
        # Check if table exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'wordpress_sites'
            )
        """)
        table_exists = cursor.fetchone()[0]
        
        if not table_exists:
            print("⚠️  wordpress_sites table not found. Creating it automatically...")
            # Create the table
            cursor.execute("""
                CREATE TABLE wordpress_sites (
                    id SERIAL PRIMARY KEY,
                    site_id VARCHAR(255) UNIQUE NOT NULL,
                    site_name VARCHAR(255) NOT NULL,
                    site_url VARCHAR(500) NOT NULL,
                    wp_username VARCHAR(255),
                    app_password TEXT,
                    connection_status VARCHAR(50) DEFAULT 'pending',
                    last_connection_test TIMESTAMP,
                    status VARCHAR(50) DEFAULT 'active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indexes
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_wordpress_sites_site_id 
                ON wordpress_sites(site_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_wordpress_sites_status 
                ON wordpress_sites(status)
            """)
            
            conn.commit()
            print("✅ wordpress_sites table created successfully")
        
        cursor.close()
    except Exception as e:
        conn.rollback()
        cursor.close()
        raise

# Database helper
def get_db():
    """Get database connection with proper error handling"""
    try:
        # Get password with fallback to default (matching docker-compose)
        password = os.getenv("POSTGRES_PASSWORD") or "revflow2026"
        
        # Determine host - if running locally, try localhost first
        # Docker uses 'revflow-postgres-docker', local uses 'localhost'
        host = os.getenv("POSTGRES_HOST")
        if not host:
            # Default to localhost for local development
            # If connecting to Docker PostgreSQL, use localhost (port 5433)
            host = "localhost"
        
        # Port: Docker maps to 5433, local PostgreSQL uses 5432
        port = os.getenv("POSTGRES_PORT", "5432")
        
        # If host is the Docker container name, we're in Docker - use default port
        # Otherwise, if localhost, check if Docker PostgreSQL is running (port 5433)
        if host == "localhost" and port == "5432":
            # Try to detect if Docker PostgreSQL is available on 5433
            try:
                test_conn = psycopg2.connect(
                    host="localhost",
                    port=5433,
                    database=os.getenv("POSTGRES_DB", "revflow"),
                    user=os.getenv("POSTGRES_USER", "revflow"),
                    password=password,
                    connect_timeout=2
                )
                test_conn.close()
                port = "5433"  # Use Docker port
            except:
                pass  # Use default port 5432
        
        return psycopg2.connect(
            host=host,
            port=int(port),
            database=os.getenv("POSTGRES_DB", "revflow"),
            user=os.getenv("POSTGRES_USER", "revflow"),
            password=password
        )
    except ValueError as e:
        raise
    except psycopg2.OperationalError as e:
        error_msg = str(e)
        if "could not connect" in error_msg.lower() or "connection refused" in error_msg.lower():
            raise ConnectionError(
                "Cannot connect to PostgreSQL database. "
                "Please ensure PostgreSQL is running and accessible. "
                f"Error: {error_msg}"
            )
        elif "authentication failed" in error_msg.lower() or "password authentication failed" in error_msg.lower():
            raise ConnectionError(
                "Database authentication failed. "
                "Please check your POSTGRES_USER and POSTGRES_PASSWORD in your .env file."
            )
        elif "database" in error_msg.lower() and "does not exist" in error_msg.lower():
            raise ConnectionError(
                f"Database '{os.getenv('POSTGRES_DB', 'revflow')}' does not exist. "
                "Please create the database first."
            )
        else:
            raise ConnectionError(f"Database connection error: {error_msg}")
    except Exception as e:
        raise ConnectionError(f"Unexpected database error: {str(e)}")

@router.get("/sites")
async def get_sites(page: int = 1, per_page: int = 10):
    """List all WordPress sites - MAIN ENDPOINT"""
    conn = None
    cursor = None
    try:
        conn = get_db()
        
        # Auto-create table if it doesn't exist
        ensure_table_exists(conn)
        
        cursor = conn.cursor()
        
        offset = (page - 1) * per_page
        
        # Get total count
        cursor.execute("SELECT COUNT(*) FROM wordpress_sites")
        total = cursor.fetchone()[0]
        
        # Get paginated sites
        cursor.execute("""
            SELECT id, site_id, site_name, site_url, 
                   CONCAT(site_url, '/wp-admin') as wp_admin_url,
                   status, created_at, updated_at
            FROM wordpress_sites
            ORDER BY site_name
            LIMIT %s OFFSET %s
        """, (per_page, offset))
        
        sites = []
        for row in cursor.fetchall():
            sites.append({
                "id": row[0],
                "site_name": row[2],
                "site_url": row[3],
                "wp_admin_url": row[4],
                "status": row[5] or "active",
                "created_at": row[6].isoformat() if row[6] else None,
                "updated_at": row[7].isoformat() if row[7] else None
            })
        
        if cursor:
            cursor.close()
        if conn:
            conn.close()
        
        pages = (total + per_page - 1) // per_page
        
        return {
            "status": "success",
            "sites": sites,
            "page": page,
            "per_page": per_page,
            "total": total,
            "pages": pages
        }
        
    except HTTPException:
        raise
    except ConnectionError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Database connection failed: {str(e)}. Please ensure PostgreSQL is running and configured correctly."
        )
    except ValueError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Configuration error: {str(e)}"
        )
    except psycopg2.Error as e:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )
    except Exception as e:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")

@router.get("/sites/{site_id}")
async def get_site_details(site_id: str):
    """Get details for a single site - LEVEL 2 SCREEN"""
    try:
        conn = get_db()
        
        # Auto-create table if it doesn't exist
        ensure_table_exists(conn)
        
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, site_id, site_name, site_url, wp_username, 
                   status, connection_status, last_connection_test,
                   created_at, updated_at
            FROM wordpress_sites
            WHERE site_id = %s
        """, (site_id,))
        
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Site not found")
        
        site = {
            "id": row[0],
            "site_id": row[1],
            "site_name": row[2],
            "site_url": row[3],
            "wp_username": row[4],
            "status": row[5] or "active",
            "connection_status": row[6],
            "last_connection_test": row[7].isoformat() if row[7] else None,
            "created_at": row[8].isoformat() if row[8] else None,
            "updated_at": row[9].isoformat() if row[9] else None
        }
        
        cursor.close()
        conn.close()
        
        return {"status": "success", "site": site}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class SiteUpdate(BaseModel):
    site_name: Optional[str] = None
    wp_username: Optional[str] = None
    app_password: Optional[str] = None
    status: Optional[str] = None

@router.put("/sites/{site_id}")
async def update_site(
    site_id: str,
    site_name: Optional[str] = Form(None),
    wp_username: Optional[str] = Form(None),
    app_password: Optional[str] = Form(None),
    status: Optional[str] = Form(None)
):
    """Update site details - LEVEL 3 SCREEN - Accepts form-data"""
    try:
        conn = get_db()
        
        # Auto-create table if it doesn't exist
        ensure_table_exists(conn)
        
        cursor = conn.cursor()
        
        updates = []
        values = []
        
        if site_name:
            updates.append("site_name = %s")
            values.append(site_name)
        if wp_username:
            updates.append("wp_username = %s")
            values.append(wp_username)
        if app_password:
            updates.append("app_password = %s")
            values.append(app_password)
        if status:
            updates.append("status = %s")
            values.append(status)
        
        if not updates:
            return {"status": "success", "message": "No changes"}
        
        updates.append("updated_at = NOW()")
        values.append(site_id)
        
        # Use id column for WHERE clause (form sends id value as site_id parameter)
        query = f"UPDATE wordpress_sites SET {', '.join(updates)} WHERE id = %s"
        cursor.execute(query, values)
        conn.commit()
        
        # Get site details to return
        cursor.execute("""
            SELECT id, site_id, site_name, site_url, wp_username, status
            FROM wordpress_sites
            WHERE id = %s
        """, (site_id,))
        site_row = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        site_info = None
        if site_row:
            site_info = {
                "id": site_row[0],
                "site_id": site_row[1],
                "site_name": site_row[2],
                "site_url": site_row[3],
                "wp_username": site_row[4],
                "status": site_row[5] or "active"
            }
        
        return {
            "status": "success", 
            "site_id": site_id, 
            "updated": True,
            "site": site_info
        }
        
    except psycopg2.ProgrammingError as e:
        error_msg = str(e)
        # If table doesn't exist, try to create it and retry
        if "does not exist" in error_msg.lower() and "wordpress_sites" in error_msg.lower():
            try:
                conn = get_db()
                ensure_table_exists(conn)
                conn.close()
                # Retry the operation
                return await update_site(site_id, site_name, wp_username, app_password, status)
            except Exception as retry_error:
                raise HTTPException(
                    status_code=500, 
                    detail=f"Failed to create table and retry: {str(retry_error)}"
                )
        raise HTTPException(status_code=500, detail=f"Database error: {error_msg}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/dashboard-stats")
async def get_dashboard_stats():
    """Dashboard statistics"""
    conn = None
    cursor = None
    try:
        conn = get_db()
        
        # Auto-create table if it doesn't exist
        ensure_table_exists(conn)
        
        cursor = conn.cursor()
        
        # Total sites
        cursor.execute("SELECT COUNT(*) FROM wordpress_sites")
        total_sites = cursor.fetchone()[0]
        
        # Connected sites
        cursor.execute("SELECT COUNT(*) FROM wordpress_sites WHERE connection_status = 'success'")
        connected = cursor.fetchone()[0]
        
        if cursor:
            cursor.close()
        if conn:
            conn.close()
        
        return {
            "total_sites": total_sites,
            "connected_sites": connected,
            "pending_deployments": 0,
            "active_queue": 0
        }
        
    except ConnectionError as e:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
        raise HTTPException(
            status_code=503,
            detail=f"Database connection failed: {str(e)}"
        )
    except Exception as e:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/queue")
async def get_queue():
    """Deployment queue (placeholder)"""
    return {
        "status": "success",
        "queue": [],
        "total": 0
    }

@router.get("/deployments")
async def get_deployments():
    """Deployment history (placeholder)"""
    return {
        "status": "success",
        "deployments": [],
        "total": 0
    }

@router.get("/conflicts")
async def get_conflicts():
    """Recent conflicts (placeholder)"""
    return {
        "status": "success",
        "conflicts": [],
        "total": 0
    }

@router.get("/conflicts/scan")
async def scan_conflicts():
    """Scan for conflicts (placeholder)"""
    return {
        "status": "success",
        "message": "Conflict scanning feature coming soon",
        "conflicts_found": 0
    }
