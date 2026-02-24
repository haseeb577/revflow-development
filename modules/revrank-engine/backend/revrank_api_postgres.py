"""
RevRank API Integration - PostgreSQL Backend
Drop-in replacement for main_enhanced.py to use real portfolio data
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import psycopg2
from psycopg2.extras import RealDictCursor
import os

app = FastAPI(title="RevRank Portfolio API - Live Data")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database connection
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', 5432)),
    'database': os.getenv('DB_NAME', 'revrank_portfolio'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', 'your_password')
}

def get_db_connection():
    """Get database connection"""
    return psycopg2.connect(**DB_CONFIG, cursor_factory=RealDictCursor)

# ============================================================================
# MODELS (Match your existing dashboard expectations)
# ============================================================================

class Site(BaseModel):
    id: str
    name: str
    category: str
    city: str
    state: str
    score: float
    tier: str
    monthly_potential: int
    decision: str
    domain: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    site_published: Optional[bool] = None
    indexed_by_google: Optional[bool] = None
    geo_quality_score: Optional[int] = None

class PortfolioSummary(BaseModel):
    total_sites: int
    tier_distribution: dict
    revenue_potential: dict
    category_breakdown: List[dict]
    top_sites: List[Site]
    bottom_sites: List[Site]
    recommendations: List[dict]

# ============================================================================
# ENDPOINTS
# ============================================================================

@app.get("/api/portfolio", response_model=PortfolioSummary)
async def get_portfolio():
    """Get complete portfolio summary"""
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Total sites
        cursor.execute("SELECT COUNT(*) as total FROM rr_sites")
        total_sites = cursor.fetchone()['total']
        
        # Tier distribution
        cursor.execute("""
            SELECT tier, COUNT(*) as count 
            FROM rr_sites 
            GROUP BY tier
        """)
        tier_dist = {row['tier'].lower(): row['count'] for row in cursor.fetchall()}
        
        # Revenue potential
        cursor.execute("""
            SELECT 
                tier,
                SUM(monthly_potential) as total_monthly,
                SUM(monthly_potential * 12) as total_annual
            FROM rr_sites
            GROUP BY tier
        """)
        revenue_by_tier = cursor.fetchall()
        
        revenue_potential = {
            'activate_monthly': sum(r['total_monthly'] for r in revenue_by_tier if r['tier'] == 'ACTIVATE') or 0,
            'watchlist_monthly': sum(r['total_monthly'] for r in revenue_by_tier if r['tier'] == 'WATCHLIST') or 0,
            'total_monthly': sum(r['total_monthly'] for r in revenue_by_tier) or 0,
            'activate_annual': sum(r['total_annual'] for r in revenue_by_tier if r['tier'] == 'ACTIVATE') or 0,
            'total_annual': sum(r['total_annual'] for r in revenue_by_tier) or 0,
        }
        
        # Category breakdown
        cursor.execute("""
            SELECT 
                category,
                COUNT(*) as site_count,
                AVG(score) as avg_score,
                SUM(monthly_potential) as total_potential,
                tier
            FROM rr_sites
            GROUP BY category, tier
            ORDER BY avg_score DESC
        """)
        categories = cursor.fetchall()
        
        category_breakdown = []
        for cat in categories:
            category_breakdown.append({
                'category': cat['category'],
                'site_count': cat['site_count'],
                'avg_score': round(float(cat['avg_score'] or 0), 2),
                'total_potential': cat['total_potential'] or 0,
                'recommended': cat['avg_score'] and cat['avg_score'] >= 3.5,
                'category_tier': 1 if cat['avg_score'] and cat['avg_score'] >= 3.9 else 2 if cat['avg_score'] and cat['avg_score'] >= 3.5 else 3
            })
        
        # Top 10 sites
        cursor.execute("""
            SELECT site_id, business_name, category, city, state, score, tier, monthly_potential,
                   domain, phone, email, site_published, indexed_by_google, geo_quality_score
            FROM rr_sites
            ORDER BY score DESC
            LIMIT 10
        """)
        top_sites_data = cursor.fetchall()
        
        top_sites = [
            Site(
                id=site['site_id'],
                name=site['business_name'],
                category=site['category'] or 'Unknown',
                city=site['city'] or 'Unknown',
                state=site['state'] or 'Unknown',
                score=float(site['score'] or 0),
                tier=site['tier'] or 'WATCHLIST',
                monthly_potential=site['monthly_potential'] or 0,
                decision=f"KEEP & {site['tier']}" if site['tier'] else "EVALUATE",
                domain=site['domain'],
                phone=site['phone'],
                email=site['email'],
                site_published=site['site_published'],
                indexed_by_google=site['indexed_by_google'],
                geo_quality_score=site['geo_quality_score']
            )
            for site in top_sites_data
        ]
        
        # Bottom 10 sites
        cursor.execute("""
            SELECT site_id, business_name, category, city, state, score, tier, monthly_potential,
                   domain, phone, email, site_published, indexed_by_google, geo_quality_score
            FROM rr_sites
            ORDER BY score ASC
            LIMIT 10
        """)
        bottom_sites_data = cursor.fetchall()
        
        bottom_sites = [
            Site(
                id=site['site_id'],
                name=site['business_name'],
                category=site['category'] or 'Unknown',
                city=site['city'] or 'Unknown',
                state=site['state'] or 'Unknown',
                score=float(site['score'] or 0),
                tier=site['tier'] or 'SUNSET',
                monthly_potential=site['monthly_potential'] or 0,
                decision="SUNSET" if site['tier'] == 'SUNSET' else "EVALUATE",
                domain=site['domain'],
                phone=site['phone'],
                email=site['email'],
                site_published=site['site_published'],
                indexed_by_google=site['indexed_by_google'],
                geo_quality_score=site['geo_quality_score']
            )
            for site in bottom_sites_data
        ]
        
        # Recommendations
        recommendations = [
            {
                'priority': 1,
                'action': 'ACTIVATE',
                'description': f"Begin contractor outreach for all {tier_dist.get('activate', 0)} Activate Now sites",
                'sites_affected': tier_dist.get('activate', 0),
                'expected_impact': f"${revenue_potential.get('activate_monthly', 0):,}/month potential"
            },
            {
                'priority': 2,
                'action': 'OPTIMIZE_CONTENT',
                'description': "Generate V3.0 framework content for published sites",
                'sites_affected': tier_dist.get('activate', 0) + tier_dist.get('watchlist', 0),
                'expected_impact': "41% traffic increase (70% → 85% capture)"
            },
            {
                'priority': 3,
                'action': 'MONITOR',
                'description': f"Track {tier_dist.get('watchlist', 0)} Watchlist sites for 90 days",
                'sites_affected': tier_dist.get('watchlist', 0),
                'expected_impact': "Identify 5-8 promotion candidates"
            },
            {
                'priority': 4,
                'action': 'SUNSET',
                'description': f"Stop investment in {tier_dist.get('sunset', 0)} low-scoring sites",
                'sites_affected': tier_dist.get('sunset', 0),
                'expected_impact': "Free up resources for high-potential sites"
            }
        ]
        
        return PortfolioSummary(
            total_sites=total_sites,
            tier_distribution=tier_dist,
            revenue_potential=revenue_potential,
            category_breakdown=category_breakdown,
            top_sites=top_sites,
            bottom_sites=bottom_sites,
            recommendations=recommendations
        )
    
    finally:
        cursor.close()
        conn.close()

@app.get("/api/sites")
async def get_sites(tier: Optional[str] = None):
    """Get sites, optionally filtered by tier"""
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        if tier:
            cursor.execute("""
                SELECT site_id, business_name, category, city, state, score, tier, monthly_potential,
                       domain, phone, email, site_published, indexed_by_google, geo_quality_score
                FROM rr_sites
                WHERE tier = %s
                ORDER BY score DESC
            """, (tier.upper(),))
        else:
            cursor.execute("""
                SELECT site_id, business_name, category, city, state, score, tier, monthly_potential,
                       domain, phone, email, site_published, indexed_by_google, geo_quality_score
                FROM rr_sites
                ORDER BY score DESC
            """)
        
        sites_data = cursor.fetchall()
        
        sites = [
            {
                'id': site['site_id'],
                'name': site['business_name'],
                'category': site['category'] or 'Unknown',
                'city': site['city'] or 'Unknown',
                'state': site['state'] or 'Unknown',
                'score': float(site['score'] or 0),
                'tier': site['tier'] or 'WATCHLIST',
                'monthly_potential': site['monthly_potential'] or 0,
                'domain': site['domain'],
                'phone': site['phone'],
                'email': site['email'],
                'site_published': site['site_published'],
                'indexed_by_google': site['indexed_by_google'],
                'geo_quality_score': site['geo_quality_score']
            }
            for site in sites_data
        ]
        
        return {'sites': sites, 'count': len(sites)}
    
    finally:
        cursor.close()
        conn.close()

@app.get("/api/site/{site_id}")
async def get_site(site_id: str):
    """Get detailed site information"""
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT *
            FROM rr_sites
            WHERE site_id = %s
        """, (site_id,))
        
        site = cursor.fetchone()
        
        if not site:
            raise HTTPException(status_code=404, detail="Site not found")
        
        return dict(site)
    
    finally:
        cursor.close()
        conn.close()

@app.get("/")
async def root():
    """Health check"""
    return {
        'status': 'ok',
        'service': 'RevRank Portfolio API',
        'version': '2.0 - Live Data',
        'endpoints': [
            '/api/portfolio',
            '/api/sites',
            '/api/site/{site_id}'
        ]
    }

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8001)
