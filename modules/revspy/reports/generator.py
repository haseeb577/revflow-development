"""
RevSPY™ Report Generator
Main engine for generating competitive analysis reports
"""
import psycopg2
from psycopg2.extras import RealDictCursor
import json
from datetime import datetime
from typing import Dict, List, Optional
import os
from dotenv import load_dotenv

# Load shared environment
load_dotenv('/opt/shared-api-engine/.env')

class ReportGenerator:
    """Main report generation engine"""
    
    def __init__(self):
        self.database_url = os.getenv('DATABASE_URL')
        self.db_config = {
            'host': os.getenv('POSTGRES_HOST', os.getenv('DATABASE_HOST', 'localhost')),
            'port': int(os.getenv('POSTGRES_PORT', os.getenv('DATABASE_PORT', '5432'))),
            'database': os.getenv('POSTGRES_DB', os.getenv('DATABASE_NAME', 'revflow')),
            'user': os.getenv('POSTGRES_USER', os.getenv('DATABASE_USER', 'revflow')),
            'password': os.getenv('POSTGRES_PASSWORD', os.getenv('DATABASE_PASSWORD', ''))
        }

    def get_connection(self):
        """Get database connection, preferring DATABASE_URL"""
        if self.database_url:
            return psycopg2.connect(self.database_url)
        return psycopg2.connect(**self.db_config)
    
    def generate_prospect_report(self, prospect_place_id: str, market: str) -> Dict:
        """
        Generate competitive analysis for prospect
        Used for: Sales outreach, initial assessments
        """
        conn = self.get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Get prospect data
        cur.execute("""
            SELECT 
                business_name, primary_category, rating, review_count,
                photo_count, post_count, competitor_rank, gbp_health_score,
                competitive_threat, city, state, zip_code
            FROM revspy_gbp_profiles
            WHERE place_id = %s
        """, (prospect_place_id,))
        
        prospect = cur.fetchone()
        if not prospect:
            cur.close()
            conn.close()
            return {"error": "Prospect not found"}
        
        # Get market averages
        cur.execute("""
            SELECT 
                AVG(rating) as avg_rating,
                AVG(review_count) as avg_reviews,
                AVG(photo_count) as avg_photos,
                AVG(post_count) as avg_posts,
                COUNT(*) as total_competitors
            FROM revspy_gbp_profiles
            WHERE market = %s AND primary_category = %s
        """, (market, prospect['primary_category']))
        
        market_data = cur.fetchone()
        
        # Get top 3 competitors
        cur.execute("""
            SELECT 
                business_name, rating, review_count, photo_count,
                post_count, competitor_rank, gbp_health_score
            FROM revspy_gbp_profiles
            WHERE market = %s 
                AND primary_category = %s
                AND place_id != %s
            ORDER BY competitor_rank ASC
            LIMIT 3
        """, (market, prospect['primary_category'], prospect_place_id))
        
        competitors = cur.fetchall()
        
        # Build report
        report = {
            "report_type": "prospect_analysis",
            "generated_at": datetime.now().isoformat(),
            "prospect": dict(prospect),
            "market": {
                "avg_rating": float(market_data['avg_rating'] or 0),
                "avg_reviews": int(market_data['avg_reviews'] or 0),
                "avg_photos": int(market_data['avg_photos'] or 0),
                "avg_posts": int(market_data['avg_posts'] or 0),
                "total_competitors": market_data['total_competitors']
            },
            "gaps": {
                "rating": round((market_data['avg_rating'] or 0) - (prospect['rating'] or 0), 2),
                "reviews": (market_data['avg_reviews'] or 0) - (prospect['review_count'] or 0),
                "photos": (market_data['avg_photos'] or 0) - (prospect['photo_count'] or 0),
                "posts": (market_data['avg_posts'] or 0) - (prospect['post_count'] or 0),
                "rank_position": prospect['competitor_rank']
            },
            "top_competitors": [dict(c) for c in competitors],
            "recommendation": self._generate_recommendation(
                prospect['gbp_health_score'],
                market_data['total_competitors'],
                prospect['competitor_rank']
            )
        }
        
        cur.close()
        conn.close()
        
        return report
    
    def generate_monthly_client_report(self, client_place_id: str, market: str) -> Dict:
        """
        Generate monthly progress report for existing client
        Used for: Retention, progress tracking
        """
        conn = self.get_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Get current data
        cur.execute("""
            SELECT 
                business_name, rating, review_count, photo_count,
                competitor_rank, gbp_health_score, competitive_threat
            FROM revspy_gbp_profiles
            WHERE place_id = %s
        """, (client_place_id,))
        
        current = cur.fetchone()
        if not current:
            cur.close()
            conn.close()
            return {"error": "Client not found"}
        
        # Get previous month data (from benchmarks)
        cur.execute("""
            SELECT 
                rating, review_count, competitor_rank, gbp_health_score
            FROM revspy_competitive_benchmarks
            WHERE place_id = %s
            ORDER BY snapshot_date DESC
            LIMIT 1 OFFSET 1
        """, (client_place_id,))
        
        previous = cur.fetchone()
        
        # Calculate changes
        changes = None
        if previous:
            changes = {
                "rating": round((current['rating'] or 0) - (previous['rating'] or 0), 2),
                "reviews": (current['review_count'] or 0) - (previous['review_count'] or 0),
                "rank": (previous['competitor_rank'] or 0) - (current['competitor_rank'] or 0),  # Positive = moved up
                "score": (current['gbp_health_score'] or 0) - (previous['gbp_health_score'] or 0)
            }
        
        report = {
            "report_type": "monthly_client_progress",
            "generated_at": datetime.now().isoformat(),
            "client": dict(current),
            "monthly_changes": changes,
            "performance": self._calculate_performance(changes) if changes else "NEW CLIENT",
            "report_month": datetime.now().strftime("%B %Y")
        }
        
        cur.close()
        conn.close()
        
        return report
    
    def _generate_recommendation(self, health_score: int, total_competitors: int, rank: int) -> Dict:
        """Generate sales recommendation"""
        if rank and rank <= 3:
            return {
                "priority": "MAINTAIN",
                "message": "You're in the top 3! Focus on maintaining position.",
                "investment": "$1,500-2,000/month"
            }
        elif health_score and health_score >= 80:
            return {
                "priority": "OPTIMIZE",
                "message": "Strong foundation. Small improvements for big gains.",
                "investment": "$1,500-2,500/month"
            }
        elif health_score and health_score >= 60:
            return {
                "priority": "IMPROVE",
                "message": "Significant opportunity to close gaps vs competition.",
                "investment": "$2,500-3,500/month"
            }
        else:
            return {
                "priority": "REBUILD",
                "message": "Major overhaul needed to compete effectively.",
                "investment": "$3,500-5,000/month"
            }
    
    def _calculate_performance(self, changes: Dict) -> str:
        """Calculate overall monthly performance"""
        if not changes:
            return "NEW CLIENT"
        
        score = 0
        
        # Rank improvement (most important)
        if changes['rank'] > 0:  # Moved up
            score += 40
        elif changes['rank'] < 0:  # Moved down
            score -= 30
        
        # Score improvement
        if changes['score'] >= 5:
            score += 30
        elif changes['score'] > 0:
            score += 15
        
        # Review growth
        if changes['reviews'] >= 5:
            score += 30
        elif changes['reviews'] > 0:
            score += 15
        
        if score >= 70:
            return "EXCELLENT"
        elif score >= 40:
            return "GOOD"
        elif score >= 0:
            return "FAIR"
        else:
            return "NEEDS ATTENTION"
