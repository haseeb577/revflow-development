"""
RevCite: Citation Optimization Engine
Unified engine combining Clarity + IndexNow for GEO optimization
"""

from clarity_citation_tracker import CitationEngagementTracker
from indexnow_citation_notifier import CitationIndexNotifier
from datetime import datetime
from typing import Dict, List
import json


class CitationOptimizationEngine:
    """
    RevCite's core optimization engine
    This makes RevCite OPTIMIZE for citations, not just monitor
    """
    
    def __init__(self, config_file: str = "/opt/revcite/config/tracking_config.json"):
        # Load config
        with open(config_file, 'r') as f:
            config = json.load(f)
        
        self.clarity = CitationEngagementTracker(
            clarity_project_id=config["clarity_project_id"]
        )
        
        self.indexnow = CitationIndexNotifier(
            api_key=config["indexnow_key"],
            host=config.get("default_host", "example.com")
        )
        
        self.config = config
    
    def process_new_citation_discovered(self, citation_data: Dict) -> Dict:
        """
        Called when RevCite discovers a new AI citation
        
        Workflow:
        1. Inject Clarity tracking
        2. Notify search engines via IndexNow
        3. Log for analytics
        """
        
        page_url = citation_data["page_url"]
        ai_engine = citation_data.get("ai_engine", "unknown")
        
        # Notify search engines immediately
        notification_result = self.indexnow.notify_new_citations(
            page_urls=[page_url],
            citation_context={
                "ai_engine": ai_engine,
                "discovery_timestamp": datetime.now().isoformat()
            }
        )
        
        return {
            "citation_id": citation_data.get("id"),
            "search_engines_notified": notification_result["success"],
            "indexnow_status": notification_result["status"],
            "geo_optimization_status": "active",
            "timestamp": datetime.now().isoformat()
        }
    
    def run_citation_velocity_check(self, site_url: str, recent_citation_count: int, 
                                   days: int = 7) -> Dict:
        """
        Check citation velocity and notify if threshold crossed
        Key for GEO - momentum matters!
        """
        
        velocity = recent_citation_count / days
        threshold = self.config.get("citation_velocity_threshold", 2.0)
        
        if velocity >= threshold:
            # VELOCITY BOOST DETECTED - Notify search engines
            result = self.indexnow.notify_citation_boost(
                site_url=site_url,
                citation_count=recent_citation_count
            )
            
            return {
                "status": "citation_boost_detected",
                "velocity": velocity,
                "threshold": threshold,
                "notifications_sent": result["success"],
                "geo_impact": "high",
                "message": f"Notified search engines of authority surge ({velocity:.1f} citations/day)"
            }
        
        return {
            "status": "normal",
            "velocity": velocity,
            "threshold": threshold,
            "notifications_sent": False
        }


if __name__ == "__main__":
    print("✅ Citation Optimization Engine ready")
