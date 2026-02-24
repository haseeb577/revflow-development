"""
RevCite: IndexNow Citation Signal Propagation
Notifies search engines immediately when citations are earned/updated
"""

import requests
import json
from typing import List, Dict
from datetime import datetime


class CitationIndexNotifier:
    """Notify search engines when citations change"""
    
    def __init__(self, api_key: str, host: str):
        self.api_key = api_key
        self.host = host
        self.indexnow_endpoint = "https://www.bing.com/indexnow"
        self.key_location = f"https://{host}/{api_key}.txt"
        
    def notify_new_citations(self, page_urls: List[str], citation_context: Dict = None) -> Dict:
        """Notify search engines when NEW citations are discovered"""
        
        payload = {
            "host": self.host,
            "key": self.api_key,
            "keyLocation": self.key_location,
            "urlList": page_urls
        }
        
        try:
            response = requests.post(
                self.indexnow_endpoint,
                json=payload,
                headers={"Content-Type": "application/json; charset=utf-8"},
                timeout=10
            )
            
            result = {
                "status": response.status_code,
                "success": response.status_code in [200, 202],
                "urls_submitted": len(page_urls),
                "timestamp": datetime.now().isoformat()
            }
            
            # Log for analytics
            self._log_notification(result)
            
            return result
            
        except Exception as e:
            return {
                "status": "error",
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def notify_citation_boost(self, site_url: str, citation_count: int) -> Dict:
        """Notify when citation velocity threshold is crossed"""
        
        return self.notify_new_citations(
            [site_url],
            {"type": "citation_boost", "count": citation_count}
        )
    
    def batch_notify(self, urls: List[str]) -> Dict:
        """Batch notify multiple URLs (max 10,000 per request)"""
        
        if len(urls) > 10000:
            # Split into batches
            batches = [urls[i:i+10000] for i in range(0, len(urls), 10000)]
            results = [self.notify_new_citations(batch) for batch in batches]
            
            return {
                "total_urls": len(urls),
                "batches": len(batches),
                "results": results
            }
        
        return self.notify_new_citations(urls)
    
    def _log_notification(self, result: Dict):
        """Log notifications for analytics"""
        log_file = "/opt/revcite/logs/citation_notifications.jsonl"
        
        try:
            with open(log_file, "a") as f:
                f.write(json.dumps(result) + "\n")
        except Exception as e:
            print(f"Warning: Could not log notification: {e}")


if __name__ == "__main__":
    # Test
    print("✅ IndexNow notifier initialized")
