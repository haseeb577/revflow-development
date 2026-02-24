"""
Power Prompts API - FastAPI endpoints for RevPrompt Unified integration
RevAudit: ENABLED
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime
import os
import sys

from dotenv import load_dotenv
load_dotenv('/opt/shared-api-engine/.env')

# RevAudit Anti-Hallucination Integration
sys.path.insert(0, '/opt/shared-api-engine')
try:
    from revaudit.integrate import integrate_revaudit
    REVAUDIT_AVAILABLE = True
except ImportError:
    REVAUDIT_AVAILABLE = False

from power_prompts import (
    get_all_power_prompts, get_power_prompt, update_power_prompt,
    create_power_prompt, get_prompts_for_site, render_prompt,
    ensure_default_prompts
)

app = FastAPI(
    title="RevPrompt Unified - Power Prompts API",
    description="Manage AI visibility Power Prompts",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# RevAudit Integration
if REVAUDIT_AVAILABLE:
    integrate_revaudit(app, "RevPrompt_Unified")


# ─────────────────────────────────────────────────────────────────────────────
# Models
# ─────────────────────────────────────────────────────────────────────────────

class PowerPromptCreate(BaseModel):
    prompt_id: str
    name: str
    template: str
    description: str = ''
    purpose: str = ''
    tracks: List[str] = []
    required_vars: List[str] = []
    frequency: str = 'weekly'


class PowerPromptUpdate(BaseModel):
    template: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class RenderRequest(BaseModel):
    prompt_id: str
    variables: Dict[str, str]


class SiteConfig(BaseModel):
    service: str
    location: str
    client_name: str
    competitor_name: Optional[str] = None
    problem: Optional[str] = None
    use_case: Optional[str] = None


# ─────────────────────────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "RevPrompt Unified - Power Prompts",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/api/v1/power-prompts")
async def list_power_prompts(active_only: bool = Query(True)):
    """List all Power Prompts"""
    prompts = get_all_power_prompts(active_only=active_only)
    return {
        "count": len(prompts),
        "prompts": [
            {
                "prompt_id": p['prompt_id'],
                "name": p['name'],
                "template": p['template'],
                "description": p['description'],
                "purpose": p['purpose'],
                "tracks": p['tracks'],
                "required_vars": p['required_vars'],
                "frequency": p['frequency'],
                "is_active": p['is_active'],
                "version": p['version'],
                "updated_at": p['updated_at'].isoformat() if p['updated_at'] else None
            }
            for p in prompts
        ]
    }


@app.get("/api/v1/power-prompts/{prompt_id}")
async def get_single_prompt(prompt_id: str):
    """Get a specific Power Prompt"""
    prompt = get_power_prompt(prompt_id)
    if not prompt:
        raise HTTPException(status_code=404, detail="Power Prompt not found")
    return {
        "prompt_id": prompt['prompt_id'],
        "name": prompt['name'],
        "template": prompt['template'],
        "description": prompt['description'],
        "purpose": prompt['purpose'],
        "tracks": prompt['tracks'],
        "required_vars": prompt['required_vars'],
        "frequency": prompt['frequency'],
        "is_active": prompt['is_active'],
        "version": prompt['version']
    }


@app.post("/api/v1/power-prompts")
async def create_prompt(prompt: PowerPromptCreate):
    """Create a new Power Prompt"""
    success = create_power_prompt(
        prompt_id=prompt.prompt_id,
        name=prompt.name,
        template=prompt.template,
        description=prompt.description,
        purpose=prompt.purpose,
        tracks=prompt.tracks,
        required_vars=prompt.required_vars,
        frequency=prompt.frequency
    )
    if not success:
        raise HTTPException(status_code=500, detail="Failed to create Power Prompt")
    return {"status": "created", "prompt_id": prompt.prompt_id}


@app.patch("/api/v1/power-prompts/{prompt_id}")
async def update_prompt(prompt_id: str, update: PowerPromptUpdate):
    """Update a Power Prompt"""
    success = update_power_prompt(
        prompt_id=prompt_id,
        template=update.template,
        description=update.description,
        is_active=update.is_active
    )
    if not success:
        raise HTTPException(status_code=404, detail="Power Prompt not found or no changes made")
    return {"status": "updated", "prompt_id": prompt_id}


@app.post("/api/v1/power-prompts/render")
async def render_single_prompt(request: RenderRequest):
    """Render a Power Prompt with variables"""
    try:
        rendered = render_prompt(request.prompt_id, request.variables)
        return {
            "prompt_id": request.prompt_id,
            "rendered": rendered,
            "variables_used": request.variables
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/v1/power-prompts/for-site")
async def get_site_prompts(config: SiteConfig):
    """Get all applicable Power Prompts for a site"""
    site_config = config.dict()
    prompts = get_prompts_for_site(site_config)
    return {
        "site": config.client_name,
        "count": len(prompts),
        "prompts": prompts
    }


@app.on_event("startup")
async def startup_event():
    """Ensure default prompts exist on startup"""
    ensure_default_prompts()


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv('POWER_PROMPT_PORT', 8401))
    uvicorn.run(app, host="0.0.0.0", port=port)
