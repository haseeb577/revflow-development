"""
Rank & Rent Decision Tool - Main API Application
Integrates with R&R/RevFlow platform
RevAudit: ENABLED
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
import json
import sys

# RevAudit Anti-Hallucination Integration
sys.path.insert(0, '/opt/shared-api-engine')
try:
    from revaudit.integrate import integrate_revaudit
    REVAUDIT_AVAILABLE = True
except ImportError:
    REVAUDIT_AVAILABLE = False

from services.scoring_engine import ScoringEngine
from services.market_discovery import MarketDiscoveryService
from services.whatif_analyzer import WhatIfAnalyzer
from api.local_signals_routes import router as local_signals_router
from models.schemas import (
    Site, SiteCreate, SiteScore, MarketOpportunity, 
    WhatIfScenario, WhatIfResult, PortfolioSummary,
    CategoryBenchmark, MarketSearchRequest, MarketSearchResult
)

app = FastAPI(
    title="Rank & Rent Decision Tool API",
    description="Decision support system for rank & rent portfolio management",
    version="1.0.0"
)

# CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for your R&R/RevFlow domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# RevAudit Integration
if REVAUDIT_AVAILABLE:
    integrate_revaudit(app, "RevRank_Engine")

# Initialize services
scoring_engine = ScoringEngine()
market_discovery = MarketDiscoveryService()
whatif_analyzer = WhatIfAnalyzer()

# Include routers
app.include_router(local_signals_router)

# =============================================================================
# PORTFOLIO MANAGEMENT ENDPOINTS
# =============================================================================

@app.get("/api/portfolio", response_model=PortfolioSummary)
async def get_portfolio_summary():
    """Get complete portfolio overview with tier distribution and recommendations"""
    return scoring_engine.get_portfolio_summary()

@app.get("/api/sites", response_model=List[Site])
async def get_all_sites(
    tier: Optional[str] = Query(None, description="Filter by tier: activate, watchlist, sunset"),
    category: Optional[str] = Query(None, description="Filter by category"),
    state: Optional[str] = Query(None, description="Filter by state"),
    sort_by: Optional[str] = Query("score", description="Sort by: score, potential, category"),
    order: Optional[str] = Query("desc", description="Order: asc, desc")
):
    """Get all sites with optional filtering and sorting"""
    return scoring_engine.get_sites(
        tier=tier, 
        category=category, 
        state=state,
        sort_by=sort_by,
        order=order
    )

@app.get("/api/sites/{site_id}", response_model=Site)
async def get_site(site_id: str):
    """Get detailed information for a specific site"""
    site = scoring_engine.get_site_by_id(site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    return site

@app.post("/api/sites", response_model=Site)
async def create_site(site: SiteCreate):
    """Add a new site to the portfolio"""
    return scoring_engine.create_site(site)

@app.put("/api/sites/{site_id}", response_model=Site)
async def update_site(site_id: str, site: SiteCreate):
    """Update an existing site"""
    updated = scoring_engine.update_site(site_id, site)
    if not updated:
        raise HTTPException(status_code=404, detail="Site not found")
    return updated

@app.delete("/api/sites/{site_id}")
async def delete_site(site_id: str):
    """Remove a site from the portfolio"""
    if not scoring_engine.delete_site(site_id):
        raise HTTPException(status_code=404, detail="Site not found")
    return {"status": "deleted", "site_id": site_id}

# =============================================================================
# SCORING ENDPOINTS
# =============================================================================

@app.post("/api/score", response_model=SiteScore)
async def score_site(site: SiteCreate):
    """Score a potential or existing site using the enhanced model"""
    return scoring_engine.calculate_score(site)

@app.post("/api/score/bulk", response_model=List[SiteScore])
async def score_bulk_sites(sites: List[SiteCreate]):
    """Score multiple sites at once"""
    return [scoring_engine.calculate_score(site) for site in sites]

@app.get("/api/score/criteria")
async def get_scoring_criteria():
    """Get the full scoring criteria with weights and descriptions"""
    return scoring_engine.get_criteria()

@app.put("/api/score/criteria")
async def update_scoring_criteria(criteria: Dict[str, float]):
    """Update scoring weights (for what-if analysis)"""
    return scoring_engine.update_criteria_weights(criteria)

# =============================================================================
# WHAT-IF ANALYSIS ENDPOINTS
# =============================================================================

@app.post("/api/whatif/scenario", response_model=WhatIfResult)
async def run_whatif_scenario(scenario: WhatIfScenario):
    """Run a what-if scenario analysis"""
    return whatif_analyzer.analyze_scenario(scenario)

@app.post("/api/whatif/weight-sensitivity")
async def analyze_weight_sensitivity(
    site_id: Optional[str] = None,
    criterion: str = Query(..., description="Criterion to analyze"),
    range_min: float = Query(0, description="Minimum weight to test"),
    range_max: float = Query(20, description="Maximum weight to test"),
    steps: int = Query(10, description="Number of steps to test")
):
    """Analyze how changing a specific weight affects scores"""
    return whatif_analyzer.weight_sensitivity_analysis(
        site_id=site_id,
        criterion=criterion,
        range_min=range_min,
        range_max=range_max,
        steps=steps
    )

@app.post("/api/whatif/tier-threshold")
async def analyze_tier_thresholds(
    activate_threshold: float = Query(3.7, description="Threshold for Activate tier"),
    watchlist_threshold: float = Query(3.2, description="Threshold for Watchlist tier")
):
    """Analyze impact of changing tier thresholds"""
    return whatif_analyzer.tier_threshold_analysis(
        activate_threshold=activate_threshold,
        watchlist_threshold=watchlist_threshold
    )

@app.post("/api/whatif/category-focus")
async def analyze_category_focus(categories: List[str]):
    """Analyze portfolio if focused only on specific categories"""
    return whatif_analyzer.category_focus_analysis(categories)

# =============================================================================
# MARKET DISCOVERY ENDPOINTS
# =============================================================================

@app.post("/api/discover/markets", response_model=List[MarketSearchResult])
async def discover_markets(request: MarketSearchRequest):
    """
    Discover new market opportunities based on criteria.
    Integrates with R&R competitive analysis.
    """
    return market_discovery.search_markets(request)

@app.get("/api/discover/categories")
async def get_category_recommendations():
    """Get recommended categories based on portfolio analysis"""
    return market_discovery.get_category_recommendations()

@app.get("/api/discover/locations")
async def get_location_recommendations(
    category: Optional[str] = Query(None, description="Category to find locations for"),
    state: Optional[str] = Query(None, description="Limit to specific state"),
    min_population: int = Query(50000, description="Minimum city population"),
    max_population: int = Query(250000, description="Maximum city population")
):
    """Get recommended locations for expansion"""
    return market_discovery.get_location_recommendations(
        category=category,
        state=state,
        min_population=min_population,
        max_population=max_population
    )

@app.post("/api/discover/evaluate-opportunity")
async def evaluate_opportunity(
    category: str = Query(..., description="Business category"),
    city: str = Query(..., description="City name"),
    state: str = Query(..., description="State code")
):
    """
    Evaluate a specific market opportunity.
    Pulls data from R&R/RevFlow for competitive analysis.
    """
    return market_discovery.evaluate_opportunity(category, city, state)

@app.get("/api/discover/hotspots")
async def get_market_hotspots(
    category: Optional[str] = None,
    limit: int = Query(20, description="Number of hotspots to return")
):
    """Get top market hotspots based on opportunity score"""
    return market_discovery.get_hotspots(category=category, limit=limit)

# =============================================================================
# CATEGORY BENCHMARKS ENDPOINTS
# =============================================================================

@app.get("/api/benchmarks/categories", response_model=List[CategoryBenchmark])
async def get_category_benchmarks():
    """Get all category benchmarks with industry data"""
    return scoring_engine.get_category_benchmarks()

@app.get("/api/benchmarks/categories/{category}")
async def get_category_benchmark(category: str):
    """Get benchmark data for a specific category"""
    benchmark = scoring_engine.get_category_benchmark(category)
    if not benchmark:
        raise HTTPException(status_code=404, detail="Category not found")
    return benchmark

# =============================================================================
# INTEGRATION ENDPOINTS (for R&R/RevFlow)
# =============================================================================

@app.post("/api/integrate/revflow/leads")
async def receive_revflow_leads(leads_data: Dict[str, Any]):
    """
    Receive lead data from RevFlow to update site performance metrics.
    Used to refine scoring based on actual performance.
    """
    return scoring_engine.update_from_revflow(leads_data)

@app.post("/api/integrate/rr/competitive")
async def receive_rr_competitive(competitive_data: Dict[str, Any]):
    """
    Receive competitive analysis from R&R app.
    Used to update SERP and competition scores.
    """
    return scoring_engine.update_from_rr_competitive(competitive_data)

@app.get("/api/integrate/export/{site_id}")
async def export_site_to_rr(site_id: str):
    """Export site data to R&R format for competitive analysis"""
    site = scoring_engine.get_site_by_id(site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    return scoring_engine.export_to_rr_format(site)

# =============================================================================
# REPORTING ENDPOINTS
# =============================================================================

@app.get("/api/reports/action-plan")
async def get_action_plan(days: int = Query(90, description="Action plan duration in days")):
    """Generate prioritized action plan"""
    return scoring_engine.generate_action_plan(days)

@app.get("/api/reports/revenue-projection")
async def get_revenue_projection(
    months: int = Query(12, description="Projection period in months"),
    success_rate: float = Query(0.6, description="Assumed success rate for Activate tier")
):
    """Project revenue based on current portfolio"""
    return scoring_engine.project_revenue(months, success_rate)

@app.get("/api/reports/category-analysis")
async def get_category_analysis():
    """Get detailed category performance analysis"""
    return scoring_engine.analyze_categories()

# =============================================================================
# HEALTH CHECK
# =============================================================================

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "rankrent-decision-tool",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
