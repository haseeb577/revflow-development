"""
Market Discovery Service
Find and evaluate new rank & rent opportunities
Integrates with R&R/RevFlow for competitive analysis
"""

from typing import List, Dict, Optional
import random

# Target markets database (would connect to real data sources in production)
TARGET_MARKETS = {
    "TX": {
        "cities": [
            {"city": "Duncanville", "population": 40000, "growth": 0.02, "competition": "low"},
            {"city": "Lancaster", "population": 39000, "growth": 0.03, "competition": "low"},
            {"city": "Kingsville", "population": 26000, "growth": 0.01, "competition": "very_low"},
            {"city": "Socorro", "population": 35000, "growth": 0.04, "competition": "low"},
            {"city": "La Porte", "population": 36000, "growth": 0.02, "competition": "moderate"},
            {"city": "Harker Heights", "population": 33000, "growth": 0.05, "competition": "low"},
            {"city": "Balch Springs", "population": 27000, "growth": 0.02, "competition": "low"},
            {"city": "Allen", "population": 110000, "growth": 0.06, "competition": "moderate"},
            {"city": "McKinney", "population": 200000, "growth": 0.08, "competition": "high"},
            {"city": "Frisco", "population": 220000, "growth": 0.10, "competition": "high"},
            {"city": "Plano", "population": 290000, "growth": 0.03, "competition": "very_high"},
            {"city": "Cedar Hill", "population": 50000, "growth": 0.02, "competition": "low"},
            {"city": "DeSoto", "population": 55000, "growth": 0.01, "competition": "low"},
            {"city": "Waxahachie", "population": 40000, "growth": 0.04, "competition": "low"},
        ],
        "housing_age": 22,
        "sun_belt": True
    },
    "FL": {
        "cities": [
            {"city": "Key West", "population": 25000, "growth": 0.01, "competition": "moderate"},
            {"city": "Ocoee", "population": 52000, "growth": 0.04, "competition": "low"},
            {"city": "Fontainebleau", "population": 60000, "growth": 0.02, "competition": "moderate"},
            {"city": "Boyton Beach", "population": 80000, "growth": 0.03, "competition": "moderate"},
            {"city": "Palm Bay", "population": 120000, "growth": 0.05, "competition": "low"},
            {"city": "Melbourne", "population": 85000, "growth": 0.03, "competition": "moderate"},
            {"city": "Deltona", "population": 95000, "growth": 0.04, "competition": "low"},
            {"city": "Port St. Lucie", "population": 220000, "growth": 0.06, "competition": "moderate"},
            {"city": "Cape Coral", "population": 210000, "growth": 0.07, "competition": "moderate"},
            {"city": "Lehigh Acres", "population": 130000, "growth": 0.05, "competition": "low"},
        ],
        "housing_age": 25,
        "sun_belt": True
    },
    "AZ": {
        "cities": [
            {"city": "El Mirage", "population": 38000, "growth": 0.04, "competition": "low"},
            {"city": "San Tan Valley", "population": 100000, "growth": 0.08, "competition": "low"},
            {"city": "Maricopa", "population": 60000, "growth": 0.06, "competition": "low"},
            {"city": "Buckeye", "population": 90000, "growth": 0.10, "competition": "low"},
            {"city": "Queen Creek", "population": 65000, "growth": 0.09, "competition": "low"},
            {"city": "Florence", "population": 30000, "growth": 0.04, "competition": "very_low"},
            {"city": "Casa Grande", "population": 58000, "growth": 0.05, "competition": "low"},
            {"city": "Apache Junction", "population": 42000, "growth": 0.03, "competition": "low"},
        ],
        "housing_age": 18,
        "sun_belt": True
    },
    "CA": {
        "cities": [
            {"city": "Benicia", "population": 28000, "growth": 0.01, "competition": "moderate"},
            {"city": "Castro Valley", "population": 65000, "growth": 0.01, "competition": "moderate"},
            {"city": "San Lorenzo", "population": 30000, "growth": 0.00, "competition": "moderate"},
            {"city": "Arcadia", "population": 58000, "growth": 0.01, "competition": "high"},
            {"city": "La Puente", "population": 40000, "growth": 0.00, "competition": "moderate"},
            {"city": "Bell Gardens", "population": 42000, "growth": 0.00, "competition": "moderate"},
            {"city": "Lawndale", "population": 33000, "growth": 0.01, "competition": "moderate"},
            {"city": "East Palo Alto", "population": 30000, "growth": 0.02, "competition": "high"},
            {"city": "Banning", "population": 32000, "growth": 0.02, "competition": "low"},
            {"city": "Hanford", "population": 60000, "growth": 0.02, "competition": "low"},
            {"city": "Reedley", "population": 26000, "growth": 0.01, "competition": "very_low"},
            {"city": "Tulare", "population": 68000, "growth": 0.02, "competition": "low"},
            {"city": "Galt", "population": 27000, "growth": 0.03, "competition": "low"},
        ],
        "housing_age": 35,
        "sun_belt": True
    },
    "NC": {
        "cities": [
            {"city": "Apex", "population": 60000, "growth": 0.08, "competition": "moderate"},
            {"city": "Holly Springs", "population": 45000, "growth": 0.10, "competition": "low"},
            {"city": "Wake Forest", "population": 50000, "growth": 0.07, "competition": "moderate"},
            {"city": "Garner", "population": 35000, "growth": 0.04, "competition": "low"},
            {"city": "Clayton", "population": 25000, "growth": 0.06, "competition": "low"},
            {"city": "Mooresville", "population": 48000, "growth": 0.05, "competition": "moderate"},
            {"city": "Indian Trail", "population": 42000, "growth": 0.04, "competition": "low"},
        ],
        "housing_age": 20,
        "sun_belt": True
    },
    "GA": {
        "cities": [
            {"city": "Alpharetta", "population": 68000, "growth": 0.04, "competition": "high"},
            {"city": "Johns Creek", "population": 85000, "growth": 0.03, "competition": "moderate"},
            {"city": "Peachtree City", "population": 38000, "growth": 0.02, "competition": "moderate"},
            {"city": "Newnan", "population": 45000, "growth": 0.05, "competition": "low"},
            {"city": "Douglasville", "population": 35000, "growth": 0.04, "competition": "low"},
            {"city": "Kennesaw", "population": 35000, "growth": 0.03, "competition": "moderate"},
            {"city": "Woodstock", "population": 35000, "growth": 0.05, "competition": "low"},
        ],
        "housing_age": 22,
        "sun_belt": True
    }
}

CATEGORY_PRIORITY = [
    {"category": "Concrete", "priority": 1, "reason": "High job value, proven performer"},
    {"category": "Roofing", "priority": 1, "reason": "Highest monthly potential, emergency nature"},
    {"category": "Water Damage", "priority": 1, "reason": "Emergency service, insurance-paid"},
    {"category": "Electric", "priority": 2, "reason": "Year-round demand, strong renter pool"},
    {"category": "Fence", "priority": 2, "reason": "Good job value, low competition"},
    {"category": "Tree Care", "priority": 2, "reason": "Storm-driven demand, repeat business"},
    {"category": "Plumbing", "priority": 2, "reason": "Emergency nature, but high competition"},
    {"category": "Drywall", "priority": 3, "reason": "Lower urgency, selective markets only"},
    {"category": "Carpentry", "priority": 3, "reason": "Lower urgency, selective markets only"},
    {"category": "Masonry", "priority": 3, "reason": "High job value but seasonal"},
]


class MarketDiscoveryService:
    def __init__(self):
        self.markets = TARGET_MARKETS
        self.categories = CATEGORY_PRIORITY
    
    def search_markets(self, request: Dict) -> List[Dict]:
        """
        Search for market opportunities based on criteria.
        Integrates with R&R for competitive analysis.
        """
        results = []
        
        categories = request.get("categories", [c["category"] for c in self.categories[:6]])
        states = request.get("states", list(self.markets.keys()))
        min_pop = request.get("min_population", 25000)
        max_pop = request.get("max_population", 250000)
        max_competition = request.get("max_competition", "moderate")
        
        competition_levels = {"very_low": 1, "low": 2, "moderate": 3, "high": 4, "very_high": 5}
        max_comp_level = competition_levels.get(max_competition, 3)
        
        for state, state_data in self.markets.items():
            if state not in states:
                continue
            
            for city_data in state_data["cities"]:
                if city_data["population"] < min_pop or city_data["population"] > max_pop:
                    continue
                
                city_comp_level = competition_levels.get(city_data["competition"], 3)
                if city_comp_level > max_comp_level:
                    continue
                
                for category in categories:
                    opportunity = self._evaluate_market_opportunity(
                        category, city_data["city"], state, city_data, state_data
                    )
                    if opportunity["score"] >= 3.5:
                        results.append(opportunity)
        
        # Sort by score
        results = sorted(results, key=lambda x: x["score"], reverse=True)
        
        return results[:50]  # Return top 50 opportunities
    
    def _evaluate_market_opportunity(self, category: str, city: str, 
                                     state: str, city_data: Dict, 
                                     state_data: Dict) -> Dict:
        """Evaluate a specific market opportunity"""
        
        # Base score from category priority
        cat_info = next((c for c in self.categories if c["category"] == category), None)
        cat_priority = cat_info["priority"] if cat_info else 3
        category_score = 5 - (cat_priority - 1) * 1.5
        
        # Competition score (inverse)
        comp_levels = {"very_low": 5, "low": 4, "moderate": 3, "high": 2, "very_high": 1}
        competition_score = comp_levels.get(city_data["competition"], 3)
        
        # Growth score
        growth_score = min(5, city_data["growth"] * 50 + 2)
        
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
        
        # Sun Belt bonus
        sun_belt_bonus = 0.3 if state_data.get("sun_belt", False) else 0
        
        # Calculate weighted score
        score = (
            category_score * 0.30 +
            competition_score * 0.25 +
            growth_score * 0.20 +
            pop_score * 0.25 +
            sun_belt_bonus
        )
        
        # Determine tier
        if score >= 3.7:
            tier = "high_opportunity"
            recommendation = "ACQUIRE"
        elif score >= 3.2:
            tier = "moderate_opportunity"
            recommendation = "EVALUATE"
        else:
            tier = "low_opportunity"
            recommendation = "SKIP"
        
        return {
            "category": category,
            "city": city,
            "state": state,
            "score": round(score, 2),
            "tier": tier,
            "recommendation": recommendation,
            "population": pop,
            "growth_rate": city_data["growth"],
            "competition_level": city_data["competition"],
            "category_priority": cat_priority,
            "scoring_breakdown": {
                "category_score": round(category_score, 2),
                "competition_score": round(competition_score, 2),
                "growth_score": round(growth_score, 2),
                "population_score": round(pop_score, 2),
                "sun_belt_bonus": round(sun_belt_bonus, 2)
            },
            "next_steps": self._get_next_steps(tier, category),
            "estimated_potential": self._estimate_potential(category)
        }
    
    def _get_next_steps(self, tier: str, category: str) -> List[str]:
        """Get recommended next steps for opportunity"""
        if tier == "high_opportunity":
            return [
                f"Run R&R competitive analysis for {category} in this market",
                "Identify top 5 local competitors",
                "Check Local Pack for review counts and ratings",
                "Begin domain acquisition research",
                "Prepare contractor outreach list"
            ]
        elif tier == "moderate_opportunity":
            return [
                "Conduct deeper market research",
                "Analyze SERP weakness potential",
                "Verify renter willingness in area",
                "Compare against other opportunities"
            ]
        else:
            return [
                "Low priority - focus on higher-scoring opportunities",
                "Revisit if other markets don't pan out"
            ]
    
    def _estimate_potential(self, category: str) -> Dict:
        """Estimate monthly potential for category"""
        potentials = {
            "Concrete": {"monthly": 2000, "annual": 24000},
            "Roofing": {"monthly": 2500, "annual": 30000},
            "Water Damage": {"monthly": 2000, "annual": 24000},
            "Electric": {"monthly": 1500, "annual": 18000},
            "Fence": {"monthly": 1500, "annual": 18000},
            "Tree Care": {"monthly": 1200, "annual": 14400},
            "Plumbing": {"monthly": 1500, "annual": 18000},
            "Drywall": {"monthly": 1000, "annual": 12000},
            "Carpentry": {"monthly": 1000, "annual": 12000},
            "Masonry": {"monthly": 1200, "annual": 14400},
        }
        return potentials.get(category, {"monthly": 800, "annual": 9600})
    
    def get_category_recommendations(self) -> Dict:
        """Get category recommendations based on portfolio analysis"""
        return {
            "tier_1_priority": [
                {
                    "category": "Concrete",
                    "reason": "Highest average score in portfolio (4.03), proven renter demand",
                    "current_sites": 7,
                    "recommendation": "EXPAND - add 3-5 more sites"
                },
                {
                    "category": "Roofing",
                    "reason": "Highest monthly potential ($2,500), emergency nature",
                    "current_sites": 2,
                    "recommendation": "EXPAND - significantly underweight"
                },
                {
                    "category": "Water Damage",
                    "reason": "Emergency service, insurance coverage, high close rate",
                    "current_sites": 2,
                    "recommendation": "EXPAND - high opportunity"
                }
            ],
            "tier_2_maintain": [
                {
                    "category": "Electric",
                    "reason": "Year-round demand, strong renter pool",
                    "current_sites": 2,
                    "recommendation": "MAINTAIN - good balance"
                },
                {
                    "category": "Fence",
                    "reason": "Good job value, low competition",
                    "current_sites": 3,
                    "recommendation": "MAINTAIN - well positioned"
                },
                {
                    "category": "Tree Care",
                    "reason": "Storm-driven demand, repeat business",
                    "current_sites": 3,
                    "recommendation": "MAINTAIN - solid performer"
                }
            ],
            "avoid": [
                {
                    "category": "Towing",
                    "reason": "Very low job value ($200), heavily regulated",
                    "current_sites": 2,
                    "recommendation": "EXIT - sunset existing sites"
                },
                {
                    "category": "Mobile mechanic",
                    "reason": "Fragmented renter pool, low density",
                    "current_sites": 3,
                    "recommendation": "EXIT - sunset existing sites"
                },
                {
                    "category": "Bee rescue",
                    "reason": "Too niche, minimal renter pool",
                    "current_sites": 1,
                    "recommendation": "EXIT - sunset immediately"
                }
            ]
        }
    
    def get_location_recommendations(self, category: str = None, 
                                     state: str = None,
                                     min_population: int = 50000,
                                     max_population: int = 250000) -> List[Dict]:
        """Get recommended locations for expansion"""
        results = []
        
        states_to_check = [state] if state else list(self.markets.keys())
        categories_to_check = [category] if category else [c["category"] for c in self.categories[:3]]
        
        for st in states_to_check:
            if st not in self.markets:
                continue
            
            state_data = self.markets[st]
            for city_data in state_data["cities"]:
                if city_data["population"] < min_population or city_data["population"] > max_population:
                    continue
                
                # Check competition level
                if city_data["competition"] in ["high", "very_high"]:
                    continue
                
                for cat in categories_to_check:
                    opp = self._evaluate_market_opportunity(cat, city_data["city"], st, city_data, state_data)
                    if opp["score"] >= 3.5:
                        results.append(opp)
        
        return sorted(results, key=lambda x: x["score"], reverse=True)[:20]
    
    def evaluate_opportunity(self, category: str, city: str, state: str) -> Dict:
        """
        Evaluate a specific market opportunity.
        Would pull data from R&R/RevFlow for competitive analysis.
        """
        # Find city data
        city_data = None
        state_data = None
        
        if state in self.markets:
            state_data = self.markets[state]
            for c in state_data["cities"]:
                if c["city"].lower() == city.lower():
                    city_data = c
                    break
        
        if not city_data:
            # Create estimated data for unknown city
            city_data = {
                "city": city,
                "population": 75000,
                "growth": 0.03,
                "competition": "moderate"
            }
            state_data = {"sun_belt": state in ["TX", "FL", "AZ", "NC", "GA"], "housing_age": 20}
        
        opportunity = self._evaluate_market_opportunity(category, city, state, city_data, state_data)
        
        # Add integration notes
        opportunity["integration"] = {
            "rr_analysis": "Use R&R app to run competitive analysis",
            "revflow_tracking": "Set up RevFlow lead tracking after site launch",
            "data_sources": ["DataForSEO for keywords", "Census for demographics", "Google Maps for GBP data"]
        }
        
        return opportunity
    
    def get_hotspots(self, category: str = None, limit: int = 20) -> List[Dict]:
        """Get top market hotspots based on opportunity score"""
        all_opportunities = []
        
        categories = [category] if category else [c["category"] for c in self.categories[:6]]
        
        for state, state_data in self.markets.items():
            for city_data in state_data["cities"]:
                for cat in categories:
                    opp = self._evaluate_market_opportunity(
                        cat, city_data["city"], state, city_data, state_data
                    )
                    if opp["score"] >= 3.5:
                        all_opportunities.append(opp)
        
        return sorted(all_opportunities, key=lambda x: x["score"], reverse=True)[:limit]
