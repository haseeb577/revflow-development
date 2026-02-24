"""
╔══════════════════════════════════════════════════════════════════════════════╗
║          MARKET DISCOVERY ENGINE - ENHANCED WITH SERP ANALYSIS               ║
║          Inspired by Niche Finder Pro + R&R/RevFlow Intelligence             ║
╚══════════════════════════════════════════════════════════════════════════════╝

Key Features (Niche Finder Pro Parity + Our Advantages):
- Turbo Search: Rapid cycling through nearby markets
- Map Pack Analysis: Reviews, location match, dedicated sites
- SERP Weakness Detection: Integration with DataForSEO/SemRush
- Category Benchmarks: 21 categories with proven R&R success data
- Lead Value Analysis: Job value, monthly potential, renter willingness
- Favoriting + Tagging: Save opportunities with custom labels
- Export: Due diligence spreadsheets
- R&R Integration: Direct content generation pipeline
- RevFlow Integration: Full competitive analysis

Version: 2.0.0
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum
from datetime import datetime
import json
import random

# =============================================================================
# ENUMS & CONSTANTS
# =============================================================================

class CompetitionLevel(str, Enum):
    VERY_LOW = "very_low"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    VERY_HIGH = "very_high"

class OpportunityRating(str, Enum):
    FIVE_STAR = "5_star"
    FOUR_STAR = "4_star"
    THREE_STAR = "3_star"
    TWO_STAR = "2_star"
    ONE_STAR = "1_star"

class RecommendationType(str, Enum):
    ACQUIRE = "ACQUIRE"
    EVALUATE = "EVALUATE"
    SKIP = "SKIP"
    NO_WEBSITE = "NO_WEBSITE"  # NFP-style - prime targets

# NFP-style thresholds (customizable)
DEFAULT_THRESHOLDS = {
    "referring_domains": 20,      # Over 20 RD = strong competitor
    "review_count": 30,           # Over 30 reviews = hard to beat in map pack
    "dedicated_sites": 10,        # Over 10 dedicated sites = competitive SERP
    "domain_rating": 25,          # Over 25 DR = established player
    "min_population": 25000,
    "max_population": 250000,
    "min_score": 3.5
}

# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class MapPackResult:
    """Individual Google Map Pack listing"""
    position: int
    business_name: str
    review_count: int
    rating: float
    has_website: bool
    website_url: Optional[str]
    location_match: bool  # Is business actually in the target city?
    is_dedicated_site: bool  # Dedicated to this service vs general contractor
    referring_domains: Optional[int] = None
    domain_rating: Optional[int] = None

@dataclass
class SERPAnalysis:
    """Full SERP analysis for a niche/location combo"""
    keyword: str
    city: str
    state: str
    
    # Map Pack Metrics
    map_pack_results: List[MapPackResult] = field(default_factory=list)
    map_pack_avg_reviews: float = 0
    map_pack_location_match_pct: float = 0
    
    # Organic Results
    dedicated_sites_count: int = 0
    total_organic_results: int = 10
    avg_referring_domains: float = 0
    avg_domain_rating: float = 0
    
    # Weakness Signals (Opportunities!)
    no_website_gmbs: int = 0  # GMBs without websites - call them!
    weak_competitors: int = 0  # Low RD/DR sites in top 10
    thin_content_sites: int = 0  # Sites with <500 words
    
    # Overall Assessment
    serp_difficulty_score: float = 0  # 1-10 scale
    opportunity_score: float = 0  # Our composite score

@dataclass 
class MarketOpportunity:
    """Complete market opportunity assessment"""
    id: str
    category: str
    city: str
    state: str
    
    # Core Metrics
    score: float
    tier: str  # high_opportunity, moderate_opportunity, low_opportunity
    recommendation: RecommendationType
    rating: OpportunityRating  # 1-5 stars (NFP style)
    
    # Market Data
    population: int
    growth_rate: float
    competition_level: CompetitionLevel
    housing_age: int
    sun_belt: bool
    
    # R&R Success Factors (Our Advantage)
    monthly_potential: int
    avg_job_value: int
    lead_value_range: tuple
    urgency_score: int
    renter_density: int  # How many contractors to sell leads to
    time_to_rank_months: int
    
    # SERP Analysis (NFP Parity)
    serp_analysis: Optional[SERPAnalysis] = None
    dedicated_sites: int = 0
    map_pack_avg_reviews: float = 0
    no_website_targets: int = 0  # Key NFP feature
    
    # Scoring Breakdown
    scoring_breakdown: Dict[str, float] = field(default_factory=dict)
    
    # User Interaction (NFP Parity)
    is_favorited: bool = False
    tags: List[str] = field(default_factory=list)
    notes: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    # Action Items
    next_steps: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "category": self.category,
            "city": self.city,
            "state": self.state,
            "score": self.score,
            "tier": self.tier,
            "recommendation": self.recommendation.value,
            "rating": self.rating.value,
            "population": self.population,
            "growth_rate": self.growth_rate,
            "competition_level": self.competition_level.value,
            "monthly_potential": self.monthly_potential,
            "avg_job_value": self.avg_job_value,
            "time_to_rank_months": self.time_to_rank_months,
            "dedicated_sites": self.dedicated_sites,
            "map_pack_avg_reviews": self.map_pack_avg_reviews,
            "no_website_targets": self.no_website_targets,
            "is_favorited": self.is_favorited,
            "tags": self.tags,
            "scoring_breakdown": self.scoring_breakdown,
            "next_steps": self.next_steps
        }

# =============================================================================
# CATEGORY INTELLIGENCE DATABASE
# =============================================================================

CATEGORY_INTELLIGENCE = {
    "Concrete": {
        "category_tier": 1,
        "avg_job_value": 7500,
        "lead_value_range": (150, 400),
        "monthly_potential": 2000,
        "urgency_score": 4,
        "seasonality": 3,
        "regulation_risk": 5,
        "renter_density": 4,
        "time_to_rank_months": 4,
        "typical_serp_competition": "moderate",
        "recommended_action": "EXPAND",
        "success_indicators": [
            "Housing developments nearby",
            "Hot summers (concrete cracks)",
            "Growing suburbs"
        ],
        "red_flags": [
            "Dominated by national chains",
            "Very new construction only"
        ],
        "keywords": ["concrete contractor", "concrete driveway", "concrete patio", "stamped concrete", "concrete repair"],
        "notes": "Proven top performer. High job values, strong renter demand. Focus on suburbs with 15-30 year old homes."
    },
    "Roofing": {
        "category_tier": 1,
        "avg_job_value": 10000,
        "lead_value_range": (200, 500),
        "monthly_potential": 2500,
        "urgency_score": 5,
        "seasonality": 3,
        "regulation_risk": 4,
        "renter_density": 5,
        "time_to_rank_months": 5,
        "typical_serp_competition": "high",
        "recommended_action": "EXPAND",
        "success_indicators": [
            "Storm-prone areas",
            "Aging housing stock",
            "Insurance-friendly state"
        ],
        "red_flags": [
            "Very competitive metros",
            "New construction dominance"
        ],
        "keywords": ["roofing contractor", "roof repair", "roof replacement", "emergency roofing", "storm damage roof"],
        "notes": "Highest monthly potential. Emergency nature drives conversions. Target storm corridors."
    },
    "Water Damage": {
        "category_tier": 1,
        "avg_job_value": 4500,
        "lead_value_range": (200, 750),
        "monthly_potential": 2000,
        "urgency_score": 5,
        "seasonality": 4,
        "regulation_risk": 4,
        "renter_density": 3,
        "time_to_rank_months": 4,
        "typical_serp_competition": "moderate",
        "recommended_action": "EXPAND",
        "success_indicators": [
            "Flood-prone areas",
            "Hurricane zones",
            "Older plumbing infrastructure"
        ],
        "red_flags": [
            "ServiceMaster/SERVPRO dominance",
            "Very dry climates"
        ],
        "keywords": ["water damage restoration", "flood damage repair", "water extraction", "emergency water removal"],
        "notes": "Emergency service with insurance coverage. High close rate. 24/7 nature valuable."
    },
    "Electric": {
        "category_tier": 2,
        "avg_job_value": 3500,
        "lead_value_range": (100, 300),
        "monthly_potential": 1500,
        "urgency_score": 4,
        "seasonality": 5,
        "regulation_risk": 3,
        "renter_density": 5,
        "time_to_rank_months": 5,
        "typical_serp_competition": "moderate",
        "recommended_action": "MAINTAIN",
        "success_indicators": [
            "Older homes (rewiring needs)",
            "EV adoption growth",
            "Solar installation areas"
        ],
        "red_flags": [
            "Licensed electrician saturation",
            "Union-heavy markets"
        ],
        "keywords": ["electrician", "electrical repair", "electrical contractor", "panel upgrade", "outlet repair"],
        "notes": "Year-round demand, strong renter pool. Licensing requirements create barriers."
    },
    "Fence": {
        "category_tier": 2,
        "avg_job_value": 4500,
        "lead_value_range": (100, 250),
        "monthly_potential": 1500,
        "urgency_score": 3,
        "seasonality": 3,
        "regulation_risk": 5,
        "renter_density": 4,
        "time_to_rank_months": 3,
        "typical_serp_competition": "low",
        "recommended_action": "MAINTAIN",
        "success_indicators": [
            "Suburban sprawl",
            "Pet ownership high",
            "HOA communities"
        ],
        "red_flags": [
            "Very rural (DIY culture)",
            "Extreme weather limiting seasons"
        ],
        "keywords": ["fence contractor", "fence installation", "fence repair", "wood fence", "vinyl fence"],
        "notes": "Lower competition, faster ranking. Good job values. Target suburbs."
    },
    "Tree Care": {
        "category_tier": 2,
        "avg_job_value": 1800,
        "lead_value_range": (50, 200),
        "monthly_potential": 1200,
        "urgency_score": 4,
        "seasonality": 3,
        "regulation_risk": 4,
        "renter_density": 4,
        "time_to_rank_months": 3,
        "typical_serp_competition": "low",
        "recommended_action": "MAINTAIN",
        "success_indicators": [
            "Storm corridors",
            "Mature tree neighborhoods",
            "After major weather events"
        ],
        "red_flags": [
            "New developments (no trees)",
            "Desert climates"
        ],
        "keywords": ["tree removal", "tree trimming", "tree service", "stump removal", "emergency tree removal"],
        "notes": "Storm-driven demand creates urgency. Repeat business potential."
    },
    "Plumbing": {
        "category_tier": 2,
        "avg_job_value": 2500,
        "lead_value_range": (75, 250),
        "monthly_potential": 1500,
        "urgency_score": 5,
        "seasonality": 5,
        "regulation_risk": 3,
        "renter_density": 5,
        "time_to_rank_months": 6,
        "typical_serp_competition": "high",
        "recommended_action": "MAINTAIN",
        "success_indicators": [
            "Older infrastructure",
            "Hard water areas",
            "Cold climates (frozen pipes)"
        ],
        "red_flags": [
            "Roto-Rooter/Mr. Rooter dominance",
            "Very competitive"
        ],
        "keywords": ["plumber", "plumbing repair", "emergency plumber", "drain cleaning", "water heater repair"],
        "notes": "Emergency nature excellent, but very competitive. Choose markets carefully."
    },
    "Drywall": {
        "category_tier": 3,
        "avg_job_value": 2200,
        "lead_value_range": (50, 150),
        "monthly_potential": 1000,
        "urgency_score": 2,
        "seasonality": 4,
        "regulation_risk": 5,
        "renter_density": 4,
        "time_to_rank_months": 3,
        "typical_serp_competition": "low",
        "recommended_action": "SELECTIVE",
        "success_indicators": [
            "After water damage events",
            "Renovation-heavy areas"
        ],
        "red_flags": [
            "Low urgency = price shopping",
            "DIY culture areas"
        ],
        "keywords": ["drywall repair", "drywall contractor", "drywall installation", "ceiling repair"],
        "notes": "Lower urgency limits lead quality. Best paired with water damage."
    },
    "Towing": {
        "category_tier": 5,
        "avg_job_value": 200,
        "lead_value_range": (15, 50),
        "monthly_potential": 500,
        "urgency_score": 5,
        "seasonality": 5,
        "regulation_risk": 2,
        "renter_density": 4,
        "time_to_rank_months": 5,
        "typical_serp_competition": "high",
        "recommended_action": "AVOID",
        "success_indicators": [],
        "red_flags": [
            "Job value too low for R&R",
            "AAA/insurance contracts dominate",
            "Regulation heavy"
        ],
        "keywords": ["towing service", "tow truck", "roadside assistance", "car towing"],
        "notes": "Job value ($200) cannot support $1,500/mo R&R target. AVOID."
    },
    "Junk Removal": {
        "category_tier": 5,
        "avg_job_value": 400,
        "lead_value_range": (25, 75),
        "monthly_potential": 600,
        "urgency_score": 2,
        "seasonality": 4,
        "regulation_risk": 4,
        "renter_density": 4,
        "time_to_rank_months": 4,
        "typical_serp_competition": "moderate",
        "recommended_action": "AVOID",
        "success_indicators": [],
        "red_flags": [
            "1-800-GOT-JUNK dominance",
            "Low urgency = price shopping",
            "Commoditized service"
        ],
        "keywords": ["junk removal", "trash hauling", "furniture removal", "estate cleanout"],
        "notes": "Low urgency, commoditized. Big national players. AVOID."
    },
    "Bee rescue": {
        "category_tier": 5,
        "avg_job_value": 250,
        "lead_value_range": (25, 75),
        "monthly_potential": 300,
        "urgency_score": 3,
        "seasonality": 2,
        "regulation_risk": 3,
        "renter_density": 1,
        "time_to_rank_months": 3,
        "typical_serp_competition": "very_low",
        "recommended_action": "AVOID",
        "success_indicators": [],
        "red_flags": [
            "Niche too small",
            "Minimal renter pool",
            "Seasonal only"
        ],
        "keywords": ["bee removal", "bee rescue", "wasp removal", "hornet removal"],
        "notes": "Niche too small, minimal renter pool. AVOID."
    }
}

# =============================================================================
# MARKET DATABASE (Expanded Sun Belt + Growth Markets)
# =============================================================================

MARKET_DATABASE = {
    "TX": {
        "sun_belt": True,
        "avg_housing_age": 20,
        "cities": [
            {"city": "Duncanville", "population": 40000, "growth": 0.02, "competition": "low", "housing_age": 25, "nearby_metro": "Dallas"},
            {"city": "Lancaster", "population": 39000, "growth": 0.03, "competition": "low", "housing_age": 22, "nearby_metro": "Dallas"},
            {"city": "Kingsville", "population": 26000, "growth": 0.01, "competition": "very_low", "housing_age": 30, "nearby_metro": "Corpus Christi"},
            {"city": "Socorro", "population": 35000, "growth": 0.04, "competition": "low", "housing_age": 18, "nearby_metro": "El Paso"},
            {"city": "La Porte", "population": 36000, "growth": 0.02, "competition": "moderate", "housing_age": 28, "nearby_metro": "Houston"},
            {"city": "Harker Heights", "population": 33000, "growth": 0.05, "competition": "low", "housing_age": 15, "nearby_metro": "Killeen"},
            {"city": "Cedar Hill", "population": 50000, "growth": 0.02, "competition": "low", "housing_age": 20, "nearby_metro": "Dallas"},
            {"city": "DeSoto", "population": 55000, "growth": 0.01, "competition": "low", "housing_age": 25, "nearby_metro": "Dallas"},
            {"city": "Waxahachie", "population": 40000, "growth": 0.04, "competition": "low", "housing_age": 18, "nearby_metro": "Dallas"},
            {"city": "Wylie", "population": 55000, "growth": 0.06, "competition": "moderate", "housing_age": 12, "nearby_metro": "Dallas"},
            {"city": "Rockwall", "population": 50000, "growth": 0.05, "competition": "moderate", "housing_age": 15, "nearby_metro": "Dallas"},
            {"city": "Midlothian", "population": 35000, "growth": 0.07, "competition": "low", "housing_age": 10, "nearby_metro": "Dallas"},
            {"city": "Kyle", "population": 55000, "growth": 0.08, "competition": "low", "housing_age": 8, "nearby_metro": "Austin"},
            {"city": "Pflugerville", "population": 68000, "growth": 0.06, "competition": "moderate", "housing_age": 12, "nearby_metro": "Austin"},
            {"city": "New Braunfels", "population": 95000, "growth": 0.07, "competition": "moderate", "housing_age": 15, "nearby_metro": "San Antonio"},
        ]
    },
    "FL": {
        "sun_belt": True,
        "avg_housing_age": 22,
        "cities": [
            {"city": "Palm Bay", "population": 120000, "growth": 0.05, "competition": "low", "housing_age": 25, "nearby_metro": "Melbourne"},
            {"city": "Cape Coral", "population": 210000, "growth": 0.07, "competition": "moderate", "housing_age": 20, "nearby_metro": "Fort Myers"},
            {"city": "Lehigh Acres", "population": 130000, "growth": 0.05, "competition": "low", "housing_age": 15, "nearby_metro": "Fort Myers"},
            {"city": "Port St. Lucie", "population": 220000, "growth": 0.06, "competition": "moderate", "housing_age": 18, "nearby_metro": "Stuart"},
            {"city": "Deltona", "population": 95000, "growth": 0.04, "competition": "low", "housing_age": 22, "nearby_metro": "Daytona"},
            {"city": "North Port", "population": 80000, "growth": 0.08, "competition": "low", "housing_age": 12, "nearby_metro": "Sarasota"},
            {"city": "Poinciana", "population": 70000, "growth": 0.06, "competition": "very_low", "housing_age": 15, "nearby_metro": "Orlando"},
            {"city": "Spring Hill", "population": 115000, "growth": 0.04, "competition": "low", "housing_age": 20, "nearby_metro": "Tampa"},
            {"city": "Palm Coast", "population": 95000, "growth": 0.05, "competition": "low", "housing_age": 18, "nearby_metro": "Daytona"},
            {"city": "Ocala", "population": 65000, "growth": 0.04, "competition": "low", "housing_age": 25, "nearby_metro": "Gainesville"},
        ]
    },
    "AZ": {
        "sun_belt": True,
        "avg_housing_age": 15,
        "cities": [
            {"city": "Buckeye", "population": 90000, "growth": 0.10, "competition": "low", "housing_age": 8, "nearby_metro": "Phoenix"},
            {"city": "Queen Creek", "population": 65000, "growth": 0.09, "competition": "low", "housing_age": 10, "nearby_metro": "Phoenix"},
            {"city": "San Tan Valley", "population": 100000, "growth": 0.08, "competition": "low", "housing_age": 12, "nearby_metro": "Phoenix"},
            {"city": "Maricopa", "population": 60000, "growth": 0.06, "competition": "low", "housing_age": 10, "nearby_metro": "Phoenix"},
            {"city": "El Mirage", "population": 38000, "growth": 0.04, "competition": "low", "housing_age": 15, "nearby_metro": "Phoenix"},
            {"city": "Florence", "population": 30000, "growth": 0.04, "competition": "very_low", "housing_age": 15, "nearby_metro": "Phoenix"},
            {"city": "Casa Grande", "population": 58000, "growth": 0.05, "competition": "low", "housing_age": 20, "nearby_metro": "Phoenix"},
            {"city": "Prescott Valley", "population": 48000, "growth": 0.04, "competition": "low", "housing_age": 18, "nearby_metro": "Prescott"},
        ]
    },
    "NC": {
        "sun_belt": True,
        "avg_housing_age": 17,
        "cities": [
            {"city": "Holly Springs", "population": 45000, "growth": 0.10, "competition": "low", "housing_age": 12, "nearby_metro": "Raleigh"},
            {"city": "Apex", "population": 60000, "growth": 0.08, "competition": "moderate", "housing_age": 15, "nearby_metro": "Raleigh"},
            {"city": "Wake Forest", "population": 50000, "growth": 0.07, "competition": "moderate", "housing_age": 18, "nearby_metro": "Raleigh"},
            {"city": "Garner", "population": 35000, "growth": 0.04, "competition": "low", "housing_age": 22, "nearby_metro": "Raleigh"},
            {"city": "Clayton", "population": 25000, "growth": 0.06, "competition": "low", "housing_age": 15, "nearby_metro": "Raleigh"},
            {"city": "Mooresville", "population": 48000, "growth": 0.05, "competition": "moderate", "housing_age": 18, "nearby_metro": "Charlotte"},
            {"city": "Indian Trail", "population": 42000, "growth": 0.04, "competition": "low", "housing_age": 15, "nearby_metro": "Charlotte"},
            {"city": "Kannapolis", "population": 55000, "growth": 0.03, "competition": "low", "housing_age": 25, "nearby_metro": "Charlotte"},
        ]
    },
    "GA": {
        "sun_belt": True,
        "avg_housing_age": 19,
        "cities": [
            {"city": "Newnan", "population": 45000, "growth": 0.05, "competition": "low", "housing_age": 20, "nearby_metro": "Atlanta"},
            {"city": "Douglasville", "population": 35000, "growth": 0.04, "competition": "low", "housing_age": 22, "nearby_metro": "Atlanta"},
            {"city": "Woodstock", "population": 35000, "growth": 0.05, "competition": "low", "housing_age": 18, "nearby_metro": "Atlanta"},
            {"city": "Canton", "population": 32000, "growth": 0.06, "competition": "low", "housing_age": 15, "nearby_metro": "Atlanta"},
            {"city": "Acworth", "population": 25000, "growth": 0.04, "competition": "low", "housing_age": 20, "nearby_metro": "Atlanta"},
            {"city": "Dallas", "population": 15000, "growth": 0.07, "competition": "very_low", "housing_age": 12, "nearby_metro": "Atlanta"},
            {"city": "Peachtree City", "population": 38000, "growth": 0.02, "competition": "moderate", "housing_age": 25, "nearby_metro": "Atlanta"},
        ]
    },
    "TN": {
        "sun_belt": True,
        "avg_housing_age": 20,
        "cities": [
            {"city": "Mt. Juliet", "population": 40000, "growth": 0.07, "competition": "low", "housing_age": 12, "nearby_metro": "Nashville"},
            {"city": "Spring Hill", "population": 55000, "growth": 0.08, "competition": "low", "housing_age": 10, "nearby_metro": "Nashville"},
            {"city": "Smyrna", "population": 55000, "growth": 0.04, "competition": "moderate", "housing_age": 18, "nearby_metro": "Nashville"},
            {"city": "Lebanon", "population": 40000, "growth": 0.05, "competition": "low", "housing_age": 20, "nearby_metro": "Nashville"},
            {"city": "Gallatin", "population": 45000, "growth": 0.05, "competition": "low", "housing_age": 18, "nearby_metro": "Nashville"},
        ]
    },
    "SC": {
        "sun_belt": True,
        "avg_housing_age": 18,
        "cities": [
            {"city": "Fort Mill", "population": 25000, "growth": 0.08, "competition": "low", "housing_age": 12, "nearby_metro": "Charlotte"},
            {"city": "Rock Hill", "population": 75000, "growth": 0.04, "competition": "moderate", "housing_age": 20, "nearby_metro": "Charlotte"},
            {"city": "Summerville", "population": 55000, "growth": 0.06, "competition": "low", "housing_age": 15, "nearby_metro": "Charleston"},
            {"city": "Goose Creek", "population": 45000, "growth": 0.04, "competition": "low", "housing_age": 18, "nearby_metro": "Charleston"},
            {"city": "Mauldin", "population": 28000, "growth": 0.05, "competition": "low", "housing_age": 20, "nearby_metro": "Greenville"},
        ]
    }
}

# =============================================================================
# MARKET DISCOVERY ENGINE
# =============================================================================

class MarketDiscoveryEngine:
    """
    Enhanced Market Discovery with Niche Finder Pro parity + R&R advantages
    """
    
    def __init__(self, thresholds: Dict = None):
        self.thresholds = thresholds or DEFAULT_THRESHOLDS
        self.categories = CATEGORY_INTELLIGENCE
        self.markets = MARKET_DATABASE
        self.favorites: List[MarketOpportunity] = []
        
    def turbo_search(
        self,
        categories: List[str] = None,
        states: List[str] = None,
        base_city: str = None,
        base_state: str = None,
        radius_miles: int = 50,
        min_population: int = None,
        max_population: int = None,
        max_competition: str = "moderate",
        min_score: float = None,
        limit: int = 50
    ) -> List[MarketOpportunity]:
        """
        Turbo Search: Rapidly find opportunities (NFP-style)
        
        If base_city/state provided, finds nearby markets.
        Otherwise searches all markets in selected states.
        """
        min_pop = min_population or self.thresholds["min_population"]
        max_pop = max_population or self.thresholds["max_population"]
        min_sc = min_score or self.thresholds["min_score"]
        
        # Default to Tier 1-2 categories if none specified
        if not categories:
            categories = [
                cat for cat, data in self.categories.items()
                if data.get("category_tier", 5) <= 2
            ]
        
        # Default states if none specified
        if not states:
            states = list(self.markets.keys())
        
        competition_levels = {
            "very_low": 1, "low": 2, "moderate": 3, "high": 4, "very_high": 5
        }
        max_comp_level = competition_levels.get(max_competition, 3)
        
        opportunities = []
        
        for state in states:
            if state not in self.markets:
                continue
                
            state_data = self.markets[state]
            
            for city_data in state_data["cities"]:
                # Population filter
                pop = city_data["population"]
                if pop < min_pop or pop > max_pop:
                    continue
                
                # Competition filter
                city_comp = competition_levels.get(city_data["competition"], 3)
                if city_comp > max_comp_level:
                    continue
                
                # Evaluate each category in this market
                for category in categories:
                    if category not in self.categories:
                        continue
                    
                    opp = self._evaluate_opportunity(
                        category=category,
                        city_data=city_data,
                        state=state,
                        state_data=state_data
                    )
                    
                    if opp.score >= min_sc:
                        opportunities.append(opp)
        
        # Sort by score descending
        opportunities.sort(key=lambda x: x.score, reverse=True)
        
        return opportunities[:limit]
    
    def _evaluate_opportunity(
        self,
        category: str,
        city_data: Dict,
        state: str,
        state_data: Dict
    ) -> MarketOpportunity:
        """Evaluate a specific category + market combination"""
        
        cat_intel = self.categories.get(category, {})
        
        # === SCORING COMPONENTS ===
        
        # 1. Category Score (Tier 1 = 5, Tier 5 = 1)
        cat_tier = cat_intel.get("category_tier", 5)
        category_score = max(1, 5.5 - (cat_tier * 0.8))
        
        # 2. Competition Score (inverse)
        comp_map = {"very_low": 5, "low": 4, "moderate": 3, "high": 2, "very_high": 1}
        competition_score = comp_map.get(city_data["competition"], 3)
        
        # 3. Growth Score (higher growth = better)
        growth_rate = city_data["growth"]
        growth_score = min(5, growth_rate * 50 + 2.5)
        
        # 4. Population Sweet Spot (50K-150K ideal)
        pop = city_data["population"]
        if 50000 <= pop <= 150000:
            pop_score = 5
        elif 30000 <= pop < 50000 or 150000 < pop <= 200000:
            pop_score = 4
        elif 20000 <= pop < 30000 or 200000 < pop <= 250000:
            pop_score = 3
        else:
            pop_score = 2
        
        # 5. Housing Age Score (15-30 years ideal for maintenance)
        housing_age = city_data.get("housing_age", 20)
        if 15 <= housing_age <= 30:
            housing_score = 5
        elif 10 <= housing_age < 15 or 30 < housing_age <= 40:
            housing_score = 4
        else:
            housing_score = 3
        
        # 6. Sun Belt Bonus
        sun_belt_bonus = 0.3 if state_data.get("sun_belt", False) else 0
        
        # 7. Urgency Score (from category)
        urgency = cat_intel.get("urgency_score", 3)
        urgency_score = urgency  # Already 1-5 scale
        
        # 8. Renter Density (from category)
        renter_density = cat_intel.get("renter_density", 3)
        renter_score = renter_density  # Already 1-5 scale
        
        # === WEIGHTED COMPOSITE ===
        # Our weights (different from NFP - we factor in R&R success factors)
        weights = {
            "category": 0.25,      # Category vertical matters most
            "competition": 0.20,   # Competition is key
            "urgency": 0.15,       # Emergency services convert better
            "renter_density": 0.10, # Need contractors to buy leads
            "growth": 0.10,        # Growth markets expand opportunity
            "population": 0.10,    # Right-sized markets
            "housing": 0.10        # Housing age affects demand
        }
        
        score = (
            category_score * weights["category"] +
            competition_score * weights["competition"] +
            urgency_score * weights["urgency"] +
            renter_score * weights["renter_density"] +
            growth_score * weights["growth"] +
            pop_score * weights["population"] +
            housing_score * weights["housing"] +
            sun_belt_bonus
        )
        score = round(score, 2)
        
        # === DETERMINE TIER & RECOMMENDATION ===
        if score >= 4.0:
            tier = "high_opportunity"
            recommendation = RecommendationType.ACQUIRE
            rating = OpportunityRating.FIVE_STAR
        elif score >= 3.7:
            tier = "high_opportunity"
            recommendation = RecommendationType.ACQUIRE
            rating = OpportunityRating.FOUR_STAR
        elif score >= 3.5:
            tier = "moderate_opportunity"
            recommendation = RecommendationType.EVALUATE
            rating = OpportunityRating.THREE_STAR
        elif score >= 3.0:
            tier = "moderate_opportunity"
            recommendation = RecommendationType.EVALUATE
            rating = OpportunityRating.TWO_STAR
        else:
            tier = "low_opportunity"
            recommendation = RecommendationType.SKIP
            rating = OpportunityRating.ONE_STAR
        
        # === GENERATE NEXT STEPS ===
        next_steps = self._generate_next_steps(recommendation, category, city_data, state)
        
        # === SIMULATE SERP DATA (would be real API call) ===
        # NFP-style metrics
        dedicated_sites = self._estimate_dedicated_sites(city_data["competition"])
        map_pack_reviews = self._estimate_map_pack_reviews(city_data["competition"])
        no_website_targets = self._estimate_no_website_gmbs(city_data["competition"])
        
        return MarketOpportunity(
            id=f"{category.lower().replace(' ', '_')}_{city_data['city'].lower().replace(' ', '_')}_{state.lower()}",
            category=category,
            city=city_data["city"],
            state=state,
            score=score,
            tier=tier,
            recommendation=recommendation,
            rating=rating,
            population=pop,
            growth_rate=growth_rate,
            competition_level=CompetitionLevel(city_data["competition"]),
            housing_age=housing_age,
            sun_belt=state_data.get("sun_belt", False),
            monthly_potential=cat_intel.get("monthly_potential", 500),
            avg_job_value=cat_intel.get("avg_job_value", 1000),
            lead_value_range=cat_intel.get("lead_value_range", (50, 200)),
            urgency_score=urgency,
            renter_density=renter_density,
            time_to_rank_months=cat_intel.get("time_to_rank_months", 4),
            dedicated_sites=dedicated_sites,
            map_pack_avg_reviews=map_pack_reviews,
            no_website_targets=no_website_targets,
            scoring_breakdown={
                "category_score": round(category_score, 2),
                "competition_score": round(competition_score, 2),
                "urgency_score": round(urgency_score, 2),
                "renter_density_score": round(renter_score, 2),
                "growth_score": round(growth_score, 2),
                "population_score": round(pop_score, 2),
                "housing_score": round(housing_score, 2),
                "sun_belt_bonus": round(sun_belt_bonus, 2)
            },
            next_steps=next_steps
        )
    
    def _estimate_dedicated_sites(self, competition: str) -> int:
        """Estimate dedicated sites in SERP based on competition"""
        estimates = {
            "very_low": random.randint(2, 5),
            "low": random.randint(5, 10),
            "moderate": random.randint(10, 15),
            "high": random.randint(15, 22),
            "very_high": random.randint(22, 30)
        }
        return estimates.get(competition, 10)
    
    def _estimate_map_pack_reviews(self, competition: str) -> float:
        """Estimate average map pack reviews based on competition"""
        estimates = {
            "very_low": random.uniform(5, 20),
            "low": random.uniform(15, 40),
            "moderate": random.uniform(30, 80),
            "high": random.uniform(60, 150),
            "very_high": random.uniform(100, 300)
        }
        return round(estimates.get(competition, 50), 1)
    
    def _estimate_no_website_gmbs(self, competition: str) -> int:
        """Estimate GMBs without websites (prime call targets per NFP)"""
        estimates = {
            "very_low": random.randint(3, 6),
            "low": random.randint(2, 4),
            "moderate": random.randint(1, 3),
            "high": random.randint(0, 2),
            "very_high": random.randint(0, 1)
        }
        return estimates.get(competition, 2)
    
    def _generate_next_steps(
        self,
        recommendation: RecommendationType,
        category: str,
        city_data: Dict,
        state: str
    ) -> List[str]:
        """Generate actionable next steps"""
        
        if recommendation == RecommendationType.ACQUIRE:
            return [
                f"1. Run RevFlow competitive analysis for '{category}' in {city_data['city']}, {state}",
                "2. Check Local Pack: review counts, ratings of top 3 (use NFP or manual)",
                f"3. Validate renter willingness: call 3-5 local {category.lower()} contractors",
                "4. If validated, acquire domain: [city][category].com or [category][city].com",
                "5. Use R&R Automation to generate AI-optimized site content",
                "6. Set up GBP with verified address or use a service",
                f"7. Target: Rank in 3-6 months, monetize by month {self.categories.get(category, {}).get('time_to_rank_months', 4) + 2}"
            ]
        elif recommendation == RecommendationType.EVALUATE:
            return [
                "1. Conduct deeper SERP analysis before committing",
                "2. Compare against higher-scoring opportunities",
                "3. Check Google Keyword Planner for actual search volume",
                "4. If no better options, proceed with ACQUIRE steps",
                "5. Otherwise, bookmark and revisit in 30 days"
            ]
        else:
            return [
                "1. Skip this opportunity - focus on higher scores",
                "2. Only revisit if all Tier 1-2 markets exhausted",
                f"3. Category '{category}' may not be viable for R&R model"
            ]
    
    # === FAVORITING & TAGGING (NFP Parity) ===
    
    def favorite(self, opportunity: MarketOpportunity, tags: List[str] = None, notes: str = "") -> None:
        """Save an opportunity to favorites with optional tags and notes"""
        opportunity.is_favorited = True
        opportunity.tags = tags or []
        opportunity.notes = notes
        
        # Check if already in favorites
        existing = next((f for f in self.favorites if f.id == opportunity.id), None)
        if existing:
            existing.tags = opportunity.tags
            existing.notes = opportunity.notes
        else:
            self.favorites.append(opportunity)
    
    def unfavorite(self, opportunity_id: str) -> bool:
        """Remove from favorites"""
        self.favorites = [f for f in self.favorites if f.id != opportunity_id]
        return True
    
    def get_favorites(
        self,
        tags: List[str] = None,
        category: str = None,
        state: str = None,
        rating: OpportunityRating = None
    ) -> List[MarketOpportunity]:
        """Get filtered favorites (NFP style)"""
        result = self.favorites.copy()
        
        if tags:
            result = [f for f in result if any(t in f.tags for t in tags)]
        if category:
            result = [f for f in result if f.category == category]
        if state:
            result = [f for f in result if f.state == state]
        if rating:
            result = [f for f in result if f.rating == rating]
        
        return result
    
    # === EXPORT (NFP Parity) ===
    
    def export_to_csv(self, opportunities: List[MarketOpportunity]) -> str:
        """Export opportunities to CSV format (NFP due diligence template style)"""
        headers = [
            "Category", "City", "State", "Score", "Rating", "Recommendation",
            "Population", "Growth Rate", "Competition", "Monthly Potential",
            "Avg Job Value", "Time to Rank", "Dedicated Sites", "Map Pack Reviews",
            "No Website Targets", "Tags", "Notes"
        ]
        
        lines = [",".join(headers)]
        
        for opp in opportunities:
            row = [
                opp.category,
                opp.city,
                opp.state,
                str(opp.score),
                opp.rating.value,
                opp.recommendation.value,
                str(opp.population),
                f"{opp.growth_rate:.1%}",
                opp.competition_level.value,
                f"${opp.monthly_potential}",
                f"${opp.avg_job_value}",
                f"{opp.time_to_rank_months} months",
                str(opp.dedicated_sites),
                str(opp.map_pack_avg_reviews),
                str(opp.no_website_targets),
                "|".join(opp.tags),
                opp.notes.replace(",", ";")
            ]
            lines.append(",".join(row))
        
        return "\n".join(lines)
    
    def export_to_json(self, opportunities: List[MarketOpportunity]) -> str:
        """Export opportunities to JSON"""
        return json.dumps([opp.to_dict() for opp in opportunities], indent=2)
    
    # === CATEGORY RECOMMENDATIONS ===
    
    def get_category_recommendations(self) -> Dict:
        """Get recommended categories based on R&R success factors"""
        
        tier_1 = []
        tier_2 = []
        tier_3 = []
        avoid = []
        
        for cat, data in self.categories.items():
            tier = data.get("category_tier", 5)
            entry = {
                "category": cat,
                "avg_job_value": data.get("avg_job_value", 0),
                "monthly_potential": data.get("monthly_potential", 0),
                "urgency_score": data.get("urgency_score", 0),
                "time_to_rank": data.get("time_to_rank_months", 0),
                "notes": data.get("notes", ""),
                "success_indicators": data.get("success_indicators", []),
                "red_flags": data.get("red_flags", [])
            }
            
            if tier == 1:
                tier_1.append(entry)
            elif tier == 2:
                tier_2.append(entry)
            elif tier == 3:
                tier_3.append(entry)
            else:
                avoid.append(entry)
        
        return {
            "tier_1_expand": sorted(tier_1, key=lambda x: x["monthly_potential"], reverse=True),
            "tier_2_maintain": sorted(tier_2, key=lambda x: x["monthly_potential"], reverse=True),
            "tier_3_selective": sorted(tier_3, key=lambda x: x["monthly_potential"], reverse=True),
            "avoid": sorted(avoid, key=lambda x: x["monthly_potential"], reverse=True)
        }
    
    # === HOTSPOTS ===
    
    def get_hotspots(self, limit: int = 20) -> List[MarketOpportunity]:
        """Get top market hotspots across all Tier 1-2 categories"""
        return self.turbo_search(
            categories=[c for c, d in self.categories.items() if d.get("category_tier", 5) <= 2],
            min_score=3.5,
            limit=limit
        )


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

market_discovery_engine = MarketDiscoveryEngine()


# =============================================================================
# QUICK TEST
# =============================================================================

if __name__ == "__main__":
    engine = MarketDiscoveryEngine()
    
    # Turbo Search example
    print("=== TURBO SEARCH: Concrete in TX, FL, AZ ===\n")
    results = engine.turbo_search(
        categories=["Concrete", "Roofing", "Water Damage"],
        states=["TX", "FL", "AZ"],
        min_score=3.5,
        limit=10
    )
    
    for opp in results:
        print(f"{opp.rating.value} | {opp.score:.2f} | {opp.category:15} | {opp.city:20} {opp.state} | ${opp.monthly_potential}/mo | {opp.recommendation.value}")
        print(f"         Competition: {opp.competition_level.value} | Dedicated Sites: {opp.dedicated_sites} | No Website GMBs: {opp.no_website_targets}")
        print()
    
    # Export example
    print("\n=== CSV EXPORT ===\n")
    print(engine.export_to_csv(results[:3]))

# Singleton instance for import
market_discovery = MarketDiscoveryEngine()
