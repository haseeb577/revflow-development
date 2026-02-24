"""
RevVest IQ™ - Portfolio Analysis & Investment Intelligence
Module 14 - Backend API
"""
from fastapi import FastAPI, HTTPException, Depends


import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv("/opt/shared-api-engine/.env")

def get_db_connection():
    """Get PostgreSQL database connection"""
    return psycopg2.connect(
        host="localhost",
        database="revflow",
        user="postgres",
        password=os.getenv("POSTGRES_PASSWORD")
    )

from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
import psycopg2
import psycopg2.extras
import os
from datetime import datetime, date
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="RevVest IQ™ API",
    description="Portfolio Analysis & Investment Intelligence - Module 14",
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

# Database connection
def get_db():
    """Connect to PostgreSQL"""
    try:
        conn = psycopg2.connect(
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=os.getenv("POSTGRES_PORT", "5432"),
            database=os.getenv("POSTGRES_DB", "revflow"),
            user=os.getenv("POSTGRES_USER", "postgres"),
            password=os.getenv("POSTGRES_PASSWORD")
        )
        return conn
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise HTTPException(status_code=500, detail="Database connection failed")

# Pydantic Models
class OpportunityAnalysisRequest(BaseModel):
    niche: str = Field(..., description="Niche/industry to analyze")
    geographic_area: str = Field(..., description="Geographic area (city, state, zip)")
    keywords: Optional[List[str]] = Field(default=[], description="Target keywords")

class OpportunityResponse(BaseModel):
    opportunity_id: int
    niche: str
    geographic_area: str
    opportunity_score: int
    category: str
    revenue_forecast: Optional[float]
    confidence_score: Optional[int]
    keywords: Optional[List[str]]
    created_at: datetime

class BlueprintResponse(BaseModel):
    blueprint_id: int
    blueprint_name: str
    target_domain: Optional[str]
    estimated_investment: Optional[float]
    estimated_revenue: Optional[float]
    estimated_roi: Optional[float]
    deployment_status: str

class PortfolioSiteResponse(BaseModel):
    site_id: int
    domain: str
    niche: Optional[str]
    geographic_area: Optional[str]
    monthly_revenue: Optional[float]
    monthly_traffic: Optional[int]
    roi_percentage: Optional[float]
    status: str
    health_score: Optional[int]

class RecommendationResponse(BaseModel):
    recommendation_id: int
    recommendation_type: str
    title: str
    description: str
    priority: str
    impact_score: Optional[int]
    status: str

# Scoring Functions
def calculate_opportunity_score(factors: Dict) -> tuple:
    """
    Calculate opportunity score using 19-point weighted model
    Returns: (total_score, category)
    """
    # 19-Point Weights (Critical=4, Important=2, Minor=1)
    weights = {
        'serp_competition': 4,
        'search_demand': 4,
        'commercial_intent': 4,
        'local_competition': 4,
        'geographic_density': 2,
        'content_saturation': 2,
        'brand_authority': 2,
        'conversion_rate': 2,
        'customer_lifetime_value': 2,
        'market_maturity': 2,
        'scalability': 2,
        'competitive_moat': 2,
        'domain_availability': 1,
        'monetization_potential': 1,
        'entry_barrier': 1,
        'seasonality_risk': 1,
        'regulatory_complexity': 1,
        'technical_difficulty': 1,
        'revenue_predictability': 1
    }
    
    # Calculate weighted sum
    total_weighted = sum(factors.get(key, 0) * weight for key, weight in weights.items())
    max_possible = sum(weights.values())  # Should be 38
    
    # Normalize to 0-100 scale
    score = int((total_weighted / max_possible) * 100)
    
    # Categorize
    if score >= 80:
        category = "EXCELLENT"
    elif score >= 60:
        category = "GOOD"
    elif score >= 40:
        category = "FAIR"
    else:
        category = "POOR"
    
    return score, category

# API Routes
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "RevVest IQ™",
        "module": 14,
        "status": "operational",
        "version": "1.0.0"
    }




@app.get("/api/portfolio/view")
async def get_portfolio_from_view():
    """Get portfolio sites from vw_revvest_portfolio view (reads from revpublish_sites)"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                site_id,
                domain,
                business_name,
                niche,
                geographic_area,
                status,
                hosting_provider,
                monthly_revenue,
                monthly_traffic,
                initial_investment,
                roi_percentage,
                notes,
                created_at,
                updated_at
            FROM vw_revvest_portfolio
            ORDER BY business_name
        """)
        
        sites = []
        for row in cursor.fetchall():
            sites.append({
                "site_id": row[0],
                "domain": row[1],
                "business_name": row[2],
                "niche": row[3],
                "geographic_area": row[4],
                "status": row[5],
                "hosting_provider": row[6],
                "monthly_revenue": float(row[7]) if row[7] else 0.0,
                "monthly_traffic": row[8] or 0,
                "initial_investment": float(row[9]) if row[9] else 0.0,
                "roi_percentage": float(row[10]) if row[10] else 0.0,
                "notes": row[11],
                "created_at": row[12].isoformat() if row[12] else None,
                "updated_at": row[13].isoformat() if row[13] else None
            })
        
        cursor.close()
        return {
            "total": len(sites),
            "sites": sites,
            "source": "vw_revvest_portfolio (revpublish_sites)",
            "note": "This is your existing portfolio from RevPublish module"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn:
            conn.close()


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.close()
        conn.close()
        return {
            "status": "healthy",
            "database": "connected",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e)
        }

@app.post("/api/analyze-opportunity", response_model=OpportunityResponse)
async def analyze_opportunity(request: OpportunityAnalysisRequest):
    """
    Analyze a new market opportunity using 19-point scoring model
    """
    conn = get_db()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    try:
        # TODO: Integrate with Module 15 (RevSPY) for actual SERP data
        # For now, using placeholder scoring
        
        # Placeholder scoring factors (would come from RevSPY and DataForSEO)
        factors = {
            'serp_competition': 3,  # 0-4
            'search_demand': 4,      # 0-4
            'commercial_intent': 3,  # 0-4
            'local_competition': 2,  # 0-4
            'geographic_density': 2, # 0-2
            'content_saturation': 1, # 0-2
            'brand_authority': 1,    # 0-2
            'conversion_rate': 2,    # 0-2
            'customer_lifetime_value': 2, # 0-2
            'market_maturity': 1,    # 0-2
            'scalability': 2,        # 0-2
            'competitive_moat': 1,   # 0-2
            'domain_availability': 1, # 0-1
            'monetization_potential': 1, # 0-1
            'entry_barrier': 1,      # 0-1
            'seasonality_risk': 0,   # 0-1
            'regulatory_complexity': 0, # 0-1
            'technical_difficulty': 0, # 0-1
            'revenue_predictability': 1 # 0-1
        }
        
        # Calculate score
        score, category = calculate_opportunity_score(factors)
        
        # Estimate revenue (placeholder formula)
        revenue_forecast = score * 50  # $50 per score point
        confidence_score = min(95, score + 10)
        
        # Insert into database
        cursor.execute("""
            INSERT INTO revvest_opportunities (
                niche, geographic_area, opportunity_score, category,
                revenue_forecast, confidence_score, keywords,
                serp_competition, search_demand, commercial_intent,
                local_competition, geographic_density, content_saturation,
                brand_authority, conversion_rate, customer_lifetime_value,
                market_maturity, scalability, competitive_moat,
                domain_availability, monetization_potential, entry_barrier,
                seasonality_risk, regulatory_complexity, technical_difficulty,
                revenue_predictability, analyzed_by
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s
            )
            RETURNING opportunity_id, niche, geographic_area, opportunity_score,
                      category, revenue_forecast, confidence_score, keywords, created_at
        """, (
            request.niche, request.geographic_area, score, category,
            revenue_forecast, confidence_score, request.keywords,
            factors['serp_competition'], factors['search_demand'], 
            factors['commercial_intent'], factors['local_competition'],
            factors['geographic_density'], factors['content_saturation'],
            factors['brand_authority'], factors['conversion_rate'],
            factors['customer_lifetime_value'], factors['market_maturity'],
            factors['scalability'], factors['competitive_moat'],
            factors['domain_availability'], factors['monetization_potential'],
            factors['entry_barrier'], factors['seasonality_risk'],
            factors['regulatory_complexity'], factors['technical_difficulty'],
            factors['revenue_predictability'], 'system'
        ))
        
        result = cursor.fetchone()
        conn.commit()
        
        logger.info(f"Created opportunity {result['opportunity_id']}: {request.niche} in {request.geographic_area}")
        
        return OpportunityResponse(**result)
        
    except psycopg2.IntegrityError:
        conn.rollback()
        raise HTTPException(status_code=409, detail="Opportunity already exists for this niche/area")
    except Exception as e:
        conn.rollback()
        logger.error(f"Error analyzing opportunity: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()

@app.get("/api/opportunities", response_model=List[OpportunityResponse])
async def list_opportunities(
    category: Optional[str] = None,
    min_score: Optional[int] = None,
    limit: int = 50
):
    """List all opportunities with optional filters"""
    conn = get_db()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    try:
        query = """
            SELECT opportunity_id, niche, geographic_area, opportunity_score,
                   category, revenue_forecast, confidence_score, keywords, created_at
            FROM revvest_opportunities
            WHERE 1=1
        """
        params = []
        
        if category:
            query += " AND category = %s"
            params.append(category)
        
        if min_score:
            query += " AND opportunity_score >= %s"
            params.append(min_score)
        
        query += " ORDER BY opportunity_score DESC LIMIT %s"
        params.append(limit)
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        
        return [OpportunityResponse(**row) for row in results]
        
    finally:
        cursor.close()
        conn.close()

@app.get("/api/opportunities/{opportunity_id}")
async def get_opportunity(opportunity_id: int):
    """Get detailed opportunity information"""
    conn = get_db()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    try:
        cursor.execute("""
            SELECT * FROM revvest_opportunities
            WHERE opportunity_id = %s
        """, (opportunity_id,))
        
        result = cursor.fetchone()
        if not result:
            raise HTTPException(status_code=404, detail="Opportunity not found")
        
        return result
        
    finally:
        cursor.close()
        conn.close()

@app.get("/api/portfolio", response_model=List[PortfolioSiteResponse])
async def list_portfolio_sites(status: Optional[str] = None):
    """List all portfolio sites"""
    conn = get_db()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    try:
        query = """
            SELECT site_id, domain, niche, geographic_area,
                   monthly_revenue, monthly_traffic, roi_percentage,
                   status, health_score
            FROM revvest_portfolio
            WHERE 1=1
        """
        params = []
        
        if status:
            query += " AND status = %s"
            params.append(status)
        
        query += " ORDER BY monthly_revenue DESC"
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        
        return [PortfolioSiteResponse(**row) for row in results]
        
    finally:
        cursor.close()
        conn.close()

@app.post("/api/portfolio")
async def add_portfolio_site(
    domain: str,
    niche: Optional[str] = None,
    geographic_area: Optional[str] = None,
    initial_investment: Optional[float] = None
):
    """Add a new site to portfolio"""
    conn = get_db()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    try:
        cursor.execute("""
            INSERT INTO revvest_portfolio (
                domain, niche, geographic_area, initial_investment
            ) VALUES (%s, %s, %s, %s)
            RETURNING site_id, domain, status
        """, (domain, niche, geographic_area, initial_investment))
        
        result = cursor.fetchone()
        conn.commit()
        
        return result
        
    except psycopg2.IntegrityError:
        conn.rollback()
        raise HTTPException(status_code=409, detail="Domain already exists in portfolio")
    finally:
        cursor.close()
        conn.close()

@app.get("/api/recommendations", response_model=List[RecommendationResponse])
async def list_recommendations(priority: Optional[str] = None):
    """List action recommendations"""
    conn = get_db()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    try:
        query = """
            SELECT recommendation_id, recommendation_type, title, description,
                   priority, impact_score, status
            FROM revvest_recommendations
            WHERE status != 'dismissed'
        """
        params = []
        
        if priority:
            query += " AND priority = %s"
            params.append(priority)
        
        query += " ORDER BY CASE priority WHEN 'P0' THEN 0 WHEN 'P1' THEN 1 WHEN 'P2' THEN 2 ELSE 3 END, impact_score DESC"
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        
        return [RecommendationResponse(**row) for row in results]
        
    finally:
        cursor.close()
        conn.close()

@app.get("/api/blueprints", response_model=List[BlueprintResponse])
async def list_blueprints():
    """List market blueprints"""
    conn = get_db()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    try:
        cursor.execute("""
            SELECT blueprint_id, blueprint_name, target_domain,
                   estimated_investment, estimated_revenue, estimated_roi,
                   deployment_status
            FROM revvest_blueprints
            ORDER BY estimated_roi DESC
        """)
        
        results = cursor.fetchall()
        return [BlueprintResponse(**row) for row in results]
        
    finally:
        cursor.close()
        conn.close()

@app.post("/api/blueprints/{opportunity_id}")
async def create_blueprint(opportunity_id: int):
    """Generate market blueprint from opportunity"""
    conn = get_db()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    try:
        # Get opportunity details
        cursor.execute("""
            SELECT * FROM revvest_opportunities
            WHERE opportunity_id = %s
        """, (opportunity_id,))
        
        opp = cursor.fetchone()
        if not opp:
            raise HTTPException(status_code=404, detail="Opportunity not found")
        
        # Generate blueprint name
        blueprint_name = f"{opp['niche']} - {opp['geographic_area']} Blueprint"
        
        # Placeholder blueprint data
        estimated_investment = 5000.00  # $5,000 initial
        estimated_revenue = opp['revenue_forecast']
        estimated_roi = ((estimated_revenue - estimated_investment) / estimated_investment) * 100 if estimated_investment > 0 else 0
        
        # Create blueprint
        cursor.execute("""
            INSERT INTO revvest_blueprints (
                opportunity_id, blueprint_name, estimated_investment,
                estimated_revenue, estimated_roi, content_strategy,
                local_seo_plan
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING blueprint_id, blueprint_name, estimated_roi
        """, (
            opportunity_id, blueprint_name, estimated_investment,
            estimated_revenue, estimated_roi,
            f"Content strategy for {opp['niche']} in {opp['geographic_area']}",
            f"Local SEO plan targeting {opp['keywords']}"
        ))
        
        result = cursor.fetchone()
        conn.commit()
        
        return result
        
    finally:
        cursor.close()
        conn.close()

@app.get("/api/stats/dashboard")
async def get_dashboard_stats():
    """Get dashboard statistics"""
    conn = get_db()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    try:
        stats = {}
        
        # Opportunities count by category
        cursor.execute("""
            SELECT category, COUNT(*) as count
            FROM revvest_opportunities
            GROUP BY category
        """)
        stats['opportunities_by_category'] = {row['category']: row['count'] for row in cursor.fetchall()}
        
        # Portfolio stats
        cursor.execute("""
            SELECT 
                COUNT(*) as total_sites,
                SUM(monthly_revenue) as total_monthly_revenue,
                AVG(roi_percentage) as avg_roi,
                COUNT(CASE WHEN status = 'active' THEN 1 END) as active_sites
            FROM revvest_portfolio
        """)
        stats['portfolio'] = cursor.fetchone()
        
        # Recommendations by priority
        cursor.execute("""
            SELECT priority, COUNT(*) as count
            FROM revvest_recommendations
            WHERE status = 'pending'
            GROUP BY priority
        """)
        stats['pending_recommendations'] = {row['priority']: row['count'] for row in cursor.fetchall()}
        
        return stats
        
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3013)
