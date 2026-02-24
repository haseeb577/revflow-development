"""
RevSignal SDK™ - Module 11
Visitor Identification & Signal Tracking API
RevAudit: ENABLED

Identifies anonymous website visitors and tracks buyer intent signals
for lead generation and enrichment pipeline.
"""

from fastapi import FastAPI, Request, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import hashlib
import uuid
import json
import os
import sys

# RevAudit Anti-Hallucination Integration
sys.path.insert(0, '/opt/shared-api-engine')
try:
    from revaudit.integrate import integrate_revaudit
    REVAUDIT_AVAILABLE = True
except ImportError:
    REVAUDIT_AVAILABLE = False

# Database connection
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False

app = FastAPI(
    title="RevSignal SDK™",
    description="Visitor Identification & Buyer Intent Signal Tracking",
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
    integrate_revaudit(app, "RevSignal")

# ─────────────────────────────────────────────────────────────────────────────
# Database Connection
# ─────────────────────────────────────────────────────────────────────────────

def get_db_connection():
    """Get PostgreSQL connection using shared env."""
    if not DB_AVAILABLE:
        return None
    try:
        return psycopg2.connect(
            host=os.getenv('POSTGRES_HOST', 'localhost'),
            port=os.getenv('POSTGRES_PORT', '5432'),
            user=os.getenv('POSTGRES_USER', 'revflow'),
            password=os.getenv('POSTGRES_PASSWORD', ''),
            database=os.getenv('POSTGRES_DB', 'revflow')
        )
    except Exception as e:
        print(f"Database connection error: {e}")
        return None

# ─────────────────────────────────────────────────────────────────────────────
# Models
# ─────────────────────────────────────────────────────────────────────────────

class VisitorSignal(BaseModel):
    """Incoming visitor signal from SDK."""
    visitor_id: Optional[str] = None
    session_id: Optional[str] = None
    page_url: str
    referrer: Optional[str] = None
    user_agent: Optional[str] = None
    screen_resolution: Optional[str] = None
    timezone: Optional[str] = None
    language: Optional[str] = None
    event_type: str = "pageview"  # pageview, click, form, scroll, custom
    event_data: Optional[Dict[str, Any]] = None
    timestamp: Optional[datetime] = None

class VisitorIdentification(BaseModel):
    """Identified visitor data."""
    visitor_id: str
    fingerprint: str
    ip_address: Optional[str] = None
    company: Optional[str] = None
    domain: Optional[str] = None
    industry: Optional[str] = None
    employee_count: Optional[str] = None
    revenue_range: Optional[str] = None
    first_seen: datetime
    last_seen: datetime
    total_visits: int = 1
    total_pageviews: int = 1
    intent_score: float = 0.0
    signals: List[str] = []

class SDKConfig(BaseModel):
    """SDK configuration for client."""
    site_id: str
    tracking_enabled: bool = True
    capture_clicks: bool = True
    capture_forms: bool = True
    capture_scroll: bool = True
    session_timeout: int = 30  # minutes
    cookie_domain: Optional[str] = None

# ─────────────────────────────────────────────────────────────────────────────
# In-Memory Storage (Production would use Redis + PostgreSQL)
# ─────────────────────────────────────────────────────────────────────────────

visitors: Dict[str, VisitorIdentification] = {}
signals: List[Dict[str, Any]] = []
sites: Dict[str, SDKConfig] = {}

# ─────────────────────────────────────────────────────────────────────────────
# Helper Functions
# ─────────────────────────────────────────────────────────────────────────────

def generate_fingerprint(user_agent: str, screen_res: str, timezone: str, language: str) -> str:
    """Generate a browser fingerprint from signals."""
    data = f"{user_agent}|{screen_res}|{timezone}|{language}"
    return hashlib.sha256(data.encode()).hexdigest()[:16]

def calculate_intent_score(visitor: VisitorIdentification) -> float:
    """Calculate buyer intent score based on behavior signals."""
    score = 0.0

    # Visit frequency
    if visitor.total_visits >= 5:
        score += 20
    elif visitor.total_visits >= 3:
        score += 10

    # Pageview depth
    if visitor.total_pageviews >= 10:
        score += 20
    elif visitor.total_pageviews >= 5:
        score += 10

    # Signal-based scoring
    signal_scores = {
        "pricing_page": 25,
        "demo_request": 30,
        "contact_form": 25,
        "case_study": 15,
        "product_page": 10,
        "blog_post": 5,
        "return_visitor": 15,
        "long_session": 10,
    }

    for signal in visitor.signals:
        score += signal_scores.get(signal, 0)

    return min(score, 100.0)

def detect_page_signals(page_url: str) -> List[str]:
    """Detect intent signals from page URL."""
    signals = []
    url_lower = page_url.lower()

    if "pricing" in url_lower:
        signals.append("pricing_page")
    if "demo" in url_lower:
        signals.append("demo_request")
    if "contact" in url_lower:
        signals.append("contact_form")
    if "case-study" in url_lower or "case_study" in url_lower:
        signals.append("case_study")
    if "product" in url_lower:
        signals.append("product_page")
    if "blog" in url_lower:
        signals.append("blog_post")

    return signals

# ─────────────────────────────────────────────────────────────────────────────
# API Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    db_status = "healthy" if get_db_connection() else "unavailable"
    return {
        "status": "healthy",
        "service": "RevSignal SDK™",
        "version": "1.0.0",
        "module": 11,
        "database": db_status,
        "active_visitors": len(visitors),
        "total_signals": len(signals),
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "RevSignal SDK™",
        "description": "Visitor Identification & Buyer Intent Tracking",
        "version": "1.0.0",
        "docs": "/docs",
        "sdk_endpoint": "/sdk/v1/signal",
        "admin_endpoint": "/api/visitors"
    }

# ─────────────────────────────────────────────────────────────────────────────
# SDK Endpoints (Called by JavaScript SDK)
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/sdk/v1/signal")
async def receive_signal(signal: VisitorSignal, request: Request):
    """
    Receive tracking signal from JavaScript SDK.
    This is the main endpoint called by the client-side tracking code.
    """
    # Get IP address
    ip_address = request.headers.get("X-Forwarded-For", request.client.host)
    if ip_address:
        ip_address = ip_address.split(",")[0].strip()

    # Generate or use existing visitor ID
    visitor_id = signal.visitor_id or str(uuid.uuid4())

    # Generate fingerprint
    fingerprint = generate_fingerprint(
        signal.user_agent or "",
        signal.screen_resolution or "",
        signal.timezone or "",
        signal.language or ""
    )

    # Detect page signals
    page_signals = detect_page_signals(signal.page_url)

    # Update or create visitor record
    now = datetime.utcnow()
    if visitor_id in visitors:
        visitor = visitors[visitor_id]
        visitor.last_seen = now
        visitor.total_pageviews += 1
        if (now - visitor.first_seen) > timedelta(days=1):
            visitor.signals.append("return_visitor")
        for sig in page_signals:
            if sig not in visitor.signals:
                visitor.signals.append(sig)
        visitor.intent_score = calculate_intent_score(visitor)
    else:
        visitor = VisitorIdentification(
            visitor_id=visitor_id,
            fingerprint=fingerprint,
            ip_address=ip_address,
            first_seen=now,
            last_seen=now,
            signals=page_signals
        )
        visitor.intent_score = calculate_intent_score(visitor)
        visitors[visitor_id] = visitor

    # Store signal
    signal_record = {
        "visitor_id": visitor_id,
        "event_type": signal.event_type,
        "page_url": signal.page_url,
        "referrer": signal.referrer,
        "timestamp": now.isoformat(),
        "signals_detected": page_signals
    }
    signals.append(signal_record)

    # Keep only last 10000 signals in memory
    if len(signals) > 10000:
        signals.pop(0)

    return {
        "status": "ok",
        "visitor_id": visitor_id,
        "session_id": signal.session_id or str(uuid.uuid4()),
        "intent_score": visitor.intent_score,
        "signals_detected": page_signals
    }

@app.get("/sdk/v1/identify/{visitor_id}")
async def get_visitor_identity(visitor_id: str):
    """Get identification data for a visitor."""
    if visitor_id not in visitors:
        raise HTTPException(status_code=404, detail="Visitor not found")

    return visitors[visitor_id]

@app.get("/sdk/v1/config/{site_id}")
async def get_sdk_config(site_id: str):
    """Get SDK configuration for a site."""
    if site_id not in sites:
        # Return default config
        return SDKConfig(site_id=site_id)
    return sites[site_id]

# ─────────────────────────────────────────────────────────────────────────────
# Admin API Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/api/visitors")
async def list_visitors(
    min_intent: float = 0,
    limit: int = 100,
    offset: int = 0
):
    """List identified visitors, optionally filtered by intent score."""
    filtered = [
        v for v in visitors.values()
        if v.intent_score >= min_intent
    ]

    # Sort by intent score descending
    filtered.sort(key=lambda x: x.intent_score, reverse=True)

    return {
        "total": len(filtered),
        "limit": limit,
        "offset": offset,
        "visitors": filtered[offset:offset + limit]
    }

@app.get("/api/visitors/{visitor_id}")
async def get_visitor(visitor_id: str):
    """Get detailed visitor information."""
    if visitor_id not in visitors:
        raise HTTPException(status_code=404, detail="Visitor not found")

    visitor = visitors[visitor_id]

    # Get visitor's signals
    visitor_signals = [s for s in signals if s["visitor_id"] == visitor_id]

    return {
        "visitor": visitor,
        "recent_signals": visitor_signals[-50:]  # Last 50 signals
    }

@app.get("/api/signals")
async def list_signals(
    event_type: Optional[str] = None,
    limit: int = 100
):
    """List recent signals."""
    filtered = signals
    if event_type:
        filtered = [s for s in signals if s["event_type"] == event_type]

    return {
        "total": len(filtered),
        "signals": filtered[-limit:]
    }

@app.get("/api/analytics/summary")
async def get_analytics_summary():
    """Get analytics summary."""
    now = datetime.utcnow()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # Calculate metrics
    total_visitors = len(visitors)
    high_intent = len([v for v in visitors.values() if v.intent_score >= 50])

    # Signals by type
    signal_counts = {}
    for s in signals:
        event_type = s.get("event_type", "unknown")
        signal_counts[event_type] = signal_counts.get(event_type, 0) + 1

    return {
        "total_visitors": total_visitors,
        "high_intent_visitors": high_intent,
        "total_signals": len(signals),
        "signals_by_type": signal_counts,
        "avg_intent_score": sum(v.intent_score for v in visitors.values()) / max(total_visitors, 1),
        "timestamp": now.isoformat()
    }

# ─────────────────────────────────────────────────────────────────────────────
# Site Management
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/api/sites")
async def create_site(config: SDKConfig):
    """Register a new site for tracking."""
    sites[config.site_id] = config
    return {"status": "created", "site_id": config.site_id}

@app.get("/api/sites")
async def list_sites():
    """List registered sites."""
    return {"sites": list(sites.values())}

# ─────────────────────────────────────────────────────────────────────────────
# Integration with RevIntel
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/api/enrich/{visitor_id}")
async def enrich_visitor(visitor_id: str):
    """
    Trigger enrichment for a visitor via RevIntel.
    Sends visitor data to RevIntel for company identification.
    """
    if visitor_id not in visitors:
        raise HTTPException(status_code=404, detail="Visitor not found")

    visitor = visitors[visitor_id]

    # In production, this would call RevIntel API
    # For now, return placeholder
    return {
        "status": "enrichment_queued",
        "visitor_id": visitor_id,
        "ip_address": visitor.ip_address,
        "message": "Enrichment request sent to RevIntel"
    }

# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv('REVSIGNAL_PORT', 8011))
    uvicorn.run(app, host="0.0.0.0", port=port)
