"""
RevRank Engine Client
Integrates with existing RevRank Engine (port 8200)
"""

import requests
from typing import Dict

class RevRankEngineClient:
    """Client for RevRank Engine content generation"""
    
    def __init__(self, base_url: str = "http://localhost:8200"):
        self.base_url = base_url.rstrip('/')
    
    def generate_content(self, params: Dict) -> Dict:
        """
        Generate content via RevRank Engine
        
        Args:
            params: Generation parameters
        
        Returns:
            Generated content
        """
        response = requests.post(
            f"{self.base_url}/api/generate/page",
            json=params
        )
        
        if response.status_code == 200:
            data = response.json()
            
            return {
                'title': data.get('title', 'Generated Content'),
                'content_html': data.get('html', data.get('content', '')),
                'status': 'draft',
                'post_type': params.get('page_type', 'post'),
                'meta_data': {
                    'geo_score': data.get('geo_score'),
                    'quality_score': data.get('quality_score'),
                    'generated_at': data.get('timestamp')
                }
            }
        else:
            raise Exception(f"RevRank generation failed: {response.text}")
    
    def health_check(self) -> bool:
        """Check if RevRank Engine is available"""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=2)
            return response.status_code == 200
        except:
            return False
