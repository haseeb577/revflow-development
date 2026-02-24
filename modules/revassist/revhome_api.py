from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import datetime
import sys

# RevAudit Anti-Hallucination Integration
sys.path.insert(0, '/opt/shared-api-engine')
try:
    from revaudit.integrate import integrate_revaudit
    REVAUDIT_AVAILABLE = True
except ImportError:
    REVAUDIT_AVAILABLE = False

print("✅ Starting revhome_api.py")

app = FastAPI(title="RevHome Assessment Engine v2")

# RevAudit Integration
if REVAUDIT_AVAILABLE:
    integrate_revaudit(app, "RevAssist")

from app.health import router as health_router
app.include_router(health_router)

class AssessmentRequest(BaseModel):
    company_url: str
    anchor_city: str
    search_radius: int
    competitors: list[str]
    mode: str
    output_format: str

@app.get("/health")
async def health_check():
    return {"status": "ok", "message": "RevHome API running successfully"}

@app.post("/run-assessment")
async def run_assessment(request: AssessmentRequest):
    try:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        return {
            "status": "success",
            "timestamp": timestamp,
            "company_url": request.company_url,
            "anchor_city": request.anchor_city,
            "message": f"Assessment for {request.company_url} in {request.anchor_city} complete.",
            "output_files": {
                "xlsx": f"/outputs/{request.anchor_city}_Assessment_{timestamp}.xlsx",
                "pdf": f"/outputs/{request.anchor_city}_Assessment_{timestamp}.pdf"
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Assessment failed: {str(e)}")
# --- added to provide a friendly root for the API/landing ---
from fastapi.responses import PlainTextResponse
@app.get("/", response_class=PlainTextResponse)
def root():
    return "RevHome API — see /health or /docs"
# --- end added ---
