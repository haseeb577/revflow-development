"""REVFLOW SCORING CLIENT - Shared library for all services"""
import requests
import logging

logger = logging.getLogger(__name__)
SCORING_API_URL = "http://localhost:8500"

class RevFlowScoringClient:
    def __init__(self, api_url=SCORING_API_URL):
        self.api_url = api_url
    
    def health_check(self):
        try:
            response = requests.get(f"{self.api_url}/health", timeout=5)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
    
    def get_profiles(self):
        try:
            response = requests.get(f"{self.api_url}/profiles", timeout=5)
            return response.json() if response.status_code == 200 else None
        except Exception as e:
            logger.error(f"Error getting profiles: {e}")
            return None
    
    def get_profile(self, industry_slug, customer_id=None):
        try:
            params = {'customer_id': customer_id} if customer_id else {}
            response = requests.get(f"{self.api_url}/profile/{industry_slug}", params=params, timeout=5)
            return response.json() if response.status_code == 200 else None
        except Exception as e:
            logger.error(f"Error getting profile: {e}")
            return None
    
    def calculate_score(self, module_scores, industry_slug, customer_id=None):
        try:
            payload = {'module_scores': module_scores, 'industry_slug': industry_slug}
            if customer_id:
                payload['customer_id'] = customer_id
            response = requests.post(f"{self.api_url}/score", json=payload,
                headers={'Content-Type': 'application/json'}, timeout=10)
            return response.json() if response.status_code == 200 else None
        except Exception as e:
            logger.error(f"Error calculating score: {e}")
            return None
    
    def get_weights_for_industry(self, industry_slug):
        profile = self.get_profile(industry_slug)
        return profile.get('weights', {}) if profile else None

def score_assessment(module_scores, industry_slug, customer_id=None):
    client = RevFlowScoringClient()
    return client.calculate_score(module_scores, industry_slug, customer_id)

def get_industry_weights(industry_slug):
    client = RevFlowScoringClient()
    return client.get_weights_for_industry(industry_slug)
