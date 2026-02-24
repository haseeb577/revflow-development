"""
RevFlow OS™ Daily Cost Aggregation Worker
==========================================
Runs every night at 1:00 AM to aggregate raw API logs into summary table

Purpose:
- Aggregate yesterday's api_audit_logs into daily_cost_summary
- Calculate breakdowns by service, model, and industry
- Enable fast dashboard queries (read 30 rows instead of millions)
- Track escalation rates and cache efficiency

Usage:
    # Manual run:
    python3 daily_cleanup_worker.py
    
    # Automated (crontab):
    0 1 * * * /usr/bin/python3 /opt/revpublish/backend/workers/daily_cleanup_worker.py
"""

import os
import sys
import psycopg2
from datetime import datetime, timedelta
from typing import Dict

import os
from pathlib import Path

def load_env_file(env_file="/opt/shared-api-engine/.env"):
    """Load environment variables from file"""
    if not Path(env_file).exists():
        return
    
    with open(env_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                # Remove quotes
                value = value.strip().strip('"').strip("'")
                os.environ[key] = value

# Load environment on import
load_env_file()



import os
from pathlib import Path

def load_env_file(env_file="/opt/shared-api-engine/.env"):
    """Load environment variables from file"""
    if not Path(env_file).exists():
        return
    
    with open(env_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                # Remove quotes
                value = value.strip().strip('"').strip("'")
                os.environ[key] = value

# Load environment on import
load_env_file()


import logging
import json

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DailyCleanupWorker:
    """
    Aggregates raw API logs into daily summaries
    """
    
    def __init__(self, db_url: str = None):
        """
        Initialize worker with database connection
        
        Args:
            db_url: PostgreSQL connection URL (from env if not provided)
        """
        self.db_url = db_url or os.getenv("DATABASE_URL")
        
        if not self.db_url:
            raise ValueError("DATABASE_URL must be set in environment")
        
        self.conn = psycopg2.connect(self.db_url)
        
        logger.info("Daily Cleanup Worker initialized")
    
    def run(self, target_date: datetime = None):
        """
        Run aggregation for a specific date
        
        Args:
            target_date: Date to aggregate (defaults to yesterday)
        """
        if target_date is None:
            # Default to yesterday
            target_date = (datetime.now() - timedelta(days=1)).date()
        
        logger.info(f"Starting aggregation for {target_date}")
        
        # Step 1: Aggregate costs
        summary = self._aggregate_costs(target_date)
        
        # Step 2: Calculate breakdowns
        api_breakdown = self._calculate_api_breakdown(target_date)
        model_breakdown = self._calculate_model_breakdown(target_date)
        industry_breakdown = self._calculate_industry_breakdown(target_date)
        
        # Step 3: Find top performers
        top_industry = self._find_top_performer(target_date, "industry_tag")
        top_service = self._find_top_performer(target_date, "service_name")
        top_model = self._find_top_performer(target_date, "model_name")
        
        # Step 4: Calculate efficiency metrics
        escalation_count = self._count_escalations(target_date)
        
        # Step 5: Insert/update summary
        self._upsert_summary(
            target_date,
            summary,
            api_breakdown,
            model_breakdown,
            industry_breakdown,
            top_industry,
            top_service,
            top_model,
            escalation_count
        )
        
        logger.info(f"✓ Aggregation complete for {target_date}")
        
        return summary
    
    def _aggregate_costs(self, target_date) -> Dict:
        """
        Aggregate total costs and tokens for the date
        
        Args:
            target_date: Date to aggregate
        
        Returns:
            Dict with totals
        """
        cursor = self.conn.cursor()
        
        cursor.execute("""
            SELECT 
                COALESCE(SUM(credits_spent), 0) as total_usd,
                COALESCE(SUM(input_tokens + output_tokens), 0) as total_tokens
            FROM api_audit_logs
            WHERE DATE(timestamp) = %s
        """, (target_date,))
        
        result = cursor.fetchone()
        cursor.close()
        
        return {
            "total_usd": float(result[0]),
            "total_tokens": int(result[1])
        }
    
    def _calculate_api_breakdown(self, target_date) -> Dict:
        """
        Calculate cost breakdown by API service
        
        Args:
            target_date: Date to analyze
        
        Returns:
            Dict mapping service -> cost
        """
        cursor = self.conn.cursor()
        
        cursor.execute("""
            SELECT 
                service_name,
                SUM(credits_spent) as total_cost
            FROM api_audit_logs
            WHERE DATE(timestamp) = %s
            GROUP BY service_name
        """, (target_date,))
        
        breakdown = {}
        for row in cursor.fetchall():
            service_name = row[0]
            total_cost = float(row[1])
            breakdown[service_name] = total_cost
        
        cursor.close()
        
        return breakdown
    
    def _calculate_model_breakdown(self, target_date) -> Dict:
        """
        Calculate cost breakdown by AI model
        
        Args:
            target_date: Date to analyze
        
        Returns:
            Dict mapping model -> cost
        """
        cursor = self.conn.cursor()
        
        cursor.execute("""
            SELECT 
                model_name,
                SUM(credits_spent) as total_cost
            FROM api_audit_logs
            WHERE DATE(timestamp) = %s
              AND model_name IS NOT NULL
            GROUP BY model_name
        """, (target_date,))
        
        breakdown = {}
        for row in cursor.fetchall():
            model_name = row[0]
            total_cost = float(row[1])
            breakdown[model_name] = total_cost
        
        cursor.close()
        
        return breakdown
    
    def _calculate_industry_breakdown(self, target_date) -> Dict:
        """
        Calculate cost breakdown by industry
        
        Args:
            target_date: Date to analyze
        
        Returns:
            Dict mapping industry -> cost
        """
        cursor = self.conn.cursor()
        
        cursor.execute("""
            SELECT 
                industry_tag,
                SUM(credits_spent) as total_cost
            FROM api_audit_logs
            WHERE DATE(timestamp) = %s
              AND industry_tag IS NOT NULL
            GROUP BY industry_tag
        """, (target_date,))
        
        breakdown = {}
        for row in cursor.fetchall():
            industry = row[0]
            total_cost = float(row[1])
            breakdown[industry] = total_cost
        
        cursor.close()
        
        return breakdown
    
    def _find_top_performer(self, target_date, field: str) -> str:
        """
        Find top performer (highest cost) for a field
        
        Args:
            target_date: Date to analyze
            field: Field to analyze (industry_tag, service_name, model_name)
        
        Returns:
            Name of top performer
        """
        cursor = self.conn.cursor()
        
        cursor.execute(f"""
            SELECT {field}
            FROM api_audit_logs
            WHERE DATE(timestamp) = %s
              AND {field} IS NOT NULL
            GROUP BY {field}
            ORDER BY SUM(credits_spent) DESC
            LIMIT 1
        """, (target_date,))
        
        result = cursor.fetchone()
        cursor.close()
        
        return result[0] if result else None
    
    def _count_escalations(self, target_date) -> int:
        """
        Count how many times we escalated to expensive models
        
        Args:
            target_date: Date to analyze
        
        Returns:
            Count of escalations
        """
        cursor = self.conn.cursor()
        
        cursor.execute("""
            SELECT COUNT(*)
            FROM api_audit_logs
            WHERE DATE(timestamp) = %s
              AND escalated = TRUE
        """, (target_date,))
        
        result = cursor.fetchone()
        cursor.close()
        
        return int(result[0]) if result else 0
    
    def _upsert_summary(
        self,
        target_date,
        summary: Dict,
        api_breakdown: Dict,
        model_breakdown: Dict,
        industry_breakdown: Dict,
        top_industry: str,
        top_service: str,
        top_model: str,
        escalation_count: int
    ):
        """
        Insert or update daily summary
        
        Args:
            target_date: Date being summarized
            summary: Total cost/tokens
            api_breakdown: Cost by service
            model_breakdown: Cost by model
            industry_breakdown: Cost by industry
            top_industry: Top industry by cost
            top_service: Top service by cost
            top_model: Top model by cost
            escalation_count: Number of escalations
        """
        cursor = self.conn.cursor()
        
        cursor.execute("""
            INSERT INTO daily_cost_summary (
                summary_date,
                total_usd_spent,
                total_tokens_consumed,
                api_breakdown,
                model_breakdown,
                industry_breakdown,
                escalation_count,
                top_industry,
                top_service,
                top_model
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (summary_date) DO UPDATE SET
                total_usd_spent = EXCLUDED.total_usd_spent,
                total_tokens_consumed = EXCLUDED.total_tokens_consumed,
                api_breakdown = EXCLUDED.api_breakdown,
                model_breakdown = EXCLUDED.model_breakdown,
                industry_breakdown = EXCLUDED.industry_breakdown,
                escalation_count = EXCLUDED.escalation_count,
                top_industry = EXCLUDED.top_industry,
                top_service = EXCLUDED.top_service,
                top_model = EXCLUDED.top_model,
                updated_at = CURRENT_TIMESTAMP
        """, (
            target_date,
            summary['total_usd'],
            summary['total_tokens'],
            json.dumps(api_breakdown),
            json.dumps(model_breakdown),
            json.dumps(industry_breakdown),
            escalation_count,
            top_industry,
            top_service,
            top_model
        ))
        
        self.conn.commit()
        cursor.close()
        
        logger.info(f"✓ Summary saved: ${summary['total_usd']:.2f}, {escalation_count} escalations")
    
    def cleanup_old_logs(self, days_to_keep: int = 90):
        """
        Delete raw logs older than specified days
        (Keep summaries forever, only delete raw logs)
        
        Args:
            days_to_keep: How many days of raw logs to keep
        """
        cursor = self.conn.cursor()
        
        cursor.execute("""
            DELETE FROM api_audit_logs
            WHERE timestamp < CURRENT_DATE - INTERVAL '%s days'
        """, (days_to_keep,))
        
        deleted_count = cursor.rowcount
        self.conn.commit()
        cursor.close()
        
        logger.info(f"✓ Cleaned up {deleted_count} old log entries")
    
    def close(self):
        """Close database connection"""
        self.conn.close()
        logger.info("Database connection closed")


# ============================================================================
# Main Entry Point
# ============================================================================

def main():
    """
    Main function for running as script or cron job
    """
    logger.info("=" * 60)
    logger.info("RevFlow OS Daily Cost Aggregation Worker")
    logger.info("=" * 60)
    
    worker = DailyCleanupWorker()
    
    try:
        # Aggregate yesterday's data
        yesterday = (datetime.now() - timedelta(days=1)).date()
        summary = worker.run(target_date=yesterday)
        
        logger.info("")
        logger.info("Summary:")
        logger.info(f"  Date: {yesterday}")
        logger.info(f"  Total cost: ${summary['total_usd']:.2f}")
        logger.info(f"  Total tokens: {summary['total_tokens']:,}")
        logger.info("")
        
        # Optional: Cleanup old logs
        # worker.cleanup_old_logs(days_to_keep=90)
        
        logger.info("✓ Daily aggregation complete!")
        
    except Exception as e:
        logger.error(f"✗ Aggregation failed: {e}")
        raise
    
    finally:
        worker.close()


if __name__ == "__main__":
    main()
