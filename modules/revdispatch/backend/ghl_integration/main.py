from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
import psycopg2
from psycopg2.extras import RealDictCursor
import httpx
import logging
import os
from typing import Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="RevFlow GHL Integration", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

GHL_CLIENT_ID = os.getenv('GHL_CLIENT_ID')
GHL_CLIENT_SECRET = os.getenv('GHL_CLIENT_SECRET')

def get_db():
    return psycopg2.connect(
        host="/var/run/postgresql",
        port="5432",
        user="revflow",
        database="revflow",
        cursor_factory=RealDictCursor
    )

@app.post("/dispatch/{lead_id}")
async def dispatch_to_ghl(lead_id: int):
    """
    Dispatch a lead to GoHighLevel
    """
    try:
        conn = get_db()
        cur = conn.cursor()
        
        # Get lead details
        cur.execute("SELECT * FROM leads WHERE id = %s", (lead_id,))
        lead = cur.fetchone()
        
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")
        
        # TODO: Implement actual GHL API call
        # This is a placeholder for the OAuth flow completion
        
        logger.info(f"✓ Lead {lead_id} ready for GHL dispatch")
        
        # Log dispatch attempt
        cur.execute("""
            INSERT INTO dispatch_logs (lead_id, destination, status, dispatched_at)
            VALUES (%s, %s, %s, NOW())
        """, (lead_id, 'ghl', 'pending'))
        conn.commit()
        
        return {
            "status": "pending",
            "lead_id": lead_id,
            "message": "Lead queued for GHL dispatch"
        }
        
    except Exception as e:
        logger.error(f"✗ Dispatch error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if 'conn' in locals():
            conn.close()

@app.get("/oauth/callback")
async def oauth_callback(code: str, location_id: str):
    """
    GHL OAuth callback handler
    """
    try:
        # Exchange code for access token
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://services.leadconnectorhq.com/oauth/token",
                data={
                    "client_id": GHL_CLIENT_ID,
                    "client_secret": GHL_CLIENT_SECRET,
                    "grant_type": "authorization_code",
                    "code": code
                }
            )
            
            if response.status_code == 200:
                token_data = response.json()
                
                # Store tokens in database
                conn = get_db()
                cur = conn.cursor()
                
                cur.execute("""
                    INSERT INTO customer_credentials (
                        customer_id, service, access_token, 
                        refresh_token, location_id, created_at
                    )
                    VALUES (%s, %s, %s, %s, %s, NOW())
                    ON CONFLICT (customer_id, service) 
                    DO UPDATE SET 
                        access_token = EXCLUDED.access_token,
                        refresh_token = EXCLUDED.refresh_token,
                        location_id = EXCLUDED.location_id
                """, (
                    1,  # Default customer
                    'ghl',
                    token_data.get('access_token'),
                    token_data.get('refresh_token'),
                    location_id
                ))
                conn.commit()
                
                logger.info(f"✓ GHL OAuth completed for location {location_id}")
                
                return {
                    "status": "success",
                    "message": "GoHighLevel connected successfully",
                    "location_id": location_id
                }
            else:
                raise HTTPException(status_code=400, detail="OAuth exchange failed")
                
    except Exception as e:
        logger.error(f"✗ OAuth error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if 'conn' in locals():
            conn.close()

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "GHL Integration",
        "client_id": GHL_CLIENT_ID[:8] + "..." if GHL_CLIENT_ID else "not configured"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8166)
