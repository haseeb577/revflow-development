"""
RevPublish Backend API v2.0 - ENHANCED
Port 8550
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import content, deployment, templates
from routes.deployment_enhanced import router as deployment_enhanced_router

app = FastAPI(
    title="RevPublish API",
    version="2.0",
    description="Universal content deployment to WordPress with Elementor"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(content.router, prefix="/api/content", tags=["content"])
app.include_router(deployment.router, prefix="/api/deployment", tags=["deployment"])
app.include_router(deployment_enhanced_router, prefix="/api/deploy", tags=["deploy"])
app.include_router(templates.router, prefix="/api/templates", tags=["templates"])

@app.get("/")
async def root():
    return {
        "app": "RevPublish™ v2.0",
        "status": "operational",
        "backend_port": 8550,
        "frontend_port": 3550,
        "sources": ["RevRank Engine", "Google Docs", "Google Sheets", "CSV", "JSON"],
        "features": ["HTML → Elementor Conversion", "Multi-site Deployment", "53+ Sites Ready"],
        "architecture": "React + JSON Render"
    }

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "RevPublish Backend"}
