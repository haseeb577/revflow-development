"""
RevAttr™ Attribution API Endpoint
Module 10: RevMetrics™ - Attribution Sub-Module

Receives attribution tracking events from JavaScript tracker
and stores them in PostgreSQL for multi-touch attribution analysis.

Author: RevFlow OS
Date: 2026-02-08
Version: 1.0.0
"""

from fastapi import APIRouter, Body, HTTPException, Request
from fastapi.responses import JSONResponse
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
import asyncpg
import json
import os
from contextlib import asynccontextmanager

# =====================================================================
# PYDANTIC MODELS
# =====================================================================

class AttributionEventPayload(BaseModel):
    """Attribution event from JavaScript tracker"""
    event: str = Field(..., description="Event type (session_start, page_view, conversion)")
    timestamp: str = Field(..., description="ISO timestamp")
    data: Dict[str, Any] = Field(..., description="Event data")
    meta: Dict[str, Any] = Field(default_factory=dict, description="Browser metadata")


class AttributionAnalysisRequest(BaseModel):
    """Request for attribution analysis"""
    visitor_id: Optional[str] = None
    session_id: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    conversion_type: Optional[str] = None


# =====================================================================
# DATABASE CONNECTION
# =====================================================================

DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': os.getenv('POSTGRES_DB', 'revflow'),
    'user': os.getenv('POSTGRES_USER', 'postgres'),
    'password': os.getenv('POSTGRES_PASSWORD', 'revflow2026')
}

@asynccontextmanager
async def get_db_connection():
    """Get database connection from pool"""
    conn = await asyncpg.connect(**DB_CONFIG)
    try:
        yield conn
    finally:
        await conn.close()


# =====================================================================
# API ROUTER
# =====================================================================

router = APIRouter(prefix="/api/attribution", tags=["RevAttr™ Attribution"])


@router.post("/track", 
    summary="Track Attribution Event",
    description="Receives attribution tracking events from RevAttr™ JavaScript tracker",
    response_model=dict
)
async def track_attribution_event(
    request: Request,
    payload: AttributionEventPayload = Body(...)
):
    """
    Track attribution events from landing pages
    
    Event types:
    - session_start: New visitor session started
    - page_view: Page viewed
    - conversion: Conversion action (form submit, phone click, etc.)
    
    Returns:
        Status and event ID
    """
    try:
        event = payload.event
        timestamp = payload.timestamp
        data = payload.data
        meta = payload.meta
        
        # Extract key fields
        visitor_id = data.get('visitor_id')
        session_id = data.get('session_id')
        event_type = data.get('event_type', event)
        
        # Get client IP (for additional analysis)
        client_ip = request.client.host if request.client else 'unknown'
        
        # Store in PostgreSQL
        async with get_db_connection() as conn:
            event_id = await conn.fetchval("""
                INSERT INTO attribution_events 
                (event_name, event_type, event_data, visitor_id, session_id, 
                 first_touch_utm, last_touch_utm, timestamp, meta, client_ip)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                RETURNING id
            """, 
                event,
                event_type,
                json.dumps(data),
                visitor_id,
                session_id,
                json.dumps(data.get('first_touch', {})),
                json.dumps(data.get('last_touch', {})),
                timestamp,
                json.dumps(meta),
                client_ip
            )
        
        return {
            "status": "tracked",
            "event": event,
            "event_id": event_id,
            "timestamp": timestamp
        }
        
    except Exception as e:
        print(f"[RevAttr] Tracking error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to track event: {str(e)}")


@router.get("/visitor/{visitor_id}",
    summary="Get Visitor Journey",
    description="Retrieve complete attribution journey for a visitor"
)
async def get_visitor_journey(visitor_id: str):
    """
    Get complete attribution journey for a specific visitor
    
    Returns all touchpoints, sessions, and conversions
    """
    try:
        async with get_db_connection() as conn:
            events = await conn.fetch("""
                SELECT 
                    id, event_name, event_type, event_data, 
                    session_id, first_touch_utm, last_touch_utm,
                    timestamp, created_at
                FROM attribution_events
                WHERE visitor_id = $1
                ORDER BY timestamp ASC
            """, visitor_id)
            
            if not events:
                raise HTTPException(status_code=404, detail="Visitor not found")
            
            # Parse events
            journey = []
            for event in events:
                journey.append({
                    'id': event['id'],
                    'event': event['event_name'],
                    'event_type': event['event_type'],
                    'data': json.loads(event['event_data']),
                    'session_id': event['session_id'],
                    'first_touch': json.loads(event['first_touch_utm']),
                    'last_touch': json.loads(event['last_touch_utm']),
                    'timestamp': event['timestamp']
                })
            
            return {
                "visitor_id": visitor_id,
                "total_events": len(journey),
                "journey": journey
            }
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve journey: {str(e)}")


@router.get("/conversions",
    summary="Get Conversions",
    description="Retrieve conversion events with attribution data"
)
async def get_conversions(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    conversion_type: Optional[str] = None,
    limit: int = 100
):
    """
    Get conversion events with full attribution data
    
    Query parameters:
    - start_date: ISO date string
    - end_date: ISO date string
    - conversion_type: Filter by conversion type (form_submit, phone_click, etc.)
    - limit: Max results (default 100)
    """
    try:
        query = """
            SELECT 
                id, event_type, visitor_id, session_id,
                event_data, first_touch_utm, last_touch_utm,
                timestamp, created_at
            FROM attribution_events
            WHERE event_name = 'conversion'
        """
        
        params = []
        param_count = 1
        
        if start_date:
            query += f" AND timestamp >= ${param_count}"
            params.append(start_date)
            param_count += 1
            
        if end_date:
            query += f" AND timestamp <= ${param_count}"
            params.append(end_date)
            param_count += 1
            
        if conversion_type:
            query += f" AND event_type = ${param_count}"
            params.append(conversion_type)
            param_count += 1
        
        query += f" ORDER BY timestamp DESC LIMIT ${param_count}"
        params.append(limit)
        
        async with get_db_connection() as conn:
            conversions = await conn.fetch(query, *params)
            
            result = []
            for conv in conversions:
                result.append({
                    'id': conv['id'],
                    'conversion_type': conv['event_type'],
                    'visitor_id': conv['visitor_id'],
                    'session_id': conv['session_id'],
                    'data': json.loads(conv['event_data']),
                    'first_touch': json.loads(conv['first_touch_utm']),
                    'last_touch': json.loads(conv['last_touch_utm']),
                    'timestamp': conv['timestamp']
                })
            
            return {
                "total": len(result),
                "conversions": result
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve conversions: {str(e)}")


@router.post("/analyze",
    summary="Analyze Attribution",
    description="Run attribution analysis on collected data"
)
async def analyze_attribution(analysis: AttributionAnalysisRequest):
    """
    Analyze attribution patterns
    
    Returns:
    - First-touch attribution breakdown
    - Last-touch attribution breakdown
    - Multi-touch weighted attribution
    - Conversion paths
    - Time to conversion stats
    """
    try:
        filters = []
        params = []
        param_count = 1
        
        if analysis.visitor_id:
            filters.append(f"visitor_id = ${param_count}")
            params.append(analysis.visitor_id)
            param_count += 1
            
        if analysis.session_id:
            filters.append(f"session_id = ${param_count}")
            params.append(analysis.session_id)
            param_count += 1
            
        if analysis.start_date:
            filters.append(f"timestamp >= ${param_count}")
            params.append(analysis.start_date)
            param_count += 1
            
        if analysis.end_date:
            filters.append(f"timestamp <= ${param_count}")
            params.append(analysis.end_date)
            param_count += 1
            
        if analysis.conversion_type:
            filters.append(f"event_type = ${param_count}")
            params.append(analysis.conversion_type)
            param_count += 1
        
        where_clause = " AND ".join(filters) if filters else "1=1"
        
        async with get_db_connection() as conn:
            # First-touch attribution
            first_touch_query = f"""
                SELECT 
                    first_touch_utm->>'utm_source' as source,
                    first_touch_utm->>'utm_medium' as medium,
                    first_touch_utm->>'utm_campaign' as campaign,
                    COUNT(*) as conversions
                FROM attribution_events
                WHERE event_name = 'conversion' AND {where_clause}
                GROUP BY source, medium, campaign
                ORDER BY conversions DESC
            """
            first_touch = await conn.fetch(first_touch_query, *params)
            
            # Last-touch attribution
            last_touch_query = f"""
                SELECT 
                    last_touch_utm->>'utm_source' as source,
                    last_touch_utm->>'utm_medium' as medium,
                    last_touch_utm->>'utm_campaign' as campaign,
                    COUNT(*) as conversions
                FROM attribution_events
                WHERE event_name = 'conversion' AND {where_clause}
                GROUP BY source, medium, campaign
                ORDER BY conversions DESC
            """
            last_touch = await conn.fetch(last_touch_query, *params)
            
            # Time to conversion stats
            time_stats_query = f"""
                SELECT 
                    AVG(CAST(event_data->>'time_to_conversion' AS INTEGER)) as avg_time,
                    MIN(CAST(event_data->>'time_to_conversion' AS INTEGER)) as min_time,
                    MAX(CAST(event_data->>'time_to_conversion' AS INTEGER)) as max_time
                FROM attribution_events
                WHERE event_name = 'conversion' 
                  AND event_data->>'time_to_conversion' IS NOT NULL
                  AND {where_clause}
            """
            time_stats = await conn.fetchrow(time_stats_query, *params)
            
            return {
                "first_touch_attribution": [dict(row) for row in first_touch],
                "last_touch_attribution": [dict(row) for row in last_touch],
                "time_to_conversion": {
                    "average_seconds": int(time_stats['avg_time']) if time_stats['avg_time'] else 0,
                    "min_seconds": int(time_stats['min_time']) if time_stats['min_time'] else 0,
                    "max_seconds": int(time_stats['max_time']) if time_stats['max_time'] else 0
                }
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to analyze attribution: {str(e)}")


@router.get("/health",
    summary="Health Check",
    description="Check RevAttr™ API health status"
)
async def health_check():
    """Health check endpoint"""
    try:
        # Test database connection
        async with get_db_connection() as conn:
            await conn.fetchval("SELECT 1")
        
        return {
            "status": "healthy",
            "service": "RevAttr™ Attribution API",
            "timestamp": datetime.utcnow().isoformat(),
            "database": "connected"
        }
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )
