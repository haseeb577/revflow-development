from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime
import psycopg2
from psycopg2.extras import Json
import logging
import os

app = FastAPI(title="RevIntel")
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Use environment variables for database connection (set in systemd)
# Defaults to UNIX socket authentication
DB_CONFIG = {
    'host': os.getenv('PGHOST', '/var/run/postgresql'),
    'port': int(os.getenv('PGPORT', 5432)),
    'database': os.getenv('PGDATABASE', 'revflow'),
    'user': os.getenv('PGUSER', 'revflow')
}

class LeadInput(BaseModel):
    first_name: str
    last_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    company_name: Optional[str] = None
    source_id: str
    customer_id: Optional[int] = None
    raw_data: Optional[Dict[str, Any]] = None

@app.get("/health")
async def health():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("SELECT version()")
        version = cursor.fetchone()[0].split(',')[0]
        cursor.close()
        conn.close()
        return {
            "status": "healthy",
            "service": "RevIntel",
            "database": "connected",
            "postgres": version
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {"status": "unhealthy", "error": str(e)}, 503

@app.post("/webhook/ingest")
async def ingest_lead(lead: LeadInput):
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO leads (first_name, last_name, email, phone, company_name, source_id, customer_id,
                             lead_status, approval_status, tags, raw_data, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (lead.first_name, lead.last_name, lead.email, lead.phone, lead.company_name,
              lead.source_id, lead.customer_id, 'new', 'pending', [f'Web-{lead.source_id}'],
              Json(lead.raw_data or {}), datetime.now()))
        lead_id = cursor.fetchone()[0]
        cursor.execute("""INSERT INTO dispatch_logs (lead_id, customer_id, action_type, status, created_at)
            VALUES (%s, %s, %s, %s, %s)""", (lead_id, lead.customer_id, 'ingest', 'success', datetime.now()))
        conn.commit()
        cursor.close()
        conn.close()
        logger.info(f"Lead {lead_id} ingested from {lead.source_id}")
        return {"status": "success", "lead_id": lead_id, "message": f"Lead {lead_id} created"}
    except Exception as e:
        logger.error(f"Ingest error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/webhook/test")
async def test_webhook(data: Dict[str, Any]):
    return {"status": "test_received", "fields": len(data), "message": "Webhook endpoint is working"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8160, log_level="info")
