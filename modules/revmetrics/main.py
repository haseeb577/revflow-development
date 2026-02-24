"""
RevMetrics™ Main API
Module 10: RevMetrics™

FastAPI application with RevAttr™ attribution tracking
RevAudit: ENABLED
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import sys
import os

# Add api directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'api'))

# RevAudit Anti-Hallucination Integration
sys.path.insert(0, '/opt/shared-api-engine')
try:
    from revaudit.integrate import integrate_revaudit
    REVAUDIT_AVAILABLE = True
except ImportError:
    REVAUDIT_AVAILABLE = False

# Import attribution API
try:
    from api.attribution_api import router as attribution_router
    ATTRIBUTION_ENABLED = True
except ImportError:
    ATTRIBUTION_ENABLED = False
    print("Warning: Attribution API not available")

# Create FastAPI app
app = FastAPI(
    title="RevMetrics™ API",
    description="Analytics and Attribution Tracking",
    version="1.0.0"
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
    integrate_revaudit(app, "RevMetrics")

# Include attribution router if available
if ATTRIBUTION_ENABLED:
    app.include_router(attribution_router)
    print("✓ RevAttr™ Attribution API enabled")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "RevMetrics™",
        "attribution_enabled": ATTRIBUTION_ENABLED
    }

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "RevMetrics™ API",
        "version": "1.0.0",
        "attribution": "enabled" if ATTRIBUTION_ENABLED else "disabled",
        "docs": "/docs"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8401)
