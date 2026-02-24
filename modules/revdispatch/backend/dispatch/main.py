"""
GHL Dispatcher - RevFlow Dispatch™
RevAudit: ENABLED
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
import sys

# RevAudit Anti-Hallucination Integration
sys.path.insert(0, '/opt/shared-api-engine')
try:
    from revaudit.integrate import integrate_revaudit
    REVAUDIT_AVAILABLE = True
except ImportError:
    REVAUDIT_AVAILABLE = False

app = FastAPI(title="GHL Dispatcher", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# RevAudit Integration
if REVAUDIT_AVAILABLE:
    integrate_revaudit(app, "RevDispatch")

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "ghl-dispatcher"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv('DISPATCH_PORT', 8165)))
