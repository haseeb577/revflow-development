"""
RevFlow Enrichment Service (RevIntel™)
Production-ready FastAPI service for contact and company data enrichment
Port: 8500
RevAudit: ENABLED - All API calls logged
"""

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List, Dict, Any
import httpx
from datetime import datetime
import asyncio
import sys

# RevAudit Anti-Hallucination Integration
sys.path.insert(0, '/opt/shared-api-engine')
try:
    from revaudit.integrate import integrate_revaudit
    REVAUDIT_AVAILABLE = True
except ImportError:
    REVAUDIT_AVAILABLE = False

from models import (
    EmailEnrichRequest, PhoneEnrichRequest, EmailValidationRequest,
    PhoneValidationRequest, LinkedInPersonRequest, LinkedInCompanyRequest,
    PersonEnrichRequest, WaterfallEnrichRequest, BatchEnrichRequest,
    CompanyFirmographicsRequest, CompanyTechStackRequest, CompanyBacklinksRequest,
    CompanyKeywordsRequest, CompanyReviewsRequest, HiringIntentRequest,
    FundingDataRequest, BehavioralIntentRequest,
    EnrichmentResponse, WaterfallResponse, BatchEnrichmentResponse
)
from services import (
    HunterService, ProspeoService, DatagmaService,
    ZeroBounceService, TwilioService, PeopleDataLabsService,
    DataForSEOService, AudienceLabService
)
from utils import WaterfallEngine, CostTracker
from config import settings

# Initialize FastAPI app
app = FastAPI(
    title="RevFlow Enrichment Service",
    description="Contact and company data enrichment API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# RevAudit Integration
if REVAUDIT_AVAILABLE:
    integrate_revaudit(app, "RevIntel")

# Initialize services
hunter = HunterService()
prospeo = ProspeoService()
datagma = DatagmaService()
zerobounce = ZeroBounceService()
twilio = TwilioService()
people_data_labs = PeopleDataLabsService()
dataforseo = DataForSEOService()
audiencelab = AudienceLabService()

# Initialize utilities
waterfall_engine = WaterfallEngine(
    email_providers=[hunter, prospeo, datagma],
    phone_providers=[datagma]
)
cost_tracker = CostTracker(backend_url=settings.BACKEND_URL)

# ============================================================================
# HEALTH & SYSTEM
# ============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    services_status = {
        "hunter": await hunter.health_check(),
        "zerobounce": await zerobounce.health_check(),
        "dataforseo": await dataforseo.health_check(),
        "audiencelab": await audiencelab.health_check(),
    }
    
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "services": services_status,
        "version": "1.0.0"
    }

@app.get("/")
async def root():
    """API information"""
    return {
        "service": "RevFlow Enrichment Service",
        "version": "1.0.0",
        "endpoints": 17,
        "docs": "/docs"
    }

# ============================================================================
# GROUP 1: CONTACT ENRICHMENT (9 ENDPOINTS)
# ============================================================================

@app.post("/api/v1/enrich/email", response_model=EnrichmentResponse)
async def find_email(
    request: EmailEnrichRequest,
    background_tasks: BackgroundTasks
):
    """
    Find work email address using waterfall approach
    Tries multiple providers: Hunter.io → Prospeo → Datagma
    """
    try:
        result = await waterfall_engine.find_email(
            first_name=request.first_name,
            last_name=request.last_name,
            company_domain=request.company_domain
        )
        
        # Track cost in background
        background_tasks.add_task(
            cost_tracker.track,
            provider=result.get("provider", "unknown"),
            endpoint="email_find",
            cost=result.get("cost", 0.02)
        )
        
        return EnrichmentResponse(
            success=True,
            data=result,
            provider=result.get("provider"),
            cost=result.get("cost"),
            timestamp=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/enrich/phone", response_model=EnrichmentResponse)
async def find_phone(
    request: PhoneEnrichRequest,
    background_tasks: BackgroundTasks
):
    """
    Find phone number from email or name + company
    Uses: Datagma → ContactOut
    """
    try:
        result = await waterfall_engine.find_phone(
            email=request.email,
            first_name=request.first_name,
            last_name=request.last_name,
            company_domain=request.company_domain
        )
        
        background_tasks.add_task(
            cost_tracker.track,
            provider=result.get("provider", "datagma"),
            endpoint="phone_find",
            cost=result.get("cost", 0.03)
        )
        
        return EnrichmentResponse(
            success=True,
            data=result,
            provider=result.get("provider"),
            cost=result.get("cost"),
            timestamp=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/enrich/validate/email", response_model=EnrichmentResponse)
async def validate_email(
    request: EmailValidationRequest,
    background_tasks: BackgroundTasks
):
    """
    Validate email deliverability using ZeroBounce
    Returns: valid, deliverable, disposable, catch-all status
    """
    try:
        result = await zerobounce.validate_email(request.email)
        
        background_tasks.add_task(
            cost_tracker.track,
            provider="zerobounce",
            endpoint="email_validate",
            cost=0.008  # $8 per 1000 validations
        )
        
        return EnrichmentResponse(
            success=True,
            data=result,
            provider="zerobounce",
            cost=0.008,
            timestamp=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/enrich/validate/phone", response_model=EnrichmentResponse)
async def validate_phone(
    request: PhoneValidationRequest,
    background_tasks: BackgroundTasks
):
    """
    Validate phone number using Twilio Lookup
    Returns: valid, carrier, line_type (mobile/landline)
    """
    try:
        result = await twilio.validate_phone(request.phone)
        
        background_tasks.add_task(
            cost_tracker.track,
            provider="twilio",
            endpoint="phone_validate",
            cost=0.005
        )
        
        return EnrichmentResponse(
            success=True,
            data=result,
            provider="twilio",
            cost=0.005,
            timestamp=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/enrich/linkedin/person", response_model=EnrichmentResponse)
async def find_linkedin_person(
    request: LinkedInPersonRequest,
    background_tasks: BackgroundTasks
):
    """
    Find LinkedIn profile URL for a person
    Uses: People Data Labs
    """
    try:
        result = await people_data_labs.find_linkedin_person(
            first_name=request.first_name,
            last_name=request.last_name,
            company=request.company
        )
        
        background_tasks.add_task(
            cost_tracker.track,
            provider="peopledatalabs",
            endpoint="linkedin_person",
            cost=0.02
        )
        
        return EnrichmentResponse(
            success=True,
            data=result,
            provider="peopledatalabs",
            cost=0.02,
            timestamp=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/enrich/linkedin/company", response_model=EnrichmentResponse)
async def find_linkedin_company(
    request: LinkedInCompanyRequest,
    background_tasks: BackgroundTasks
):
    """
    Find LinkedIn company page URL
    Uses: People Data Labs
    """
    try:
        result = await people_data_labs.find_linkedin_company(
            company_domain=request.company_domain
        )
        
        background_tasks.add_task(
            cost_tracker.track,
            provider="peopledatalabs",
            endpoint="linkedin_company",
            cost=0.02
        )
        
        return EnrichmentResponse(
            success=True,
            data=result,
            provider="peopledatalabs",
            cost=0.02,
            timestamp=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/enrich/person", response_model=EnrichmentResponse)
async def enrich_person(
    request: PersonEnrichRequest,
    background_tasks: BackgroundTasks
):
    """
    Full person enrichment - get all available data
    Returns: email, phone, LinkedIn, job title, location, etc.
    """
    try:
        result = await people_data_labs.enrich_person(
            email=request.email,
            first_name=request.first_name,
            last_name=request.last_name,
            company_domain=request.company_domain
        )
        
        background_tasks.add_task(
            cost_tracker.track,
            provider="peopledatalabs",
            endpoint="person_enrich",
            cost=0.05
        )
        
        return EnrichmentResponse(
            success=True,
            data=result,
            provider="peopledatalabs",
            cost=0.05,
            timestamp=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/enrich/waterfall", response_model=WaterfallResponse)
async def waterfall_enrich(
    request: WaterfallEnrichRequest,
    background_tasks: BackgroundTasks
):
    """
    Multi-provider waterfall enrichment
    Tries providers sequentially until data is found
    """
    try:
        results = await waterfall_engine.run_waterfall(
            input_data=request.input,
            data_points=request.data_points,
            providers=request.providers
        )
        
        # Track total cost
        total_cost = sum(r.get("cost", 0) for r in results.values())
        background_tasks.add_task(
            cost_tracker.track,
            provider="waterfall_multi",
            endpoint="waterfall",
            cost=total_cost
        )
        
        return WaterfallResponse(
            success=True,
            data=results,
            providers_used=list(results.keys()),
            total_cost=total_cost,
            timestamp=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/enrich/batch", response_model=BatchEnrichmentResponse)
async def batch_enrich(
    request: BatchEnrichRequest,
    background_tasks: BackgroundTasks
):
    """
    Bulk enrichment for multiple contacts
    Processes array of contacts with specified data points
    """
    try:
        results = []
        total_cost = 0
        
        for contact in request.contacts:
            enriched = await waterfall_engine.run_waterfall(
                input_data=contact,
                data_points=request.data_points,
                providers=["audiencelab", "hunter", "prospeo"]
            )
            results.append(enriched)
            total_cost += sum(r.get("cost", 0) for r in enriched.values())
        
        background_tasks.add_task(
            cost_tracker.track,
            provider="batch_multi",
            endpoint="batch_enrich",
            cost=total_cost
        )
        
        return BatchEnrichmentResponse(
            success=True,
            data=results,
            total_enriched=len(results),
            total_cost=total_cost,
            timestamp=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# GROUP 2: COMPANY ENRICHMENT (5 ENDPOINTS)
# ============================================================================

@app.post("/api/v1/enrich/company/firmographics", response_model=EnrichmentResponse)
async def get_company_firmographics(
    request: CompanyFirmographicsRequest,
    background_tasks: BackgroundTasks
):
    """
    Get company firmographic data
    Returns: employees, revenue, industry, founded year
    """
    try:
        result = await people_data_labs.get_company_firmographics(
            domain=request.domain
        )
        
        background_tasks.add_task(
            cost_tracker.track,
            provider="peopledatalabs",
            endpoint="firmographics",
            cost=0.03
        )
        
        return EnrichmentResponse(
            success=True,
            data=result,
            provider="peopledatalabs",
            cost=0.03,
            timestamp=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/enrich/company/tech-stack", response_model=EnrichmentResponse)
async def get_tech_stack(
    request: CompanyTechStackRequest,
    background_tasks: BackgroundTasks
):
    """
    Get company technology stack using DataForSEO
    Returns: CMS, analytics, hosting, frameworks
    """
    try:
        result = await dataforseo.get_domain_technologies(
            domain=request.domain
        )
        
        background_tasks.add_task(
            cost_tracker.track,
            provider="dataforseo",
            endpoint="tech_stack",
            cost=0.05
        )
        
        return EnrichmentResponse(
            success=True,
            data=result,
            provider="dataforseo",
            cost=0.05,
            timestamp=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/enrich/company/backlinks", response_model=EnrichmentResponse)
async def get_backlinks(
    request: CompanyBacklinksRequest,
    background_tasks: BackgroundTasks
):
    """
    Get company backlink profile using DataForSEO
    Returns: total backlinks, referring domains, domain authority
    """
    try:
        result = await dataforseo.get_backlinks(
            domain=request.domain
        )
        
        background_tasks.add_task(
            cost_tracker.track,
            provider="dataforseo",
            endpoint="backlinks",
            cost=0.10
        )
        
        return EnrichmentResponse(
            success=True,
            data=result,
            provider="dataforseo",
            cost=0.10,
            timestamp=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/enrich/company/keywords", response_model=EnrichmentResponse)
async def get_keywords(
    request: CompanyKeywordsRequest,
    background_tasks: BackgroundTasks
):
    """
    Get company ranking keywords using DataForSEO
    Returns: total keywords, top keywords, estimated traffic
    """
    try:
        result = await dataforseo.get_ranking_keywords(
            domain=request.domain
        )
        
        background_tasks.add_task(
            cost_tracker.track,
            provider="dataforseo",
            endpoint="keywords",
            cost=0.05
        )
        
        return EnrichmentResponse(
            success=True,
            data=result,
            provider="dataforseo",
            cost=0.05,
            timestamp=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/enrich/company/reviews", response_model=EnrichmentResponse)
async def get_reviews(
    request: CompanyReviewsRequest,
    background_tasks: BackgroundTasks
):
    """
    Get Google reviews using DataForSEO
    Returns: rating, review count, recent reviews
    """
    try:
        result = await dataforseo.get_google_reviews(
            business_name=request.business_name,
            location=request.location
        )
        
        background_tasks.add_task(
            cost_tracker.track,
            provider="dataforseo",
            endpoint="reviews",
            cost=0.05
        )
        
        return EnrichmentResponse(
            success=True,
            data=result,
            provider="dataforseo",
            cost=0.05,
            timestamp=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# GROUP 3: INTENT & SIGNALS (3 ENDPOINTS)
# ============================================================================

@app.post("/api/v1/enrich/intent/hiring", response_model=EnrichmentResponse)
async def get_hiring_intent(
    request: HiringIntentRequest,
    background_tasks: BackgroundTasks
):
    """
    Detect hiring intent from job postings
    Scrapes careers page for active openings
    """
    try:
        result = await dataforseo.detect_hiring_intent(
            domain=request.domain
        )
        
        background_tasks.add_task(
            cost_tracker.track,
            provider="dataforseo",
            endpoint="hiring_intent",
            cost=0.10
        )
        
        return EnrichmentResponse(
            success=True,
            data=result,
            provider="dataforseo",
            cost=0.10,
            timestamp=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/enrich/intent/funding", response_model=EnrichmentResponse)
async def get_funding_data(
    request: FundingDataRequest,
    background_tasks: BackgroundTasks
):
    """
    Get funding data (if available)
    Note: Requires Crunchbase API integration (optional)
    """
    try:
        # Placeholder - integrate Crunchbase API if needed
        result = {
            "company_name": request.company_name,
            "funding_available": False,
            "message": "Crunchbase integration not configured"
        }
        
        return EnrichmentResponse(
            success=True,
            data=result,
            provider="crunchbase",
            cost=0.00,
            timestamp=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/enrich/intent/behavioral", response_model=EnrichmentResponse)
async def get_behavioral_intent(
    request: BehavioralIntentRequest,
    background_tasks: BackgroundTasks
):
    """
    Get behavioral intent data from AudienceLab
    Returns: website visitors, top visiting companies (SuperPixel data)
    """
    try:
        result = await audiencelab.get_visitor_intelligence(
            domain=request.domain,
            days=request.days or 7
        )
        
        background_tasks.add_task(
            cost_tracker.track,
            provider="audiencelab",
            endpoint="behavioral_intent",
            cost=0.00  # Included in AudienceLab subscription
        )
        
        return EnrichmentResponse(
            success=True,
            data=result,
            provider="audiencelab",
            cost=0.00,
            timestamp=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8500)
