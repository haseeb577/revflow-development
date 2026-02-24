"""
Pydantic models for RevFlow Enrichment Service
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime


# ============================================================================
# REQUEST MODELS - GROUP 1: CONTACT ENRICHMENT
# ============================================================================

class EmailEnrichRequest(BaseModel):
    first_name: str = Field(..., description="First name")
    last_name: str = Field(..., description="Last name")
    company_domain: str = Field(..., description="Company domain (e.g., acmeplumbing.com)")
    
    @validator('company_domain')
    def validate_domain(cls, v):
        # Remove http/https if present
        v = v.replace('http://', '').replace('https://', '').replace('www.', '')
        # Remove trailing slash
        v = v.rstrip('/')
        return v


class PhoneEnrichRequest(BaseModel):
    email: Optional[str] = Field(None, description="Email address")
    first_name: Optional[str] = Field(None, description="First name")
    last_name: Optional[str] = Field(None, description="Last name")
    company_domain: Optional[str] = Field(None, description="Company domain")


class EmailValidationRequest(BaseModel):
    email: str = Field(..., description="Email to validate")


class PhoneValidationRequest(BaseModel):
    phone: str = Field(..., description="Phone number to validate")


class LinkedInPersonRequest(BaseModel):
    first_name: str = Field(..., description="First name")
    last_name: str = Field(..., description="Last name")
    company: str = Field(..., description="Company name")


class LinkedInCompanyRequest(BaseModel):
    company_domain: str = Field(..., description="Company domain")


class PersonEnrichRequest(BaseModel):
    email: Optional[str] = Field(None, description="Email address")
    first_name: Optional[str] = Field(None, description="First name")
    last_name: Optional[str] = Field(None, description="Last name")
    company_domain: Optional[str] = Field(None, description="Company domain")


class WaterfallEnrichRequest(BaseModel):
    input: Dict[str, Any] = Field(..., description="Input data (name, company, etc.)")
    data_points: List[str] = Field(..., description="Data points to enrich: email, phone, linkedin, etc.")
    providers: Optional[List[str]] = Field(
        default=["audiencelab", "hunter", "prospeo", "datagma"],
        description="Providers to try in order"
    )


class BatchEnrichRequest(BaseModel):
    contacts: List[Dict[str, Any]] = Field(..., description="Array of contacts to enrich")
    data_points: List[str] = Field(..., description="Data points to enrich for each contact")


# ============================================================================
# REQUEST MODELS - GROUP 2: COMPANY ENRICHMENT
# ============================================================================

class CompanyFirmographicsRequest(BaseModel):
    domain: str = Field(..., description="Company domain")


class CompanyTechStackRequest(BaseModel):
    domain: str = Field(..., description="Company domain")


class CompanyBacklinksRequest(BaseModel):
    domain: str = Field(..., description="Company domain")


class CompanyKeywordsRequest(BaseModel):
    domain: str = Field(..., description="Company domain")


class CompanyReviewsRequest(BaseModel):
    business_name: str = Field(..., description="Business name")
    location: str = Field(..., description="Location (e.g., Dallas, TX)")


# ============================================================================
# REQUEST MODELS - GROUP 3: INTENT & SIGNALS
# ============================================================================

class HiringIntentRequest(BaseModel):
    domain: str = Field(..., description="Company domain")


class FundingDataRequest(BaseModel):
    company_name: str = Field(..., description="Company name")


class BehavioralIntentRequest(BaseModel):
    domain: str = Field(..., description="Company domain")
    days: Optional[int] = Field(default=7, description="Days of data to retrieve")


# ============================================================================
# RESPONSE MODELS
# ============================================================================

class EnrichmentResponse(BaseModel):
    success: bool = Field(..., description="Whether enrichment succeeded")
    data: Dict[str, Any] = Field(..., description="Enriched data")
    provider: Optional[str] = Field(None, description="Provider used")
    cost: Optional[float] = Field(None, description="Cost in USD")
    timestamp: str = Field(..., description="ISO timestamp")


class WaterfallResponse(BaseModel):
    success: bool = Field(..., description="Whether waterfall succeeded")
    data: Dict[str, Any] = Field(..., description="Enriched data from all providers")
    providers_used: List[str] = Field(..., description="Providers that returned data")
    total_cost: float = Field(..., description="Total cost across all providers")
    timestamp: str = Field(..., description="ISO timestamp")


class BatchEnrichmentResponse(BaseModel):
    success: bool = Field(..., description="Whether batch enrichment succeeded")
    data: List[Dict[str, Any]] = Field(..., description="Array of enriched contacts")
    total_enriched: int = Field(..., description="Total contacts enriched")
    total_cost: float = Field(..., description="Total cost")
    timestamp: str = Field(..., description="ISO timestamp")


# ============================================================================
# INTERNAL DATA MODELS
# ============================================================================

class ProviderResponse(BaseModel):
    """Standardized response from any provider"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    provider: str
    cost: float = 0.0
    confidence: Optional[int] = None  # 0-100


class ContactData(BaseModel):
    """Standardized contact data structure"""
    email: Optional[str] = None
    email_verified: Optional[bool] = None
    phone: Optional[str] = None
    phone_verified: Optional[bool] = None
    linkedin_url: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    job_title: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None
    

class CompanyData(BaseModel):
    """Standardized company data structure"""
    domain: str
    name: Optional[str] = None
    industry: Optional[str] = None
    employees: Optional[str] = None
    revenue: Optional[str] = None
    founded: Optional[int] = None
    location: Optional[str] = None
    technologies: Optional[List[str]] = None
    backlinks_count: Optional[int] = None
    domain_authority: Optional[int] = None
    keywords_count: Optional[int] = None
    estimated_traffic: Optional[str] = None
