"""
REVSPY™ GBP INTELLIGENCE - QUERY LIBRARY
Module 15: RevSPY™ Enhancement

Purpose: Pre-built queries for common competitive intelligence tasks
Usage: Import and use in reports, dashboards, and analysis scripts

Date: 2026-02-08
"""

import psycopg2
from typing import List, Dict, Optional, Tuple
import os
from datetime import datetime, timedelta


class RevSpyGBPQueries:
    """
    Query library for RevSPY GBP Intelligence
    All common competitive analysis queries in one place
    """
    
    def __init__(self):
        """Initialize database connection, preferring DATABASE_URL"""
        database_url = os.getenv("DATABASE_URL")
        if database_url:
            self.conn = psycopg2.connect(database_url)
        else:
            self.conn = psycopg2.connect(
                host=os.getenv("POSTGRES_HOST", os.getenv("DATABASE_HOST", "localhost")),
                port=int(os.getenv("POSTGRES_PORT", os.getenv("DATABASE_PORT", "5432"))),
                database=os.getenv("POSTGRES_DB", os.getenv("DATABASE_NAME", "revflow")),
                user=os.getenv("POSTGRES_USER", os.getenv("DATABASE_USER", "revflow")),
                password=os.getenv("POSTGRES_PASSWORD", os.getenv("DATABASE_PASSWORD", ""))
            )
    
    def __del__(self):
        """Close connection on cleanup"""
        if hasattr(self, 'conn'):
            self.conn.close()
    
    # ========================================================================
    # MARKET OVERVIEW QUERIES
    # ========================================================================
    
    def get_all_markets(self) -> List[Dict]:
        """
        Get list of all analyzed markets with stats
        
        Returns:
            List of markets with profile counts and last update times
        """
        cur = self.conn.cursor()
        
        cur.execute("""
            SELECT 
                market,
                primary_category,
                COUNT(*) as profile_count,
                COUNT(*) FILTER (WHERE local_pack_position = TRUE) as local_pack_count,
                AVG(rating) as avg_rating,
                AVG(review_count) as avg_reviews,
                MAX(scraped_at) as last_updated,
                COUNT(DISTINCT scraped_by) as users_tracked
            FROM revspy_gbp_profiles
            GROUP BY market, primary_category
            ORDER BY last_updated DESC
        """)
        
        markets = []
        for row in cur.fetchall():
            markets.append({
                "market": row[0],
                "category": row[1],
                "total_profiles": row[2],
                "local_pack_count": row[3],
                "avg_rating": float(row[4]) if row[4] else 0,
                "avg_reviews": int(row[5]) if row[5] else 0,
                "last_updated": row[6].isoformat() if row[6] else None,
                "users_tracked": row[7]
            })
        
        cur.close()
        return markets
    
    def get_market_summary(self, market: str) -> Dict:
        """
        Get comprehensive summary of a specific market
        
        Args:
            market: Market identifier (e.g., 'electrician chicago')
        
        Returns:
            Dict with complete market overview
        """
        cur = self.conn.cursor()
        
        # Overall stats
        cur.execute("""
            SELECT 
                COUNT(*) as total_competitors,
                COUNT(*) FILTER (WHERE local_pack_position = TRUE) as local_pack_count,
                AVG(rating) as avg_rating,
                AVG(review_count) as avg_reviews,
                AVG(photo_count) as avg_photos,
                AVG(gbp_health_score) as avg_health_score,
                MAX(gbp_health_score) as top_score,
                MIN(gbp_health_score) as lowest_score
            FROM revspy_gbp_profiles
            WHERE market = %s
        """, (market,))
        
        stats = cur.fetchone()
        
        # Category breakdown
        cur.execute("""
            SELECT 
                primary_category,
                COUNT(*) as count,
                AVG(rating) as avg_rating
            FROM revspy_gbp_profiles
            WHERE market = %s
            GROUP BY primary_category
            ORDER BY count DESC
        """, (market,))
        
        categories = [
            {
                "category": row[0],
                "count": row[1],
                "avg_rating": float(row[2]) if row[2] else 0
            }
            for row in cur.fetchall()
        ]
        
        # Geographic distribution
        cur.execute("""
            SELECT 
                city,
                COUNT(*) as count
            FROM revspy_gbp_profiles
            WHERE market = %s AND city IS NOT NULL
            GROUP BY city
            ORDER BY count DESC
            LIMIT 10
        """, (market,))
        
        cities = [{"city": row[0], "count": row[1]} for row in cur.fetchall()]
        
        cur.close()
        
        return {
            "market": market,
            "stats": {
                "total_competitors": stats[0],
                "local_pack_count": stats[1],
                "avg_rating": float(stats[2]) if stats[2] else 0,
                "avg_reviews": int(stats[3]) if stats[3] else 0,
                "avg_photos": int(stats[4]) if stats[4] else 0,
                "avg_health_score": int(stats[5]) if stats[5] else 0,
                "top_score": stats[6],
                "lowest_score": stats[7]
            },
            "categories": categories,
            "top_cities": cities
        }
    
    # ========================================================================
    # COMPETITIVE ANALYSIS QUERIES
    # ========================================================================
    
    def get_top_competitors(self, market: str, limit: int = 10) -> List[Dict]:
        """
        Get top competitors in a market by rank
        
        Args:
            market: Market identifier
            limit: Number of competitors to return (default 10)
        
        Returns:
            List of top competitors with full details
        """
        cur = self.conn.cursor()
        
        cur.execute("""
            SELECT 
                place_id,
                business_name,
                primary_category,
                rating,
                review_count,
                photo_count,
                post_count,
                competitor_rank,
                gbp_health_score,
                competitive_threat,
                has_website,
                city,
                state,
                zip_code
            FROM revspy_gbp_profiles
            WHERE market = %s
            ORDER BY competitor_rank ASC
            LIMIT %s
        """, (market, limit))
        
        competitors = []
        for row in cur.fetchall():
            competitors.append({
                "place_id": row[0],
                "business_name": row[1],
                "category": row[2],
                "rating": float(row[3]) if row[3] else 0,
                "reviews": row[4],
                "photos": row[5],
                "posts": row[6],
                "rank": row[7],
                "health_score": row[8],
                "threat_level": row[9],
                "has_website": row[10],
                "location": f"{row[11]}, {row[12]} {row[13]}" if row[11] else None
            })
        
        cur.close()
        return competitors
    
    def get_weak_competitors(self, market: str, max_score: int = 60) -> List[Dict]:
        """
        Find weak competitors that could be outranked
        
        Args:
            market: Market identifier
            max_score: Maximum health score to consider "weak" (default 60)
        
        Returns:
            List of weak competitors
        """
        cur = self.conn.cursor()
        
        cur.execute("""
            SELECT 
                business_name,
                rating,
                review_count,
                photo_count,
                competitor_rank,
                gbp_health_score,
                competitive_threat,
                local_pack_position
            FROM revspy_gbp_profiles
            WHERE market = %s 
                AND gbp_health_score IS NOT NULL
                AND gbp_health_score <= %s
            ORDER BY competitor_rank ASC
        """, (market, max_score))
        
        competitors = []
        for row in cur.fetchall():
            competitors.append({
                "business_name": row[0],
                "rating": float(row[1]) if row[1] else 0,
                "reviews": row[2],
                "photos": row[3],
                "rank": row[4],
                "health_score": row[5],
                "threat_level": row[6],
                "in_local_pack": row[7],
                "vulnerability": "HIGH" if row[7] and row[5] < 50 else "MEDIUM"
            })
        
        cur.close()
        return competitors
    
    def benchmark_against_market(self, place_id: str, market: str) -> Dict:
        """
        Benchmark a specific business against market averages
        
        Args:
            place_id: Google Place ID of business to benchmark
            market: Market identifier
        
        Returns:
            Dict with business stats vs market averages
        """
        cur = self.conn.cursor()
        
        # Get business data
        cur.execute("""
            SELECT 
                business_name,
                rating,
                review_count,
                photo_count,
                post_count,
                competitor_rank,
                gbp_health_score
            FROM revspy_gbp_profiles
            WHERE place_id = %s
        """, (place_id,))
        
        business = cur.fetchone()
        
        if not business:
            cur.close()
            return {"error": "Business not found"}
        
        # Get market averages
        cur.execute("""
            SELECT 
                AVG(rating) as avg_rating,
                AVG(review_count) as avg_reviews,
                AVG(photo_count) as avg_photos,
                AVG(post_count) as avg_posts,
                AVG(gbp_health_score) as avg_score,
                COUNT(*) as total_competitors
            FROM revspy_gbp_profiles
            WHERE market = %s
        """, (market,))
        
        market_avg = cur.fetchone()
        
        cur.close()
        
        return {
            "business": {
                "name": business[0],
                "rating": float(business[1]) if business[1] else 0,
                "reviews": business[2],
                "photos": business[3],
                "posts": business[4],
                "rank": business[5],
                "health_score": business[6]
            },
            "market": {
                "avg_rating": float(market_avg[0]) if market_avg[0] else 0,
                "avg_reviews": int(market_avg[1]) if market_avg[1] else 0,
                "avg_photos": int(market_avg[2]) if market_avg[2] else 0,
                "avg_posts": int(market_avg[3]) if market_avg[3] else 0,
                "avg_score": int(market_avg[4]) if market_avg[4] else 0,
                "total_competitors": market_avg[5]
            },
            "gaps": {
                "rating": round((market_avg[0] or 0) - (business[1] or 0), 2),
                "reviews": int((market_avg[1] or 0) - (business[2] or 0)),
                "photos": int((market_avg[2] or 0) - (business[3] or 0)),
                "posts": int((market_avg[3] or 0) - (business[4] or 0)),
                "score": int((market_avg[4] or 0) - (business[6] or 0))
            }
        }
    
    # ========================================================================
    # OPPORTUNITY QUERIES
    # ========================================================================
    
    def get_geographic_gaps(self, market: str = None, min_opportunity: int = 70) -> List[Dict]:
        """
        Find geographic gaps (underserved zip codes)
        
        Args:
            market: Optional market filter
            min_opportunity: Minimum opportunity score (0-100)
        
        Returns:
            List of geographic opportunities
        """
        cur = self.conn.cursor()
        
        query = """
            SELECT 
                zip_code,
                city,
                state,
                market,
                primary_category,
                competitor_count,
                opportunity_score,
                gap_severity,
                deployment_priority
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
                "category": row[4],
                "competitor_count": row[5],
                "opportunity_score": row[6],
                "gap_severity": row[7],
                "priority": row[8]
            })
        
        cur.close()
        return gaps
    
    def get_category_opportunities(self, market: str = None) -> List[Dict]:
        """
        Find underserved categories
        
        Args:
            market: Optional market filter
        
        Returns:
            List of category opportunities
        """
        cur = self.conn.cursor()
        
        query = """
            SELECT 
                category,
                market,
                total_competitors,
                saturation_level,
                opportunity_score,
                recommended_action,
                avg_rating,
                avg_review_count
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
                "competitors": row[2],
                "saturation": row[3],
                "opportunity_score": row[4],
                "recommendation": row[5],
                "avg_rating": float(row[6]) if row[6] else 0,
                "avg_reviews": int(row[7]) if row[7] else 0
            })
        
        cur.close()
        return opportunities
    
    def get_best_opportunities(self, limit: int = 10) -> List[Dict]:
        """
        Get overall best opportunities across all markets
        Combines geographic and category analysis
        
        Args:
            limit: Number of opportunities to return
        
        Returns:
            Ranked list of best opportunities
        """
        cur = self.conn.cursor()
        
        cur.execute("""
            WITH combined_opportunities AS (
                -- Geographic opportunities
                SELECT 
                    market,
                    primary_category as category,
                    zip_code as location,
                    'GEOGRAPHIC' as type,
                    opportunity_score,
                    competitor_count,
                    deployment_priority as priority
                FROM revspy_geographic_density
                WHERE is_geographic_gap = TRUE
                
                UNION ALL
                
                -- Category opportunities
                SELECT 
                    market,
                    category,
                    'Multiple zips' as location,
                    'CATEGORY' as type,
                    opportunity_score,
                    total_competitors as competitor_count,
                    CASE 
                        WHEN recommended_action = 'ENTER' THEN 'URGENT'
                        ELSE 'HIGH'
                    END as priority
                FROM revspy_category_intelligence
                WHERE opportunity_level IN ('HIGH', 'CRITICAL')
            )
            SELECT 
                market,
                category,
                location,
                type,
                opportunity_score,
                competitor_count,
                priority
            FROM combined_opportunities
            ORDER BY opportunity_score DESC, competitor_count ASC
            LIMIT %s
        """, (limit,))
        
        opportunities = []
        for row in cur.fetchall():
            opportunities.append({
                "market": row[0],
                "category": row[1],
                "location": row[2],
                "type": row[3],
                "opportunity_score": row[4],
                "competitor_count": row[5],
                "priority": row[6]
            })
        
        cur.close()
        return opportunities
    
    # ========================================================================
    # TREND ANALYSIS QUERIES
    # ========================================================================
    
    def get_competitor_trends(self, place_id: str, days: int = 30) -> Dict:
        """
        Analyze competitor trends over time
        
        Args:
            place_id: Google Place ID
            days: Number of days to analyze
        
        Returns:
            Dict with trend analysis
        """
        cur = self.conn.cursor()
        
        since_date = datetime.now() - timedelta(days=days)
        
        cur.execute("""
            SELECT 
                snapshot_date,
                competitor_rank,
                gbp_health_score,
                rating,
                review_count
            FROM revspy_competitive_benchmarks
            WHERE place_id = %s
                AND snapshot_date >= %s
            ORDER BY snapshot_date ASC
        """, (place_id, since_date))
        
        snapshots = []
        for row in cur.fetchall():
            snapshots.append({
                "date": row[0].isoformat(),
                "rank": row[1],
                "score": row[2],
                "rating": float(row[3]) if row[3] else 0,
                "reviews": row[4]
            })
        
        # Calculate trends
        if len(snapshots) >= 2:
            first = snapshots[0]
            last = snapshots[-1]
            
            trends = {
                "rank_change": first["rank"] - last["rank"] if first["rank"] and last["rank"] else 0,
                "score_change": last["score"] - first["score"] if last["score"] and first["score"] else 0,
                "review_growth": last["reviews"] - first["reviews"],
                "trend_direction": "IMPROVING" if (last["score"] or 0) > (first["score"] or 0) else "DECLINING"
            }
        else:
            trends = None
        
        cur.close()
        
        return {
            "place_id": place_id,
            "period_days": days,
            "snapshots": snapshots,
            "trends": trends
        }
    
    # ========================================================================
    # UTILITY METHODS
    # ========================================================================
    
    def get_profile_by_place_id(self, place_id: str) -> Optional[Dict]:
        """Get complete profile data for a place ID"""
        cur = self.conn.cursor()
        
        cur.execute("""
            SELECT 
                place_id,
                business_name,
                primary_category,
                secondary_categories,
                rating,
                review_count,
                photo_count,
                post_count,
                competitor_rank,
                gbp_health_score,
                competitive_threat,
                market,
                city,
                state,
                zip_code
            FROM revspy_gbp_profiles
            WHERE place_id = %s
        """, (place_id,))
        
        row = cur.fetchone()
        cur.close()
        
        if not row:
            return None
        
        return {
            "place_id": row[0],
            "business_name": row[1],
            "primary_category": row[2],
            "secondary_categories": row[3],
            "rating": float(row[4]) if row[4] else 0,
            "review_count": row[5],
            "photo_count": row[6],
            "post_count": row[7],
            "competitor_rank": row[8],
            "gbp_health_score": row[9],
            "competitive_threat": row[10],
            "market": row[11],
            "city": row[12],
            "state": row[13],
            "zip_code": row[14]
        }


# ============================================================================
# USAGE EXAMPLES
# ============================================================================

if __name__ == "__main__":
    # Initialize query library
    queries = RevSpyGBPQueries()
    
    # Example 1: Get all markets
    print("=== ALL MARKETS ===")
    markets = queries.get_all_markets()
    for market in markets[:5]:
        print(f"{market['market']} - {market['total_profiles']} profiles")
    
    # Example 2: Get market summary
    print("\n=== MARKET SUMMARY ===")
    summary = queries.get_market_summary("electrician chicago")
    print(f"Total Competitors: {summary['stats']['total_competitors']}")
    print(f"Avg Rating: {summary['stats']['avg_rating']}")
    
    # Example 3: Find geographic gaps
    print("\n=== GEOGRAPHIC GAPS ===")
    gaps = queries.get_geographic_gaps("electrician chicago", min_opportunity=80)
    for gap in gaps[:3]:
        print(f"{gap['zip_code']} - Score: {gap['opportunity_score']}")
    
    # Example 4: Find category opportunities
    print("\n=== CATEGORY OPPORTUNITIES ===")
    opps = queries.get_category_opportunities("electrician chicago")
    for opp in opps[:3]:
        print(f"{opp['category']} - Score: {opp['opportunity_score']}")
    
    # Example 5: Benchmark a business
    print("\n=== BENCHMARK ===")
    benchmark = queries.benchmark_against_market("ChIJ_TEST_001", "electrician chicago")
    if "error" not in benchmark:
        print(f"Business: {benchmark['business']['name']}")
        print(f"Rank: #{benchmark['business']['rank']}")
        print(f"Gap vs Market: {benchmark['gaps']['score']} points")
