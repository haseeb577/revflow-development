"""
RevSPY™ Main API
Module 15: Blind Spot Research & Competitive Intelligence
RevAudit: ENABLED
"""

from fastapi import FastAPI
import sys

# RevAudit Anti-Hallucination Integration
sys.path.insert(0, '/opt/shared-api-engine')
try:
    from revaudit.integrate import integrate_revaudit
    REVAUDIT_AVAILABLE = True
except ImportError:
    REVAUDIT_AVAILABLE = False

from gbp_intelligence.api import router as gbp_router
from gbp_intelligence.reports_api import router as reports_router

app = FastAPI(
    title="RevSPY™ API",
    description="Competitive intelligence and blind spot research",
    version="2.0.0"
)

# RevAudit Integration
if REVAUDIT_AVAILABLE:
    integrate_revaudit(app, "RevSPY")

# Include routers
app.include_router(gbp_router)
app.include_router(reports_router)

@app.get("/")
async def root():
    return {
        "service": "RevSPY™",
        "version": "2.0.0",
        "modules": ["gbp_intelligence", "reports"],
        "status": "operational"
    }

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "RevSPY™",
        "modules": {
            "gbp_intelligence": "active",
            "reports": "active"
        }
    }
