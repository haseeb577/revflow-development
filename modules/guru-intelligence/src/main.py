"""Guru Intelligence Platform - Main API
RevAudit: ENABLED
"""
import sys
sys.path.insert(0, '/opt/guru-intelligence/src')
sys.path.insert(0, '/opt/shared-api-engine')

from dotenv import load_dotenv
load_dotenv('/opt/.env.master')

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
from datetime import datetime

# RevAudit Anti-Hallucination Integration
try:
    from revaudit.integrate import integrate_revaudit
    REVAUDIT_AVAILABLE = True
except ImportError:
    REVAUDIT_AVAILABLE = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/opt/guru-intelligence/logs/app.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Guru Intelligence Platform",
    version="1.0.0",
    description="Automated SEO rule discovery and validation"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# RevAudit Integration
if REVAUDIT_AVAILABLE:
    integrate_revaudit(app, "RevSEO_Intelligence")

# Import and register routes
from api import analyze_routes
app.include_router(analyze_routes.router, tags=["analyze"])

from api import approval_routes
app.include_router(approval_routes.router, prefix="/approval", tags=["approval"])

from api import rr_routes  
app.include_router(rr_routes.router, tags=["rr-integration"])
from api.unified_knowledge_routes import knowledge_router, prompts_router, scoring_router
app.include_router(knowledge_router)  # ADD THIS LINE
app.include_router(prompts_router)
app.include_router(scoring_router)

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Guru Intelligence Platform",
        "version": "1.0.0",
        "status": "operational"
    }

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "scheduler": "active"
    }


# Knowledge Graph API routes
# OLD - Replaced by unified_knowledge_routes
# from api import knowledge_routes
# app.include_router(knowledge_routes.router, prefix="/knowledge", tags=["knowledge"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8103)

