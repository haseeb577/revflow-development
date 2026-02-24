"""
RevSpend IQ™ - Module 16
Tech Spend Intelligence & Optimization API
RevAudit: ENABLED

Tracks, analyzes, and optimizes technology spending across
SaaS subscriptions, tools, and infrastructure.
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, date, timedelta
from enum import Enum
import uuid
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
    title="RevSpend IQ™",
    description="Tech Spend Intelligence & Optimization Platform",
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
    integrate_revaudit(app, "RevSpend")

# ─────────────────────────────────────────────────────────────────────────────
# Enums and Models
# ─────────────────────────────────────────────────────────────────────────────

class SpendCategory(str, Enum):
    SAAS = "saas"
    INFRASTRUCTURE = "infrastructure"
    DEVELOPMENT = "development"
    MARKETING = "marketing"
    ANALYTICS = "analytics"
    SECURITY = "security"
    COMMUNICATION = "communication"
    PRODUCTIVITY = "productivity"
    AI_ML = "ai_ml"
    OTHER = "other"

class BillingCycle(str, Enum):
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"
    ONE_TIME = "one_time"

class UsageLevel(str, Enum):
    HIGH = "high"          # >70% utilization
    MEDIUM = "medium"      # 30-70% utilization
    LOW = "low"            # <30% utilization
    UNKNOWN = "unknown"

class Subscription(BaseModel):
    """Tech subscription/tool record."""
    id: Optional[str] = None
    name: str
    vendor: str
    category: SpendCategory
    description: Optional[str] = None
    monthly_cost: float
    billing_cycle: BillingCycle = BillingCycle.MONTHLY
    contract_start: Optional[date] = None
    contract_end: Optional[date] = None
    renewal_date: Optional[date] = None
    auto_renew: bool = True
    seats_purchased: Optional[int] = None
    seats_used: Optional[int] = None
    usage_level: UsageLevel = UsageLevel.UNKNOWN
    owner: Optional[str] = None
    department: Optional[str] = None
    tags: List[str] = []
    integrations: List[str] = []
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class SpendAlert(BaseModel):
    """Spend optimization alert."""
    id: str
    subscription_id: str
    alert_type: str  # underutilized, renewal_upcoming, price_increase, duplicate
    severity: str    # high, medium, low
    title: str
    description: str
    potential_savings: Optional[float] = None
    recommendation: str
    created_at: datetime
    acknowledged: bool = False

class SpendSummary(BaseModel):
    """Monthly spend summary."""
    total_monthly_spend: float
    total_annual_spend: float
    subscription_count: int
    category_breakdown: Dict[str, float]
    underutilized_spend: float
    upcoming_renewals: int
    potential_savings: float

# ─────────────────────────────────────────────────────────────────────────────
# In-Memory Storage (Production would use PostgreSQL)
# ─────────────────────────────────────────────────────────────────────────────

subscriptions: Dict[str, Subscription] = {}
alerts: List[SpendAlert] = []

# Pre-populate with sample data
def init_sample_data():
    samples = [
        Subscription(
            id="sub_001",
            name="Anthropic API",
            vendor="Anthropic",
            category=SpendCategory.AI_ML,
            description="Claude API for AI-powered features",
            monthly_cost=500.00,
            billing_cycle=BillingCycle.MONTHLY,
            usage_level=UsageLevel.HIGH,
            owner="Engineering",
            tags=["ai", "core", "production"]
        ),
        Subscription(
            id="sub_002",
            name="AWS",
            vendor="Amazon",
            category=SpendCategory.INFRASTRUCTURE,
            description="Cloud infrastructure hosting",
            monthly_cost=2500.00,
            billing_cycle=BillingCycle.MONTHLY,
            usage_level=UsageLevel.MEDIUM,
            owner="DevOps",
            tags=["infrastructure", "core", "production"]
        ),
        Subscription(
            id="sub_003",
            name="DataForSEO",
            vendor="DataForSEO",
            category=SpendCategory.ANALYTICS,
            description="SEO and SERP data API",
            monthly_cost=299.00,
            billing_cycle=BillingCycle.MONTHLY,
            usage_level=UsageLevel.HIGH,
            owner="SEO Team",
            tags=["seo", "data", "api"]
        ),
        Subscription(
            id="sub_004",
            name="Slack",
            vendor="Salesforce",
            category=SpendCategory.COMMUNICATION,
            description="Team communication",
            monthly_cost=12.50,
            billing_cycle=BillingCycle.MONTHLY,
            seats_purchased=50,
            seats_used=35,
            usage_level=UsageLevel.MEDIUM,
            owner="Operations",
            tags=["communication", "team"]
        ),
        Subscription(
            id="sub_005",
            name="HubSpot",
            vendor="HubSpot",
            category=SpendCategory.MARKETING,
            description="CRM and marketing automation",
            monthly_cost=890.00,
            billing_cycle=BillingCycle.MONTHLY,
            seats_purchased=10,
            seats_used=4,
            usage_level=UsageLevel.LOW,
            owner="Marketing",
            tags=["crm", "marketing", "automation"]
        ),
        Subscription(
            id="sub_006",
            name="GitHub Enterprise",
            vendor="Microsoft",
            category=SpendCategory.DEVELOPMENT,
            description="Code repository and CI/CD",
            monthly_cost=21.00,
            billing_cycle=BillingCycle.MONTHLY,
            seats_purchased=25,
            seats_used=22,
            usage_level=UsageLevel.HIGH,
            owner="Engineering",
            tags=["development", "git", "ci-cd"]
        ),
    ]

    for sub in samples:
        sub.created_at = datetime.utcnow()
        sub.updated_at = datetime.utcnow()
        subscriptions[sub.id] = sub

    # Generate alerts for underutilized subscriptions
    generate_alerts()

def generate_alerts():
    """Generate optimization alerts based on subscription data."""
    alerts.clear()

    for sub_id, sub in subscriptions.items():
        # Underutilization alert
        if sub.usage_level == UsageLevel.LOW:
            potential_savings = sub.monthly_cost * 0.5  # Assume 50% savings possible
            alerts.append(SpendAlert(
                id=f"alert_{uuid.uuid4().hex[:8]}",
                subscription_id=sub_id,
                alert_type="underutilized",
                severity="high",
                title=f"Low utilization: {sub.name}",
                description=f"{sub.name} shows low usage ({sub.usage_level.value}). Consider downgrading or consolidating.",
                potential_savings=potential_savings,
                recommendation=f"Review {sub.name} usage and consider downgrading to a lower tier or consolidating with similar tools.",
                created_at=datetime.utcnow()
            ))

        # Seat optimization alert
        if sub.seats_purchased and sub.seats_used:
            utilization = sub.seats_used / sub.seats_purchased
            if utilization < 0.7:
                unused_seats = sub.seats_purchased - sub.seats_used
                per_seat_cost = sub.monthly_cost / sub.seats_purchased
                potential_savings = unused_seats * per_seat_cost
                alerts.append(SpendAlert(
                    id=f"alert_{uuid.uuid4().hex[:8]}",
                    subscription_id=sub_id,
                    alert_type="unused_seats",
                    severity="medium",
                    title=f"Unused seats: {sub.name}",
                    description=f"{unused_seats} of {sub.seats_purchased} seats unused in {sub.name}.",
                    potential_savings=potential_savings,
                    recommendation=f"Reduce seat count from {sub.seats_purchased} to {sub.seats_used + 5} (with buffer).",
                    created_at=datetime.utcnow()
                ))

        # Renewal alert (simulate upcoming renewal)
        if sub.renewal_date and sub.renewal_date <= date.today() + timedelta(days=30):
            alerts.append(SpendAlert(
                id=f"alert_{uuid.uuid4().hex[:8]}",
                subscription_id=sub_id,
                alert_type="renewal_upcoming",
                severity="medium",
                title=f"Renewal upcoming: {sub.name}",
                description=f"{sub.name} renews on {sub.renewal_date}. Review before auto-renewal.",
                potential_savings=None,
                recommendation="Review contract terms and negotiate better rates before renewal.",
                created_at=datetime.utcnow()
            ))

# Initialize sample data on startup
init_sample_data()

# ─────────────────────────────────────────────────────────────────────────────
# API Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "RevSpend IQ™",
        "version": "1.0.0",
        "module": 16,
        "subscriptions_tracked": len(subscriptions),
        "active_alerts": len([a for a in alerts if not a.acknowledged]),
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "RevSpend IQ™",
        "description": "Tech Spend Intelligence & Optimization",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "subscriptions": "/api/subscriptions",
            "alerts": "/api/alerts",
            "summary": "/api/summary",
            "optimize": "/api/optimize"
        }
    }

# ─────────────────────────────────────────────────────────────────────────────
# Subscription Management
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/api/subscriptions")
async def list_subscriptions(
    category: Optional[SpendCategory] = None,
    usage_level: Optional[UsageLevel] = None,
    min_cost: Optional[float] = None,
    max_cost: Optional[float] = None
):
    """List all tracked subscriptions with optional filtering."""
    result = list(subscriptions.values())

    if category:
        result = [s for s in result if s.category == category]
    if usage_level:
        result = [s for s in result if s.usage_level == usage_level]
    if min_cost is not None:
        result = [s for s in result if s.monthly_cost >= min_cost]
    if max_cost is not None:
        result = [s for s in result if s.monthly_cost <= max_cost]

    # Sort by monthly cost descending
    result.sort(key=lambda x: x.monthly_cost, reverse=True)

    return {
        "total": len(result),
        "subscriptions": result
    }

@app.post("/api/subscriptions")
async def create_subscription(subscription: Subscription):
    """Add a new subscription to track."""
    subscription.id = subscription.id or f"sub_{uuid.uuid4().hex[:8]}"
    subscription.created_at = datetime.utcnow()
    subscription.updated_at = datetime.utcnow()

    subscriptions[subscription.id] = subscription

    # Regenerate alerts
    generate_alerts()

    return {"status": "created", "subscription": subscription}

@app.get("/api/subscriptions/{subscription_id}")
async def get_subscription(subscription_id: str):
    """Get details of a specific subscription."""
    if subscription_id not in subscriptions:
        raise HTTPException(status_code=404, detail="Subscription not found")
    return subscriptions[subscription_id]

@app.put("/api/subscriptions/{subscription_id}")
async def update_subscription(subscription_id: str, subscription: Subscription):
    """Update a subscription."""
    if subscription_id not in subscriptions:
        raise HTTPException(status_code=404, detail="Subscription not found")

    subscription.id = subscription_id
    subscription.updated_at = datetime.utcnow()
    subscription.created_at = subscriptions[subscription_id].created_at
    subscriptions[subscription_id] = subscription

    # Regenerate alerts
    generate_alerts()

    return {"status": "updated", "subscription": subscription}

@app.delete("/api/subscriptions/{subscription_id}")
async def delete_subscription(subscription_id: str):
    """Remove a subscription from tracking."""
    if subscription_id not in subscriptions:
        raise HTTPException(status_code=404, detail="Subscription not found")

    del subscriptions[subscription_id]

    # Regenerate alerts
    generate_alerts()

    return {"status": "deleted", "subscription_id": subscription_id}

# ─────────────────────────────────────────────────────────────────────────────
# Spend Analysis
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/api/summary")
async def get_spend_summary():
    """Get overall spend summary and analytics."""
    total_monthly = sum(s.monthly_cost for s in subscriptions.values())

    # Calculate annual spend based on billing cycles
    total_annual = 0
    for s in subscriptions.values():
        if s.billing_cycle == BillingCycle.MONTHLY:
            total_annual += s.monthly_cost * 12
        elif s.billing_cycle == BillingCycle.QUARTERLY:
            total_annual += s.monthly_cost * 4
        elif s.billing_cycle == BillingCycle.ANNUAL:
            total_annual += s.monthly_cost
        else:
            total_annual += s.monthly_cost

    # Category breakdown
    category_breakdown = {}
    for s in subscriptions.values():
        cat = s.category.value
        category_breakdown[cat] = category_breakdown.get(cat, 0) + s.monthly_cost

    # Underutilized spend
    underutilized = sum(
        s.monthly_cost for s in subscriptions.values()
        if s.usage_level == UsageLevel.LOW
    )

    # Upcoming renewals (next 30 days)
    upcoming = len([
        s for s in subscriptions.values()
        if s.renewal_date and s.renewal_date <= date.today() + timedelta(days=30)
    ])

    # Potential savings from alerts
    potential_savings = sum(
        a.potential_savings for a in alerts
        if a.potential_savings and not a.acknowledged
    )

    return SpendSummary(
        total_monthly_spend=total_monthly,
        total_annual_spend=total_annual,
        subscription_count=len(subscriptions),
        category_breakdown=category_breakdown,
        underutilized_spend=underutilized,
        upcoming_renewals=upcoming,
        potential_savings=potential_savings
    )

@app.get("/api/analytics/by-category")
async def analytics_by_category():
    """Get spend breakdown by category."""
    breakdown = {}
    for s in subscriptions.values():
        cat = s.category.value
        if cat not in breakdown:
            breakdown[cat] = {
                "category": cat,
                "total_monthly": 0,
                "subscription_count": 0,
                "subscriptions": []
            }
        breakdown[cat]["total_monthly"] += s.monthly_cost
        breakdown[cat]["subscription_count"] += 1
        breakdown[cat]["subscriptions"].append({
            "name": s.name,
            "cost": s.monthly_cost,
            "usage": s.usage_level.value
        })

    # Sort by total spend
    result = sorted(breakdown.values(), key=lambda x: x["total_monthly"], reverse=True)

    return {"categories": result}

@app.get("/api/analytics/by-vendor")
async def analytics_by_vendor():
    """Get spend breakdown by vendor."""
    breakdown = {}
    for s in subscriptions.values():
        vendor = s.vendor
        if vendor not in breakdown:
            breakdown[vendor] = {
                "vendor": vendor,
                "total_monthly": 0,
                "subscription_count": 0,
                "products": []
            }
        breakdown[vendor]["total_monthly"] += s.monthly_cost
        breakdown[vendor]["subscription_count"] += 1
        breakdown[vendor]["products"].append(s.name)

    result = sorted(breakdown.values(), key=lambda x: x["total_monthly"], reverse=True)

    return {"vendors": result}

@app.get("/api/analytics/trends")
async def get_spend_trends():
    """Get spend trends (simulated for demo)."""
    # In production, this would pull from historical data
    current_month = datetime.utcnow().month
    months = []

    base_spend = sum(s.monthly_cost for s in subscriptions.values())

    for i in range(6):
        month_num = ((current_month - 6 + i) % 12) + 1
        # Simulate slight variations
        variation = 1 + (i * 0.02)  # 2% growth per month
        months.append({
            "month": month_num,
            "spend": round(base_spend * variation, 2)
        })

    return {
        "trend": "increasing",
        "growth_rate": "2%",
        "monthly_data": months
    }

# ─────────────────────────────────────────────────────────────────────────────
# Alerts & Optimization
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/api/alerts")
async def list_alerts(
    severity: Optional[str] = None,
    alert_type: Optional[str] = None,
    acknowledged: Optional[bool] = None
):
    """List spend optimization alerts."""
    result = alerts.copy()

    if severity:
        result = [a for a in result if a.severity == severity]
    if alert_type:
        result = [a for a in result if a.alert_type == alert_type]
    if acknowledged is not None:
        result = [a for a in result if a.acknowledged == acknowledged]

    # Sort by severity (high first) then by potential savings
    severity_order = {"high": 0, "medium": 1, "low": 2}
    result.sort(key=lambda x: (severity_order.get(x.severity, 3), -(x.potential_savings or 0)))

    return {
        "total": len(result),
        "unacknowledged": len([a for a in result if not a.acknowledged]),
        "total_potential_savings": sum(a.potential_savings or 0 for a in result if not a.acknowledged),
        "alerts": result
    }

@app.post("/api/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str):
    """Acknowledge an alert."""
    for alert in alerts:
        if alert.id == alert_id:
            alert.acknowledged = True
            return {"status": "acknowledged", "alert_id": alert_id}

    raise HTTPException(status_code=404, detail="Alert not found")

@app.get("/api/optimize")
async def get_optimization_recommendations():
    """Get comprehensive optimization recommendations."""
    recommendations = []

    # Analyze underutilized subscriptions
    underutilized = [s for s in subscriptions.values() if s.usage_level == UsageLevel.LOW]
    if underutilized:
        total_waste = sum(s.monthly_cost for s in underutilized)
        recommendations.append({
            "category": "Underutilized Tools",
            "priority": "high",
            "potential_savings": total_waste * 0.5,
            "description": f"{len(underutilized)} tools with low utilization",
            "action": "Review and consider downgrading or canceling",
            "affected_subscriptions": [s.name for s in underutilized]
        })

    # Analyze seat optimization
    seat_waste = 0
    seat_subs = []
    for s in subscriptions.values():
        if s.seats_purchased and s.seats_used and s.seats_used < s.seats_purchased * 0.7:
            unused = s.seats_purchased - s.seats_used
            per_seat = s.monthly_cost / s.seats_purchased
            seat_waste += unused * per_seat
            seat_subs.append(s.name)

    if seat_subs:
        recommendations.append({
            "category": "Unused Seats",
            "priority": "medium",
            "potential_savings": seat_waste,
            "description": f"{len(seat_subs)} subscriptions with unused seats",
            "action": "Reduce seat counts to match actual usage",
            "affected_subscriptions": seat_subs
        })

    # Consolidation opportunities
    category_counts = {}
    for s in subscriptions.values():
        cat = s.category.value
        category_counts[cat] = category_counts.get(cat, 0) + 1

    duplicates = [cat for cat, count in category_counts.items() if count >= 2]
    if duplicates:
        recommendations.append({
            "category": "Consolidation Opportunities",
            "priority": "medium",
            "potential_savings": None,
            "description": f"Multiple tools in same category: {', '.join(duplicates)}",
            "action": "Review for potential consolidation",
            "affected_categories": duplicates
        })

    # Calculate total savings
    total_savings = sum(r.get("potential_savings", 0) or 0 for r in recommendations)

    return {
        "total_potential_monthly_savings": total_savings,
        "total_potential_annual_savings": total_savings * 12,
        "recommendation_count": len(recommendations),
        "recommendations": recommendations
    }

# ─────────────────────────────────────────────────────────────────────────────
# ROI Tracking
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/api/roi/calculate")
async def calculate_roi(
    subscription_id: str,
    revenue_attributed: float = Query(..., description="Revenue attributed to this tool"),
    time_saved_hours: float = Query(0, description="Hours saved per month"),
    hourly_rate: float = Query(50, description="Hourly rate for time savings calculation")
):
    """Calculate ROI for a specific subscription."""
    if subscription_id not in subscriptions:
        raise HTTPException(status_code=404, detail="Subscription not found")

    sub = subscriptions[subscription_id]
    monthly_cost = sub.monthly_cost

    # Calculate time savings value
    time_savings_value = time_saved_hours * hourly_rate

    # Total value generated
    total_value = revenue_attributed + time_savings_value

    # ROI calculation
    roi_percentage = ((total_value - monthly_cost) / monthly_cost) * 100 if monthly_cost > 0 else 0

    return {
        "subscription": sub.name,
        "monthly_cost": monthly_cost,
        "revenue_attributed": revenue_attributed,
        "time_savings_value": time_savings_value,
        "total_value_generated": total_value,
        "net_value": total_value - monthly_cost,
        "roi_percentage": round(roi_percentage, 2),
        "recommendation": "Keep" if roi_percentage > 100 else "Review" if roi_percentage > 0 else "Consider canceling"
    }

# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv('REVSPEND_PORT', 8016))
    uvicorn.run(app, host="0.0.0.0", port=port)
