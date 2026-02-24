"""
Utility classes for RevFlow Enrichment Service
- WaterfallEngine: Sequential multi-provider enrichment
- CostTracker: Integration with backend cost tracking
"""

import httpx
from typing import List, Dict, Any, Optional
from datetime import datetime
import asyncio


class WaterfallEngine:
    """
    Implements waterfall enrichment logic
    Tries providers sequentially until data is found
    """
    
    def __init__(self, email_providers: List, phone_providers: List):
        self.email_providers = email_providers
        self.phone_providers = phone_providers
    
    async def find_email(self, first_name: str, last_name: str, 
                        company_domain: str) -> Dict[str, Any]:
        """
        Try multiple email providers in sequence
        Returns first successful result
        """
        for provider in self.email_providers:
            try:
                result = await provider.find_email(first_name, last_name, company_domain)
                
                if result.get("email") and not result.get("error"):
                    return result
                
            except Exception as e:
                continue
        
        return {
            "error": "Email not found after trying all providers",
            "providers_tried": [p.name for p in self.email_providers],
            "cost": 0.0
        }
    
    async def find_phone(self, email: Optional[str] = None,
                        first_name: Optional[str] = None,
                        last_name: Optional[str] = None,
                        company_domain: Optional[str] = None) -> Dict[str, Any]:
        """
        Try multiple phone providers in sequence
        """
        for provider in self.phone_providers:
            try:
                if hasattr(provider, 'find_phone'):
                    if email:
                        result = await provider.find_phone(email)
                    else:
                        result = await provider.find_email(first_name, last_name, company_domain)
                    
                    if result.get("phone") and not result.get("error"):
                        return result
                
            except Exception as e:
                continue
        
        return {
            "error": "Phone not found after trying all providers",
            "providers_tried": [p.name for p in self.phone_providers],
            "cost": 0.0
        }
    
    async def run_waterfall(self, input_data: Dict[str, Any], 
                           data_points: List[str],
                           providers: List[str]) -> Dict[str, Any]:
        """
        Run complete waterfall for multiple data points
        
        Args:
            input_data: Initial contact/company data
            data_points: List of fields to enrich (email, phone, linkedin, etc.)
            providers: Ordered list of provider names to try
        
        Returns:
            Dictionary with all enriched data points
        """
        results = {}
        
        # Extract common fields
        first_name = input_data.get("first_name")
        last_name = input_data.get("last_name")
        company_domain = input_data.get("company_domain")
        email = input_data.get("email")
        
        # Email enrichment
        if "email" in data_points and first_name and last_name and company_domain:
            email_result = await self.find_email(first_name, last_name, company_domain)
            results["email"] = email_result
            
            # Use found email for subsequent lookups
            if email_result.get("email"):
                email = email_result["email"]
        
        # Phone enrichment
        if "phone" in data_points:
            phone_result = await self.find_phone(
                email=email,
                first_name=first_name,
                last_name=last_name,
                company_domain=company_domain
            )
            results["phone"] = phone_result
        
        # LinkedIn enrichment (would implement similarly)
        if "linkedin" in data_points:
            results["linkedin"] = {
                "message": "LinkedIn enrichment not yet implemented",
                "cost": 0.0
            }
        
        # Company data enrichment
        if "company" in data_points and company_domain:
            results["company"] = {
                "message": "Company enrichment available via separate endpoint",
                "cost": 0.0
            }
        
        return results
    
    async def run_parallel_waterfall(self, contacts: List[Dict[str, Any]],
                                    data_points: List[str]) -> List[Dict[str, Any]]:
        """
        Run waterfall for multiple contacts in parallel
        Uses asyncio.gather for concurrent processing
        """
        tasks = [
            self.run_waterfall(contact, data_points, providers=["audiencelab", "hunter", "prospeo"])
            for contact in contacts
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions
        return [r for r in results if not isinstance(r, Exception)]


class CostTracker:
    """
    Tracks API costs and reports to backend cost management system
    """
    
    def __init__(self, backend_url: str):
        self.backend_url = backend_url
        self.client = httpx.AsyncClient(timeout=5.0)
    
    async def track(self, provider: str, endpoint: str, cost: float,
                   user_id: Optional[str] = None,
                   project_id: Optional[str] = None):
        """
        Send cost tracking data to backend
        
        POST /api/v1/costs/track
        """
        try:
            payload = {
                "provider": provider,
                "endpoint": endpoint,
                "cost": cost,
                "timestamp": datetime.utcnow().isoformat(),
                "service": "enrichment",
                "user_id": user_id or "system",
                "project_id": project_id or "default"
            }
            
            response = await self.client.post(
                f"{self.backend_url}/api/v1/costs/track",
                json=payload
            )
            
            if response.status_code != 200:
                print(f"Cost tracking failed: {response.status_code}")
            
        except Exception as e:
            # Don't fail enrichment if cost tracking fails
            print(f"Cost tracking error: {e}")
    
    async def get_summary(self, days: int = 30) -> Dict[str, Any]:
        """Get cost summary from backend"""
        try:
            response = await self.client.get(
                f"{self.backend_url}/api/v1/costs/summary",
                params={"days": days}
            )
            
            if response.status_code == 200:
                return response.json()
            
            return {"error": "Failed to fetch cost summary"}
            
        except Exception as e:
            return {"error": str(e)}
    
    async def close(self):
        await self.client.aclose()


class RateLimiter:
    """
    Simple rate limiter for API calls
    Prevents exceeding provider rate limits
    """
    
    def __init__(self, calls_per_minute: int = 60):
        self.calls_per_minute = calls_per_minute
        self.calls = []
    
    async def acquire(self):
        """Wait if rate limit would be exceeded"""
        now = datetime.utcnow()
        
        # Remove calls older than 1 minute
        self.calls = [call_time for call_time in self.calls 
                     if (now - call_time).total_seconds() < 60]
        
        # If at limit, wait
        if len(self.calls) >= self.calls_per_minute:
            oldest_call = min(self.calls)
            wait_time = 60 - (now - oldest_call).total_seconds()
            
            if wait_time > 0:
                await asyncio.sleep(wait_time)
        
        # Record this call
        self.calls.append(now)


class ResponseNormalizer:
    """
    Normalizes responses from different providers into standard format
    """
    
    @staticmethod
    def normalize_contact(provider_response: Dict[str, Any], 
                         provider_name: str) -> Dict[str, Any]:
        """
        Normalize contact data from any provider
        """
        normalized = {
            "provider": provider_name,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Email normalization
        if "email" in provider_response:
            normalized["email"] = {
                "address": provider_response.get("email"),
                "verified": provider_response.get("verified", False),
                "confidence": provider_response.get("confidence", 0)
            }
        
        # Phone normalization
        if "phone" in provider_response:
            normalized["phone"] = {
                "number": provider_response.get("phone"),
                "type": provider_response.get("type", "unknown"),
                "verified": provider_response.get("verified", False)
            }
        
        # LinkedIn normalization
        if "linkedin_url" in provider_response:
            normalized["linkedin"] = {
                "url": provider_response.get("linkedin_url"),
                "verified": provider_response.get("verified", False)
            }
        
        # Job info normalization
        if "job_title" in provider_response:
            normalized["employment"] = {
                "title": provider_response.get("job_title"),
                "company": provider_response.get("company"),
                "seniority": provider_response.get("seniority")
            }
        
        return normalized
    
    @staticmethod
    def normalize_company(provider_response: Dict[str, Any],
                         provider_name: str) -> Dict[str, Any]:
        """
        Normalize company data from any provider
        """
        normalized = {
            "provider": provider_name,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Firmographics
        if "employees" in provider_response or "revenue" in provider_response:
            normalized["firmographics"] = {
                "employees": provider_response.get("employees"),
                "revenue": provider_response.get("revenue"),
                "industry": provider_response.get("industry"),
                "founded": provider_response.get("founded")
            }
        
        # Technographics
        if "technologies" in provider_response:
            normalized["technographics"] = {
                "technologies": provider_response.get("technologies"),
                "total_count": len(provider_response.get("technologies", []))
            }
        
        # Web metrics
        if "backlinks_count" in provider_response or "keywords_count" in provider_response:
            normalized["web_metrics"] = {
                "backlinks": provider_response.get("backlinks_count"),
                "referring_domains": provider_response.get("referring_domains"),
                "keywords": provider_response.get("keywords_count"),
                "estimated_traffic": provider_response.get("estimated_traffic")
            }
        
        return normalized
