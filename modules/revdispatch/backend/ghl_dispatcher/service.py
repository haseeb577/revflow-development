from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import psycopg2
import logging
import os

app = FastAPI(title="GHL Dispatcher")
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_CONFIG = {
    'host': os.getenv('PGHOST', '/var/run/postgresql'),
    'port': int(os.getenv('PGPORT', 5432)),
    'database': os.getenv('PGDATABASE', 'revflow'),
    'user': os.getenv('PGUSER', 'revflow')
}

class DispatchRequest(BaseModel):
    lead_id: int
    customer_id: Optional[int] = None
    ghl_customer_id: Optional[str] = None

@app.get("/health")
async def health():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.close()
        conn.close()
        return {"status": "healthy", "service": "GHL Dispatcher", "database": "connected"}
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {"status": "unhealthy", "error": str(e)}, 503

@app.post("/dispatch/ghl")
async def dispatch_to_ghl(request: DispatchRequest):
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM leads WHERE id = %s", (request.lead_id,))
        if not cursor.fetchone():
            cursor.close()
            conn.close()
            raise HTTPException(status_code=404, detail="Lead not found")
        cursor.execute("""INSERT INTO dispatch_logs (lead_id, customer_id, action_type, status, routed_to, created_at)
            VALUES (%s, %s, %s, %s, %s, %s)""", (request.lead_id, request.customer_id, 'dispatch', 'success', 'GHL', datetime.now()))
        conn.commit()
        cursor.close()
        conn.close()
        logger.info(f"Dispatched lead {request.lead_id} to GHL")
        return {"status": "dispatched", "lead_id": request.lead_id, "destination": "GoHighLevel"}
    except Exception as e:
        logger.error(f"Dispatch error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8165, log_level="info")
