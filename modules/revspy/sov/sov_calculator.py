
"""
RevInsight™ Share of Voice Calculator
Competitive intelligence for AI citations
"""

from typing import Dict, List
from datetime import datetime, date, timedelta
import psycopg2
from psycopg2.extras import RealDictCursor
import os
import logging

from dotenv import load_dotenv
load_dotenv('/opt/shared-api-engine/.env')

logger = logging.getLogger(__name__)

def get_db_connection():
    """Get database connection, preferring DATABASE_URL"""
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return psycopg2.connect(database_url)
    return psycopg2.connect(
        host=os.getenv('POSTGRES_HOST', 'localhost'),
        port=int(os.getenv('POSTGRES_PORT', 5432)),
        database=os.getenv('POSTGRES_DB', 'revflow'),
        user=os.getenv('POSTGRES_USER', 'revflow'),
        password=os.getenv('POSTGRES_PASSWORD', '')
    )


class ShareOfVoiceCalculator:
    """Calculate and track Share of Voice vs competitors"""
    
    def __init__(self, site_id: int, client_domains: List[str], 
                 competitor_domains: List[str]):
        self.site_id = site_id
        self.client_domains = [d.lower() for d in client_domains]
        self.competitor_domains = [d.lower() for d in competitor_domains]
        
    def calculate_from_results(self, start_date: date, end_date: date) -> Dict:
        """Calculate SOV from stored citation results"""
        conn = get_db_connection()
        
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT 
                        r.ai_platform,
                        r.citations,
                        r.client_mentioned,
                        r.competitor_domains
                    FROM ai_citation_results r
                    JOIN ai_citation_queries q ON r.query_id = q.id
                    WHERE q.site_id = %s
                      AND DATE(r.scraped_at) BETWEEN %s AND %s
                """, (self.site_id, start_date, end_date))
                
                results = cur.fetchall()
                
        finally:
            conn.close()
        
        sov_data = {
            'by_platform': {},
            'by_competitor': {},
            'overall': {
                'client_mentions': 0,
                'total_opportunities': 0,
                'client_sov': 0
            }
        }
        
        platform_stats = {}
        competitor_stats = {d: 0 for d in self.competitor_domains}
        
        for row in results:
            platform = row['ai_platform']
            
            if platform not in platform_stats:
                platform_stats[platform] = {
                    'client_mentions': 0,
                    'total': 0
                }
            
            platform_stats[platform]['total'] += 1
            sov_data['overall']['total_opportunities'] += 1
            
            if row['client_mentioned']:
                platform_stats[platform]['client_mentions'] += 1
                sov_data['overall']['client_mentions'] += 1
            
            for comp_domain in row.get('competitor_domains', []) or []:
                comp_lower = comp_domain.lower()
                if comp_lower in competitor_stats:
                    competitor_stats[comp_lower] += 1
        
        # Calculate percentages
        for platform, stats in platform_stats.items():
            total = stats['total']
            if total > 0:
                sov_data['by_platform'][platform] = {
                    'client_sov': round(stats['client_mentions'] / total * 100, 1),
                    'total_queries': total,
                    'client_mentions': stats['client_mentions']
                }
        
        total_opps = sov_data['overall']['total_opportunities']
        if total_opps > 0:
            sov_data['overall']['client_sov'] = round(
                sov_data['overall']['client_mentions'] / total_opps * 100, 1
            )
            
            for comp_domain, mentions in competitor_stats.items():
                comp_sov = round(mentions / total_opps * 100, 1)
                sov_data['by_competitor'][comp_domain] = {
                    'mentions': mentions,
                    'sov': comp_sov,
                    'gap': round(sov_data['overall']['client_sov'] - comp_sov, 1)
                }
        
        return sov_data
    
    def identify_citation_gaps(self, limit: int = 50) -> List[Dict]:
        """Identify queries where competitors cited but client is not"""
        conn = get_db_connection()
        gaps = []
        
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT 
                        q.query_rendered,
                        q.query_type,
                        r.ai_platform,
                        r.competitor_domains,
                        r.citations
                    FROM ai_citation_results r
                    JOIN ai_citation_queries q ON r.query_id = q.id
                    WHERE q.site_id = %s
                      AND r.client_mentioned = FALSE
                      AND COALESCE(jsonb_array_length(r.competitor_domains), 0) > 0
                    ORDER BY r.scraped_at DESC
                    LIMIT %s
                """, (self.site_id, limit))
                
                results = cur.fetchall()
                
                for row in results:
                    gaps.append({
                        'query': row['query_rendered'],
                        'query_type': row['query_type'],
                        'platform': row['ai_platform'],
                        'competitors_cited': row['competitor_domains'],
                        'opportunity': 'HIGH',
                        'recommendation': f"Optimize content for: {row['query_rendered'][:80]}..."
                    })
                    
        finally:
            conn.close()
            
        return gaps
    
    def save_daily_sov(self, sov_data: Dict, measurement_date: date):
        """Save SOV data to database"""
        conn = get_db_connection()
        
        try:
            with conn.cursor() as cur:
                for comp_domain, data in sov_data.get('by_competitor', {}).items():
                    for platform, platform_data in sov_data.get('by_platform', {}).items():
                        cur.execute("""
                            INSERT INTO ai_share_of_voice 
                            (site_id, competitor_domain, measurement_date, ai_platform,
                             client_mentions, competitor_mentions, total_queries,
                             client_sov_percent, competitor_sov_percent, gap_percent)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (site_id, competitor_domain, measurement_date, ai_platform)
                            DO UPDATE SET
                                client_mentions = EXCLUDED.client_mentions,
                                competitor_mentions = EXCLUDED.competitor_mentions,
                                total_queries = EXCLUDED.total_queries,
                                client_sov_percent = EXCLUDED.client_sov_percent,
                                competitor_sov_percent = EXCLUDED.competitor_sov_percent,
                                gap_percent = EXCLUDED.gap_percent
                        """, (
                            self.site_id,
                            comp_domain,
                            measurement_date,
                            platform,
                            sov_data['overall']['client_mentions'],
                            data['mentions'],
                            platform_data['total_queries'],
                            platform_data['client_sov'],
                            data['sov'],
                            data['gap']
                        ))
                
                conn.commit()
        finally:
            conn.close()


def get_sov_history(site_id: int, days: int = 30) -> List[Dict]:
    """Get SOV history for a site"""
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT 
                    measurement_date,
                    competitor_domain,
                    ai_platform,
                    client_sov_percent,
                    competitor_sov_percent,
                    gap_percent
                FROM ai_share_of_voice
                WHERE site_id = %s
                  AND measurement_date >= CURRENT_DATE - INTERVAL '%s days'
                ORDER BY measurement_date DESC, competitor_domain
            """, (site_id, days))
            return cur.fetchall()
    finally:
        conn.close()
