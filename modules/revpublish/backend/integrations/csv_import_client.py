"""
CSV Import Engine Client
Integrates with existing CSV Import Engine on port 8766
"""

import requests
from typing import List, Dict

class CSVImportEngineClient:
    """Client for existing CSV Import Engine (port 8766)"""
    
    def __init__(self, base_url: str = "http://localhost:8766"):
        self.base_url = base_url.rstrip('/')
    
    def import_csv(self, csv_content: str, mapping: Dict = None) -> List[Dict]:
        """
        Import CSV using existing CSV Import Engine
        
        Args:
            csv_content: CSV file content
            mapping: Field mapping configuration
        
        Returns:
            List of processed content items
        """
        response = requests.post(
            f"{self.base_url}/api/import/csv",
            json={
                'csv_content': csv_content,
                'mapping': mapping or {}
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            return data.get('items', [])
        else:
            raise Exception(f"CSV Import Engine error: {response.text}")
    
    def upload_csv_file(self, file_path: str, mapping: Dict = None) -> List[Dict]:
        """Upload CSV file to CSV Import Engine"""
        with open(file_path, 'rb') as f:
            files = {'file': f}
            data = {'mapping': mapping} if mapping else {}
            
            response = requests.post(
                f"{self.base_url}/api/import/upload",
                files=files,
                data=data
            )
        
        if response.status_code == 200:
            return response.json().get('items', [])
        else:
            raise Exception(f"CSV upload error: {response.text}")
    
    def get_field_mappings(self) -> List[Dict]:
        """Get available field mapping templates"""
        response = requests.get(f"{self.base_url}/api/mappings")
        
        if response.status_code == 200:
            return response.json().get('mappings', [])
        return []
    
    def health_check(self) -> bool:
        """Check if CSV Import Engine is available"""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=2)
            return response.status_code == 200
        except:
            return False
