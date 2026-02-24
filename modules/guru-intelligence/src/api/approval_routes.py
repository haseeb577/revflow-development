"""Approval workflow API routes"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict
import psycopg2
import os
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

def get_db():
    return psycopg2.connect(os.getenv('DATABASE_URL'))

class PendingRequest(BaseModel):
    status: str = "pending"
    limit: int = 10

@router.post("/pending")
def get_pending_updates(request: PendingRequest):
    """Get pending rule updates"""
    try:
        conn = get_db()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT update_id, rule_name, definition, 
                   created_at, confidence_score
            FROM pending_updates 
            WHERE approval_status = %s
            ORDER BY confidence_score DESC, created_at DESC
            LIMIT %s
        """, (request.status, request.limit))
        
        updates = []
        for row in cur.fetchall():
            updates.append({
                'update_id': row[0],
                'rule_name': row[1],
                'definition': row[2][:200],
                'created_at': str(row[3]),
                'confidence_score': float(row[4])
            })
        
        cur.close()
        conn.close()
        
        return {'total': len(updates), 'updates': updates}
        
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats")
def get_approval_stats():
    """Get approval statistics"""
    try:
        conn = get_db()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT approval_status, COUNT(*) as count
            FROM pending_updates 
            GROUP BY approval_status
        """)
        
        stats = {}
        for row in cur.fetchall():
            stats[row[0]] = row[1]
        
        cur.close()
        conn.close()
        
        return stats
        
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
