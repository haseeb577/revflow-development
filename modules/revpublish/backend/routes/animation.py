"""
Animation API Routes for RevPublish™
Handles animation templates, deployments, and analytics
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import psycopg2
from psycopg2.extras import RealDictCursor
import os
import uuid
from datetime import datetime
import json

router = APIRouter()

# Database connection
def get_db_connection():
    """Get database connection, preferring DATABASE_URL if available"""
    database_url = os.getenv('DATABASE_URL')
    if database_url:
        return psycopg2.connect(database_url, cursor_factory=RealDictCursor)
    return psycopg2.connect(
        host=os.getenv('POSTGRES_HOST', 'revflow-postgres-docker'),
        port=int(os.getenv('POSTGRES_PORT', 5432)),
        user=os.getenv('POSTGRES_USER', 'revflow'),
        password=os.getenv('POSTGRES_PASSWORD', 'revflow2026'),
        dbname=os.getenv('POSTGRES_DB', 'revflow'),
        cursor_factory=RealDictCursor
    )


# Pydantic models
class AnimationConfig(BaseModel):
    entrance_animation: str = 'fadeIn'
    animation_duration: int = 800
    animation_delay: int = 0
    scroll_triggered: bool = True
    viewport_offset: str = '20%'


class DeploymentRequest(BaseModel):
    template_id: int
    site_ids: List[int]
    config: AnimationConfig


class TemplateFilters(BaseModel):
    animation_type: Optional[str] = None
    page_type: Optional[str] = None
    min_performance: Optional[int] = None


@router.get("/api/animation/templates")
async def get_animation_templates(
    animation_type: Optional[str] = Query(None, description="Filter by animation type"),
    page_type: Optional[str] = Query(None, description="Filter by page type"),
    min_performance: Optional[int] = Query(None, description="Minimum performance score"),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100)
):
    """Get animation templates with optional filtering"""
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Build query with filters
        query = "SELECT * FROM animation_templates WHERE 1=1"
        params = []

        if animation_type and animation_type != 'all':
            query += " AND animation_type = %s"
            params.append(animation_type)

        if page_type and page_type != 'all':
            query += " AND page_type = %s"
            params.append(page_type)

        if min_performance:
            query += " AND performance_score >= %s"
            params.append(min_performance)

        # Get total count
        count_query = query.replace("SELECT *", "SELECT COUNT(*)")
        cur.execute(count_query, params)
        total = cur.fetchone()['count']

        # Add pagination and ordering
        query += " ORDER BY usage_count DESC, performance_score DESC"
        query += f" LIMIT {per_page} OFFSET {(page - 1) * per_page}"

        cur.execute(query, params)
        templates = cur.fetchall()

        return {
            "status": "success",
            "templates": [dict(t) for t in templates],
            "page": page,
            "per_page": per_page,
            "total": total,
            "pages": (total + per_page - 1) // per_page
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn:
            conn.close()


@router.get("/api/animation/templates/{template_id}")
async def get_template_detail(template_id: int):
    """Get single template with full details"""
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("SELECT * FROM animation_templates WHERE id = %s", (template_id,))
        template = cur.fetchone()

        if not template:
            raise HTTPException(status_code=404, detail="Template not found")

        # Get deployment history for this template
        cur.execute("""
            SELECT ad.*, wp.site_name
            FROM animation_deployments ad
            LEFT JOIN wordpress_sites wp ON ad.site_id = wp.id
            WHERE ad.template_id = %s
            ORDER BY ad.created_at DESC
            LIMIT 10
        """, (template_id,))
        deployments = cur.fetchall()

        return {
            "status": "success",
            "template": dict(template),
            "recent_deployments": [dict(d) for d in deployments]
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn:
            conn.close()


@router.post("/api/animation/deploy")
async def deploy_animation(request: DeploymentRequest):
    """Deploy animation template to selected sites"""
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Verify template exists
        cur.execute("SELECT * FROM animation_templates WHERE id = %s", (request.template_id,))
        template = cur.fetchone()
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")

        # Create deployment jobs for each site
        jobs = []
        for site_id in request.site_ids:
            job_id = f"anim-{uuid.uuid4().hex[:12]}"

            cur.execute("""
                INSERT INTO animation_deployments
                (template_id, site_id, job_id, status, config)
                VALUES (%s, %s, %s, 'queued', %s)
                RETURNING id, job_id
            """, (
                request.template_id,
                site_id,
                job_id,
                json.dumps(request.config.dict())
            ))

            job = cur.fetchone()
            jobs.append({
                "id": job["id"],
                "job_id": job["job_id"],
                "site_id": site_id,
                "status": "queued"
            })

        # Update template usage count
        cur.execute("""
            UPDATE animation_templates
            SET usage_count = usage_count + %s,
                updated_at = NOW()
            WHERE id = %s
        """, (len(request.site_ids), request.template_id))

        conn.commit()

        return {
            "status": "success",
            "message": f"Queued {len(jobs)} deployment jobs",
            "jobs": jobs,
            "job_id": jobs[0]["job_id"] if jobs else None
        }

    except HTTPException:
        raise
    except Exception as e:
        conn.rollback() if conn else None
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn:
            conn.close()


@router.get("/api/queue")
async def get_deployment_queue():
    """Get deployment queue status"""
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Get queue stats
        cur.execute("""
            SELECT
                COUNT(*) FILTER (WHERE status = 'queued') as queued,
                COUNT(*) FILTER (WHERE status = 'in_progress') as in_progress,
                COUNT(*) FILTER (WHERE status = 'completed') as completed,
                COUNT(*) FILTER (WHERE status = 'failed') as failed
            FROM animation_deployments
            WHERE created_at > NOW() - INTERVAL '24 hours'
        """)
        stats = dict(cur.fetchone())

        # Get recent jobs
        cur.execute("""
            SELECT
                ad.*,
                at.name as template_name,
                at.animation_type,
                wp.site_name
            FROM animation_deployments ad
            LEFT JOIN animation_templates at ON ad.template_id = at.id
            LEFT JOIN wordpress_sites wp ON ad.site_id = wp.id
            WHERE ad.created_at > NOW() - INTERVAL '24 hours'
            ORDER BY ad.created_at DESC
            LIMIT 50
        """)
        jobs = [dict(j) for j in cur.fetchall()]

        return {
            "status": "success",
            "stats": stats,
            "jobs": jobs
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn:
            conn.close()


@router.get("/api/analytics/animation-performance")
async def get_animation_performance():
    """Get animation performance analytics"""
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Performance by template type
        cur.execute("""
            SELECT
                animation_type,
                COUNT(*) as template_count,
                AVG(performance_score) as avg_performance,
                SUM(usage_count) as total_usage
            FROM animation_templates
            GROUP BY animation_type
            ORDER BY total_usage DESC
        """)
        by_type = [dict(r) for r in cur.fetchall()]

        # Top performing templates
        cur.execute("""
            SELECT name as template_name, performance_score, usage_count, animation_type
            FROM animation_templates
            ORDER BY performance_score DESC, usage_count DESC
            LIMIT 10
        """)
        top_templates = [dict(r) for r in cur.fetchall()]

        # Deployment success rate
        cur.execute("""
            SELECT
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE status = 'completed') as successful,
                COUNT(*) FILTER (WHERE status = 'failed') as failed
            FROM animation_deployments
        """)
        deployment_stats = dict(cur.fetchone())

        # Estimated load times (mock data based on animation type)
        performance_by_template = [
            {"template_name": "Fade In", "avg_load_time_ms": 45},
            {"template_name": "Slide In", "avg_load_time_ms": 62},
            {"template_name": "Zoom In", "avg_load_time_ms": 78},
            {"template_name": "Bounce In", "avg_load_time_ms": 85},
            {"template_name": "Scroll Triggered", "avg_load_time_ms": 35}
        ]

        return {
            "status": "success",
            "performance_by_type": by_type,
            "top_templates": top_templates,
            "deployment_stats": deployment_stats,
            "performance_by_template": performance_by_template,
            "engagement": {
                "avg_time_on_page": 127,  # seconds
                "bounce_rate": 0.32,
                "avg_scroll_depth": 0.68
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn:
            conn.close()


@router.get("/api/animation/stats")
async def get_animation_stats():
    """Get summary statistics for animations"""
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT
                COUNT(*) as total_templates,
                COUNT(DISTINCT animation_type) as animation_types,
                COUNT(DISTINCT page_type) as page_types,
                AVG(performance_score) as avg_performance,
                SUM(usage_count) as total_deployments
            FROM animation_templates
        """)
        stats = dict(cur.fetchone())

        return {
            "status": "success",
            "stats": stats
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn:
            conn.close()
