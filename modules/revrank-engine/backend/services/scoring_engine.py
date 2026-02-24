"""
Scoring Engine Service
Core scoring logic for the Rank & Rent Decision Tool
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid
import json

# Industry benchmarks from research
CATEGORY_BENCHMARKS = {
    "Concrete": {
        "avg_job_value": 7500,
        "lead_value_range": [150, 400],
        "urgency_score": 4,
        "seasonality": 3,
        "regulation_risk": 5,
        "renter_density": 4,
        "serp_competition": "moderate",
        "monthly_potential": 2000,
        "category_tier": 1,
        "recommended": True
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
        "recommended": True
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
        "recommended": True
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
        "recommended": True
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
        "recommended": True
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
        "recommended": True
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
        "recommended": True
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
        "recommended": False
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
        "recommended": False
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
        "recommended": False
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
        "recommended": False
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
        "recommended": False
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
        "recommended": False
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
        "recommended": False
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
        "recommended": False
    },
    "Law": {
        "avg_job_value": 15000,
        "lead_value_range": [200, 1000],
        "urgency_score": 3,
        "seasonality": 5,
        "regulation_risk": 1,
        "renter_density": 5,
        "serp_competition": "very_high",
        "monthly_potential": 3000,
        "category_tier": 4,
        "recommended": False
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
        "recommended": False
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
        "recommended": False
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
        "recommended": False
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
        "recommended": False
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
        "recommended": False
    }
}

# Enhanced scoring criteria
DEFAULT_CRITERIA = {
    "category_vertical_score": {"weight": 12, "description": "Industry-specific success probability"},
    "local_search_demand": {"weight": 10, "description": "Monthly search volume for service + city"},
    "competition_quality": {"weight": 10, "description": "Quality of ranking competitors"},
    "lead_value_proxy": {"weight": 10, "description": "Average job value / CPC indicator"},
    "serp_weakness_index": {"weight": 8, "description": "Exploitable weaknesses in top results"},
    "renter_willingness_evidence": {"weight": 8, "description": "Proof of contractor interest"},
    "business_density": {"weight": 6, "description": "Number of potential renter contractors"},
    "urgency_call_first": {"weight": 6, "description": "Emergency nature of service"},
    "regulation_compliance_risk": {"weight": 5, "description": "YMYL/licensing risk"},
    "local_pack_friction": {"weight": 5, "description": "GBP competition difficulty"},
    "replicability_nearby": {"weight": 5, "description": "Ability to clone in adjacent markets"},
    "portfolio_diversification": {"weight": 4, "description": "Balance vs current portfolio"},
    "commercial_intent_mix": {"weight": 3, "description": "% searches with buying intent"},
    "seasonality_profile": {"weight": 3, "description": "Demand stability throughout year"},
    "city_size_growth": {"weight": 3, "description": "Population and growth trajectory"},
    "serp_vulnerability": {"weight": 2, "description": "How easily rankings can be disrupted"}
}

# Sample portfolio data
SAMPLE_PORTFOLIO = [
    {"id": "site_001", "name": "Duncanville Concrete Driveway Pros", "category": "Concrete", "city": "Duncanville", "state": "TX", "score": 4.12, "criteria_scores": {}},
    {"id": "site_002", "name": "El Mirage Concrete Contractor", "category": "Concrete", "city": "El Mirage", "state": "AZ", "score": 4.08, "criteria_scores": {}},
    {"id": "site_003", "name": "Kingsville Concrete Crafting Co.", "category": "Concrete", "city": "Kingsville", "state": "TX", "score": 4.05, "criteria_scores": {}},
    {"id": "site_004", "name": "Lancaster Concrete Driveway Pros", "category": "Concrete", "city": "Lancaster", "state": "TX", "score": 4.03, "criteria_scores": {}},
    {"id": "site_005", "name": "Manchester Concrete Craftsmanship", "category": "Concrete", "city": "Manchester", "state": "CT", "score": 4.01, "criteria_scores": {}},
    {"id": "site_006", "name": "Tewksbury Concrete Craftsmanship", "category": "Concrete", "city": "Tewksbury", "state": "MA", "score": 4.00, "criteria_scores": {}},
    {"id": "site_007", "name": "Epoxy Flooring Pros of La Porte", "category": "Concrete", "city": "La Porte", "state": "TX", "score": 3.98, "criteria_scores": {}},
    {"id": "site_008", "name": "Benicia Roofing Artisans", "category": "Roofing", "city": "Benicia", "state": "CA", "score": 3.92, "criteria_scores": {}},
    {"id": "site_009", "name": "Burke Roofing and Renovations", "category": "Roofing", "city": "Burke", "state": "VA", "score": 3.89, "criteria_scores": {}},
    {"id": "site_010", "name": "Key West Water Rescue Team", "category": "Water Damage", "city": "Key West", "state": "FL", "score": 3.87, "criteria_scores": {}},
    {"id": "site_011", "name": "Ocoee Water Damage Repair", "category": "Water Damage", "city": "Ocoee", "state": "FL", "score": 3.85, "criteria_scores": {}},
    {"id": "site_012", "name": "Belleville Electrical Masters", "category": "Electric", "city": "Belleville", "state": "NJ", "score": 3.82, "criteria_scores": {}},
    {"id": "site_013", "name": "Castro Valley Electrician Pros", "category": "Electric", "city": "Castro Valley", "state": "CA", "score": 3.80, "criteria_scores": {}},
    {"id": "site_014", "name": "San Lorenzo Fencing Builders", "category": "Fence", "city": "San Lorenzo", "state": "CA", "score": 3.78, "criteria_scores": {}},
    {"id": "site_015", "name": "San Tan Valley Fencing Co.", "category": "Fence", "city": "San Tan Valley", "state": "AZ", "score": 3.76, "criteria_scores": {}},
    {"id": "site_016", "name": "Socorro Texas Fencing Pros", "category": "Fence", "city": "Socorro", "state": "TX", "score": 3.75, "criteria_scores": {}},
    {"id": "site_017", "name": "Jamestown Tree Care Masters", "category": "Tree Care", "city": "Jamestown", "state": "NY", "score": 3.73, "criteria_scores": {}},
    {"id": "site_018", "name": "Spanaway Tree Care Collective", "category": "Tree Care", "city": "Spanaway", "state": "WA", "score": 3.71, "criteria_scores": {}},
    {"id": "site_019", "name": "Westfield Tree Care Specialists", "category": "Tree Care", "city": "Westfield", "state": "NJ", "score": 3.70, "criteria_scores": {}},
    {"id": "site_020", "name": "Bell Gardens Drywall Pros", "category": "Drywall", "city": "Bell Gardens", "state": "CA", "score": 3.52, "criteria_scores": {}},
    {"id": "site_021", "name": "Kearny Drywall Contractor", "category": "Drywall", "city": "Kearny", "state": "NJ", "score": 3.50, "criteria_scores": {}},
    {"id": "site_022", "name": "La Puente Drywall Pros", "category": "Drywall", "city": "La Puente", "state": "CA", "score": 3.48, "criteria_scores": {}},
    {"id": "site_023", "name": "Carmel Carpentry Solutions", "category": "Carpentry", "city": "Carmel", "state": "NY", "score": 3.45, "criteria_scores": {}},
    {"id": "site_024", "name": "Dedham Woodworking & Carpentry Co", "category": "Carpentry", "city": "Dedham", "state": "MA", "score": 3.42, "criteria_scores": {}},
    {"id": "site_025", "name": "Harker Heights Carpenter Collective", "category": "Carpentry", "city": "Harker Heights", "state": "TX", "score": 3.40, "criteria_scores": {}},
    {"id": "site_026", "name": "Gloucester Plumbing Pros", "category": "Plumbing", "city": "Gloucester", "state": "MA", "score": 3.38, "criteria_scores": {}},
    {"id": "site_027", "name": "Fountainebleau Plumbing Pros", "category": "Plumbing", "city": "Fontainebleau", "state": "FL", "score": 3.35, "criteria_scores": {}},
    {"id": "site_028", "name": "Hanford's Trusted Moving Company", "category": "Moving", "city": "Hanford", "state": "CA", "score": 3.25, "criteria_scores": {}},
    {"id": "site_029", "name": "Arcadia Landscaping Pros", "category": "Landscaping", "city": "Arcadia", "state": "CA", "score": 3.20, "criteria_scores": {}},
    {"id": "site_030", "name": "Banning's Green Oasis Landscaping", "category": "Landscaping", "city": "Banning", "state": "CA", "score": 3.18, "criteria_scores": {}},
    {"id": "site_031", "name": "Monroeville Masonry Specialists", "category": "Masonry", "city": "Monroeville", "state": "PA", "score": 3.15, "criteria_scores": {}},
    {"id": "site_032", "name": "Montgomery Village Masonry Works", "category": "Masonry", "city": "Montgomery Village", "state": "MD", "score": 3.12, "criteria_scores": {}},
    {"id": "site_033", "name": "Gahanna Colorful Coatings Studios", "category": "Painting", "city": "Gahanna", "state": "OH", "score": 3.05, "criteria_scores": {}},
    {"id": "site_034", "name": "Hamtramck Artistic Painting Services", "category": "Painting", "city": "Hamtramck", "state": "MI", "score": 3.00, "criteria_scores": {}},
    {"id": "site_035", "name": "Balch Springs Pool Cleaning Pros", "category": "Pool cleaning", "city": "Balch Springs", "state": "TX", "score": 2.95, "criteria_scores": {}},
    {"id": "site_036", "name": "Boyton Beach pool cleaners", "category": "Pool cleaning", "city": "Boyton Beach", "state": "FL", "score": 2.90, "criteria_scores": {}},
    {"id": "site_037", "name": "Lawndale Pool Care Crew", "category": "Pool cleaning", "city": "Lawndale", "state": "CA", "score": 2.85, "criteria_scores": {}},
    {"id": "site_038", "name": "Galt Appliance Care", "category": "Appliance repair", "city": "Galt", "state": "CA", "score": 2.75, "criteria_scores": {}},
    {"id": "site_039", "name": "Hattiesburg Appliance Repair Pros", "category": "Appliance repair", "city": "Hattiesburg", "state": "MS", "score": 2.65, "criteria_scores": {}},
    {"id": "site_040", "name": "New Iberia Appliance Fixers", "category": "Appliance repair", "city": "New Iberia", "state": "LA", "score": 2.55, "criteria_scores": {}},
    {"id": "site_041", "name": "Reedley Appliance Repair Services", "category": "Appliance repair", "city": "Reedley", "state": "CA", "score": 2.48, "criteria_scores": {}},
    {"id": "site_042", "name": "Tulare Appliance Repair Hub", "category": "Appliance repair", "city": "Tulare", "state": "CA", "score": 2.40, "criteria_scores": {}},
    {"id": "site_043", "name": "Andover Mobile Mechanic Masters", "category": "Mobile mechanic", "city": "Andover", "state": "MA", "score": 2.35, "criteria_scores": {}},
    {"id": "site_044", "name": "Banning Mobile Mechanic Service", "category": "Mobile mechanic", "city": "Banning", "state": "CA", "score": 2.32, "criteria_scores": {}},
    {"id": "site_045", "name": "Edingburg mobile mechanics", "category": "Mobile mechanic", "city": "Edingburg", "state": "TX", "score": 2.30, "criteria_scores": {}},
    {"id": "site_046", "name": "East Palo Alto Patio Covers", "category": "Patio covers", "city": "East Palo Alto", "state": "CA", "score": 2.25, "criteria_scores": {}},
    {"id": "site_047", "name": "Edingburg patio covers", "category": "Patio covers", "city": "Edingburg", "state": "TX", "score": 2.20, "criteria_scores": {}},
    {"id": "site_048", "name": "El Cerrito Personal Injury Law", "category": "Law", "city": "El Cerrito", "state": "CA", "score": 2.18, "criteria_scores": {}},
    {"id": "site_049", "name": "Kingsville Injury Justice Advocates", "category": "Law", "city": "Kingsville", "state": "TX", "score": 2.15, "criteria_scores": {}},
    {"id": "site_050", "name": "Orchard Park Towing Services", "category": "Towing", "city": "Orchard Park", "state": "NY", "score": 2.10, "criteria_scores": {}},
    {"id": "site_051", "name": "West Warwick Towing Company", "category": "Towing", "city": "West Warwick", "state": "RI", "score": 2.05, "criteria_scores": {}},
    {"id": "site_052", "name": "West Windsor Junk Removal Solutions", "category": "Junk Removal", "city": "West Windsor", "state": "NJ", "score": 2.00, "criteria_scores": {}},
    {"id": "site_053", "name": "Allen Bee Hive Rescue Services", "category": "Bee rescue", "city": "Allen", "state": "TX", "score": 1.90, "criteria_scores": {}},
]


class ScoringEngine:
    def __init__(self):
        self.criteria = DEFAULT_CRITERIA.copy()
        self.benchmarks = CATEGORY_BENCHMARKS.copy()
        self.portfolio = SAMPLE_PORTFOLIO.copy()
        self._enrich_portfolio()
    
    def _enrich_portfolio(self):
        """Enrich portfolio with benchmark data"""
        for site in self.portfolio:
            benchmark = self.benchmarks.get(site["category"], {})
            site["monthly_potential"] = benchmark.get("monthly_potential", 500)
            site["avg_job_value"] = benchmark.get("avg_job_value", 1000)
            site["tier"] = self._get_tier(site["score"])
            site["decision"] = self._get_decision(site["score"])
    
    def _get_tier(self, score: float) -> str:
        if score >= 3.7:
            return "activate"
        elif score >= 3.2:
            return "watchlist"
        else:
            return "sunset"
    
    def _get_decision(self, score: float) -> str:
        if score >= 3.7:
            return "KEEP & ACTIVATE"
        elif score >= 3.2:
            return "MONITOR 90 DAYS"
        else:
            return "SUNSET"
    
    def get_portfolio_summary(self) -> Dict:
        """Get complete portfolio summary"""
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
                "total_monthly": sum(s["monthly_potential"] for s in self.portfolio),
                "activate_annual": sum(s["monthly_potential"] for s in activate) * 12,
                "total_annual": sum(s["monthly_potential"] for s in self.portfolio) * 12
            },
            "category_breakdown": self._get_category_breakdown(),
            "top_sites": sorted(self.portfolio, key=lambda x: x["score"], reverse=True)[:10],
            "bottom_sites": sorted(self.portfolio, key=lambda x: x["score"])[:10],
            "recommendations": self._generate_recommendations()
        }
    
    def _get_category_breakdown(self) -> List[Dict]:
        """Get performance by category"""
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
                "recommended": benchmark.get("recommended", False),
                "category_tier": benchmark.get("category_tier", 5)
            })
        
        return sorted(result, key=lambda x: x["avg_score"], reverse=True)
    
    def _generate_recommendations(self) -> List[Dict]:
        """Generate actionable recommendations"""
        return [
            {
                "priority": 1,
                "action": "ACTIVATE",
                "description": "Begin contractor outreach for all 19 Activate Now sites",
                "sites_affected": len([s for s in self.portfolio if s["tier"] == "activate"]),
                "expected_impact": "$28,500/month potential"
            },
            {
                "priority": 2,
                "action": "SUNSET",
                "description": "Stop investment in 19 low-scoring sites",
                "sites_affected": len([s for s in self.portfolio if s["tier"] == "sunset"]),
                "expected_impact": "Free up resources for high-potential sites"
            },
            {
                "priority": 3,
                "action": "MONITOR",
                "description": "Track 15 Watchlist sites for 90 days",
                "sites_affected": len([s for s in self.portfolio if s["tier"] == "watchlist"]),
                "expected_impact": "Identify 5-8 promotion candidates"
            },
            {
                "priority": 4,
                "action": "ACQUIRE",
                "description": "Identify new opportunities in Concrete, Roofing, Water Damage",
                "sites_affected": 0,
                "expected_impact": "5-10 new high-potential sites"
            }
        ]
    
    def get_sites(self, tier: str = None, category: str = None, 
                  state: str = None, sort_by: str = "score", 
                  order: str = "desc") -> List[Dict]:
        """Get sites with filtering and sorting"""
        result = self.portfolio.copy()
        
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
        elif sort_by == "category":
            result = sorted(result, key=lambda x: x["category"], reverse=reverse)
        
        return result
    
    def get_site_by_id(self, site_id: str) -> Optional[Dict]:
        """Get a specific site by ID"""
        for site in self.portfolio:
            if site["id"] == site_id:
                return site
        return None
    
    def calculate_score(self, site_data: Dict) -> Dict:
        """Calculate score for a site using enhanced model"""
        category = site_data.get("category", "")
        benchmark = self.benchmarks.get(category, {})
        
        # Calculate component scores (1-5 scale)
        scores = {}
        
        # Category vertical score based on tier
        category_tier = benchmark.get("category_tier", 5)
        scores["category_vertical_score"] = max(1, 5 - (category_tier - 1) * 0.8)
        
        # Use provided scores or derive from benchmarks
        scores["urgency_call_first"] = site_data.get("urgency_score", benchmark.get("urgency_score", 3))
        scores["regulation_compliance_risk"] = site_data.get("regulation_score", benchmark.get("regulation_risk", 3))
        scores["business_density"] = site_data.get("renter_density", benchmark.get("renter_density", 3))
        
        # Lead value based on job value
        avg_job = benchmark.get("avg_job_value", 1000)
        scores["lead_value_proxy"] = min(5, avg_job / 2000)
        
        # Default other scores to provided values or 3
        for criterion in self.criteria:
            if criterion not in scores:
                scores[criterion] = site_data.get(criterion, 3)
        
        # Calculate weighted total
        total = 0
        total_weight = 0
        for criterion, score in scores.items():
            weight = self.criteria.get(criterion, {}).get("weight", 0)
            total += score * weight
            total_weight += weight
        
        final_score = total / total_weight if total_weight > 0 else 0
        final_score = round(final_score, 2)
        
        return {
            "site": site_data,
            "score": final_score,
            "tier": self._get_tier(final_score),
            "decision": self._get_decision(final_score),
            "criteria_scores": scores,
            "monthly_potential": benchmark.get("monthly_potential", 500),
            "avg_job_value": benchmark.get("avg_job_value", 1000),
            "confidence": self._calculate_confidence(scores),
            "scoring_breakdown": {
                criterion: {
                    "score": scores.get(criterion, 0),
                    "weight": self.criteria.get(criterion, {}).get("weight", 0),
                    "contribution": scores.get(criterion, 0) * self.criteria.get(criterion, {}).get("weight", 0) / 100
                }
                for criterion in self.criteria
            }
        }
    
    def _calculate_confidence(self, scores: Dict) -> float:
        """Calculate confidence level based on score variance"""
        values = list(scores.values())
        if not values:
            return 0.5
        avg = sum(values) / len(values)
        variance = sum((v - avg) ** 2 for v in values) / len(values)
        # Lower variance = higher confidence
        confidence = max(0.3, min(0.95, 1 - (variance / 10)))
        return round(confidence, 2)
    
    def get_criteria(self) -> Dict:
        """Get all scoring criteria with weights"""
        return self.criteria
    
    def update_criteria_weights(self, new_weights: Dict) -> Dict:
        """Update criteria weights for what-if analysis"""
        for criterion, weight in new_weights.items():
            if criterion in self.criteria:
                self.criteria[criterion]["weight"] = weight
        return self.criteria
    
    def get_category_benchmarks(self) -> List[Dict]:
        """Get all category benchmarks"""
        return [
            {"category": cat, **data}
            for cat, data in self.benchmarks.items()
        ]
    
    def get_category_benchmark(self, category: str) -> Optional[Dict]:
        """Get benchmark for specific category"""
        if category in self.benchmarks:
            return {"category": category, **self.benchmarks[category]}
        return None
    
    def create_site(self, site_data: Dict) -> Dict:
        """Add a new site to portfolio"""
        new_site = {
            "id": f"site_{str(uuid.uuid4())[:8]}",
            "name": site_data.get("name"),
            "category": site_data.get("category"),
            "city": site_data.get("city"),
            "state": site_data.get("state"),
            "score": site_data.get("score", 3.0),
            "criteria_scores": site_data.get("criteria_scores", {})
        }
        
        # Enrich with benchmark data
        benchmark = self.benchmarks.get(new_site["category"], {})
        new_site["monthly_potential"] = benchmark.get("monthly_potential", 500)
        new_site["avg_job_value"] = benchmark.get("avg_job_value", 1000)
        new_site["tier"] = self._get_tier(new_site["score"])
        new_site["decision"] = self._get_decision(new_site["score"])
        
        self.portfolio.append(new_site)
        return new_site
    
    def update_site(self, site_id: str, site_data: Dict) -> Optional[Dict]:
        """Update an existing site"""
        for i, site in enumerate(self.portfolio):
            if site["id"] == site_id:
                site.update(site_data)
                site["tier"] = self._get_tier(site.get("score", 3.0))
                site["decision"] = self._get_decision(site.get("score", 3.0))
                self.portfolio[i] = site
                return site
        return None
    
    def delete_site(self, site_id: str) -> bool:
        """Remove a site from portfolio"""
        for i, site in enumerate(self.portfolio):
            if site["id"] == site_id:
                self.portfolio.pop(i)
                return True
        return False
    
    def update_from_revflow(self, leads_data: Dict) -> Dict:
        """Update site performance from RevFlow lead data"""
        # This would integrate with RevFlow API
        return {"status": "updated", "sites_affected": 0}
    
    def update_from_rr_competitive(self, competitive_data: Dict) -> Dict:
        """Update competitive scores from R&R analysis"""
        # This would integrate with R&R API
        return {"status": "updated", "sites_affected": 0}
    
    def export_to_rr_format(self, site: Dict) -> Dict:
        """Export site data in R&R-compatible format"""
        return {
            "business_name": site["name"],
            "category": site["category"],
            "location": {
                "city": site["city"],
                "state": site["state"]
            },
            "analysis_request": {
                "type": "competitive",
                "keywords": [f"{site['category'].lower()} {site['city'].lower()}"],
                "scope": "local"
            }
        }
    
    def generate_action_plan(self, days: int = 90) -> List[Dict]:
        """Generate prioritized action plan"""
        activate_sites = [s for s in self.portfolio if s["tier"] == "activate"]
        
        return [
            {
                "week": "1-2",
                "action_type": "SUNSET",
                "task": "Discontinue all investment in Sunset tier sites",
                "sites": [s["name"] for s in self.portfolio if s["tier"] == "sunset"][:5],
                "impact": "Free up resources"
            },
            {
                "week": "1-2",
                "action_type": "ACTIVATE",
                "task": "Begin contractor outreach for Concrete sites",
                "sites": [s["name"] for s in activate_sites if s["category"] == "Concrete"][:5],
                "impact": "Highest scores, proven category"
            },
            {
                "week": "3-4",
                "action_type": "ACTIVATE",
                "task": "Launch Roofing and Water Damage campaigns",
                "sites": [s["name"] for s in activate_sites if s["category"] in ["Roofing", "Water Damage"]][:4],
                "impact": "High monthly potential"
            },
            {
                "week": "5-8",
                "action_type": "MONITOR",
                "task": "Set up tracking for Watchlist sites",
                "sites": [s["name"] for s in self.portfolio if s["tier"] == "watchlist"][:5],
                "impact": "Identify promotion candidates"
            }
        ]
    
    def project_revenue(self, months: int = 12, success_rate: float = 0.6) -> Dict:
        """Project revenue based on portfolio"""
        activate = [s for s in self.portfolio if s["tier"] == "activate"]
        watchlist = [s for s in self.portfolio if s["tier"] == "watchlist"]
        
        activate_potential = sum(s["monthly_potential"] for s in activate)
        watchlist_potential = sum(s["monthly_potential"] for s in watchlist)
        
        return {
            "months": months,
            "success_rate": success_rate,
            "projections": {
                "conservative": {
                    "monthly": int(activate_potential * success_rate * 0.7),
                    "annual": int(activate_potential * success_rate * 0.7 * 12)
                },
                "moderate": {
                    "monthly": int(activate_potential * success_rate),
                    "annual": int(activate_potential * success_rate * 12)
                },
                "optimistic": {
                    "monthly": int((activate_potential + watchlist_potential * 0.3) * success_rate),
                    "annual": int((activate_potential + watchlist_potential * 0.3) * success_rate * 12)
                }
            }
        }
    
    def analyze_categories(self) -> List[Dict]:
        """Detailed category analysis"""
        return self._get_category_breakdown()

# Singleton instance for import
scoring_engine = ScoringEngine()

# Export constants for main_enhanced.py
SCORING_CRITERIA = {
    "category_vertical": {"weight": 12, "description": "Industry success probability"},
    "local_search_demand": {"weight": 10, "description": "Monthly search volume"},
    "competition_quality": {"weight": 10, "description": "Competitor strength"},
    "lead_value_proxy": {"weight": 10, "description": "Avg job value / CPC"},
    "serp_weakness": {"weight": 8, "description": "Exploitable weaknesses"},
    "renter_willingness": {"weight": 8, "description": "Contractor demand signals"},
    "business_density": {"weight": 6, "description": "Potential renters in area"},
    "urgency_call_first": {"weight": 6, "description": "Emergency nature"},
    "regulation_risk": {"weight": 5, "description": "YMYL/licensing complexity"},
    "local_pack_friction": {"weight": 5, "description": "Map pack entry difficulty"},
    "replicability": {"weight": 5, "description": "Clone potential"},
    "portfolio_diversification": {"weight": 4, "description": "Balance value"},
    "commercial_intent": {"weight": 3, "description": "Buying intent %"},
    "seasonality": {"weight": 3, "description": "Year-round stability"},
    "city_growth": {"weight": 3, "description": "Population trajectory"},
    "serp_vulnerability": {"weight": 2, "description": "Algorithm risk"},
}

CATEGORY_BENCHMARKS = {
    "Concrete": {"category_tier": 1, "avg_job_value": 3500, "monthly_potential": 2000, "recommended_action": "EXPAND"},
    "Roofing": {"category_tier": 1, "avg_job_value": 8000, "monthly_potential": 2500, "recommended_action": "EXPAND"},
    "Water Damage": {"category_tier": 1, "avg_job_value": 3000, "monthly_potential": 2000, "recommended_action": "EXPAND"},
    "Electric": {"category_tier": 2, "avg_job_value": 400, "monthly_potential": 1500, "recommended_action": "MAINTAIN"},
    "Fence": {"category_tier": 2, "avg_job_value": 3500, "monthly_potential": 1500, "recommended_action": "MAINTAIN"},
    "Tree Care": {"category_tier": 2, "avg_job_value": 800, "monthly_potential": 1200, "recommended_action": "MAINTAIN"},
    "Plumbing": {"category_tier": 2, "avg_job_value": 350, "monthly_potential": 1500, "recommended_action": "MAINTAIN"},
    "Drywall": {"category_tier": 3, "avg_job_value": 600, "monthly_potential": 1000, "recommended_action": "SELECTIVE"},
    "Carpentry": {"category_tier": 3, "avg_job_value": 800, "monthly_potential": 1000, "recommended_action": "SELECTIVE"},
    "Masonry": {"category_tier": 3, "avg_job_value": 2000, "monthly_potential": 1200, "recommended_action": "SELECTIVE"},
    "Landscaping": {"category_tier": 3, "avg_job_value": 500, "monthly_potential": 1000, "recommended_action": "SELECTIVE"},
    "Painting": {"category_tier": 3, "avg_job_value": 1500, "monthly_potential": 1000, "recommended_action": "SELECTIVE"},
    "Pool cleaning": {"category_tier": 3, "avg_job_value": 150, "monthly_potential": 800, "recommended_action": "SELECTIVE"},
    "Patio covers": {"category_tier": 3, "avg_job_value": 4000, "monthly_potential": 1200, "recommended_action": "SELECTIVE"},
    "Appliance repair": {"category_tier": 4, "avg_job_value": 150, "monthly_potential": 600, "recommended_action": "REDUCE"},
    "Moving": {"category_tier": 4, "avg_job_value": 800, "monthly_potential": 700, "recommended_action": "REDUCE"},
    "Mobile mechanic": {"category_tier": 4, "avg_job_value": 200, "monthly_potential": 500, "recommended_action": "REDUCE"},
    "Towing": {"category_tier": 5, "avg_job_value": 100, "monthly_potential": 400, "recommended_action": "AVOID"},
    "Junk Removal": {"category_tier": 5, "avg_job_value": 150, "monthly_potential": 400, "recommended_action": "AVOID"},
    "Bee rescue": {"category_tier": 5, "avg_job_value": 150, "monthly_potential": 300, "recommended_action": "AVOID"},
}
