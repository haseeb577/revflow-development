from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import psycopg2
from psycopg2.extras import RealDictCursor
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="RevSEO Intelligence™ - Internal Linking (Sub 4a)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_CONFIG = {
    'host': 'localhost',
    'database': 'revflow',
    'user': os.getenv('POSTGRES_USER', 'postgres'),
    'password': os.getenv('POSTGRES_PASSWORD', '')
}

@app.get("/")
async def root():
    return {
        "service": "Internal Linking Engine",
        "sub_module": "4a",
        "parent": "Module 4 (RevSEO Intelligence™)",
        "status": "active"
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "internal-linking",
        "sub_module": "4a",
        "parent": "Module 4",
        "port": 8301,
        "features": [
            "Entity-based link suggestions",
            "Orphan page detection",
            "Link graph analysis"
        ]
    }

@app.get("/analyze/{site_id}")
async def analyze(site_id: int):
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT COUNT(*) as total FROM site_pages WHERE site_id = %s", (site_id,))
        result = cur.fetchone()
        cur.close()
        conn.close()
        return {"site_id": site_id, "total_pages": result['total'] if result else 0}
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
