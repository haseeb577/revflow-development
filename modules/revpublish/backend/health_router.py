"""
RevPublish Health Check Endpoint
For RevCore Hub and RevGuard monitoring
"""

from fastapi import APIRouter
import psycopg2
import os

router = APIRouter(prefix="/api/revpublish", tags=["health"])

@router.get("/health")
async def health_check():
    """
    Health check endpoint for RevCore Hub monitoring
    """
    health = {
        "status": "healthy",
        "module": "RevPublish",
        "module_number": 9,
        "checks": {}
    }
    
    # Check database connection
    try:
        conn = psycopg2.connect(
            host="localhost",
            database=os.getenv("DATABASE_NAME"),
            user=os.getenv("DATABASE_USER"),
            password=os.getenv("DATABASE_PASSWORD")
        )
        conn.close()
        health["checks"]["database"] = "ok"
    except Exception as e:
        health["checks"]["database"] = f"error: {str(e)}"
        health["status"] = "degraded"
    
    # Check tables exist
    try:
        conn = psycopg2.connect(
            host="localhost",
            database=os.getenv("DATABASE_NAME"),
            user=os.getenv("DATABASE_USER"),
            password=os.getenv("DATABASE_PASSWORD")
        )
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM revpublish_sites")
        site_count = cur.fetchone()[0]
        health["checks"]["sites_table"] = f"ok ({site_count} sites)"
        conn.close()
    except Exception as e:
        health["checks"]["sites_table"] = f"error: {str(e)}"
        health["status"] = "degraded"
    
    return health

@router.get("/module-info")
async def module_info():
    """
    Module information for service registry
    """
    return {
        "module_number": 9,
        "module_name": "RevPublish™",
        "suite": "Lead Generation Suite (AI-SEO/PPC)",
        "status": "active",
        "version": "2.0.0",
        "capabilities": [
            "wordpress_publishing",
            "content_deployment",
            "site_management",
            "bulk_deployment",
        ],
        "endpoints": {
            "health": "/api/revpublish/health",
            "dashboard": "/api/revpublish/dashboard-stats",
            "sites": "/api/revpublish/sites",
            "queue": "/api/revpublish/queue",
            "deploy": "/api/revpublish/deploy",
        }
    }
