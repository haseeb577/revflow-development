"""
Pydantic schemas for Rank & Rent Decision Tool API
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class TierEnum(str, Enum):
    activate = "activate"
    watchlist = "watchlist"
    sunset = "sunset"


class DecisionEnum(str, Enum):
    keep_activate = "KEEP & ACTIVATE"
    monitor = "MONITOR 90 DAYS"
    sunset = "SUNSET"


# =============================================================================
# SITE SCHEMAS
# =============================================================================

class SiteBase(BaseModel):
    name: str
    category: str
    city: str
    state: str


class SiteCreate(SiteBase):
    score: Optional[float] = None
    criteria_scores: Optional[Dict[str, float]] = {}
    local_search_demand: Optional[float] = 3
    competition_quality: Optional[float] = 3
    lead_value_proxy: Optional[float] = 3
    serp_weakness_index: Optional[float] = 3
    renter_willingness_evidence: Optional[float] = 3
    business_density: Optional[float] = 3
    urgency_score: Optional[float] = None
    regulation_score: Optional[float] = None
    renter_density: Optional[float] = None


class Site(SiteBase):
    id: str
    score: float
    tier: TierEnum
    decision: str
    monthly_potential: int
    avg_job_value: int
    criteria_scores: Optional[Dict[str, float]] = {}
    
    class Config:
        from_attributes = True


class SiteScore(BaseModel):
    site: Dict[str, Any]
    score: float
    tier: str
    decision: str
    criteria_scores: Dict[str, float]
    monthly_potential: int
    avg_job_value: int
    confidence: float
    scoring_breakdown: Dict[str, Dict[str, float]]


# =============================================================================
# PORTFOLIO SCHEMAS
# =============================================================================

class TierDistribution(BaseModel):
    activate: int
    watchlist: int
    sunset: int


class RevenuePotential(BaseModel):
    activate_monthly: int
    watchlist_monthly: int
    total_monthly: int
    activate_annual: int
    total_annual: int


class Recommendation(BaseModel):
    priority: int
    action: str
    description: str
    sites_affected: int
    expected_impact: str


class CategoryBreakdown(BaseModel):
    category: str
    site_count: int
    avg_score: float
    total_potential: int
    avg_job_value: int
    recommended: bool
    category_tier: int


class PortfolioSummary(BaseModel):
    total_sites: int
    tier_distribution: TierDistribution
    revenue_potential: RevenuePotential
    category_breakdown: List[CategoryBreakdown]
    top_sites: List[Dict[str, Any]]
    bottom_sites: List[Dict[str, Any]]
    recommendations: List[Recommendation]


# =============================================================================
# WHAT-IF SCHEMAS
# =============================================================================

class WhatIfScenario(BaseModel):
    type: str = Field(..., description="Type: weight_change, threshold_change, category_focus, site_score")
    weight_changes: Optional[Dict[str, float]] = None
    activate_threshold: Optional[float] = 3.7
    watchlist_threshold: Optional[float] = 3.2
    categories: Optional[List[str]] = None
    site_changes: Optional[Dict[str, float]] = None


class TierChangeDetail(BaseModel):
    id: str
    name: str
    original_score: Optional[float] = None
    new_score: Optional[float] = None
    score_change: Optional[float] = None
    original_tier: str
    new_tier: str
    tier_changed: bool


class WhatIfImpactSummary(BaseModel):
    sites_rescored: Optional[int] = None
    tier_changes: int
    average_score_change: Optional[float] = None
    sites_promoted: Optional[int] = None
    sites_demoted: Optional[int] = None


class WhatIfResult(BaseModel):
    scenario_type: str
    impact_summary: Dict[str, Any]
    tier_distribution: Dict[str, Any]
    tier_change_details: List[Dict[str, Any]]
    weight_changes: Optional[Dict[str, float]] = None
    thresholds: Optional[Dict[str, Any]] = None
    focus_categories: Optional[List[str]] = None
    all_sites_rescored: Optional[List[Dict[str, Any]]] = None
    focused_sites: Optional[List[Dict[str, Any]]] = None
    excluded_sites: Optional[List[Dict[str, Any]]] = None
    recommendation: Optional[str] = None


# =============================================================================
# MARKET DISCOVERY SCHEMAS
# =============================================================================

class MarketSearchRequest(BaseModel):
    categories: Optional[List[str]] = None
    states: Optional[List[str]] = None
    min_population: int = 25000
    max_population: int = 250000
    max_competition: str = "moderate"


class ScoringBreakdown(BaseModel):
    category_score: float
    competition_score: float
    growth_score: float
    population_score: float
    sun_belt_bonus: float


class EstimatedPotential(BaseModel):
    monthly: int
    annual: int


class MarketSearchResult(BaseModel):
    category: str
    city: str
    state: str
    score: float
    tier: str
    recommendation: str
    population: int
    growth_rate: float
    competition_level: str
    category_priority: int
    scoring_breakdown: ScoringBreakdown
    next_steps: List[str]
    estimated_potential: EstimatedPotential


class MarketOpportunity(BaseModel):
    category: str
    city: str
    state: str
    score: float
    tier: str
    recommendation: str
    monthly_potential: int
    next_steps: List[str]


# =============================================================================
# CATEGORY BENCHMARK SCHEMAS
# =============================================================================

class CategoryBenchmark(BaseModel):
    category: str
    avg_job_value: int
    lead_value_range: List[int]
    urgency_score: int
    seasonality: int
    regulation_risk: int
    renter_density: int
    serp_competition: str
    monthly_potential: int
    category_tier: int
    recommended: bool


# =============================================================================
# INTEGRATION SCHEMAS
# =============================================================================

class RevFlowLeadData(BaseModel):
    site_id: str
    leads_count: int
    conversion_rate: float
    avg_lead_value: float
    period_start: datetime
    period_end: datetime


class RRCompetitiveData(BaseModel):
    site_id: str
    serp_position: int
    local_pack_rank: Optional[int]
    competitor_count: int
    avg_competitor_reviews: int
    keyword_rankings: Dict[str, int]


class ExportToRR(BaseModel):
    business_name: str
    category: str
    location: Dict[str, str]
    analysis_request: Dict[str, Any]


# =============================================================================
# REPORT SCHEMAS
# =============================================================================

class ActionPlanItem(BaseModel):
    week: str
    action_type: str
    task: str
    sites: List[str]
    impact: str


class RevenueProjection(BaseModel):
    months: int
    success_rate: float
    projections: Dict[str, Dict[str, int]]


class CategoryAnalysisResult(BaseModel):
    category: str
    site_count: int
    avg_score: float
    total_potential: int
    avg_job_value: int
    recommended: bool
    category_tier: int
