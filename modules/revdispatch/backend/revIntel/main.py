from fastapi import FastAPI, HTTPException, Request, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
import psycopg2
from psycopg2.extras import RealDictCursor
import logging
import os
from typing import Optional
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="RevFlow RevIntel Webhook",
    version="2.0.0",
    description="Lead ingestion with authentication and external source support"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load webhook secret from environment
WEBHOOK_SECRET = os.getenv('WEBHOOK_SECRET_KEY', '00322244-c3f2-4c11-b9d3-79865ad289b9')

def get_db():
    return psycopg2.connect(
        host="/var/run/postgresql",
        port="5432",
        user="revflow",
        database="revflow",
        cursor_factory=RealDictCursor
    )

def verify_webhook_secret(x_webhook_secret: Optional[str] = Header(None)):
    """Verify webhook authentication"""
    if x_webhook_secret != WEBHOOK_SECRET:
        raise HTTPException(
            status_code=401,
            detail="Invalid webhook secret. Include 'X-Webhook-Secret' header."
        )
    return True

@app.post("/webhook/ingest")
async def ingest_lead(request: Request, authenticated: bool = Depends(verify_webhook_secret)):
    """
    Authenticated lead ingestion endpoint
    
    Headers:
        X-Webhook-Secret: Required authentication token
    
    Body (JSON):
        first_name: string
        last_name: string
        email: string
        phone: string
        company_name: string
        source_id: string (e.g., 'audiencelab', 'web-form', 'revintel')
        customer_id: integer
    """
    try:
        payload = await request.json()
        
        conn = get_db()
        cur = conn.cursor()
        
        # Insert lead
        cur.execute("""
            INSERT INTO leads (
                first_name, last_name, email, phone, 
                company_name, source_id, customer_id,
                created_at, updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            RETURNING id
        """, (
            payload.get('first_name'),
            payload.get('last_name'),
            payload.get('email'),
            payload.get('phone'),
            payload.get('company_name'),
            payload.get('source_id', 'unknown'),
            payload.get('customer_id')
        ))
        
        result = cur.fetchone()
        conn.commit()
        
        lead_id = result['id']
        logger.info(f"✓ Lead {lead_id} created from {payload.get('source_id')}")
        
        return {
            "status": "success",
            "lead_id": lead_id,
            "message": f"Lead {lead_id} created",
            "source": payload.get('source_id')
        }
        
    except Exception as e:
        logger.error(f"✗ Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if 'conn' in locals():
            conn.close()

@app.post("/webhook/public")
async def public_webhook(request: Request):
    """
    Public webhook endpoint (no auth required)
    Use for sources that cannot set custom headers
    """
    try:
        payload = await request.json()
        
        # Add public source identifier
        if 'source_id' not in payload:
            payload['source_id'] = 'public-webhook'
        
        conn = get_db()
        cur = conn.cursor()
        
        cur.execute("""
            INSERT INTO leads (
                first_name, last_name, email, phone,
                company_name, source_id, customer_id,
                created_at, updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            RETURNING id
        """, (
            payload.get('first_name'),
            payload.get('last_name'),
            payload.get('email'),
            payload.get('phone'),
            payload.get('company_name'),
            payload.get('source_id'),
            payload.get('customer_id', 1)  # Default to customer 1
        ))
        
        result = cur.fetchone()
        conn.commit()
        
        lead_id = result['id']
        logger.info(f"✓ Public lead {lead_id} created")
        
        return {"status": "success", "lead_id": lead_id}
        
    except Exception as e:
        logger.error(f"✗ Public webhook error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if 'conn' in locals():
            conn.close()

@app.get("/health")
async def health():
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT version()")
        result = cur.fetchone()
        conn.close()
        
        return {
            "status": "healthy",
            "service": "RevIntel",
            "database": "connected",
            "postgres": result['version'],
            "authentication": "enabled",
            "webhook_secret": WEBHOOK_SECRET[:8] + "..." # Show first 8 chars only
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}, 503

@app.get("/")
async def root():
    return {
        "service": "RevFlow RevIntel Webhook",
        "version": "2.0.0",
        "endpoints": {
            "/webhook/ingest": "Authenticated webhook (requires X-Webhook-Secret header)",
            "/webhook/public": "Public webhook (no auth)",
            "/health": "Health check"
        },
        "documentation": "/docs"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8160)
