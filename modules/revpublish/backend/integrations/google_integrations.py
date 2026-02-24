"""
Google Integrations (Sheets & Docs)
For public/shared documents only
"""

import requests
import re
from typing import Dict, List

class GoogleSheetsClient:
    """Google Sheets integration"""
    
    def extract_from_url(self, sheet_url: str) -> List[Dict]:
        """Extract content from Google Sheets URL"""
        # Extract sheet ID
        match = re.search(r'/spreadsheets/d/([a-zA-Z0-9-_]+)', sheet_url)
        if not match:
            raise Exception("Invalid Google Sheets URL")
        
        sheet_id = match.group(1)
        
        # Use CSV export (works for public sheets)
        csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
        
        response = requests.get(csv_url)
        if response.status_code == 200:
            # Parse CSV content
            return self._parse_csv(response.text)
        else:
            raise Exception(f"Failed to fetch Google Sheet: {response.status_code}")
    
    def _parse_csv(self, csv_content: str) -> List[Dict]:
        """Parse CSV content to list of dicts"""
        import csv
        from io import StringIO
        
        reader = csv.DictReader(StringIO(csv_content))
        items = []
        
        for row in reader:
            item = {
                'title': row.get('title', row.get('Title', 'Untitled')),
                'content_html': row.get('content', row.get('Content', '')),
                'status': row.get('status', row.get('Status', 'draft')),
                'post_type': row.get('post_type', row.get('Type', 'post'))
            }
            items.append(item)
        
        return items


class GoogleDocsClient:
    """Google Docs integration"""
    
    def extract_from_url(self, doc_url: str) -> Dict:
        """Extract content from Google Docs URL"""
        # Extract doc ID
        match = re.search(r'/document/d/([a-zA-Z0-9-_]+)', doc_url)
        if not match:
            raise Exception("Invalid Google Docs URL")
        
        doc_id = match.group(1)
        
        # Use HTML export (works for public docs)
        html_url = f"https://docs.google.com/document/d/{doc_id}/export?format=html"
        
        response = requests.get(html_url)
        if response.status_code == 200:
            html_content = response.text
            
            # Extract title
            title_match = re.search(r'<title>(.*?)</title>', html_content)
            title = title_match.group(1) if title_match else 'Untitled'
            
            # Extract body
            body_match = re.search(r'<body[^>]*>(.*?)</body>', html_content, re.DOTALL)
            content_html = body_match.group(1) if body_match else html_content
            
            return {
                'title': title,
                'content_html': content_html,
                'status': 'draft',
                'post_type': 'post'
            }
        else:
            raise Exception(f"Failed to fetch Google Doc: {response.status_code}")
