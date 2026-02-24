"""
Data Provider Client
Integrates with existing Data Provider system
"""

import requests
from typing import Dict, List

class DataProviderClient:
    """Client for Data Provider system"""
    
    def __init__(self, base_url: str = "http://localhost:8100"):
        self.base_url = base_url.rstrip('/')
    
    def query_data(self, query: Dict) -> Dict:
        """Query data from Data Provider"""
        response = requests.post(
            f"{self.base_url}/api/v1/query",
            json=query
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Data Provider error: {response.text}")
    
    def get_data_sources(self) -> List[str]:
        """Get available data sources"""
        try:
            response = requests.get(f"{self.base_url}/api/v1/sources")
            if response.status_code == 200:
                return response.json().get('sources', [])
        except:
            pass
        return []
    
    def health_check(self) -> bool:
        """Check if Data Provider is available"""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=2)
            return response.status_code == 200
        except:
            return False
