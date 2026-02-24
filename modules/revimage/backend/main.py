import os
import sys
import httpx
import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
from pydantic import BaseModel
from datetime import datetime

# RevAudit Anti-Hallucination Integration
sys.path.insert(0, '/opt/shared-api-engine')
try:
    from revaudit.integrate import integrate_revaudit
    REVAUDIT_AVAILABLE = True
except ImportError:
    REVAUDIT_AVAILABLE = False

app = FastAPI(title="RevImage™ API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# RevAudit Integration
if REVAUDIT_AVAILABLE:
    integrate_revaudit(app, "RevImage_Engine")

REVCORE_BASE = "http://localhost:8950"

def get_db():
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=os.getenv("POSTGRES_PORT", "5432"),
        database=os.getenv("POSTGRES_DB", "revflow"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD")
    )

class SiteCreate(BaseModel):
    site_id: str
    business_name: str
    business_type: str
    city: str
    state: str
    owner_visible: bool = False
    owner_ethnicity: Optional[str] = None
    owner_gender: Optional[str] = None

@app.get("/")
async def root():
    return {"service": "RevImage™ Backend API", "module": 8, "version": "1.0.0", "status": "operational"}

@app.get("/health")
async def health_check():
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.close()
        conn.close()
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"
    
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{REVCORE_BASE}/health")
            revcore_status = "healthy" if response.status_code == 200 else "degraded"
    except:
        revcore_status = "unavailable"
    
    return {
        "status": "healthy" if db_status == "healthy" else "degraded",
        "timestamp": datetime.now().isoformat(),
        "dependencies": {"database": db_status, "revcore": revcore_status}
    }

@app.post("/api/sites")
async def create_site(site: SiteCreate):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO revimage_sites 
            (site_id, business_name, business_type, city, state, owner_visible, owner_ethnicity, owner_gender)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
        """, (site.site_id, site.business_name, site.business_type, site.city, site.state, 
              site.owner_visible, site.owner_ethnicity, site.owner_gender))
        db_id = cursor.fetchone()[0]
        conn.commit()
        return {"success": True, "site_id": site.site_id, "database_id": db_id}
    except psycopg2.IntegrityError:
        conn.rollback()
        raise HTTPException(status_code=400, detail="Site ID already exists")
    finally:
        cursor.close()
        conn.close()

@app.get("/api/sites")
async def list_sites(status: Optional[str] = None):
    conn = get_db()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        if status:
            cursor.execute("SELECT * FROM revimage_sites WHERE status = %s ORDER BY created_at DESC", (status,))
        else:
            cursor.execute("SELECT * FROM revimage_sites ORDER BY created_at DESC")
        sites = cursor.fetchall()
        return {"success": True, "count": len(sites), "sites": [dict(s) for s in sites]}
    finally:
        cursor.close()
        conn.close()

@app.get("/api/sites/{site_id}")
async def get_site(site_id: str):
    conn = get_db()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cursor.execute("SELECT * FROM revimage_sites WHERE site_id = %s", (site_id,))
        site = cursor.fetchone()
        if not site:
            raise HTTPException(status_code=404, detail="Site not found")
        return {"success": True, "site": dict(site)}
    finally:
        cursor.close()
        conn.close()
