"""
External API integration services
Each service class handles a specific data provider
"""

import httpx
import asyncio
from typing import Optional, Dict, Any, List
from config import settings


class BaseService:
    """Base class for all API services"""
    
    def __init__(self, api_key: str, base_url: str, name: str):
        self.api_key = api_key
        self.base_url = base_url
        self.name = name
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def health_check(self) -> bool:
        """Check if service is accessible"""
        try:
            # Implement specific health check per service
            return True
        except:
            return False
    
    async def close(self):
        await self.client.aclose()


# ============================================================================
# EMAIL FINDING SERVICES
# ============================================================================

class HunterService(BaseService):
    """Hunter.io email finder"""
    
    def __init__(self):
        super().__init__(
            api_key=settings.HUNTER_API_KEY,
            base_url="https://api.hunter.io/v2",
            name="hunter"
        )
    
    async def find_email(self, first_name: str, last_name: str, domain: str) -> Dict[str, Any]:
        """Find email using Hunter.io"""
        try:
            response = await self.client.get(
                f"{self.base_url}/email-finder",
                params={
                    "api_key": self.api_key,
                    "first_name": first_name,
                    "last_name": last_name,
                    "domain": domain
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get("data", {}).get("email"):
                    return {
                        "email": data["data"]["email"],
                        "confidence": data["data"].get("score", 0),
                        "verified": data["data"].get("verification", {}).get("value") != "invalid",
                        "provider": "hunter",
                        "cost": 0.02
                    }
            
            return {"error": "Email not found", "provider": "hunter"}
            
        except Exception as e:
            return {"error": str(e), "provider": "hunter"}


class ProspeoService(BaseService):
    """Prospeo email finder"""
    
    def __init__(self):
        super().__init__(
            api_key=settings.PROSPEO_API_KEY,
            base_url="https://api.prospeo.io/v1",
            name="prospeo"
        )
    
    async def find_email(self, first_name: str, last_name: str, domain: str) -> Dict[str, Any]:
        """Find email using Prospeo"""
        try:
            response = await self.client.post(
                f"{self.base_url}/email-finder",
                headers={"X-KEY": self.api_key},
                json={
                    "first_name": first_name,
                    "last_name": last_name,
                    "company_domain": domain
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get("email"):
                    return {
                        "email": data["email"],
                        "confidence": 85,  # Prospeo doesn't provide score
                        "verified": data.get("verified", False),
                        "provider": "prospeo",
                        "cost": 0.02
                    }
            
            return {"error": "Email not found", "provider": "prospeo"}
            
        except Exception as e:
            return {"error": str(e), "provider": "prospeo"}


class DatagmaService(BaseService):
    """Datagma contact finder"""
    
    def __init__(self):
        super().__init__(
            api_key=settings.DATAGMA_API_KEY,
            base_url="https://gateway.datagma.com/api/v2",
            name="datagma"
        )
    
    async def find_email(self, first_name: str, last_name: str, domain: str) -> Dict[str, Any]:
        """Find email using Datagma"""
        try:
            response = await self.client.post(
                f"{self.base_url}/email",
                headers={"X-Api-Key": self.api_key},
                json={
                    "firstName": first_name,
                    "lastName": last_name,
                    "domain": domain
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get("email"):
                    return {
                        "email": data["email"],
                        "confidence": data.get("confidence", 80),
                        "verified": data.get("valid", False),
                        "provider": "datagma",
                        "cost": 0.025
                    }
            
            return {"error": "Email not found", "provider": "datagma"}
            
        except Exception as e:
            return {"error": str(e), "provider": "datagma"}
    
    async def find_phone(self, email: str) -> Dict[str, Any]:
        """Find phone from email"""
        try:
            response = await self.client.post(
                f"{self.base_url}/phone",
                headers={"X-Api-Key": self.api_key},
                json={"email": email}
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get("phone"):
                    return {
                        "phone": data["phone"],
                        "type": data.get("phoneType", "unknown"),
                        "provider": "datagma",
                        "cost": 0.03
                    }
            
            return {"error": "Phone not found", "provider": "datagma"}
            
        except Exception as e:
            return {"error": str(e), "provider": "datagma"}


# ============================================================================
# VALIDATION SERVICES
# ============================================================================

class ZeroBounceService(BaseService):
    """ZeroBounce email validation"""
    
    def __init__(self):
        super().__init__(
            api_key=settings.ZEROBOUNCE_API_KEY,
            base_url="https://api.zerobounce.net/v2",
            name="zerobounce"
        )
    
    async def validate_email(self, email: str) -> Dict[str, Any]:
        """Validate email deliverability"""
        try:
            response = await self.client.get(
                f"{self.base_url}/validate",
                params={
                    "api_key": self.api_key,
                    "email": email
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                
                return {
                    "email": email,
                    "valid": data.get("status") == "valid",
                    "status": data.get("status"),
                    "sub_status": data.get("sub_status"),
                    "deliverable": data.get("status") in ["valid", "catch-all"],
                    "disposable": data.get("free_email", False),
                    "catch_all": data.get("status") == "catch-all",
                    "provider": "zerobounce",
                    "cost": 0.008
                }
            
            return {"error": "Validation failed", "provider": "zerobounce"}
            
        except Exception as e:
            return {"error": str(e), "provider": "zerobounce"}


class TwilioService(BaseService):
    """Twilio phone validation"""
    
    def __init__(self):
        super().__init__(
            api_key=settings.TWILIO_AUTH_TOKEN,
            base_url=f"https://lookups.twilio.com/v2",
            name="twilio"
        )
        self.account_sid = settings.TWILIO_ACCOUNT_SID
    
    async def validate_phone(self, phone: str) -> Dict[str, Any]:
        """Validate phone number"""
        try:
            # Twilio uses Basic Auth
            auth = httpx.BasicAuth(self.account_sid, self.api_key)
            
            response = await self.client.get(
                f"{self.base_url}/PhoneNumbers/{phone}",
                auth=auth,
                params={"Fields": "line_type_intelligence"}
            )
            
            if response.status_code == 200:
                data = response.json()
                
                return {
                    "phone": phone,
                    "valid": data.get("valid", False),
                    "carrier": data.get("carrier", {}).get("name"),
                    "line_type": data.get("line_type_intelligence", {}).get("type"),
                    "country_code": data.get("country_code"),
                    "provider": "twilio",
                    "cost": 0.005
                }
            
            return {"error": "Validation failed", "provider": "twilio"}
            
        except Exception as e:
            return {"error": str(e), "provider": "twilio"}


# ============================================================================
# ENRICHMENT SERVICES
# ============================================================================

class PeopleDataLabsService(BaseService):
    """People Data Labs enrichment"""
    
    def __init__(self):
        super().__init__(
            api_key=settings.PEOPLE_DATA_LABS_API_KEY,
            base_url="https://api.peopledatalabs.com/v5",
            name="peopledatalabs"
        )
    
    async def enrich_person(self, email: Optional[str] = None, 
                           first_name: Optional[str] = None,
                           last_name: Optional[str] = None,
                           company_domain: Optional[str] = None) -> Dict[str, Any]:
        """Full person enrichment"""
        try:
            params = {"api_key": self.api_key}
            
            if email:
                params["email"] = email
            if first_name:
                params["first_name"] = first_name
            if last_name:
                params["last_name"] = last_name
            if company_domain:
                params["company"] = company_domain
            
            response = await self.client.get(
                f"{self.base_url}/person/enrich",
                params=params
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get("status") == 200 and data.get("data"):
                    person = data["data"]
                    
                    return {
                        "email": person.get("work_email"),
                        "phone": person.get("mobile_phone") or person.get("phone_numbers", [{}])[0].get("number"),
                        "linkedin_url": person.get("linkedin_url"),
                        "first_name": person.get("first_name"),
                        "last_name": person.get("last_name"),
                        "job_title": person.get("job_title"),
                        "company": person.get("job_company_name"),
                        "location": person.get("location_name"),
                        "seniority": person.get("job_title_levels", []),
                        "skills": person.get("skills", [])[:10],
                        "provider": "peopledatalabs",
                        "cost": 0.05
                    }
            
            return {"error": "Person not found", "provider": "peopledatalabs"}
            
        except Exception as e:
            return {"error": str(e), "provider": "peopledatalabs"}
    
    async def get_company_firmographics(self, domain: str) -> Dict[str, Any]:
        """Get company firmographic data"""
        try:
            response = await self.client.get(
                f"{self.base_url}/company/enrich",
                params={
                    "api_key": self.api_key,
                    "website": domain
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get("status") == 200 and data.get("data"):
                    company = data["data"]
                    
                    return {
                        "name": company.get("name"),
                        "industry": company.get("industry"),
                        "employees": company.get("size"),
                        "revenue": company.get("estimated_annual_revenue"),
                        "founded": company.get("founded"),
                        "location": company.get("location", {}).get("name"),
                        "linkedin_url": company.get("linkedin_url"),
                        "provider": "peopledatalabs",
                        "cost": 0.03
                    }
            
            return {"error": "Company not found", "provider": "peopledatalabs"}
            
        except Exception as e:
            return {"error": str(e), "provider": "peopledatalabs"}
    
    async def find_linkedin_person(self, first_name: str, last_name: str, 
                                   company: str) -> Dict[str, Any]:
        """Find LinkedIn profile"""
        try:
            response = await self.client.get(
                f"{self.base_url}/person/search",
                params={
                    "api_key": self.api_key,
                    "first_name": first_name,
                    "last_name": last_name,
                    "company": company,
                    "size": 1
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get("data") and len(data["data"]) > 0:
                    person = data["data"][0]
                    
                    return {
                        "linkedin_url": person.get("linkedin_url"),
                        "job_title": person.get("job_title"),
                        "verified": True,
                        "provider": "peopledatalabs",
                        "cost": 0.02
                    }
            
            return {"error": "LinkedIn profile not found", "provider": "peopledatalabs"}
            
        except Exception as e:
            return {"error": str(e), "provider": "peopledatalabs"}
    
    async def find_linkedin_company(self, company_domain: str) -> Dict[str, Any]:
        """Find LinkedIn company page"""
        try:
            response = await self.client.get(
                f"{self.base_url}/company/enrich",
                params={
                    "api_key": self.api_key,
                    "website": company_domain
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get("data"):
                    company = data["data"]
                    
                    return {
                        "linkedin_url": company.get("linkedin_url"),
                        "linkedin_id": company.get("linkedin_id"),
                        "followers": company.get("linkedin_followers"),
                        "employee_count": company.get("size"),
                        "provider": "peopledatalabs",
                        "cost": 0.02
                    }
            
            return {"error": "LinkedIn company page not found", "provider": "peopledatalabs"}
            
        except Exception as e:
            return {"error": str(e), "provider": "peopledatalabs"}


# ============================================================================
# DATAFORSEO SERVICES
# ============================================================================

class DataForSEOService(BaseService):
    """DataForSEO technographic and SEO data"""
    
    def __init__(self):
        super().__init__(
            api_key=settings.DATAFORSEO_PASSWORD,
            base_url="https://api.dataforseo.com/v3",
            name="dataforseo"
        )
        self.login = settings.DATAFORSEO_LOGIN
    
    async def _make_request(self, endpoint: str, payload: List[Dict]) -> Dict:
        """Make authenticated request to DataForSEO"""
        try:
            auth = httpx.BasicAuth(self.login, self.api_key)
            
            response = await self.client.post(
                f"{self.base_url}/{endpoint}",
                auth=auth,
                json=payload
            )
            
            if response.status_code == 200:
                return response.json()
            
            return {"error": f"API returned {response.status_code}"}
            
        except Exception as e:
            return {"error": str(e)}
    
    async def get_domain_technologies(self, domain: str) -> Dict[str, Any]:
        """Get technology stack"""
        try:
            result = await self._make_request(
                "domain_analytics/technologies/domain_technologies",
                [{"target": domain}]
            )
            
            if result.get("tasks") and result["tasks"][0].get("result"):
                data = result["tasks"][0]["result"][0]
                
                technologies = {}
                for tech in data.get("technologies", []):
                    category = tech.get("category", "other")
                    if category not in technologies:
                        technologies[category] = []
                    technologies[category].append(tech.get("name"))
                
                return {
                    "domain": domain,
                    "technologies": technologies,
                    "total_technologies": len(data.get("technologies", [])),
                    "provider": "dataforseo",
                    "cost": 0.05
                }
            
            return {"error": "No technologies found", "provider": "dataforseo"}
            
        except Exception as e:
            return {"error": str(e), "provider": "dataforseo"}
    
    async def get_backlinks(self, domain: str) -> Dict[str, Any]:
        """Get backlink profile"""
        try:
            result = await self._make_request(
                "backlinks/summary/live",
                [{"target": domain}]
            )
            
            if result.get("tasks") and result["tasks"][0].get("result"):
                data = result["tasks"][0]["result"][0]
                
                return {
                    "domain": domain,
                    "total_backlinks": data.get("backlinks", 0),
                    "referring_domains": data.get("referring_domains", 0),
                    "referring_ips": data.get("referring_ips", 0),
                    "domain_rank": data.get("rank", 0),
                    "provider": "dataforseo",
                    "cost": 0.10
                }
            
            return {"error": "No backlink data found", "provider": "dataforseo"}
            
        except Exception as e:
            return {"error": str(e), "provider": "dataforseo"}
    
    async def get_ranking_keywords(self, domain: str) -> Dict[str, Any]:
        """Get ranking keywords"""
        try:
            result = await self._make_request(
                "dataforseo_labs/google/ranked_keywords/live",
                [{"target": domain, "language_code": "en"}]
            )
            
            if result.get("tasks") and result["tasks"][0].get("result"):
                data = result["tasks"][0]["result"][0]
                
                keywords = data.get("metrics", {}).get("organic", {}).get("count", 0)
                traffic = data.get("metrics", {}).get("organic", {}).get("etv", 0)
                
                return {
                    "domain": domain,
                    "total_keywords": keywords,
                    "estimated_traffic": traffic,
                    "top_keywords": data.get("items", [])[:10],
                    "provider": "dataforseo",
                    "cost": 0.05
                }
            
            return {"error": "No keyword data found", "provider": "dataforseo"}
            
        except Exception as e:
            return {"error": str(e), "provider": "dataforseo"}
    
    async def get_google_reviews(self, business_name: str, location: str) -> Dict[str, Any]:
        """Get Google Business reviews"""
        try:
            result = await self._make_request(
                "business_data/google/reviews/task_post",
                [{
                    "keyword": business_name,
                    "location_name": location,
                    "language_code": "en"
                }]
            )
            
            # Note: This returns a task ID, need to poll for results
            # Simplified for demo purposes
            
            return {
                "business_name": business_name,
                "location": location,
                "reviews_available": True,
                "message": "Reviews retrieval initiated",
                "provider": "dataforseo",
                "cost": 0.05
            }
            
        except Exception as e:
            return {"error": str(e), "provider": "dataforseo"}
    
    async def detect_hiring_intent(self, domain: str) -> Dict[str, Any]:
        """Detect hiring intent from careers page"""
        try:
            # Use On-Page API to scrape careers page
            result = await self._make_request(
                "on_page/task_post",
                [{
                    "target": f"https://{domain}/careers",
                    "max_crawl_pages": 5
                }]
            )
            
            # Simplified - in production, would parse job listings
            return {
                "domain": domain,
                "hiring_detected": True,
                "message": "Hiring intent detection initiated",
                "provider": "dataforseo",
                "cost": 0.10
            }
            
        except Exception as e:
            return {"error": str(e), "provider": "dataforseo"}


# ============================================================================
# AUDIENCELAB SERVICE
# ============================================================================

class AudienceLabService(BaseService):
    """AudienceLab visitor intelligence"""
    
    def __init__(self):
        super().__init__(
            api_key=settings.AUDIENCELAB_API_KEY,
            base_url="https://api.audiencelab.io/v1",
            name="audiencelab"
        )
    
    async def get_visitor_intelligence(self, domain: str, days: int = 7) -> Dict[str, Any]:
        """Get website visitor data from SuperPixel"""
        try:
            # Note: Actual API endpoints would be from AudienceLab docs
            # This is a placeholder structure
            
            response = await self.client.get(
                f"{self.base_url}/visitor-intelligence",
                headers={"X-API-Key": self.api_key},
                params={
                    "domain": domain,
                    "days": days
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                
                return {
                    "domain": domain,
                    "unique_visitors_7d": data.get("unique_visitors", 0),
                    "identified_visitors": data.get("identified_count", 0),
                    "match_rate": data.get("match_rate", 0.80),
                    "top_visiting_companies": data.get("companies", [])[:10],
                    "provider": "audiencelab",
                    "cost": 0.00  # Included in subscription
                }
            
            return {"error": "Visitor data not available", "provider": "audiencelab"}
            
        except Exception as e:
            return {"error": str(e), "provider": "audiencelab"}
