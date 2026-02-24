#!/usr/bin/env python3
"""
RevFlow OS Configuration Service
Serves frontend configuration from canonical .env file
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv
from pathlib import Path

app = FastAPI(title="RevFlow Config Service")

# Load canonical .env
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

# CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, use specific origins from .env
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)

@app.get("/config/frontend")
async def get_frontend_config():
    """
    Returns ONLY the frontend-safe configuration
    Filters out sensitive backend-only config
    """
    return {
        "apiBaseUrl": os.getenv("API_BASE_URL", "/api"),
        "schemaBaseUrl": os.getenv("SCHEMA_BASE_URL", "/schemas"),
        "environment": os.getenv("REVFLOW_ENV", "production"),
    }

@app.get("/health")
async def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8900)
