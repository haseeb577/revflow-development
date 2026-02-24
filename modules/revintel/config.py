"""
Configuration for RevFlow Enrichment Service
Loads settings from environment variables
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings"""
    
    # Service Configuration
    SERVICE_NAME: str = "RevFlow Enrichment Service"
    SERVICE_VERSION: str = "1.0.0"
    PORT: int = 8500
    DEBUG: bool = False
    
    # Backend Integration
    BACKEND_URL: str = "http://217.15.168.106:5000"
    
    # Email Finding Services
    HUNTER_API_KEY: str = ""
    PROSPEO_API_KEY: str = ""
    DATAGMA_API_KEY: str = ""
    
    # Validation Services
    ZEROBOUNCE_API_KEY: str = ""
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    
    # Enrichment Services
    PEOPLE_DATA_LABS_API_KEY: str = ""
    
    # DataForSEO (Already have this)
    DATAFORSEO_LOGIN: str = ""
    DATAFORSEO_PASSWORD: str = ""
    
    # AudienceLab (Already have this)
    AUDIENCELAB_API_KEY: str = ""
    
    # Optional Services
    CRUNCHBASE_API_KEY: str = ""
    CONTACTOUT_API_KEY: str = ""
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    
    # Caching
    REDIS_URL: Optional[str] = None
    CACHE_TTL_SECONDS: int = 3600  # 1 hour
    
    # Cost Tracking
    ENABLE_COST_TRACKING: bool = True
    COST_ALERT_THRESHOLD: float = 100.0  # Alert if daily cost exceeds $100
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # Allow extra env vars from shared .env


# Initialize settings
settings = Settings()


# Provider Cost Configuration
PROVIDER_COSTS = {
    # Email Finding
    "hunter": {
        "email_find": 0.02,
    },
    "prospeo": {
        "email_find": 0.02,
    },
    "datagma": {
        "email_find": 0.025,
        "phone_find": 0.03,
    },
    
    # Validation
    "zerobounce": {
        "email_validate": 0.008,
    },
    "twilio": {
        "phone_validate": 0.005,
    },
    
    # Enrichment
    "peopledatalabs": {
        "person_enrich": 0.05,
        "company_enrich": 0.03,
        "linkedin_person": 0.02,
        "linkedin_company": 0.02,
    },
    
    # DataForSEO
    "dataforseo": {
        "tech_stack": 0.05,
        "backlinks": 0.10,
        "keywords": 0.05,
        "reviews": 0.05,
        "hiring_intent": 0.10,
    },
    
    # AudienceLab
    "audiencelab": {
        "behavioral_intent": 0.00,  # Included in subscription
        "visitor_intelligence": 0.00,
    },
}


# Waterfall Configuration
WATERFALL_CONFIGS = {
    "email_basic": {
        "providers": ["hunter", "prospeo"],
        "max_cost": 0.05,
    },
    "email_premium": {
        "providers": ["audiencelab", "hunter", "prospeo", "datagma"],
        "max_cost": 0.10,
    },
    "phone_basic": {
        "providers": ["datagma"],
        "max_cost": 0.05,
    },
    "full_contact": {
        "providers": ["peopledatalabs", "audiencelab", "hunter"],
        "max_cost": 0.15,
    },
}


# API Documentation
API_DESCRIPTION = """
## RevFlow Enrichment Service

Production-ready contact and company data enrichment API.

### Features
- 🔍 **Email Finding**: Waterfall across 3+ providers (80%+ match rate)
- 📞 **Phone Finding**: Mobile and direct lines
- ✅ **Validation**: Email deliverability and phone verification
- 👔 **LinkedIn**: Find person and company profiles
- 🏢 **Company Data**: Firmographics, technographics, backlinks
- 🎯 **Intent Signals**: Hiring, funding, behavioral data
- 💰 **Cost Tracking**: Real-time API cost monitoring

### Providers
- Hunter.io, Prospeo, Datagma (Email)
- ZeroBounce (Email Validation)
- Twilio (Phone Validation)
- People Data Labs (Enrichment)
- DataForSEO (Tech Stack, SEO)
- AudienceLab (Visitor Intelligence)

### Authentication
Currently no authentication required (add JWT in production)

### Rate Limits
- 60 requests per minute per IP
- Costs tracked and logged to backend

### Support
- Documentation: /docs
- Health Check: /health
"""
