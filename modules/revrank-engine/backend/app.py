"""
╔══════════════════════════════════════════════════════════════════════════════╗
║          RANK & RENT DECISION TOOL - BACKEND API                             ║
║          Integrated with R&R/RevFlow Platform Architecture                   ║
╚══════════════════════════════════════════════════════════════════════════════╝

Version: 1.0.0
Integration: R&R Automation + RevFlow Assessment Engine
Infrastructure: automation.smarketsherpa.ai
"""

from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum
import json
import uuid

# =============================================================================
# APPLICATION INITIALIZATION
# =============================================================================

app = FastAPI(
    title="Rank & Rent Decision Tool API",
    description="Portfolio management, market discovery, and what-if analysis for rank & rent operations",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================================================================
# PYDANTIC SCHEMAS (Following RevFlow Export Schema v2.2.0 patterns)
# =============================================================================

class TierEnum(str, Enum):
    activate = "activate"
    watchlist = "watchlist"
    sunset = "sunset"

class DecisionEnum(str, Enum):
    keep_activate = "KEEP & ACTIVATE"
    monitor = "MONITOR 90 DAYS"
    sunset = "SUNSET"

class CategoryTierEnum(int, Enum):
    tier_1_expand = 1
    tier_2_maintain = 2
    tier_3_selective = 3
    tier_4_reduce = 4
    tier_5_avoid = 5

class SiteBase(BaseModel):
    name: str = Field(..., description="Site/business name")
    category: str = Field(..., description="Service category (e.g., Concrete, Roofing)")
    city: str = Field(..., description="Primary city")
    state: str = Field(..., description="State code (e.g., TX, FL)")
    domain: Optional[str] = None

class SiteCreate(SiteBase):
    criteria_scores: Optional[Dict[str, float]] = Field(default_factory=dict)

class Site(SiteBase):
    id: str
    score: float
    tier: TierEnum
    decision: str
    monthly_potential: int
    avg_job_value: int
    criteria_scores: Dict[str, float] = Field(default_factory=dict)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class SiteScore(BaseModel):
    site: Dict[str, Any]
    score: float
    tier: str
    decision: str
    monthly_potential: int
    avg_job_value: int
    confidence: float
    criteria_breakdown: Dict[str, Dict[str, float]]
    recommendations: List[str]

class MarketSearchRequest(BaseModel):
    categories: Optional[List[str]] = None
    states: Optional[List[str]] = None
    min_population: int = Field(default=25000, ge=5000)
    max_population: int = Field(default=250000, le=1000000)
    max_competition: str = Field(default="moderate")
    min_score: float = Field(default=3.5, ge=1.0, le=5.0)

class WhatIfScenario(BaseModel):
    scenario_type: str = Field(..., description="weight_change, threshold_change, category_focus")
    parameters: Dict[str, Any] = Field(default_factory=dict)

class CompetitiveAnalysisRequest(BaseModel):
    category: str
    city: str
    state: str
    include_serp: bool = True
    include_map_pack: bool = True
    include_competitor_details: bool = True

# =============================================================================
# KNOWLEDGE BASE - CATEGORY BENCHMARKS (From Research)
# =============================================================================

CATEGORY_BENCHMARKS = {
    "Concrete": {
        "avg_job_value": 7500,
        "lead_value_range": [150, 400],
        "urgency_score": 4,
        "seasonality": 3,
        "regulation_risk": 5,  # Low risk (5 = good)
        "renter_density": 4,
        "serp_competition": "moderate",
        "monthly_potential": 2000,
        "category_tier": 1,
        "time_to_rank_months": 4,
        "recommended_action": "EXPAND",
        "notes": "Proven performer, high job values, strong renter demand"
    },
    "Roofing": {
        "avg_job_value": 10000,
        "lead_value_range": [200, 500],
        "urgency_score": 5,
        "seasonality": 3,
        "regulation_risk": 4,
        "renter_density": 5,
        "serp_competition": "high",
        "monthly_potential": 2500,
        "category_tier": 1,
        "time_to_rank_months": 5,
        "recommended_action": "EXPAND",
        "notes": "Highest monthly potential, emergency nature drives conversions"
    },
    "Water Damage": {
        "avg_job_value": 4500,
        "lead_value_range": [200, 750],
        "urgency_score": 5,
        "seasonality": 4,
        "regulation_risk": 4,
        "renter_density": 3,
        "serp_competition": "moderate",
        "monthly_potential": 2000,
        "category_tier": 1,
        "time_to_rank_months": 4,
        "recommended_action": "EXPAND",
        "notes": "Emergency service, insurance coverage, high close rate"
    },
    "Electric": {
        "avg_job_value": 3500,
        "lead_value_range": [100, 300],
        "urgency_score": 4,
        "seasonality": 5,
        "regulation_risk": 3,
        "renter_density": 5,
        "serp_competition": "moderate",
        "monthly_potential": 1500,
        "category_tier": 2,
        "time_to_rank_months": 5,
        "recommended_action": "MAINTAIN",
        "notes": "Year-round demand, strong renter pool, licensing required"
    },
    "Fence": {
        "avg_job_value": 4500,
        "lead_value_range": [100, 250],
        "urgency_score": 3,
        "seasonality": 3,
        "regulation_risk": 5,
        "renter_density": 4,
        "serp_competition": "low",
        "monthly_potential": 1500,
        "category_tier": 2,
        "time_to_rank_months": 3,
        "recommended_action": "MAINTAIN",
        "notes": "Good job values, lower competition, faster time to rank"
    },
    "Tree Care": {
        "avg_job_value": 1800,
        "lead_value_range": [50, 200],
        "urgency_score": 4,
        "seasonality": 3,
        "regulation_risk": 4,
        "renter_density": 4,
        "serp_competition": "low",
        "monthly_potential": 1200,
        "category_tier": 2,
        "time_to_rank_months": 3,
        "recommended_action": "MAINTAIN",
        "notes": "Storm-driven demand, repeat business potential"
    },
    "Plumbing": {
        "avg_job_value": 2500,
        "lead_value_range": [75, 250],
        "urgency_score": 5,
        "seasonality": 5,
        "regulation_risk": 3,
        "renter_density": 5,
        "serp_competition": "high",
        "monthly_potential": 1500,
        "category_tier": 2,
        "time_to_rank_months": 6,
        "recommended_action": "MAINTAIN",
        "notes": "Emergency nature, but very competitive markets"
    },
    "Drywall": {
        "avg_job_value": 2200,
        "lead_value_range": [50, 150],
        "urgency_score": 2,
        "seasonality": 4,
        "regulation_risk": 5,
        "renter_density": 4,
        "serp_competition": "low",
        "monthly_potential": 1000,
        "category_tier": 3,
        "time_to_rank_months": 3,
        "recommended_action": "SELECTIVE",
        "notes": "Lower urgency limits lead quality"
    },
    "Carpentry": {
        "avg_job_value": 3000,
        "lead_value_range": [75, 200],
        "urgency_score": 2,
        "seasonality": 4,
        "regulation_risk": 5,
        "renter_density": 3,
        "serp_competition": "low",
        "monthly_potential": 1000,
        "category_tier": 3,
        "time_to_rank_months": 3,
        "recommended_action": "SELECTIVE",
        "notes": "Project-based, less urgent nature"
    },
    "Masonry": {
        "avg_job_value": 5000,
        "lead_value_range": [100, 300],
        "urgency_score": 2,
        "seasonality": 3,
        "regulation_risk": 5,
        "renter_density": 3,
        "serp_competition": "low",
        "monthly_potential": 1200,
        "category_tier": 3,
        "time_to_rank_months": 4,
        "recommended_action": "SELECTIVE",
        "notes": "High job value but seasonal and project-based"
    },
    "Landscaping": {
        "avg_job_value": 3500,
        "lead_value_range": [50, 150],
        "urgency_score": 2,
        "seasonality": 2,
        "regulation_risk": 5,
        "renter_density": 5,
        "serp_competition": "moderate",
        "monthly_potential": 1000,
        "category_tier": 3,
        "time_to_rank_months": 4,
        "recommended_action": "SELECTIVE",
        "notes": "High competition from established players"
    },
    "Painting": {
        "avg_job_value": 3000,
        "lead_value_range": [50, 150],
        "urgency_score": 1,
        "seasonality": 3,
        "regulation_risk": 5,
        "renter_density": 5,
        "serp_competition": "moderate",
        "monthly_potential": 800,
        "category_tier": 3,
        "time_to_rank_months": 4,
        "recommended_action": "SELECTIVE",
        "notes": "Low urgency, price-driven market"
    },
    "Pool cleaning": {
        "avg_job_value": 1200,
        "lead_value_range": [25, 100],
        "urgency_score": 2,
        "seasonality": 2,
        "regulation_risk": 4,
        "renter_density": 4,
        "serp_competition": "moderate",
        "monthly_potential": 800,
        "category_tier": 3,
        "time_to_rank_months": 4,
        "recommended_action": "SELECTIVE",
        "notes": "Recurring revenue but highly seasonal"
    },
    "Patio covers": {
        "avg_job_value": 5500,
        "lead_value_range": [100, 250],
        "urgency_score": 1,
        "seasonality": 3,
        "regulation_risk": 4,
        "renter_density": 3,
        "serp_competition": "low",
        "monthly_potential": 1000,
        "category_tier": 3,
        "time_to_rank_months": 4,
        "recommended_action": "SELECTIVE",
        "notes": "High job value but low search volume"
    },
    "Appliance repair": {
        "avg_job_value": 350,
        "lead_value_range": [25, 75],
        "urgency_score": 4,
        "seasonality": 5,
        "regulation_risk": 4,
        "renter_density": 4,
        "serp_competition": "moderate",
        "monthly_potential": 600,
        "category_tier": 4,
        "time_to_rank_months": 4,
        "recommended_action": "REDUCE",
        "notes": "Low job values cannot support $1,500/mo target"
    },
    "Moving": {
        "avg_job_value": 1500,
        "lead_value_range": [50, 150],
        "urgency_score": 3,
        "seasonality": 3,
        "regulation_risk": 3,
        "renter_density": 4,
        "serp_competition": "moderate",
        "monthly_potential": 800,
        "category_tier": 4,
        "time_to_rank_months": 5,
        "recommended_action": "REDUCE",
        "notes": "High regulation (DOT), established players dominate"
    },
    "Mobile mechanic": {
        "avg_job_value": 500,
        "lead_value_range": [25, 100],
        "urgency_score": 4,
        "seasonality": 4,
        "regulation_risk": 4,
        "renter_density": 2,
        "serp_competition": "low",
        "monthly_potential": 500,
        "category_tier": 4,
        "time_to_rank_months": 3,
        "recommended_action": "REDUCE",
        "notes": "Fragmented renter pool, low demand"
    },
    "Law": {
        "avg_job_value": 15000,
        "lead_value_range": [200, 1000],
        "urgency_score": 3,
        "seasonality": 5,
        "regulation_risk": 1,  # YMYL - High risk
        "renter_density": 5,
        "serp_competition": "very_high",
        "monthly_potential": 3000,
        "category_tier": 4,
        "time_to_rank_months": 12,
        "recommended_action": "REDUCE",
        "notes": "YMYL content requirements, extreme competition"
    },
    "Towing": {
        "avg_job_value": 200,
        "lead_value_range": [15, 50],
        "urgency_score": 5,
        "seasonality": 5,
        "regulation_risk": 2,
        "renter_density": 4,
        "serp_competition": "high",
        "monthly_potential": 500,
        "category_tier": 5,
        "time_to_rank_months": 5,
        "recommended_action": "AVOID",
        "notes": "Job value too low for R&R model"
    },
    "Junk Removal": {
        "avg_job_value": 400,
        "lead_value_range": [25, 75],
        "urgency_score": 2,
        "seasonality": 4,
        "regulation_risk": 4,
        "renter_density": 4,
        "serp_competition": "moderate",
        "monthly_potential": 600,
        "category_tier": 5,
        "time_to_rank_months": 4,
        "recommended_action": "AVOID",
        "notes": "Low urgency, commoditized service"
    },
    "Bee rescue": {
        "avg_job_value": 250,
        "lead_value_range": [25, 75],
        "urgency_score": 3,
        "seasonality": 2,
        "regulation_risk": 3,
        "renter_density": 1,
        "serp_competition": "low",
        "monthly_potential": 300,
        "category_tier": 5,
        "time_to_rank_months": 3,
        "recommended_action": "AVOID",
        "notes": "Niche too small, minimal renter pool"
    }
}

# =============================================================================
# MARKET DATABASE (Sun Belt Focus + Growth Markets)
# =============================================================================

MARKET_DATABASE = {
    "TX": {
        "cities": [
            {"city": "Duncanville", "population": 40000, "growth": 0.02, "competition": "low", "housing_age": 25},
            {"city": "Lancaster", "population": 39000, "growth": 0.03, "competition": "low", "housing_age": 22},
            {"city": "Kingsville", "population": 26000, "growth": 0.01, "competition": "very_low", "housing_age": 30},
            {"city": "Socorro", "population": 35000, "growth": 0.04, "competition": "low", "housing_age": 18},
            {"city": "La Porte", "population": 36000, "growth": 0.02, "competition": "moderate", "housing_age": 28},
            {"city": "Harker Heights", "population": 33000, "growth": 0.05, "competition": "low", "housing_age": 15},
            {"city": "Cedar Hill", "population": 50000, "growth": 0.02, "competition": "low", "housing_age": 20},
            {"city": "DeSoto", "population": 55000, "growth": 0.01, "competition": "low", "housing_age": 25},
            {"city": "Waxahachie", "population": 40000, "growth": 0.04, "competition": "low", "housing_age": 18},
            {"city": "Wylie", "population": 55000, "growth": 0.06, "competition": "moderate", "housing_age": 12},
            {"city": "Rockwall", "population": 50000, "growth": 0.05, "competition": "moderate", "housing_age": 15},
            {"city": "Midlothian", "population": 35000, "growth": 0.07, "competition": "low", "housing_age": 10},
        ],
        "sun_belt": True,
        "avg_housing_age": 20
    },
    "FL": {
        "cities": [
            {"city": "Key West", "population": 25000, "growth": 0.01, "competition": "moderate", "housing_age": 35},
            {"city": "Ocoee", "population": 52000, "growth": 0.04, "competition": "low", "housing_age": 20},
            {"city": "Palm Bay", "population": 120000, "growth": 0.05, "competition": "low", "housing_age": 25},
            {"city": "Melbourne", "population": 85000, "growth": 0.03, "competition": "moderate", "housing_age": 28},
            {"city": "Deltona", "population": 95000, "growth": 0.04, "competition": "low", "housing_age": 22},
            {"city": "Port St. Lucie", "population": 220000, "growth": 0.06, "competition": "moderate", "housing_age": 18},
            {"city": "Cape Coral", "population": 210000, "growth": 0.07, "competition": "moderate", "housing_age": 20},
            {"city": "Lehigh Acres", "population": 130000, "growth": 0.05, "competition": "low", "housing_age": 15},
            {"city": "North Port", "population": 80000, "growth": 0.08, "competition": "low", "housing_age": 12},
            {"city": "Poinciana", "population": 70000, "growth": 0.06, "competition": "very_low", "housing_age": 15},
        ],
        "sun_belt": True,
        "avg_housing_age": 22
    },
    "AZ": {
        "cities": [
            {"city": "El Mirage", "population": 38000, "growth": 0.04, "competition": "low", "housing_age": 15},
            {"city": "San Tan Valley", "population": 100000, "growth": 0.08, "competition": "low", "housing_age": 12},
            {"city": "Maricopa", "population": 60000, "growth": 0.06, "competition": "low", "housing_age": 10},
            {"city": "Buckeye", "population": 90000, "growth": 0.10, "competition": "low", "housing_age": 8},
            {"city": "Queen Creek", "population": 65000, "growth": 0.09, "competition": "low", "housing_age": 10},
            {"city": "Florence", "population": 30000, "growth": 0.04, "competition": "very_low", "housing_age": 15},
            {"city": "Casa Grande", "population": 58000, "growth": 0.05, "competition": "low", "housing_age": 20},
            {"city": "Apache Junction", "population": 42000, "growth": 0.03, "competition": "low", "housing_age": 25},
        ],
        "sun_belt": True,
        "avg_housing_age": 15
    },
    "NC": {
        "cities": [
            {"city": "Apex", "population": 60000, "growth": 0.08, "competition": "moderate", "housing_age": 15},
            {"city": "Holly Springs", "population": 45000, "growth": 0.10, "competition": "low", "housing_age": 12},
            {"city": "Wake Forest", "population": 50000, "growth": 0.07, "competition": "moderate", "housing_age": 18},
            {"city": "Garner", "population": 35000, "growth": 0.04, "competition": "low", "housing_age": 22},
            {"city": "Clayton", "population": 25000, "growth": 0.06, "competition": "low", "housing_age": 15},
            {"city": "Mooresville", "population": 48000, "growth": 0.05, "competition": "moderate", "housing_age": 18},
            {"city": "Indian Trail", "population": 42000, "growth": 0.04, "competition": "low", "housing_age": 15},
        ],
        "sun_belt": True,
        "avg_housing_age": 17
    },
    "GA": {
        "cities": [
            {"city": "Newnan", "population": 45000, "growth": 0.05, "competition": "low", "housing_age": 20},
            {"city": "Douglasville", "population": 35000, "growth": 0.04, "competition": "low", "housing_age": 22},
            {"city": "Woodstock", "population": 35000, "growth": 0.05, "competition": "low", "housing_age": 18},
            {"city": "Canton", "population": 32000, "growth": 0.06, "competition": "low", "housing_age": 15},
            {"city": "Acworth", "population": 25000, "growth": 0.04, "competition": "low", "housing_age": 20},
            {"city": "Dallas", "population": 15000, "growth": 0.07, "competition": "very_low", "housing_age": 12},
            {"city": "Cartersville", "population": 22000, "growth": 0.03, "competition": "low", "housing_age": 25},
        ],
        "sun_belt": True,
        "avg_housing_age": 19
    },
    "CA": {
        "cities": [
            {"city": "Benicia", "population": 28000, "growth": 0.01, "competition": "moderate", "housing_age": 35},
            {"city": "Castro Valley", "population": 65000, "growth": 0.01, "competition": "moderate", "housing_age": 40},
            {"city": "Banning", "population": 32000, "growth": 0.02, "competition": "low", "housing_age": 30},
            {"city": "Hanford", "population": 60000, "growth": 0.02, "competition": "low", "housing_age": 28},
            {"city": "Tulare", "population": 68000, "growth": 0.02, "competition": "low", "housing_age": 25},
            {"city": "Galt", "population": 27000, "growth": 0.03, "competition": "low", "housing_age": 22},
        ],
        "sun_belt": True,
        "avg_housing_age": 30
    }
}

# =============================================================================
# SCORING ENGINE (Enhanced 16-Criteria Model)
# =============================================================================

SCORING_CRITERIA = {
    "category_vertical_score": {
        "weight": 12,
        "description": "Industry-specific success probability based on job value, urgency, renter density",
        "source": "Category benchmarks database"
    },
    "local_search_demand": {
        "weight": 10,
        "description": "Monthly search volume for [service] + [city] queries",
        "source": "DataForSEO / SemRush integration"
    },
    "competition_quality": {
        "weight": 10,
        "description": "Strength of ranking competitors (DR, RD, content depth)",
        "source": "R&R competitive analysis module"
    },
    "lead_value_proxy": {
        "weight": 10,
        "description": "Average job value / CPC as indicator of lead quality",
        "source": "Category benchmarks + market data"
    },
    "serp_weakness_index": {
        "weight": 8,
        "description": "Exploitable weaknesses in current top 10 (thin content, poor UX, weak backlinks)",
        "source": "RevFlow Module A analysis"
    },
    "renter_willingness_evidence": {
        "weight": 8,
        "description": "Evidence of contractors actively seeking leads in this market",
        "source": "Manual research + lead buyer database"
    },
    "business_density": {
        "weight": 6,
        "description": "Number of potential renter contractors in service area",
        "source": "Google Maps API / GBP data"
    },
    "urgency_call_first": {
        "weight": 6,
        "description": "Emergency nature of service (1-5 scale)",
        "source": "Category benchmarks"
    },
    "regulation_compliance_risk": {
        "weight": 5,
        "description": "YMYL risk, licensing requirements (5 = low risk, 1 = high risk)",
        "source": "Category benchmarks + state research"
    },
    "local_pack_friction": {
        "weight": 5,
        "description": "Difficulty of entering local 3-pack (avg reviews, established players)",
        "source": "GBP analysis"
    },
    "replicability_nearby": {
        "weight": 5,
        "description": "Ability to clone success to adjacent markets",
        "source": "Geographic analysis"
    },
    "portfolio_diversification": {
        "weight": 4,
        "description": "Value of adding to portfolio balance",
        "source": "Current portfolio analysis"
    },
    "commercial_intent_mix": {
        "weight": 3,
        "description": "Percentage of searches with buying intent",
        "source": "Keyword analysis"
    },
    "seasonality_profile": {
        "weight": 3,
        "description": "Demand stability throughout year (5 = stable, 1 = highly seasonal)",
        "source": "Category benchmarks"
    },
    "city_size_growth": {
        "weight": 3,
        "description": "Population and growth trajectory fit",
        "source": "Census data / market database"
    },
    "serp_vulnerability": {
        "weight": 2,
        "description": "How easily rankings can be disrupted by algorithm changes",
        "source": "Historical SERP analysis"
    }
}

# =============================================================================
# PORTFOLIO DATA (53 Sites)
# =============================================================================

PORTFOLIO_DATA = [
    # ACTIVATE TIER (Score >= 3.7)
    {"id": "site_001", "name": "Duncanville Concrete Driveway Pros", "category": "Concrete", "city": "Duncanville", "state": "TX", "score": 4.12},
    {"id": "site_002", "name": "El Mirage Concrete Contractor", "category": "Concrete", "city": "El Mirage", "state": "AZ", "score": 4.08},
    {"id": "site_003", "name": "Kingsville Concrete Crafting Co.", "category": "Concrete", "city": "Kingsville", "state": "TX", "score": 4.05},
    {"id": "site_004", "name": "Lancaster Concrete Driveway Pros", "category": "Concrete", "city": "Lancaster", "state": "TX", "score": 4.03},
    {"id": "site_005", "name": "Manchester Concrete Craftsmanship", "category": "Concrete", "city": "Manchester", "state": "CT", "score": 4.01},
    {"id": "site_006", "name": "Tewksbury Concrete Craftsmanship", "category": "Concrete", "city": "Tewksbury", "state": "MA", "score": 4.00},
    {"id": "site_007", "name": "Epoxy Flooring Pros of La Porte", "category": "Concrete", "city": "La Porte", "state": "TX", "score": 3.98},
    {"id": "site_008", "name": "Benicia Roofing Artisans", "category": "Roofing", "city": "Benicia", "state": "CA", "score": 3.92},
    {"id": "site_009", "name": "Burke Roofing and Renovations", "category": "Roofing", "city": "Burke", "state": "VA", "score": 3.89},
    {"id": "site_010", "name": "Key West Water Rescue Team", "category": "Water Damage", "city": "Key West", "state": "FL", "score": 3.87},
    {"id": "site_011", "name": "Ocoee Water Damage Repair", "category": "Water Damage", "city": "Ocoee", "state": "FL", "score": 3.85},
    {"id": "site_012", "name": "Belleville Electrical Masters", "category": "Electric", "city": "Belleville", "state": "NJ", "score": 3.82},
    {"id": "site_013", "name": "Castro Valley Electrician Pros", "category": "Electric", "city": "Castro Valley", "state": "CA", "score": 3.80},
    {"id": "site_014", "name": "San Lorenzo Fencing Builders", "category": "Fence", "city": "San Lorenzo", "state": "CA", "score": 3.78},
    {"id": "site_015", "name": "San Tan Valley Fencing Co.", "category": "Fence", "city": "San Tan Valley", "state": "AZ", "score": 3.76},
    {"id": "site_016", "name": "Socorro Texas Fencing Pros", "category": "Fence", "city": "Socorro", "state": "TX", "score": 3.75},
    {"id": "site_017", "name": "Jamestown Tree Care Masters", "category": "Tree Care", "city": "Jamestown", "state": "NY", "score": 3.73},
    {"id": "site_018", "name": "Spanaway Tree Care Collective", "category": "Tree Care", "city": "Spanaway", "state": "WA", "score": 3.71},
    {"id": "site_019", "name": "Westfield Tree Care Specialists", "category": "Tree Care", "city": "Westfield", "state": "NJ", "score": 3.70},
    # WATCHLIST TIER (Score 3.2 - 3.69)
    {"id": "site_020", "name": "Bell Gardens Drywall Pros", "category": "Drywall", "city": "Bell Gardens", "state": "CA", "score": 3.52},
    {"id": "site_021", "name": "Kearny Drywall Contractor", "category": "Drywall", "city": "Kearny", "state": "NJ", "score": 3.50},
    {"id": "site_022", "name": "La Puente Drywall Pros", "category": "Drywall", "city": "La Puente", "state": "CA", "score": 3.48},
    {"id": "site_023", "name": "Carmel Carpentry Solutions", "category": "Carpentry", "city": "Carmel", "state": "NY", "score": 3.45},
    {"id": "site_024", "name": "Dedham Woodworking & Carpentry", "category": "Carpentry", "city": "Dedham", "state": "MA", "score": 3.42},
    {"id": "site_025", "name": "Harker Heights Carpenter Collective", "category": "Carpentry", "city": "Harker Heights", "state": "TX", "score": 3.40},
    {"id": "site_026", "name": "Gloucester Plumbing Pros", "category": "Plumbing", "city": "Gloucester", "state": "MA", "score": 3.38},
    {"id": "site_027", "name": "Fountainebleau Plumbing Pros", "category": "Plumbing", "city": "Fontainebleau", "state": "FL", "score": 3.35},
    {"id": "site_028", "name": "Hanford's Trusted Moving Company", "category": "Moving", "city": "Hanford", "state": "CA", "score": 3.25},
    {"id": "site_029", "name": "Arcadia Landscaping Pros", "category": "Landscaping", "city": "Arcadia", "state": "CA", "score": 3.20},
    {"id": "site_030", "name": "Banning Green Oasis Landscaping", "category": "Landscaping", "city": "Banning", "state": "CA", "score": 3.18},
    {"id": "site_031", "name": "Monroeville Masonry Specialists", "category": "Masonry", "city": "Monroeville", "state": "PA", "score": 3.15},
    {"id": "site_032", "name": "Montgomery Village Masonry Works", "category": "Masonry", "city": "Montgomery Village", "state": "MD", "score": 3.12},
    {"id": "site_033", "name": "Gahanna Colorful Coatings Studios", "category": "Painting", "city": "Gahanna", "state": "OH", "score": 3.05},
    {"id": "site_034", "name": "Hamtramck Artistic Painting", "category": "Painting", "city": "Hamtramck", "state": "MI", "score": 3.00},
    # SUNSET TIER (Score < 3.2)
    {"id": "site_035", "name": "Balch Springs Pool Cleaning Pros", "category": "Pool cleaning", "city": "Balch Springs", "state": "TX", "score": 2.95},
    {"id": "site_036", "name": "Boyton Beach Pool Cleaners", "category": "Pool cleaning", "city": "Boynton Beach", "state": "FL", "score": 2.90},
    {"id": "site_037", "name": "Lawndale Pool Care Crew", "category": "Pool cleaning", "city": "Lawndale", "state": "CA", "score": 2.85},
    {"id": "site_038", "name": "Galt Appliance Care", "category": "Appliance repair", "city": "Galt", "state": "CA", "score": 2.75},
    {"id": "site_039", "name": "Hattiesburg Appliance Repair Pros", "category": "Appliance repair", "city": "Hattiesburg", "state": "MS", "score": 2.65},
    {"id": "site_040", "name": "New Iberia Appliance Fixers", "category": "Appliance repair", "city": "New Iberia", "state": "LA", "score": 2.55},
    {"id": "site_041", "name": "Reedley Appliance Repair Services", "category": "Appliance repair", "city": "Reedley", "state": "CA", "score": 2.48},
    {"id": "site_042", "name": "Tulare Appliance Repair Hub", "category": "Appliance repair", "city": "Tulare", "state": "CA", "score": 2.40},
    {"id": "site_043", "name": "Andover Mobile Mechanic Masters", "category": "Mobile mechanic", "city": "Andover", "state": "MA", "score": 2.35},
    {"id": "site_044", "name": "Banning Mobile Mechanic Service", "category": "Mobile mechanic", "city": "Banning", "state": "CA", "score": 2.32},
    {"id": "site_045", "name": "Edingburg Mobile Mechanics", "category": "Mobile mechanic", "city": "Edinburg", "state": "TX", "score": 2.30},
    {"id": "site_046", "name": "East Palo Alto Patio Covers", "category": "Patio covers", "city": "East Palo Alto", "state": "CA", "score": 2.25},
    {"id": "site_047", "name": "Edingburg Patio Covers", "category": "Patio covers", "city": "Edinburg", "state": "TX", "score": 2.20},
    {"id": "site_048", "name": "El Cerrito Personal Injury Law", "category": "Law", "city": "El Cerrito", "state": "CA", "score": 2.18},
    {"id": "site_049", "name": "Kingsville Injury Justice Advocates", "category": "Law", "city": "Kingsville", "state": "TX", "score": 2.15},
    {"id": "site_050", "name": "Orchard Park Towing Services", "category": "Towing", "city": "Orchard Park", "state": "NY", "score": 2.10},
    {"id": "site_051", "name": "West Warwick Towing Company", "category": "Towing", "city": "West Warwick", "state": "RI", "score": 2.05},
    {"id": "site_052", "name": "West Windsor Junk Removal", "category": "Junk Removal", "city": "West Windsor", "state": "NJ", "score": 2.00},
    {"id": "site_053", "name": "Allen Bee Hive Rescue Services", "category": "Bee rescue", "city": "Allen", "state": "TX", "score": 1.90},
]

# Enrich portfolio with benchmark data
def enrich_portfolio():
    for site in PORTFOLIO_DATA:
        benchmark = CATEGORY_BENCHMARKS.get(site["category"], {})
        site["monthly_potential"] = benchmark.get("monthly_potential", 500)
        site["avg_job_value"] = benchmark.get("avg_job_value", 1000)
        site["tier"] = "activate" if site["score"] >= 3.7 else ("watchlist" if site["score"] >= 3.2 else "sunset")
        site["decision"] = "KEEP & ACTIVATE" if site["score"] >= 3.7 else ("MONITOR 90 DAYS" if site["score"] >= 3.2 else "SUNSET")
        site["category_tier"] = benchmark.get("category_tier", 5)

enrich_portfolio()

# =============================================================================
# SCORING ENGINE CLASS
# =============================================================================

class ScoringEngine:
    def __init__(self):
        self.criteria = SCORING_CRITERIA
        self.benchmarks = CATEGORY_BENCHMARKS
        self.portfolio = PORTFOLIO_DATA
    
    def calculate_score(self, site_data: Dict) -> Dict:
        """Calculate comprehensive score for a site opportunity"""
        category = site_data.get("category", "")
        benchmark = self.benchmarks.get(category, {})
        
        # Calculate component scores
        scores = {}
        
        # Category vertical score (from tier)
        cat_tier = benchmark.get("category_tier", 5)
        scores["category_vertical_score"] = max(1, 5.5 - (cat_tier * 0.8))
        
        # Urgency and regulation from benchmarks
        scores["urgency_call_first"] = benchmark.get("urgency_score", 3)
        scores["regulation_compliance_risk"] = benchmark.get("regulation_risk", 3)
        scores["seasonality_profile"] = benchmark.get("seasonality", 3)
        
        # Lead value from job value
        avg_job = benchmark.get("avg_job_value", 1000)
        scores["lead_value_proxy"] = min(5, avg_job / 2000)
        
        # Use provided criteria scores or defaults
        for criterion in self.criteria:
            if criterion not in scores:
                scores[criterion] = site_data.get(criterion, 3)
        
        # Calculate weighted total
        total = 0
        total_weight = 0
        breakdown = {}
        
        for criterion, details in self.criteria.items():
            score = scores.get(criterion, 3)
            weight = details["weight"]
            contribution = score * weight / 100
            total += contribution
            total_weight += weight
            breakdown[criterion] = {
                "score": round(score, 2),
                "weight": weight,
                "contribution": round(contribution, 3)
            }
        
        final_score = round(total * (100 / total_weight), 2) if total_weight > 0 else 0
        
        # Determine tier and decision
        tier = "activate" if final_score >= 3.7 else ("watchlist" if final_score >= 3.2 else "sunset")
        decision = "KEEP & ACTIVATE" if final_score >= 3.7 else ("MONITOR 90 DAYS" if final_score >= 3.2 else "SUNSET")
        
        # Generate recommendations
        recommendations = self._generate_recommendations(category, final_score, tier, benchmark)
        
        return {
            "site": site_data,
            "score": final_score,
            "tier": tier,
            "decision": decision,
            "monthly_potential": benchmark.get("monthly_potential", 500),
            "avg_job_value": benchmark.get("avg_job_value", 1000),
            "confidence": self._calculate_confidence(scores),
            "criteria_breakdown": breakdown,
            "recommendations": recommendations
        }
    
    def _calculate_confidence(self, scores: Dict) -> float:
        """Calculate confidence based on score distribution"""
        values = list(scores.values())
        if not values:
            return 0.5
        avg = sum(values) / len(values)
        variance = sum((v - avg) ** 2 for v in values) / len(values)
        return round(max(0.3, min(0.95, 1 - (variance / 10))), 2)
    
    def _generate_recommendations(self, category: str, score: float, tier: str, benchmark: Dict) -> List[str]:
        """Generate actionable recommendations"""
        recs = []
        
        if tier == "activate":
            recs.append(f"Begin contractor outreach immediately for {category}")
            recs.append(f"Expected time to first renter: {benchmark.get('time_to_rank_months', 4)} months")
            recs.append(f"Target monthly rent: ${benchmark.get('monthly_potential', 1500)}")
        elif tier == "watchlist":
            recs.append("Monitor rankings and traffic for 90 days")
            recs.append("Run RevFlow competitive analysis to identify improvement opportunities")
            recs.append("Consider content optimization using R&R Canonical Framework")
        else:
            recs.append("SUNSET: Stop all investment in this site")
            recs.append(f"Category '{category}' has low success probability for R&R model")
            recs.append("Redirect resources to Tier 1 categories")
        
        return recs
    
    def get_portfolio_summary(self) -> Dict:
        """Get complete portfolio overview"""
        activate = [s for s in self.portfolio if s["tier"] == "activate"]
        watchlist = [s for s in self.portfolio if s["tier"] == "watchlist"]
        sunset = [s for s in self.portfolio if s["tier"] == "sunset"]
        
        return {
            "total_sites": len(self.portfolio),
            "tier_distribution": {
                "activate": len(activate),
                "watchlist": len(watchlist),
                "sunset": len(sunset)
            },
            "revenue_potential": {
                "activate_monthly": sum(s["monthly_potential"] for s in activate),
                "watchlist_monthly": sum(s["monthly_potential"] for s in watchlist),
                "sunset_monthly": sum(s["monthly_potential"] for s in sunset),
                "total_monthly": sum(s["monthly_potential"] for s in self.portfolio),
                "activate_annual": sum(s["monthly_potential"] for s in activate) * 12
            },
            "category_breakdown": self._analyze_categories(),
            "top_sites": sorted(self.portfolio, key=lambda x: x["score"], reverse=True)[:10],
            "bottom_sites": sorted(self.portfolio, key=lambda x: x["score"])[:10],
            "recommendations": self._generate_portfolio_recommendations()
        }
    
    def _analyze_categories(self) -> List[Dict]:
        """Analyze performance by category"""
        categories = {}
        for site in self.portfolio:
            cat = site["category"]
            if cat not in categories:
                categories[cat] = {"sites": [], "total_potential": 0}
            categories[cat]["sites"].append(site)
            categories[cat]["total_potential"] += site["monthly_potential"]
        
        result = []
        for cat, data in categories.items():
            avg_score = sum(s["score"] for s in data["sites"]) / len(data["sites"])
            benchmark = self.benchmarks.get(cat, {})
            result.append({
                "category": cat,
                "site_count": len(data["sites"]),
                "avg_score": round(avg_score, 2),
                "total_potential": data["total_potential"],
                "avg_job_value": benchmark.get("avg_job_value", 0),
                "category_tier": benchmark.get("category_tier", 5),
                "recommended_action": benchmark.get("recommended_action", "EVALUATE")
            })
        
        return sorted(result, key=lambda x: x["avg_score"], reverse=True)
    
    def _generate_portfolio_recommendations(self) -> List[Dict]:
        """Generate portfolio-level recommendations"""
        return [
            {"priority": 1, "action": "ACTIVATE", "description": "Begin contractor outreach for 19 Activate tier sites", "impact": "$28,500/mo potential"},
            {"priority": 2, "action": "SUNSET", "description": "Discontinue 19 low-performing sites", "impact": "Free up resources"},
            {"priority": 3, "action": "MONITOR", "description": "Track 15 Watchlist sites for 90 days", "impact": "Identify 5-8 promotion candidates"},
            {"priority": 4, "action": "ACQUIRE", "description": "Target new Concrete, Roofing, Water Damage sites", "impact": "5-10 high-potential additions"}
        ]

scoring_engine = ScoringEngine()

# =============================================================================
# MARKET DISCOVERY SERVICE (Niche Finder Pro Inspired)
# =============================================================================

class MarketDiscoveryService:
    def __init__(self):
        self.markets = MARKET_DATABASE
        self.benchmarks = CATEGORY_BENCHMARKS
    
    def search_opportunities(self, request: MarketSearchRequest) -> List[Dict]:
        """
        Search for new market opportunities (similar to Niche Finder Pro Turbo Search)
        """
        results = []
        
        categories = request.categories or [
            cat for cat, data in self.benchmarks.items() 
            if data.get("category_tier", 5) <= 2
        ]
        states = request.states or list(self.markets.keys())
        
        competition_levels = {"very_low": 1, "low": 2, "moderate": 3, "high": 4, "very_high": 5}
        max_comp = competition_levels.get(request.max_competition, 3)
        
        for state, state_data in self.markets.items():
            if state not in states:
                continue
            
            for city_data in state_data["cities"]:
                pop = city_data["population"]
                if pop < request.min_population or pop > request.max_population:
                    continue
                
                city_comp = competition_levels.get(city_data["competition"], 3)
                if city_comp > max_comp:
                    continue
                
                for category in categories:
                    opp = self._evaluate_opportunity(category, city_data, state, state_data)
                    if opp["score"] >= request.min_score:
                        results.append(opp)
        
        return sorted(results, key=lambda x: x["score"], reverse=True)[:50]
    
    def _evaluate_opportunity(self, category: str, city_data: Dict, state: str, state_data: Dict) -> Dict:
        """Evaluate a specific market opportunity"""
        benchmark = self.benchmarks.get(category, {})
        
        # Category score (Tier 1 = 5, Tier 5 = 1)
        cat_tier = benchmark.get("category_tier", 5)
        category_score = max(1, 5.5 - (cat_tier * 0.8))
        
        # Competition score (inverse)
        comp_map = {"very_low": 5, "low": 4, "moderate": 3, "high": 2, "very_high": 1}
        competition_score = comp_map.get(city_data["competition"], 3)
        
        # Growth score
        growth_score = min(5, city_data["growth"] * 50 + 2.5)
        
        # Population sweet spot (50K-150K ideal)
        pop = city_data["population"]
        if 50000 <= pop <= 150000:
            pop_score = 5
        elif 30000 <= pop < 50000 or 150000 < pop <= 200000:
            pop_score = 4
        elif 20000 <= pop < 30000 or 200000 < pop <= 250000:
            pop_score = 3
        else:
            pop_score = 2
        
        # Housing age (15-30 years ideal for maintenance needs)
        housing_age = city_data.get("housing_age", 20)
        if 15 <= housing_age <= 30:
            housing_score = 5
        elif 10 <= housing_age < 15 or 30 < housing_age <= 40:
            housing_score = 4
        else:
            housing_score = 3
        
        # Sun Belt bonus
        sun_belt_bonus = 0.25 if state_data.get("sun_belt", False) else 0
        
        # Calculate weighted score
        score = (
            category_score * 0.30 +
            competition_score * 0.25 +
            growth_score * 0.15 +
            pop_score * 0.15 +
            housing_score * 0.15 +
            sun_belt_bonus
        )
        score = round(score, 2)
        
        # Determine recommendation
        if score >= 3.8:
            recommendation = "ACQUIRE"
            tier = "high_opportunity"
        elif score >= 3.5:
            recommendation = "EVALUATE"
            tier = "moderate_opportunity"
        else:
            recommendation = "SKIP"
            tier = "low_opportunity"
        
        return {
            "category": category,
            "city": city_data["city"],
            "state": state,
            "score": score,
            "tier": tier,
            "recommendation": recommendation,
            "population": pop,
            "growth_rate": city_data["growth"],
            "competition_level": city_data["competition"],
            "housing_age": housing_age,
            "monthly_potential": benchmark.get("monthly_potential", 500),
            "avg_job_value": benchmark.get("avg_job_value", 1000),
            "time_to_rank": benchmark.get("time_to_rank_months", 4),
            "scoring_breakdown": {
                "category_score": round(category_score, 2),
                "competition_score": round(competition_score, 2),
                "growth_score": round(growth_score, 2),
                "population_score": round(pop_score, 2),
                "housing_score": round(housing_score, 2),
                "sun_belt_bonus": round(sun_belt_bonus, 2)
            },
            "next_steps": self._get_next_steps(recommendation, category)
        }
    
    def _get_next_steps(self, recommendation: str, category: str) -> List[str]:
        """Generate next steps based on recommendation"""
        if recommendation == "ACQUIRE":
            return [
                f"Run R&R competitive analysis for {category} in this market",
                "Check Local Pack: review counts, ratings of top 3",
                "Validate renter willingness (call 3-5 local contractors)",
                "Begin domain acquisition if validated",
                "Use R&R Automation to generate site content"
            ]
        elif recommendation == "EVALUATE":
            return [
                "Conduct deeper market research",
                "Analyze SERP for rankability signals",
                "Compare against higher-scoring opportunities",
                "Monitor for 30 days before deciding"
            ]
        else:
            return [
                "Skip - focus on higher-scoring opportunities",
                "Revisit only if top picks don't pan out"
            ]
    
    def get_category_recommendations(self) -> Dict:
        """Get recommended categories with rationale"""
        tier_1 = [c for c, d in self.benchmarks.items() if d.get("category_tier") == 1]
        tier_2 = [c for c, d in self.benchmarks.items() if d.get("category_tier") == 2]
        avoid = [c for c, d in self.benchmarks.items() if d.get("category_tier") >= 4]
        
        return {
            "tier_1_expand": [
                {"category": c, "reason": self.benchmarks[c].get("notes", ""), 
                 "monthly_potential": self.benchmarks[c].get("monthly_potential")}
                for c in tier_1
            ],
            "tier_2_maintain": [
                {"category": c, "reason": self.benchmarks[c].get("notes", ""),
                 "monthly_potential": self.benchmarks[c].get("monthly_potential")}
                for c in tier_2
            ],
            "avoid": [
                {"category": c, "reason": self.benchmarks[c].get("notes", ""),
                 "monthly_potential": self.benchmarks[c].get("monthly_potential")}
                for c in avoid
            ]
        }
    
    def get_hotspots(self, category: str = None, limit: int = 20) -> List[Dict]:
        """Get top market hotspots"""
        all_opps = []
        
        categories = [category] if category else [
            c for c, d in self.benchmarks.items() if d.get("category_tier", 5) <= 2
        ]
        
        for state, state_data in self.markets.items():
            for city_data in state_data["cities"]:
                for cat in categories:
                    opp = self._evaluate_opportunity(cat, city_data, state, state_data)
                    if opp["score"] >= 3.5:
                        all_opps.append(opp)
        
        return sorted(all_opps, key=lambda x: x["score"], reverse=True)[:limit]

market_discovery = MarketDiscoveryService()

# =============================================================================
# WHAT-IF ANALYZER SERVICE
# =============================================================================

class WhatIfAnalyzer:
    def __init__(self):
        self.scoring_engine = scoring_engine
    
    def analyze_scenario(self, scenario: WhatIfScenario) -> Dict:
        """Run what-if scenario analysis"""
        if scenario.scenario_type == "threshold_change":
            return self._analyze_threshold_change(scenario.parameters)
        elif scenario.scenario_type == "category_focus":
            return self._analyze_category_focus(scenario.parameters)
        elif scenario.scenario_type == "weight_change":
            return self._analyze_weight_change(scenario.parameters)
        else:
            raise HTTPException(status_code=400, detail=f"Unknown scenario type: {scenario.scenario_type}")
    
    def _analyze_threshold_change(self, params: Dict) -> Dict:
        """Analyze impact of changing tier thresholds"""
        activate_threshold = params.get("activate_threshold", 3.7)
        watchlist_threshold = params.get("watchlist_threshold", 3.2)
        
        portfolio = self.scoring_engine.portfolio
        original = {"activate": 0, "watchlist": 0, "sunset": 0}
        new = {"activate": 0, "watchlist": 0, "sunset": 0}
        changes = []
        
        for site in portfolio:
            # Original tier
            orig_tier = site["tier"]
            original[orig_tier] += 1
            
            # New tier
            score = site["score"]
            new_tier = "activate" if score >= activate_threshold else ("watchlist" if score >= watchlist_threshold else "sunset")
            new[new_tier] += 1
            
            if orig_tier != new_tier:
                changes.append({
                    "site": site["name"],
                    "score": score,
                    "original_tier": orig_tier,
                    "new_tier": new_tier
                })
        
        return {
            "scenario_type": "threshold_change",
            "parameters": {"activate_threshold": activate_threshold, "watchlist_threshold": watchlist_threshold},
            "original_distribution": original,
            "new_distribution": new,
            "tier_changes": changes,
            "impact_summary": {
                "sites_promoted": len([c for c in changes if c["new_tier"] == "activate" and c["original_tier"] != "activate"]),
                "sites_demoted": len([c for c in changes if c["new_tier"] == "sunset" and c["original_tier"] != "sunset"])
            }
        }
    
    def _analyze_category_focus(self, params: Dict) -> Dict:
        """Analyze portfolio focused on specific categories"""
        focus_categories = params.get("categories", [])
        
        portfolio = self.scoring_engine.portfolio
        focused = [s for s in portfolio if s["category"] in focus_categories]
        excluded = [s for s in portfolio if s["category"] not in focus_categories]
        
        focused_potential = sum(s["monthly_potential"] for s in focused)
        total_potential = sum(s["monthly_potential"] for s in portfolio)
        
        return {
            "scenario_type": "category_focus",
            "focus_categories": focus_categories,
            "impact_summary": {
                "focused_sites": len(focused),
                "excluded_sites": len(excluded),
                "focused_potential": focused_potential,
                "excluded_potential": sum(s["monthly_potential"] for s in excluded),
                "retention_percentage": round(focused_potential / total_potential * 100, 1) if total_potential > 0 else 0
            },
            "focused_tier_distribution": {
                "activate": len([s for s in focused if s["tier"] == "activate"]),
                "watchlist": len([s for s in focused if s["tier"] == "watchlist"]),
                "sunset": len([s for s in focused if s["tier"] == "sunset"])
            },
            "top_focused_sites": sorted(focused, key=lambda x: x["score"], reverse=True)[:10],
            "recommendation": self._get_focus_recommendation(focused, excluded)
        }
    
    def _analyze_weight_change(self, params: Dict) -> Dict:
        """Analyze impact of changing scoring weights"""
        weight_changes = params.get("weight_changes", {})
        
        # This would recalculate all scores with new weights
        # For now, return a summary of the proposed changes
        return {
            "scenario_type": "weight_change",
            "proposed_changes": weight_changes,
            "current_weights": {k: v["weight"] for k, v in SCORING_CRITERIA.items()},
            "note": "Full recalculation requires re-running scoring engine with new weights"
        }
    
    def _get_focus_recommendation(self, focused: List, excluded: List) -> str:
        """Generate recommendation for category focus scenario"""
        if not focused:
            return "No sites match the selected categories"
        
        focused_avg = sum(s["score"] for s in focused) / len(focused)
        
        if focused_avg >= 3.5 and len(focused) >= 10:
            return f"RECOMMENDED: Focus captures high-performers (avg score {focused_avg:.2f})"
        elif focused_avg >= 3.2:
            return f"MODERATE: Avg score {focused_avg:.2f}. Consider adding more Tier 1 categories."
        else:
            return f"NOT RECOMMENDED: Avg score {focused_avg:.2f} below optimal threshold."

whatif_analyzer = WhatIfAnalyzer()

# =============================================================================
# API ENDPOINTS
# =============================================================================

# Portfolio Management
@app.get("/api/portfolio")
async def get_portfolio_summary():
    """Get complete portfolio overview with tier distribution and recommendations"""
    return scoring_engine.get_portfolio_summary()

@app.get("/api/sites")
async def get_sites(
    tier: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    sort_by: str = Query("score"),
    order: str = Query("desc")
):
    """Get all sites with filtering and sorting"""
    result = scoring_engine.portfolio.copy()
    
    if tier:
        result = [s for s in result if s["tier"] == tier.lower()]
    if category:
        result = [s for s in result if s["category"].lower() == category.lower()]
    if state:
        result = [s for s in result if s["state"].upper() == state.upper()]
    
    reverse = order.lower() == "desc"
    if sort_by == "score":
        result = sorted(result, key=lambda x: x["score"], reverse=reverse)
    elif sort_by == "potential":
        result = sorted(result, key=lambda x: x["monthly_potential"], reverse=reverse)
    
    return result

@app.get("/api/sites/{site_id}")
async def get_site(site_id: str):
    """Get detailed information for a specific site"""
    site = next((s for s in scoring_engine.portfolio if s["id"] == site_id), None)
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    return site

# Scoring
@app.post("/api/score")
async def score_opportunity(site: SiteCreate):
    """Score a potential site opportunity"""
    return scoring_engine.calculate_score(site.model_dump())

@app.get("/api/scoring/criteria")
async def get_scoring_criteria():
    """Get all scoring criteria with weights and descriptions"""
    return SCORING_CRITERIA

# Market Discovery (Niche Finder Pro style)
@app.post("/api/discover/search")
async def discover_markets(request: MarketSearchRequest):
    """
    Turbo Search: Find new market opportunities based on criteria
    Similar to Niche Finder Pro rapid search functionality
    """
    return market_discovery.search_opportunities(request)

@app.get("/api/discover/hotspots")
async def get_hotspots(
    category: Optional[str] = Query(None),
    limit: int = Query(20)
):
    """Get top market hotspots"""
    return market_discovery.get_hotspots(category=category, limit=limit)

@app.get("/api/discover/categories")
async def get_category_recommendations():
    """Get recommended categories based on R&R success factors"""
    return market_discovery.get_category_recommendations()

@app.get("/api/discover/evaluate")
async def evaluate_single_opportunity(
    category: str = Query(...),
    city: str = Query(...),
    state: str = Query(...)
):
    """Evaluate a specific market opportunity"""
    state_data = MARKET_DATABASE.get(state, {"sun_belt": False, "cities": []})
    city_data = next((c for c in state_data.get("cities", []) if c["city"].lower() == city.lower()), None)
    
    if not city_data:
        # Create estimate for unknown city
        city_data = {"city": city, "population": 75000, "growth": 0.03, "competition": "moderate", "housing_age": 20}
    
    return market_discovery._evaluate_opportunity(category, city_data, state, state_data)

# What-If Analysis
@app.post("/api/whatif/analyze")
async def run_whatif_analysis(scenario: WhatIfScenario):
    """Run what-if scenario analysis"""
    return whatif_analyzer.analyze_scenario(scenario)

@app.post("/api/whatif/threshold")
async def analyze_threshold_change(
    activate_threshold: float = Query(3.7),
    watchlist_threshold: float = Query(3.2)
):
    """Quick threshold analysis endpoint"""
    scenario = WhatIfScenario(
        scenario_type="threshold_change",
        parameters={"activate_threshold": activate_threshold, "watchlist_threshold": watchlist_threshold}
    )
    return whatif_analyzer.analyze_scenario(scenario)

@app.post("/api/whatif/category-focus")
async def analyze_category_focus(categories: List[str]):
    """Quick category focus analysis endpoint"""
    scenario = WhatIfScenario(
        scenario_type="category_focus",
        parameters={"categories": categories}
    )
    return whatif_analyzer.analyze_scenario(scenario)

# Category Benchmarks
@app.get("/api/benchmarks")
async def get_all_benchmarks():
    """Get all category benchmarks"""
    return [{"category": k, **v} for k, v in CATEGORY_BENCHMARKS.items()]

@app.get("/api/benchmarks/{category}")
async def get_category_benchmark(category: str):
    """Get benchmark for specific category"""
    if category not in CATEGORY_BENCHMARKS:
        raise HTTPException(status_code=404, detail="Category not found")
    return {"category": category, **CATEGORY_BENCHMARKS[category]}

# Integration with R&R/RevFlow
@app.post("/api/integrate/revflow/competitive")
async def trigger_competitive_analysis(request: CompetitiveAnalysisRequest):
    """
    Trigger RevFlow competitive analysis for a market.
    Integrates with RevFlow Module A (Visibility & Discoverability)
    """
    return {
        "status": "analysis_queued",
        "request": request.model_dump(),
        "integration_endpoint": "/api/revflow/assess",
        "note": "Connect to RevFlow API for full competitive analysis"
    }

@app.post("/api/integrate/rr/generate")
async def trigger_site_generation(site_data: SiteCreate):
    """
    Trigger R&R Automation site generation.
    Integrates with R&R Canonical Framework V3.0
    """
    return {
        "status": "generation_queued",
        "site": site_data.model_dump(),
        "integration_endpoint": "/api/rr/generate",
        "framework_version": "V3.0",
        "note": "Connect to R&R Automation for content generation"
    }

# Reports
@app.get("/api/reports/action-plan")
async def get_action_plan(days: int = Query(90)):
    """Generate prioritized 90-day action plan"""
    return {
        "duration_days": days,
        "phases": [
            {
                "phase": 1,
                "weeks": "1-2",
                "actions": [
                    {"type": "SUNSET", "task": "Discontinue 19 low-performing sites", "sites": 19},
                    {"type": "ACTIVATE", "task": "Begin Concrete contractor outreach", "sites": 7}
                ]
            },
            {
                "phase": 2,
                "weeks": "3-4",
                "actions": [
                    {"type": "ACTIVATE", "task": "Launch Roofing campaigns", "sites": 2},
                    {"type": "ACTIVATE", "task": "Launch Water Damage campaigns", "sites": 2}
                ]
            },
            {
                "phase": 3,
                "weeks": "5-8",
                "actions": [
                    {"type": "ACTIVATE", "task": "Complete Activate tier rollout", "sites": 8},
                    {"type": "MONITOR", "task": "Set up Watchlist tracking", "sites": 15}
                ]
            },
            {
                "phase": 4,
                "weeks": "9-12",
                "actions": [
                    {"type": "EVALUATE", "task": "Reassess Watchlist sites", "sites": 15},
                    {"type": "ACQUIRE", "task": "Identify new opportunities", "sites": "5-10"}
                ]
            }
        ]
    }

@app.get("/api/reports/revenue-projection")
async def get_revenue_projection(
    months: int = Query(12),
    success_rate: float = Query(0.6)
):
    """Project revenue based on portfolio"""
    summary = scoring_engine.get_portfolio_summary()
    activate_potential = summary["revenue_potential"]["activate_monthly"]
    watchlist_potential = summary["revenue_potential"]["watchlist_monthly"]
    
    return {
        "projection_months": months,
        "success_rate": success_rate,
        "scenarios": {
            "conservative": {
                "monthly": int(activate_potential * success_rate * 0.7),
                "annual": int(activate_potential * success_rate * 0.7 * 12),
                "assumptions": "40% success rate, Activate tier only"
            },
            "moderate": {
                "monthly": int(activate_potential * success_rate),
                "annual": int(activate_potential * success_rate * 12),
                "assumptions": "60% success rate, Activate tier only"
            },
            "optimistic": {
                "monthly": int((activate_potential + watchlist_potential * 0.3) * 0.8),
                "annual": int((activate_potential + watchlist_potential * 0.3) * 0.8 * 12),
                "assumptions": "80% Activate + 30% Watchlist promotion"
            }
        }
    }

# Health Check
@app.get("/health")
async def health_check():
    """API health check"""
    return {
        "status": "healthy",
        "service": "rankrent-decision-tool",
        "version": "1.0.0",
        "portfolio_size": len(PORTFOLIO_DATA),
        "categories": len(CATEGORY_BENCHMARKS),
        "markets": sum(len(s["cities"]) for s in MARKET_DATABASE.values()),
        "timestamp": datetime.utcnow().isoformat()
    }

# =============================================================================
# RUN APPLICATION
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
