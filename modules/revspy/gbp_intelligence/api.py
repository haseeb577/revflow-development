"""
Module 15: RevSPY™ - GBP Intelligence Sub-Module
Part of: RevFlow GBP Suite™

Purpose: Competitive GBP analysis via GMB Everywhere integration
Role: Market intelligence and competitor benchmarking for GBP profiles
"""
"""
REVSPY™ GBP INTELLIGENCE API
Module 15: RevSPY™ Enhancement

Purpose: Receive and process bulk GBP competitor data from GMB Everywhere
Integration: Webhook endpoint for Chrome extension
Database: PostgreSQL (localhost:5432, database: revflow)

Date: 2026-02-08
"""

from fastapi import APIRouter, HTTPException, Request, Header
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
import psycopg2
from psycopg2.extras import Json, execute_values
import json
import os
from datetime import datetime
import logging
from dotenv import load_dotenv

# Load shared .env file (RevFlow OS standard)
load_dotenv('/opt/shared-api-engine/.env')


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create API router
router = APIRouter(prefix="/api/v1/revspy", tags=["RevSPY GBP Intelligence"])

# ============================================================================
# PYDANTIC MODELS (Data Validation)
# ============================================================================

class GBPProfile(BaseModel):
    """Single GBP profile from GMB Everywhere"""
    
    # Required fields
    place_id: str = Field(..., description="Google Place ID (unique identifier)")
    business_name: str = Field(..., description="Business name")
    primary_category: str = Field(..., description="Primary GBP category")
    
    # Categories
    secondary_categories: List[str] = Field(default=[], description="Additional categories")
    
    # Location
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    country: str = "US"
    lat: Optional[float] = None
    lng: Optional[float] = None
    
    # Performance metrics
    rating: Optional[float] = Field(None, ge=0, le=5, description="Star rating (0-5)")
    review_count: int = Field(default=0, ge=0, description="Total review count")
    
    # Visibility signals
    has_website: bool = False
    website_url: Optional[str] = None
    has_phone: bool = False
    phone_number: Optional[str] = None
    has_hours: bool = False
    hours_data: Optional[Dict] = None
    
    # Content metrics
    photo_count: int = 0
    video_count: int = 0
    post_count: int = 0
    qa_count: int = 0
    
    # Service area
    service_area_radius: Optional[int] = None
    service_area_cities: List[str] = []
    
    # Attributes
    attributes: Dict[str, Any] = {}
    amenities: Dict[str, Any] = {}
    
    # Competitive context
    competitor_rank: Optional[int] = None
    
    @validator('rating')
    def validate_rating(cls, v):
        if v is not None and (v < 0 or v > 5):
            raise ValueError('Rating must be between 0 and 5')
        return v


class GBPBulkImport(BaseModel):
    """Bulk import payload from GMB Everywhere"""
    
    profiles: List[GBPProfile] = Field(..., min_items=1, max_items=100, 
                                       description="List of GBP profiles (max 100)")
    market: str = Field(..., description="Market identifier (e.g., 'electrician chicago')")
    scraped_by: str = Field(..., description="User email who ran the audit")
    notes: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "profiles": [
                    {
                        "place_id": "ChIJN1t_tDeuEmsRUsoyG83frY4",
                        "business_name": "ABC Electrician Chicago",
                        "primary_category": "Electrician",
                        "secondary_categories": ["Emergency electrician service"],
                        "city": "Chicago",
                        "state": "IL",
                        "zip_code": "60614",
                        "rating": 4.8,
                        "review_count": 234,
                        "has_website": True,
                        "photo_count": 87,
                        "competitor_rank": 1
                    }
                ],
                "market": "electrician chicago",
                "scraped_by": "shimon@revflow.com"
            }
        }


class GBPIngestResponse(BaseModel):
    """Response model for successful ingestion"""
    status: str
    profiles_received: int
    profiles_inserted: int
    profiles_updated: int
    profiles_failed: int
    market: str
    analysis_triggered: bool
    webhook_log_id: str


# ============================================================================
# DATABASE CONNECTION
# ============================================================================

def get_db_connection():
    """Get PostgreSQL database connection"""
    try:
        # Prefer DATABASE_URL if available (correctly set in docker-compose)
        database_url = os.getenv("DATABASE_URL")
        if database_url:
            conn = psycopg2.connect(database_url, connect_timeout=10)
        else:
            conn = psycopg2.connect(
                host=os.getenv("POSTGRES_HOST", os.getenv("DATABASE_HOST", "localhost")),
                port=int(os.getenv("POSTGRES_PORT", os.getenv("DATABASE_PORT", "5432"))),
                database=os.getenv("POSTGRES_DB", os.getenv("DATABASE_NAME", "revflow")),
                user=os.getenv("POSTGRES_USER", os.getenv("DATABASE_USER", "revflow")),
                password=os.getenv("POSTGRES_PASSWORD", os.getenv("DATABASE_PASSWORD", "")),
                connect_timeout=10
            )
        return conn
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise HTTPException(status_code=500, detail="Database connection failed")


# ============================================================================
# MAIN WEBHOOK ENDPOINT
# ============================================================================

@router.post("/gbp/ingest", response_model=GBPIngestResponse)
async def ingest_gbp_data(
    data: GBPBulkImport,
    request: Request,
    x_api_key: Optional[str] = Header(None)
):
    """
    Receive bulk GBP competitor data from GMB Everywhere Chrome extension
    
    **Workflow:**
    1. Validate incoming data
    2. Log webhook call for debugging
    3. Insert/update profiles in database
    4. Calculate competitive metrics
    5. Trigger category and geographic analysis
    6. Return summary
    
    **Authentication:**
    - Requires X-API-Key header (optional, can be enforced)
    
    **Rate Limiting:**
    - Max 100 profiles per request
    - Recommended: 1 request per minute
    """
    
    start_time = datetime.now()
    client_ip = request.client.host
    
    logger.info(f"Received GBP data: {len(data.profiles)} profiles for market '{data.market}'")
    
    conn = get_db_connection()
    
    try:
        cur = conn.cursor()
        
        # Counters
        inserted = 0
        updated = 0
        failed = 0
        
        # Process each profile
        for profile in data.profiles:
            try:
                # Check if profile exists
                cur.execute(
                    "SELECT id FROM revspy_gbp_profiles WHERE place_id = %s",
                    (profile.place_id,)
                )
                existing = cur.fetchone()
                
                # Prepare data
                category_count = 1 + len(profile.secondary_categories)
                local_pack = profile.competitor_rank <= 3 if profile.competitor_rank else False
                
                if existing:
                    # Update existing profile
                    cur.execute("""
                        UPDATE revspy_gbp_profiles 
                        SET 
                            business_name = %s,
                            primary_category = %s,
                            secondary_categories = %s,
                            category_count = %s,
                            address = %s,
                            city = %s,
                            state = %s,
                            zip_code = %s,
                            country = %s,
                            lat = %s,
                            lng = %s,
                            rating = %s,
                            review_count = %s,
                            has_website = %s,
                            website_url = %s,
                            has_phone = %s,
                            phone_number = %s,
                            has_hours = %s,
                            hours_data = %s,
                            photo_count = %s,
                            video_count = %s,
                            post_count = %s,
                            qa_count = %s,
                            service_area_radius = %s,
                            service_area_cities = %s,
                            attributes = %s,
                            amenities = %s,
                            market = %s,
                            competitor_rank = %s,
                            local_pack_position = %s,
                            scraped_at = NOW(),
                            scraped_by = %s,
                            updated_at = NOW()
                        WHERE place_id = %s
                    """, (
                        profile.business_name,
                        profile.primary_category,
                        Json(profile.secondary_categories),
                        category_count,
                        profile.address,
                        profile.city,
                        profile.state,
                        profile.zip_code,
                        profile.country,
                        profile.lat,
                        profile.lng,
                        profile.rating,
                        profile.review_count,
                        profile.has_website,
                        profile.website_url,
                        profile.has_phone,
                        profile.phone_number,
                        profile.has_hours,
                        Json(profile.hours_data) if profile.hours_data else None,
                        profile.photo_count,
                        profile.video_count,
                        profile.post_count,
                        profile.qa_count,
                        profile.service_area_radius,
                        Json(profile.service_area_cities),
                        Json(profile.attributes),
                        Json(profile.amenities),
                        data.market,
                        profile.competitor_rank,
                        local_pack,
                        data.scraped_by,
                        profile.place_id
                    ))
                    updated += 1
                else:
                    # Insert new profile
                    cur.execute("""
                        INSERT INTO revspy_gbp_profiles (
                            place_id, business_name, primary_category,
                            secondary_categories, category_count,
                            address, city, state, zip_code, country,
                            lat, lng, rating, review_count,
                            has_website, website_url, has_phone, phone_number,
                            has_hours, hours_data,
                            photo_count, video_count, post_count, qa_count,
                            service_area_radius, service_area_cities,
                            attributes, amenities,
                            market, competitor_rank, local_pack_position,
                            scraped_by, scraped_at
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                            %s, %s, NOW()
                        )
                    """, (
                        profile.place_id,
                        profile.business_name,
                        profile.primary_category,
                        Json(profile.secondary_categories),
                        category_count,
                        profile.address,
                        profile.city,
                        profile.state,
                        profile.zip_code,
                        profile.country,
                        profile.lat,
                        profile.lng,
                        profile.rating,
                        profile.review_count,
                        profile.has_website,
                        profile.website_url,
                        profile.has_phone,
                        profile.phone_number,
                        profile.has_hours,
                        Json(profile.hours_data) if profile.hours_data else None,
                        profile.photo_count,
                        profile.video_count,
                        profile.post_count,
                        profile.qa_count,
                        profile.service_area_radius,
                        Json(profile.service_area_cities),
                        Json(profile.attributes),
                        Json(profile.amenities),
                        data.market,
                        profile.competitor_rank,
                        local_pack,
                        data.scraped_by
                    ))
                    inserted += 1
                    
            except Exception as e:
                logger.error(f"Failed to process profile {profile.place_id}: {e}")
                failed += 1
                continue
        
        conn.commit()
        
        # Calculate processing time
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
        
        # Log webhook call
        cur.execute("""
            INSERT INTO revspy_webhook_log (
                request_ip,
                request_payload,
                profiles_received,
                profiles_inserted,
                profiles_updated,
                profiles_failed,
                response_status,
                processing_time_ms,
                market,
                scraped_by
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            client_ip,
            Json(data.dict()),
            len(data.profiles),
            inserted,
            updated,
            failed,
            200,
            processing_time,
            data.market,
            data.scraped_by
        ))
        
        webhook_log_id = cur.fetchone()[0]
        conn.commit()
        
        # Trigger analysis (async - don't block response)
        try:
            trigger_market_analysis(data.market, data.profiles[0].primary_category)
        except Exception as e:
            logger.warning(f"Analysis trigger failed (non-fatal): {e}")
        
        logger.info(f"Successfully processed: {inserted} inserted, {updated} updated, {failed} failed")
        
        return GBPIngestResponse(
            status="success",
            profiles_received=len(data.profiles),
            profiles_inserted=inserted,
            profiles_updated=updated,
            profiles_failed=failed,
            market=data.market,
            analysis_triggered=True,
            webhook_log_id=str(webhook_log_id)
        )
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Webhook processing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()


# ============================================================================
# ANALYSIS TRIGGER
# ============================================================================

def trigger_market_analysis(market: str, primary_category: str):
    """
    Trigger automated analysis after data ingestion
    
    Analysis steps:
    1. Refresh category intelligence
    2. Update geographic density
    3. Identify gaps and opportunities
    """
    
    conn = get_db_connection()
    
    try:
        cur = conn.cursor()
        
        # Call stored procedure to refresh category intelligence
        cur.execute("SELECT refresh_category_intelligence(%s, %s)", (market, primary_category))
        
        # Update geographic density
        cur.execute("""
            INSERT INTO revspy_geographic_density (
                zip_code, city, state, market, primary_category,
                competitor_count, avg_rating, avg_review_count, total_reviews,
                has_coverage, coverage_level, is_geographic_gap
            )
            SELECT 
                zip_code,
                city,
                state,
                %s as market,
                %s as primary_category,
                COUNT(*) as competitor_count,
                AVG(rating) as avg_rating,
                AVG(review_count) as avg_review_count,
                SUM(review_count) as total_reviews,
                TRUE as has_coverage,
                CASE 
                    WHEN COUNT(*) >= 5 THEN 'HEAVY'
                    WHEN COUNT(*) >= 3 THEN 'MODERATE'
                    ELSE 'LIGHT'
                END as coverage_level,
                CASE WHEN COUNT(*) < 3 THEN TRUE ELSE FALSE END as is_geographic_gap
            FROM revspy_gbp_profiles
            WHERE market = %s AND primary_category = %s AND zip_code IS NOT NULL
            GROUP BY zip_code, city, state
            ON CONFLICT (zip_code, market, primary_category) 
            DO UPDATE SET
                competitor_count = EXCLUDED.competitor_count,
                avg_rating = EXCLUDED.avg_rating,
                avg_review_count = EXCLUDED.avg_review_count,
                total_reviews = EXCLUDED.total_reviews,
                coverage_level = EXCLUDED.coverage_level,
                is_geographic_gap = EXCLUDED.is_geographic_gap,
                last_updated = NOW()
        """, (market, primary_category, market, primary_category))
        
        conn.commit()
        logger.info(f"Analysis triggered for market: {market}, category: {primary_category}")
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Analysis failed: {e}")
        raise
    finally:
        cur.close()
        conn.close()


# ============================================================================
# QUERY ENDPOINTS (For retrieving analyzed data)
# ============================================================================

@router.get("/gbp/markets")
async def get_markets():
    """Get list of all analyzed markets"""
    
    conn = get_db_connection()
    
    try:
        cur = conn.cursor()
        
        cur.execute("""
            SELECT DISTINCT
                market,
                primary_category,
                COUNT(*) as profile_count,
                MAX(scraped_at) as last_updated
            FROM revspy_gbp_profiles
            GROUP BY market, primary_category
            ORDER BY last_updated DESC
        """)
        
        markets = []
        for row in cur.fetchall():
            markets.append({
                "market": row[0],
                "primary_category": row[1],
                "profile_count": row[2],
                "last_updated": row[3].isoformat() if row[3] else None
            })
        
        return {"markets": markets, "count": len(markets)}
        
    finally:
        cur.close()
        conn.close()


@router.get("/gbp/profiles/{market}")
async def get_market_profiles(market: str, limit: int = 50):
    """Get all GBP profiles for a specific market"""
    
    conn = get_db_connection()
    
    try:
        cur = conn.cursor()
        
        cur.execute("""
            SELECT 
                place_id, business_name, primary_category,
                rating, review_count, competitor_rank,
                city, state, zip_code,
                gbp_health_score, competitive_threat
            FROM revspy_gbp_profiles
            WHERE market = %s
            ORDER BY competitor_rank ASC, rating DESC
            LIMIT %s
        """, (market, limit))
        
        profiles = []
        for row in cur.fetchall():
            profiles.append({
                "place_id": row[0],
                "business_name": row[1],
                "primary_category": row[2],
                "rating": float(row[3]) if row[3] else None,
                "review_count": row[4],
                "competitor_rank": row[5],
                "city": row[6],
                "state": row[7],
                "zip_code": row[8],
                "gbp_health_score": row[9],
                "competitive_threat": row[10]
            })
        
        return {"profiles": profiles, "count": len(profiles), "market": market}
        
    finally:
        cur.close()
        conn.close()


@router.get("/gbp/gaps/geographic")
async def get_geographic_gaps(market: str = None, min_opportunity: int = 70):
    """Get geographic gaps (underserved zip codes)"""
    
    conn = get_db_connection()
    
    try:
        cur = conn.cursor()
        
        query = """
            SELECT 
                zip_code, city, state, market, primary_category,
                competitor_count, opportunity_score, gap_severity
            FROM revspy_geographic_density
            WHERE is_geographic_gap = TRUE
                AND opportunity_score >= %s
        """
        params = [min_opportunity]
        
        if market:
            query += " AND market = %s"
            params.append(market)
        
        query += " ORDER BY opportunity_score DESC LIMIT 50"
        
        cur.execute(query, params)
        
        gaps = []
        for row in cur.fetchall():
            gaps.append({
                "zip_code": row[0],
                "city": row[1],
                "state": row[2],
                "market": row[3],
                "primary_category": row[4],
                "competitor_count": row[5],
                "opportunity_score": row[6],
                "gap_severity": row[7]
            })
        
        return {"gaps": gaps, "count": len(gaps)}
        
    finally:
        cur.close()
        conn.close()


@router.get("/gbp/opportunities/categories")
async def get_category_opportunities(market: str = None):
    """Get category opportunities (underserved categories)"""
    
    conn = get_db_connection()
    
    try:
        cur = conn.cursor()
        
        query = """
            SELECT 
                category, market, total_competitors,
                saturation_level, opportunity_score, recommended_action
            FROM revspy_category_intelligence
            WHERE opportunity_level IN ('HIGH', 'CRITICAL')
        """
        params = []
        
        if market:
            query += " AND market = %s"
            params.append(market)
        
        query += " ORDER BY opportunity_score DESC"
        
        cur.execute(query, params)
        
        opportunities = []
        for row in cur.fetchall():
            opportunities.append({
                "category": row[0],
                "market": row[1],
                "total_competitors": row[2],
                "saturation_level": row[3],
                "opportunity_score": row[4],
                "recommended_action": row[5]
            })
        
        return {"opportunities": opportunities, "count": len(opportunities)}
        
    finally:
        cur.close()
        conn.close()


# ============================================================================
# HEALTH CHECK
# ============================================================================

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM revspy_gbp_profiles")
        profile_count = cur.fetchone()[0]
        cur.close()
        conn.close()
        
        return {
            "status": "healthy",
            "module": "RevSPY GBP Intelligence",
            "profiles_stored": profile_count,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
