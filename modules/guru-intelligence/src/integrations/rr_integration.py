"""
Phase 4: R&R Automation Integration
====================================
Provides webhook endpoints and API integration for R&R Automation V3.0.

Created: 2025-12-28
Location: /opt/guru-intelligence/src/integrations/rr_integration.py

Features:
- REST API endpoints for rule queries
- Webhook notifications for rule updates
- Category-based rule filtering
- Tier-based filtering for content quality
- Integration with 53-site portfolio
"""

import logging
from typing import List, Dict, Optional
from datetime import datetime
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class RRAutomationIntegration:
    """
    Integration layer for R&R Automation V3.0 (53 microsites).
    
    Provides:
    - Rule lookup by category/tier
    - Real-time rule updates via webhook
    - Content validation rules
    - Anti-duplication rules
    """
    
    def __init__(self, knowledge_graph_url: str, rr_webhook_url: Optional[str] = None):
        """
        Initialize R&R integration.
        
        Args:
            knowledge_graph_url: URL to Knowledge Graph API
            rr_webhook_url: URL to R&R webhook endpoint (optional)
        """
        self.knowledge_graph_url = knowledge_graph_url.rstrip('/')
        self.rr_webhook_url = rr_webhook_url
        
        # Setup HTTP session with retries
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        logger.info(f"✅ RRAutomationIntegration initialized")
        logger.info(f"   Knowledge Graph: {knowledge_graph_url}")
        logger.info(f"   R&R Webhook: {rr_webhook_url or 'Not configured'}")
    
    def get_rules_for_content_generation(
        self,
        category: Optional[str] = None,
        tier: Optional[int] = None,
        page_type: Optional[str] = None
    ) -> List[Dict]:
        """
        Get rules relevant for content generation.
        
        Used by R&R Automation when generating new content.
        
        Args:
            category: Rule category (e.g., 'Content Strategy')
            tier: Tier level (1=universal, 2=validated, 3=experimental)
            page_type: Page type (homepage, service, location, etc.)
            
        Returns:
            List of applicable rules
        """
        try:
            # Build query parameters
            params = {}
            if category:
                params['category'] = category
            if tier:
                params['tier'] = tier
            
            # Query Knowledge Graph
            response = self.session.get(
                f"{self.knowledge_graph_url}/api/v1/rules",
                params=params,
                timeout=10
            )
            response.raise_for_status()
            
            rules = response.json()
            
            # Filter by page type if specified
            if page_type:
                rules = [r for r in rules if self._is_relevant_for_page_type(r, page_type)]
            
            logger.info(f"📋 Retrieved {len(rules)} rules for R&R content generation")
            return rules
            
        except requests.RequestException as e:
            logger.error(f"Error fetching rules from Knowledge Graph: {e}")
            return []
    
    def _is_relevant_for_page_type(self, rule: Dict, page_type: str) -> bool:
        """Check if rule is relevant for specific page type"""
        # Universal rules (tier 1) apply to all pages
        if rule.get('tier') == 1:
            return True
        
        # Map page types to categories
        page_type_categories = {
            'homepage': ['Content Strategy', 'SEO Best Practices', 'Technical SEO'],
            'service': ['Content Strategy', 'Service Pages', 'Conversion Optimization'],
            'location': ['Local SEO', 'Content Strategy'],
            'emergency': ['Content Strategy', 'Local SEO', 'Conversion Optimization'],
            'contact': ['Local SEO', 'Conversion Optimization'],
            'about': ['Content Strategy', 'Brand Building'],
            'blog': ['Content Strategy', 'SEO Best Practices']
        }
        
        relevant_categories = page_type_categories.get(page_type, ['Content Strategy'])
        return rule.get('category') in relevant_categories
    
    def get_validation_rules(self) -> List[Dict]:
        """
        Get rules for content validation.
        
        Used by R&R Automation's 4-layer validation engine.
        
        Returns:
            List of validation rules
        """
        try:
            # Get all Tier 1 universal rules + validation-specific rules
            response = self.session.get(
                f"{self.knowledge_graph_url}/api/v1/rules",
                params={'tier': 1},
                timeout=10
            )
            response.raise_for_status()
            
            rules = response.json()
            
            logger.info(f"✅ Retrieved {len(rules)} validation rules for R&R")
            return rules
            
        except requests.RequestException as e:
            logger.error(f"Error fetching validation rules: {e}")
            return []
    
    def get_anti_duplication_rules(self) -> List[Dict]:
        """
        Get rules for anti-duplication checks.
        
        Used by R&R's 3-layer anti-duplication defense.
        
        Returns:
            List of anti-duplication rules
        """
        try:
            # Search for anti-duplication related rules
            response = self.session.post(
                f"{self.knowledge_graph_url}/api/v1/search",
                json={
                    'query': 'duplication semantic similarity unique content',
                    'limit': 20
                },
                timeout=10
            )
            response.raise_for_status()
            
            rules = response.json().get('results', [])
            
            logger.info(f"🔍 Retrieved {len(rules)} anti-duplication rules for R&R")
            return rules
            
        except requests.RequestException as e:
            logger.error(f"Error fetching anti-duplication rules: {e}")
            return []
    
    def notify_rr_of_rule_update(
        self,
        rule_id: str,
        rule_name: str,
        category: str,
        tier: int,
        update_type: str = 'new'
    ) -> bool:
        """
        Notify R&R Automation of rule updates via webhook.
        
        Args:
            rule_id: Rule identifier
            rule_name: Rule name
            category: Rule category
            tier: Rule tier
            update_type: 'new', 'updated', or 'deleted'
            
        Returns:
            True if notification sent successfully
        """
        if not self.rr_webhook_url:
            logger.warning("R&R webhook URL not configured - skipping notification")
            return False
        
        try:
            payload = {
                'event': 'rule_update',
                'update_type': update_type,
                'rule': {
                    'rule_id': rule_id,
                    'rule_name': rule_name,
                    'category': category,
                    'tier': tier
                },
                'timestamp': datetime.utcnow().isoformat(),
                'source': 'guru_intelligence'
            }
            
            response = self.session.post(
                self.rr_webhook_url,
                json=payload,
                timeout=5
            )
            response.raise_for_status()
            
            logger.info(f"✅ Notified R&R of {update_type} rule: {rule_name}")
            return True
            
        except requests.RequestException as e:
            logger.error(f"Failed to notify R&R webhook: {e}")
            return False
    
    def batch_notify_rr(self, rules: List[Dict]) -> int:
        """
        Send batch notification of multiple rule updates.
        
        Args:
            rules: List of rule dicts
            
        Returns:
            Count of successful notifications
        """
        if not self.rr_webhook_url:
            logger.warning("R&R webhook URL not configured - skipping batch notification")
            return 0
        
        try:
            payload = {
                'event': 'batch_rule_update',
                'count': len(rules),
                'rules': rules,
                'timestamp': datetime.utcnow().isoformat(),
                'source': 'guru_intelligence'
            }
            
            response = self.session.post(
                self.rr_webhook_url,
                json=payload,
                timeout=10
            )
            response.raise_for_status()
            
            logger.info(f"✅ Sent batch notification of {len(rules)} rules to R&R")
            return len(rules)
            
        except requests.RequestException as e:
            logger.error(f"Failed to send batch notification: {e}")
            return 0
    
    def get_rules_summary_for_site(self, site_id: str) -> Dict:
        """
        Get summary of applicable rules for a specific site.
        
        Args:
            site_id: Site identifier from 53-site portfolio
            
        Returns:
            Summary dict with rule counts and categories
        """
        try:
            # Get all rules
            response = self.session.get(
                f"{self.knowledge_graph_url}/api/v1/rules",
                timeout=10
            )
            response.raise_for_status()
            
            all_rules = response.json()
            
            # Categorize rules
            summary = {
                'site_id': site_id,
                'total_rules': len(all_rules),
                'by_tier': {1: 0, 2: 0, 3: 0},
                'by_category': {},
                'last_updated': datetime.utcnow().isoformat()
            }
            
            for rule in all_rules:
                tier = rule.get('tier', 2)
                summary['by_tier'][tier] = summary['by_tier'].get(tier, 0) + 1
                
                category = rule.get('category', 'Unknown')
                summary['by_category'][category] = summary['by_category'].get(category, 0) + 1
            
            return summary
            
        except requests.RequestException as e:
            logger.error(f"Error getting rules summary: {e}")
            return {
                'site_id': site_id,
                'error': str(e)
            }


# Integration with FastAPI
from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel, Field


router = APIRouter(prefix="/rr-integration", tags=["r&r"])

# Will be injected by main app
rr_integration: Optional[RRAutomationIntegration] = None


def set_rr_integration(integration: RRAutomationIntegration):
    """Inject R&R integration dependency"""
    global rr_integration
    rr_integration = integration


class RuleQuery(BaseModel):
    """Query parameters for rule lookup"""
    category: Optional[str] = None
    tier: Optional[int] = Field(None, ge=1, le=3)
    page_type: Optional[str] = None


class WebhookTest(BaseModel):
    """Test webhook notification"""
    rule_id: str
    rule_name: str
    category: str
    tier: int
    update_type: str = 'new'


@router.get("/rules/content-generation")
async def get_content_generation_rules(
    category: Optional[str] = Query(None),
    tier: Optional[int] = Query(None, ge=1, le=3),
    page_type: Optional[str] = Query(None)
):
    """
    Get rules for R&R content generation.
    
    Query parameters:
    - category: Filter by category
    - tier: Filter by tier (1, 2, or 3)
    - page_type: Filter by page type (homepage, service, location, etc.)
    
    Returns rules applicable to the specified content type.
    """
    if not rr_integration:
        raise HTTPException(status_code=500, detail="R&R integration not initialized")
    
    rules = rr_integration.get_rules_for_content_generation(
        category=category,
        tier=tier,
        page_type=page_type
    )
    
    return {
        "count": len(rules),
        "filters": {
            "category": category,
            "tier": tier,
            "page_type": page_type
        },
        "rules": rules
    }


@router.get("/rules/validation")
async def get_validation_rules():
    """
    Get rules for R&R content validation.
    
    Returns Tier 1 universal rules and validation-specific rules.
    Used by R&R's 4-layer validation engine.
    """
    if not rr_integration:
        raise HTTPException(status_code=500, detail="R&R integration not initialized")
    
    rules = rr_integration.get_validation_rules()
    
    return {
        "count": len(rules),
        "rules": rules
    }


@router.get("/rules/anti-duplication")
async def get_anti_duplication_rules():
    """
    Get rules for R&R anti-duplication checks.
    
    Returns rules for R&R's 3-layer anti-duplication defense.
    """
    if not rr_integration:
        raise HTTPException(status_code=500, detail="R&R integration not initialized")
    
    rules = rr_integration.get_anti_duplication_rules()
    
    return {
        "count": len(rules),
        "rules": rules
    }


@router.get("/sites/{site_id}/summary")
async def get_site_rules_summary(site_id: str):
    """
    Get summary of applicable rules for a specific site.
    
    Args:
        site_id: Site identifier from 53-site portfolio
        
    Returns rule counts by tier and category.
    """
    if not rr_integration:
        raise HTTPException(status_code=500, detail="R&R integration not initialized")
    
    summary = rr_integration.get_rules_summary_for_site(site_id)
    
    return summary


@router.post("/webhook/test")
async def test_webhook(payload: WebhookTest):
    """
    Test R&R webhook notification.
    
    Sends a test notification to R&R Automation webhook.
    """
    if not rr_integration:
        raise HTTPException(status_code=500, detail="R&R integration not initialized")
    
    success = rr_integration.notify_rr_of_rule_update(
        rule_id=payload.rule_id,
        rule_name=payload.rule_name,
        category=payload.category,
        tier=payload.tier,
        update_type=payload.update_type
    )
    
    if success:
        return {"status": "success", "message": "Webhook notification sent"}
    else:
        raise HTTPException(status_code=500, detail="Failed to send webhook notification")


@router.get("/health")
async def rr_integration_health():
    """Health check for R&R integration"""
    if not rr_integration:
        return {
            "status": "unhealthy",
            "message": "R&R integration not initialized"
        }
    
    return {
        "status": "healthy",
        "knowledge_graph_url": rr_integration.knowledge_graph_url,
        "webhook_configured": rr_integration.rr_webhook_url is not None
    }


# Example standalone usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Initialize integration
    integration = RRAutomationIntegration(
        knowledge_graph_url="http://localhost:8102",
        rr_webhook_url="http://automation.smarketsherpa.ai/webhooks/guru-updates"
    )
    
    # Get content generation rules
    rules = integration.get_rules_for_content_generation(
        category="Content Strategy",
        tier=1,
        page_type="homepage"
    )
    
    print(f"\n📋 Retrieved {len(rules)} rules for homepage content generation\n")
    
    # Get validation rules
    validation_rules = integration.get_validation_rules()
    print(f"✅ Retrieved {len(validation_rules)} validation rules\n")
    
    # Get site summary
    summary = integration.get_rules_summary_for_site("site_001")
    print(f"📊 Site Summary: {summary}\n")
