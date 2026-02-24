"""
╔══════════════════════════════════════════════════════════════════════════════╗
║          RANK & RENT DECISION TOOL - ENHANCED MAIN APPLICATION              ║
║          With Niche Finder Pro Features Integrated                           ║
╚══════════════════════════════════════════════════════════════════════════════╝

Version: 2.0.0
Integration: R&R Automation + RevFlow + Niche Finder Pro Style Features
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime

# =============================================================================
# APPLICATION SETUP
# =============================================================================

app = FastAPI(
    title="Rank & Rent Decision Tool API",
    description="""
    ## SmarketSherpa Portfolio Intelligence Platform
    
    Complete decision-making tool for rank & rent operations with:
    
    ### Core Features
    - **Portfolio Management** - Track and score your 53+ sites
    - **Scoring Engine** - Enhanced 16-criteria model with category benchmarks
    - **Market Discovery** - Find new opportunities in Sun Belt markets
    - **What-If Analysis** - Test scenarios before making decisions
    
    ### Niche Finder Pro Features
    - **Turbo Search** - Rapid multi-city opportunity scanning
    - **SERP Analysis** - Dedicated site counts, weak competitor detection
    - **No Website Finder** - Find businesses ranking without websites
    - **Bookmarks & Tags** - Save and organize opportunities
    - **VA Workflow** - Assign and track research tasks
    - **Export** - CSV, JSON, and due diligence reports
    
    ### Integration
    - R&R Automation (Content Generation)
    - RevFlow Assessment Engine (Competitive Analysis)
    """,
    version="2.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production: specify your domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================================================================
# IMPORT AND INCLUDE ROUTERS
# =============================================================================

# Import the NFP routes
from api.nfp_routes import router as nfp_router

# Include the router
app.include_router(nfp_router)

# =============================================================================
# IMPORT SERVICES FOR CORE ROUTES
# =============================================================================

from services.scoring_engine import scoring_engine, SCORING_CRITERIA, CATEGORY_BENCHMARKS
from services.market_discovery_engine import market_discovery
from services.whatif_analyzer import whatif_analyzer

# =============================================================================
# HEALTH & INFO ENDPOINTS
# =============================================================================

@app.get("/", tags=["Info"])
async def root():
    """API root - welcome and links"""
    return {
        "name": "Rank & Rent Decision Tool API",
        "version": "2.0.0",
        "description": "Portfolio intelligence platform with Niche Finder Pro features",
        "documentation": "/api/docs",
        "health": "/health",
        "features": [
            "Portfolio Management",
            "16-Criteria Scoring Engine",
            "Market Discovery (Turbo Search)",
            "SERP Analysis",
            "Bookmarks & Tagging",
            "VA Workflow Support",
            "What-If Analysis",
            "R&R/RevFlow Integration"
        ]
    }

@app.get("/health", tags=["Info"])
async def health_check():
    """API health check"""
    from services.bookmarks_manager import bookmarks_manager
    
    return {
        "status": "healthy",
        "service": "rankrent-decision-tool",
        "version": "2.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "components": {
            "scoring_engine": "operational",
            "market_discovery": "operational",
            "serp_analyzer": "operational",
            "bookmarks_manager": "operational",
            "whatif_analyzer": "operational"
        },
        "stats": {
            "portfolio_sites": len(scoring_engine.portfolio),
            "categories": len(CATEGORY_BENCHMARKS),
            "saved_bookmarks": len(bookmarks_manager.bookmarks)
        }
    }

# =============================================================================
# PORTFOLIO ENDPOINTS
# =============================================================================

@app.get("/api/portfolio", tags=["Portfolio"])
async def get_portfolio_summary():
    """Get complete portfolio overview with tier distribution and recommendations"""
    return scoring_engine.get_portfolio_summary()

@app.get("/api/portfolio/sites", tags=["Portfolio"])
async def get_portfolio_sites(
    tier: str = None,
    category: str = None,
    state: str = None,
    sort_by: str = "score",
    order: str = "desc"
):
    """Get all portfolio sites with filtering"""
    result = scoring_engine.portfolio.copy()
    
    if tier:
        result = [s for s in result if s["tier"] == tier.lower()]
    if category:
        result = [s for s in result if s["category"].lower() == category.lower()]
    if state:
        result = [s for s in result if s["state"].upper() == state.upper()]
    
    reverse = order.lower() == "desc"
    if sort_by == "score":
        result = sorted(result, key=lambda x: x["score"], reverse=reverse)
    elif sort_by == "potential":
        result = sorted(result, key=lambda x: x["monthly_potential"], reverse=reverse)
    
    return {"sites": result, "total": len(result)}

@app.get("/api/portfolio/sites/{site_id}", tags=["Portfolio"])
async def get_portfolio_site(site_id: str):
    """Get details for a specific site"""
    site = next((s for s in scoring_engine.portfolio if s["id"] == site_id), None)
    if not site:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Site not found")
    return site

# =============================================================================
# SCORING ENDPOINTS
# =============================================================================

@app.get("/api/scoring/criteria", tags=["Scoring"])
async def get_scoring_criteria():
    """Get all scoring criteria with weights and descriptions"""
    return {
        "criteria": SCORING_CRITERIA,
        "total_weight": sum(c["weight"] for c in SCORING_CRITERIA.values())
    }

@app.post("/api/scoring/calculate", tags=["Scoring"])
async def calculate_score(site_data: dict):
    """Calculate score for a potential opportunity"""
    return scoring_engine.calculate_score(site_data)

# =============================================================================
# BENCHMARKS ENDPOINTS
# =============================================================================

@app.get("/api/benchmarks", tags=["Benchmarks"])
async def get_all_benchmarks():
    """Get all category benchmarks with success factors"""
    result = []
    for category, data in CATEGORY_BENCHMARKS.items():
        result.append({
            "category": category,
            **data
        })
    return {"benchmarks": sorted(result, key=lambda x: x["category_tier"])}

@app.get("/api/benchmarks/{category}", tags=["Benchmarks"])
async def get_category_benchmark(category: str):
    """Get benchmark for a specific category"""
    if category not in CATEGORY_BENCHMARKS:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Category not found")
    return {"category": category, **CATEGORY_BENCHMARKS[category]}

@app.get("/api/benchmarks/tiers/summary", tags=["Benchmarks"])
async def get_tier_summary():
    """Get categories organized by tier"""
    tiers = {1: [], 2: [], 3: [], 4: [], 5: []}
    for cat, data in CATEGORY_BENCHMARKS.items():
        tier = data.get("category_tier", 5)
        tiers[tier].append({
            "category": cat,
            "monthly_potential": data.get("monthly_potential", 0),
            "avg_job_value": data.get("avg_job_value", 0),
            "recommended_action": data.get("recommended_action", "EVALUATE")
        })
    
    return {
        "tier_1_expand": tiers[1],
        "tier_2_maintain": tiers[2],
        "tier_3_selective": tiers[3],
        "tier_4_reduce": tiers[4],
        "tier_5_avoid": tiers[5]
    }

# =============================================================================
# MARKET DISCOVERY ENDPOINTS
# =============================================================================

@app.get("/api/discover/hotspots", tags=["Market Discovery"])
async def get_market_hotspots(
    category: str = None,
    limit: int = 20
):
    """Get top market hotspots based on opportunity scoring"""
    return {
        "hotspots": market_discovery.get_hotspots(category=category, limit=limit)
    }

@app.get("/api/discover/categories", tags=["Market Discovery"])
async def get_category_recommendations():
    """Get category recommendations based on R&R success factors"""
    return market_discovery.get_category_recommendations()

@app.post("/api/discover/search", tags=["Market Discovery"])
async def search_markets(request: dict):
    """Search for market opportunities with filters"""
    from services.market_discovery_engine import MarketSearchRequest
    
    search_request = MarketSearchRequest(**request)
    results = market_discovery.search_opportunities(search_request)
    
    return {
        "results": results,
        "total": len(results)
    }

# =============================================================================
# WHAT-IF ANALYSIS ENDPOINTS
# =============================================================================

@app.post("/api/whatif/threshold", tags=["What-If Analysis"])
async def analyze_threshold_change(
    activate_threshold: float = 3.7,
    watchlist_threshold: float = 3.2
):
    """Analyze impact of changing tier thresholds"""
    return whatif_analyzer.analyze_threshold_change({
        "activate_threshold": activate_threshold,
        "watchlist_threshold": watchlist_threshold
    })

@app.post("/api/whatif/category-focus", tags=["What-If Analysis"])
async def analyze_category_focus(categories: list):
    """Analyze portfolio focused on specific categories"""
    return whatif_analyzer.analyze_category_focus({"categories": categories})

@app.post("/api/whatif/weight-sensitivity", tags=["What-If Analysis"])
async def analyze_weight_sensitivity(
    criterion: str,
    weight_range: list = [5, 20]
):
    """Analyze sensitivity to a specific criterion weight"""
    return whatif_analyzer.analyze_weight_sensitivity({
        "criterion": criterion,
        "weight_range": weight_range
    })

# =============================================================================
# INTEGRATION ENDPOINTS (R&R / RevFlow)
# =============================================================================

@app.post("/api/integrate/revflow/analyze", tags=["Integration"])
async def trigger_revflow_analysis(
    category: str,
    city: str,
    state: str
):
    """
    Trigger RevFlow competitive analysis for a market.
    
    In production: Would call RevFlow API endpoint /api/revflow/assess
    """
    return {
        "status": "analysis_queued",
        "integration": "RevFlow Assessment Engine",
        "target": {"category": category, "city": city, "state": state},
        "modules": ["A", "B", "C", "D", "E", "E1", "E2"],
        "note": "Connect to RevFlow API for full 7-module assessment"
    }

@app.post("/api/integrate/rr/generate", tags=["Integration"])
async def trigger_rr_generation(site_data: dict):
    """
    Trigger R&R Automation site content generation.
    
    In production: Would call R&R API endpoint /api/rr/generate
    """
    return {
        "status": "generation_queued",
        "integration": "R&R Automation V3.0",
        "framework_version": "V3.0",
        "site": site_data,
        "page_types": [
            "homepage", "service_page", "location_page", "about_page",
            "faq_page", "contact_page", "reviews_page", "blog_post"
        ],
        "note": "Connect to R&R Automation API for AI-optimized content generation"
    }

# =============================================================================
# REPORTS ENDPOINTS
# =============================================================================

@app.get("/api/reports/action-plan", tags=["Reports"])
async def get_action_plan():
    """Generate prioritized 90-day action plan"""
    summary = scoring_engine.get_portfolio_summary()
    
    return {
        "plan_name": "90-Day Portfolio Optimization",
        "generated_at": datetime.utcnow().isoformat(),
        "portfolio_summary": {
            "total_sites": summary["total_sites"],
            "activate_count": summary["tier_distribution"]["activate"],
            "watchlist_count": summary["tier_distribution"]["watchlist"],
            "sunset_count": summary["tier_distribution"]["sunset"],
            "total_potential": summary["revenue_potential"]["total_monthly"]
        },
        "phases": [
            {
                "phase": 1,
                "name": "Immediate Actions",
                "weeks": "1-2",
                "actions": [
                    {"type": "SUNSET", "description": f"Discontinue {summary['tier_distribution']['sunset']} low-performing sites"},
                    {"type": "ACTIVATE", "description": "Begin outreach for top 7 Concrete sites (highest scores)"},
                    {"type": "SETUP", "description": "Configure tracking for all Activate tier sites"}
                ]
            },
            {
                "phase": 2,
                "name": "Expansion",
                "weeks": "3-4",
                "actions": [
                    {"type": "ACTIVATE", "description": "Launch Roofing and Water Damage campaigns"},
                    {"type": "INTEGRATE", "description": "Run RevFlow analysis on Watchlist sites"},
                    {"type": "DISCOVER", "description": "Use Turbo Search to identify 10 new opportunities"}
                ]
            },
            {
                "phase": 3,
                "name": "Optimization",
                "weeks": "5-8",
                "actions": [
                    {"type": "ACTIVATE", "description": "Complete all Activate tier outreach"},
                    {"type": "MONITOR", "description": "Track performance metrics weekly"},
                    {"type": "ANALYZE", "description": "Identify Watchlist promotion candidates"}
                ]
            },
            {
                "phase": 4,
                "name": "Assessment",
                "weeks": "9-12",
                "actions": [
                    {"type": "EVALUATE", "description": "Reassess all Watchlist sites"},
                    {"type": "PROMOTE", "description": "Move top Watchlist performers to Activate"},
                    {"type": "ACQUIRE", "description": "Begin acquisition of new high-score opportunities"}
                ]
            }
        ],
        "success_metrics": [
            {"metric": "Activate Sites Under Contract", "target": "50%+ by week 8"},
            {"metric": "Monthly Revenue", "target": "$15,000+ by week 12"},
            {"metric": "New Opportunities Identified", "target": "10+ high-score markets"}
        ]
    }

@app.get("/api/reports/revenue-projection", tags=["Reports"])
async def get_revenue_projection():
    """Project revenue based on current portfolio"""
    summary = scoring_engine.get_portfolio_summary()
    activate_potential = summary["revenue_potential"]["activate_monthly"]
    watchlist_potential = summary["revenue_potential"]["watchlist_monthly"]
    
    return {
        "generated_at": datetime.utcnow().isoformat(),
        "current_portfolio": {
            "activate_monthly_potential": activate_potential,
            "watchlist_monthly_potential": watchlist_potential,
            "total_monthly_potential": activate_potential + watchlist_potential
        },
        "projections": {
            "conservative": {
                "success_rate": 0.4,
                "monthly": int(activate_potential * 0.4),
                "annual": int(activate_potential * 0.4 * 12),
                "assumptions": "40% of Activate tier sites generate revenue"
            },
            "moderate": {
                "success_rate": 0.6,
                "monthly": int(activate_potential * 0.6),
                "annual": int(activate_potential * 0.6 * 12),
                "assumptions": "60% of Activate tier sites generate revenue"
            },
            "optimistic": {
                "success_rate": 0.8,
                "monthly": int(activate_potential * 0.8 + watchlist_potential * 0.3),
                "annual": int((activate_potential * 0.8 + watchlist_potential * 0.3) * 12),
                "assumptions": "80% Activate + 30% Watchlist promotion"
            }
        }
    }

# =============================================================================
# RUN APPLICATION
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
