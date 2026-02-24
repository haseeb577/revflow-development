"""
╔══════════════════════════════════════════════════════════════════════════════╗
║          SERP ANALYSIS ENGINE - NICHE FINDER PRO STYLE                       ║
║          Market Weakness Detection & Opportunity Scoring                      ║
╚══════════════════════════════════════════════════════════════════════════════╝

Inspired by Niche Finder Pro's approach to identifying rankable markets:
- Dedicated site count analysis
- Map Pack strength evaluation  
- "No Website" opportunity detection
- Referring domain thresholds
- Review count analysis
- Location match scoring
"""

from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import random
import uuid

# =============================================================================
# CONFIGURATION THRESHOLDS (Niche Finder Pro defaults)
# =============================================================================

class SERPThresholds:
    """Configurable thresholds based on Niche Finder Pro methodology"""
    REFERRING_DOMAIN_STRONG = 20  # >20 RD = strong competitor
    REFERRING_DOMAIN_MODERATE = 10  # 10-20 RD = moderate
    REFERRING_DOMAIN_WEAK = 5  # <5 RD = weak, beatable
    
    REVIEW_COUNT_HARD = 30  # >30 reviews = harder to beat in map pack
    REVIEW_COUNT_MODERATE = 15  # 15-30 = moderate difficulty
    REVIEW_COUNT_EASY = 5  # <5 = easy opportunity
    
    DEDICATED_SITES_SATURATED = 15  # >15 dedicated = saturated market
    DEDICATED_SITES_MODERATE = 8  # 8-15 = moderate competition
    DEDICATED_SITES_OPPORTUNITY = 4  # <4 = good opportunity
    
    DOMAIN_RATING_STRONG = 40  # DR >40 = strong domain
    DOMAIN_RATING_MODERATE = 20  # DR 20-40 = moderate
    DOMAIN_RATING_WEAK = 10  # DR <10 = weak, beatable

# =============================================================================
# DATA CLASSES
# =============================================================================

class CompetitorType(str, Enum):
    DEDICATED_SITE = "dedicated"  # Niche-specific site (e.g., dallasplumber.com)
    AGGREGATOR = "aggregator"  # Yelp, Angi, HomeAdvisor, etc.
    DIRECTORY = "directory"  # Yellow Pages, BBB, etc.
    FRANCHISE = "franchise"  # National franchise site
    GENERAL_CONTRACTOR = "general"  # Multi-service contractor
    GMB_ONLY = "gmb_only"  # Has GMB but no website

@dataclass
class SERPCompetitor:
    """Individual SERP competitor analysis"""
    position: int
    name: str
    url: Optional[str]
    competitor_type: CompetitorType
    
    # Domain metrics (would come from Ahrefs/DataForSEO in production)
    domain_rating: int = 0
    referring_domains: int = 0
    organic_keywords: int = 0
    
    # Local signals
    has_location_match: bool = False  # City name in domain/title
    has_gmb: bool = True
    
    # Content signals
    word_count: int = 0
    has_schema: bool = False
    page_speed_score: int = 50
    
    # Weakness indicators
    is_weak_competitor: bool = False
    weakness_reasons: List[str] = field(default_factory=list)
    
    def calculate_weakness(self) -> None:
        """Determine if this is a beatable competitor"""
        self.weakness_reasons = []
        
        if self.url is None:
            self.weakness_reasons.append("NO_WEBSITE")
            self.is_weak_competitor = True
            return
            
        if self.referring_domains < SERPThresholds.REFERRING_DOMAIN_WEAK:
            self.weakness_reasons.append(f"LOW_RD ({self.referring_domains})")
        
        if self.domain_rating < SERPThresholds.DOMAIN_RATING_WEAK:
            self.weakness_reasons.append(f"LOW_DR ({self.domain_rating})")
        
        if not self.has_location_match:
            self.weakness_reasons.append("NO_LOCATION_MATCH")
        
        if self.word_count < 500:
            self.weakness_reasons.append(f"THIN_CONTENT ({self.word_count} words)")
        
        if not self.has_schema:
            self.weakness_reasons.append("NO_SCHEMA")
        
        if self.page_speed_score < 40:
            self.weakness_reasons.append(f"SLOW_SITE ({self.page_speed_score})")
        
        # Weak if 2+ weakness factors
        self.is_weak_competitor = len(self.weakness_reasons) >= 2

@dataclass
class MapPackListing:
    """Google Map Pack / Local Pack listing"""
    position: int
    business_name: str
    has_website: bool
    website_url: Optional[str]
    
    # GMB metrics
    review_count: int = 0
    rating: float = 0.0
    has_location_match: bool = False
    
    # Business signals
    years_in_business: Optional[int] = None
    is_verified: bool = True
    has_photos: int = 0
    response_rate: Optional[float] = None
    
    # Opportunity indicators
    is_opportunity: bool = False
    opportunity_reasons: List[str] = field(default_factory=list)
    
    def calculate_opportunity(self) -> None:
        """Determine if this represents an opportunity"""
        self.opportunity_reasons = []
        
        if not self.has_website:
            self.opportunity_reasons.append("NO_WEBSITE - Direct outreach target")
            self.is_opportunity = True
        
        if self.review_count < SERPThresholds.REVIEW_COUNT_EASY:
            self.opportunity_reasons.append(f"LOW_REVIEWS ({self.review_count})")
        
        if self.rating < 4.0 and self.review_count > 0:
            self.opportunity_reasons.append(f"LOW_RATING ({self.rating})")
        
        if not self.has_location_match:
            self.opportunity_reasons.append("WEAK_LOCAL_SIGNAL")
        
        if self.has_photos < 5:
            self.opportunity_reasons.append("POOR_GMB_OPTIMIZATION")
        
        self.is_opportunity = len(self.opportunity_reasons) >= 2

@dataclass 
class SERPAnalysisResult:
    """Complete SERP analysis for a niche + location"""
    id: str
    category: str
    city: str
    state: str
    search_query: str
    analyzed_at: datetime
    
    # Organic SERP analysis
    organic_results: List[SERPCompetitor] = field(default_factory=list)
    total_results_analyzed: int = 10
    
    # Map Pack analysis
    map_pack_results: List[MapPackListing] = field(default_factory=list)
    
    # Aggregate metrics
    dedicated_site_count: int = 0
    aggregator_count: int = 0
    no_website_count: int = 0
    weak_competitor_count: int = 0
    
    # Map Pack metrics
    avg_map_pack_reviews: float = 0.0
    map_pack_no_website_count: int = 0
    
    # Opportunity scoring (1-5 scale, 5 = best opportunity)
    serp_opportunity_score: float = 0.0
    map_pack_opportunity_score: float = 0.0
    overall_opportunity_score: float = 0.0
    
    # Recommendation
    recommendation: str = ""
    difficulty_rating: str = ""  # Easy, Moderate, Hard, Very Hard
    estimated_time_to_rank: int = 0  # months
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "category": self.category,
            "city": self.city,
            "state": self.state,
            "search_query": self.search_query,
            "analyzed_at": self.analyzed_at.isoformat(),
            "dedicated_site_count": self.dedicated_site_count,
            "aggregator_count": self.aggregator_count,
            "no_website_count": self.no_website_count,
            "weak_competitor_count": self.weak_competitor_count,
            "avg_map_pack_reviews": self.avg_map_pack_reviews,
            "map_pack_no_website_count": self.map_pack_no_website_count,
            "serp_opportunity_score": self.serp_opportunity_score,
            "map_pack_opportunity_score": self.map_pack_opportunity_score,
            "overall_opportunity_score": self.overall_opportunity_score,
            "recommendation": self.recommendation,
            "difficulty_rating": self.difficulty_rating,
            "estimated_time_to_rank": self.estimated_time_to_rank,
            "organic_results": [
                {
                    "position": r.position,
                    "name": r.name,
                    "url": r.url,
                    "type": r.competitor_type.value,
                    "domain_rating": r.domain_rating,
                    "referring_domains": r.referring_domains,
                    "is_weak": r.is_weak_competitor,
                    "weaknesses": r.weakness_reasons
                }
                for r in self.organic_results
            ],
            "map_pack_results": [
                {
                    "position": m.position,
                    "business_name": m.business_name,
                    "has_website": m.has_website,
                    "review_count": m.review_count,
                    "rating": m.rating,
                    "is_opportunity": m.is_opportunity,
                    "opportunity_reasons": m.opportunity_reasons
                }
                for m in self.map_pack_results
            ]
        }

# =============================================================================
# SERP ANALYZER SERVICE
# =============================================================================

class SERPAnalyzer:
    """
    SERP Analysis Engine - Niche Finder Pro Style
    
    In production, this would integrate with:
    - DataForSEO SERP API
    - Ahrefs/SEMrush for domain metrics
    - Google Places API for Map Pack data
    """
    
    def __init__(self):
        self.thresholds = SERPThresholds()
        
        # Aggregator domains to identify
        self.aggregator_domains = [
            'yelp.com', 'angi.com', 'homeadvisor.com', 'thumbtack.com',
            'houzz.com', 'porch.com', 'bark.com', 'networx.com',
            'facebook.com', 'nextdoor.com', 'bbb.org', 'yellowpages.com',
            'superpages.com', 'manta.com', 'buildzoom.com'
        ]
        
        # Franchise indicators
        self.franchise_indicators = [
            'mr-', 'mister', 'brothers', 'pros', '1800', '800',
            'servicemaster', 'servpro', 'stanley', 'roto-rooter',
            'benjamin-franklin', 'one-hour', 'mr-electric'
        ]
    
    def analyze_serp(self, category: str, city: str, state: str) -> SERPAnalysisResult:
        """
        Perform complete SERP analysis for a niche + location
        
        In production: Would call DataForSEO/Ahrefs APIs
        For now: Generates realistic mock data based on category difficulty
        """
        search_query = f"{category.lower()} {city.lower()} {state.upper()}"
        
        result = SERPAnalysisResult(
            id=str(uuid.uuid4()),
            category=category,
            city=city,
            state=state,
            search_query=search_query,
            analyzed_at=datetime.utcnow()
        )
        
        # Generate organic SERP results
        result.organic_results = self._generate_organic_results(category, city, state)
        
        # Generate Map Pack results
        result.map_pack_results = self._generate_map_pack_results(category, city)
        
        # Calculate aggregate metrics
        self._calculate_metrics(result)
        
        # Score the opportunity
        self._score_opportunity(result)
        
        # Generate recommendation
        self._generate_recommendation(result)
        
        return result
    
    def _generate_organic_results(self, category: str, city: str, state: str) -> List[SERPCompetitor]:
        """Generate realistic SERP competitor data"""
        results = []
        
        # Category difficulty affects competitor strength
        category_difficulty = self._get_category_difficulty(category)
        
        for position in range(1, 11):
            # Determine competitor type (weighted by category)
            comp_type = self._determine_competitor_type(position, category_difficulty)
            
            # Generate competitor based on type
            competitor = self._create_competitor(position, comp_type, category, city, state, category_difficulty)
            competitor.calculate_weakness()
            results.append(competitor)
        
        return results
    
    def _generate_map_pack_results(self, category: str, city: str) -> List[MapPackListing]:
        """Generate realistic Map Pack / Local 3-Pack data"""
        results = []
        category_difficulty = self._get_category_difficulty(category)
        
        # Generate 3-7 map pack results (Google shows 3, but we analyze more)
        num_results = random.randint(3, 7)
        
        for position in range(1, num_results + 1):
            # Higher difficulty = more reviews, better optimization
            base_reviews = int(30 * category_difficulty)
            review_variance = random.randint(-20, 40)
            
            has_website = random.random() > (0.15 if category_difficulty > 0.6 else 0.25)
            
            listing = MapPackListing(
                position=position,
                business_name=f"{city} {category} {'Pro' if position <= 2 else 'Service'} #{position}",
                has_website=has_website,
                website_url=f"https://{city.lower()}{category.lower().replace(' ', '')}.com" if has_website else None,
                review_count=max(0, base_reviews + review_variance),
                rating=round(random.uniform(3.8, 5.0), 1),
                has_location_match=random.random() > 0.3,
                has_photos=random.randint(0, 50),
                is_verified=random.random() > 0.1
            )
            listing.calculate_opportunity()
            results.append(listing)
        
        return results
    
    def _get_category_difficulty(self, category: str) -> float:
        """Return difficulty multiplier (0.3 = easy, 1.0 = very hard)"""
        difficulty_map = {
            # Tier 1 - High value, moderate competition
            "Concrete": 0.5,
            "Roofing": 0.7,
            "Water Damage": 0.6,
            
            # Tier 2 - Good value, varies
            "Electric": 0.7,
            "Plumbing": 0.8,
            "Fence": 0.4,
            "Tree Care": 0.4,
            
            # Tier 3 - Moderate
            "Drywall": 0.35,
            "Carpentry": 0.35,
            "Masonry": 0.4,
            "Landscaping": 0.5,
            "Painting": 0.5,
            
            # Tier 4-5 - Saturated or low value
            "Towing": 0.8,
            "Law": 0.95,
            "Moving": 0.6,
            "Appliance repair": 0.5,
        }
        return difficulty_map.get(category, 0.5)
    
    def _determine_competitor_type(self, position: int, difficulty: float) -> CompetitorType:
        """Determine what type of competitor occupies this position"""
        rand = random.random()
        
        # Higher positions more likely to be dedicated/strong
        position_factor = (11 - position) / 10  # 1.0 for pos 1, 0.1 for pos 10
        
        # Aggregators typically appear in positions 3-8
        if 3 <= position <= 8 and rand < 0.4:
            return CompetitorType.AGGREGATOR
        
        # Dedicated sites more common in competitive niches
        if rand < (0.5 * difficulty * position_factor):
            return CompetitorType.DEDICATED_SITE
        
        # GMB only opportunities
        if rand > 0.85:
            return CompetitorType.GMB_ONLY
        
        # General contractors
        if rand > 0.7:
            return CompetitorType.GENERAL_CONTRACTOR
        
        return CompetitorType.DIRECTORY
    
    def _create_competitor(self, position: int, comp_type: CompetitorType, 
                          category: str, city: str, state: str, difficulty: float) -> SERPCompetitor:
        """Create a realistic competitor based on type"""
        
        position_strength = (11 - position) / 10  # Higher positions = stronger
        
        if comp_type == CompetitorType.GMB_ONLY:
            return SERPCompetitor(
                position=position,
                name=f"{city} {category} Services",
                url=None,
                competitor_type=comp_type,
                domain_rating=0,
                referring_domains=0,
                has_location_match=False,
                has_gmb=True
            )
        
        if comp_type == CompetitorType.AGGREGATOR:
            agg = random.choice(['Yelp', 'Angi', 'HomeAdvisor', 'Thumbtack', 'BBB'])
            return SERPCompetitor(
                position=position,
                name=f"{category} in {city} - {agg}",
                url=f"https://www.{agg.lower()}.com/{category.lower()}/{city.lower()}-{state.lower()}",
                competitor_type=comp_type,
                domain_rating=random.randint(70, 95),
                referring_domains=random.randint(50000, 500000),
                has_location_match=True,
                has_gmb=False,
                word_count=random.randint(200, 500),
                has_schema=True
            )
        
        if comp_type == CompetitorType.DEDICATED_SITE:
            # Dedicated sites vary in strength
            strength = difficulty * position_strength
            return SERPCompetitor(
                position=position,
                name=f"{city} {category} Pros",
                url=f"https://{city.lower()}{category.lower().replace(' ', '')}.com",
                competitor_type=comp_type,
                domain_rating=int(random.uniform(10, 50) * strength),
                referring_domains=int(random.uniform(5, 100) * strength),
                has_location_match=True,
                has_gmb=True,
                word_count=int(random.uniform(500, 2500) * strength),
                has_schema=random.random() < (0.3 + 0.4 * strength),
                page_speed_score=int(random.uniform(30, 90))
            )
        
        # Directory or general contractor
        return SERPCompetitor(
            position=position,
            name=f"{city} Home Services" if comp_type == CompetitorType.GENERAL_CONTRACTOR else f"{category} - Directory",
            url=f"https://example-{comp_type.value}.com/{city.lower()}",
            competitor_type=comp_type,
            domain_rating=random.randint(20, 60),
            referring_domains=random.randint(100, 5000),
            has_location_match=random.random() > 0.5,
            has_gmb=comp_type == CompetitorType.GENERAL_CONTRACTOR,
            word_count=random.randint(200, 1000),
            has_schema=random.random() > 0.6
        )
    
    def _calculate_metrics(self, result: SERPAnalysisResult) -> None:
        """Calculate aggregate metrics from individual results"""
        
        # Organic metrics
        result.dedicated_site_count = sum(
            1 for r in result.organic_results 
            if r.competitor_type == CompetitorType.DEDICATED_SITE
        )
        result.aggregator_count = sum(
            1 for r in result.organic_results 
            if r.competitor_type == CompetitorType.AGGREGATOR
        )
        result.no_website_count = sum(
            1 for r in result.organic_results 
            if r.url is None
        )
        result.weak_competitor_count = sum(
            1 for r in result.organic_results 
            if r.is_weak_competitor
        )
        
        # Map Pack metrics
        if result.map_pack_results:
            result.avg_map_pack_reviews = sum(
                m.review_count for m in result.map_pack_results
            ) / len(result.map_pack_results)
            
            result.map_pack_no_website_count = sum(
                1 for m in result.map_pack_results 
                if not m.has_website
            )
    
    def _score_opportunity(self, result: SERPAnalysisResult) -> None:
        """Calculate opportunity scores (1-5 scale, higher = better opportunity)"""
        
        # SERP Opportunity Score
        serp_score = 3.0  # Start neutral
        
        # Fewer dedicated sites = better
        if result.dedicated_site_count <= SERPThresholds.DEDICATED_SITES_OPPORTUNITY:
            serp_score += 1.0
        elif result.dedicated_site_count >= SERPThresholds.DEDICATED_SITES_SATURATED:
            serp_score -= 1.0
        
        # More weak competitors = better
        if result.weak_competitor_count >= 5:
            serp_score += 0.75
        elif result.weak_competitor_count >= 3:
            serp_score += 0.5
        
        # More aggregators = better (easier to beat with dedicated site)
        if result.aggregator_count >= 4:
            serp_score += 0.5
        
        # No website opportunities
        if result.no_website_count >= 2:
            serp_score += 0.25
        
        result.serp_opportunity_score = max(1.0, min(5.0, serp_score))
        
        # Map Pack Opportunity Score
        map_score = 3.0
        
        # Lower average reviews = easier
        if result.avg_map_pack_reviews < SERPThresholds.REVIEW_COUNT_EASY:
            map_score += 1.0
        elif result.avg_map_pack_reviews > SERPThresholds.REVIEW_COUNT_HARD:
            map_score -= 1.0
        
        # No website listings = outreach opportunities
        if result.map_pack_no_website_count >= 2:
            map_score += 0.5
        
        result.map_pack_opportunity_score = max(1.0, min(5.0, map_score))
        
        # Overall score (weighted average)
        result.overall_opportunity_score = round(
            (result.serp_opportunity_score * 0.6) + 
            (result.map_pack_opportunity_score * 0.4),
            2
        )
    
    def _generate_recommendation(self, result: SERPAnalysisResult) -> None:
        """Generate actionable recommendation based on analysis"""
        score = result.overall_opportunity_score
        
        if score >= 4.0:
            result.difficulty_rating = "Easy"
            result.estimated_time_to_rank = 3
            result.recommendation = (
                f"STRONG OPPORTUNITY: Only {result.dedicated_site_count} dedicated sites, "
                f"{result.weak_competitor_count} weak competitors. "
                f"Low map pack competition (avg {result.avg_map_pack_reviews:.0f} reviews). "
                f"Recommend immediate acquisition."
            )
        elif score >= 3.5:
            result.difficulty_rating = "Moderate"
            result.estimated_time_to_rank = 5
            result.recommendation = (
                f"GOOD OPPORTUNITY: {result.dedicated_site_count} dedicated sites present, "
                f"but {result.weak_competitor_count} are weak/beatable. "
                f"Map pack has {result.avg_map_pack_reviews:.0f} avg reviews. "
                f"Recommend further due diligence."
            )
        elif score >= 3.0:
            result.difficulty_rating = "Hard"
            result.estimated_time_to_rank = 8
            result.recommendation = (
                f"MODERATE OPPORTUNITY: {result.dedicated_site_count} dedicated sites with "
                f"competitive map pack ({result.avg_map_pack_reviews:.0f} avg reviews). "
                f"Consider only if high-value category. Requires significant investment."
            )
        else:
            result.difficulty_rating = "Very Hard"
            result.estimated_time_to_rank = 12
            result.recommendation = (
                f"SATURATED MARKET: {result.dedicated_site_count} dedicated sites, "
                f"strong map pack ({result.avg_map_pack_reviews:.0f} avg reviews). "
                f"Recommend exploring alternative locations or categories."
            )
    
    def find_no_website_opportunities(self, category: str, cities: List[Dict], 
                                      state: str) -> List[Dict]:
        """
        Scan multiple cities for "no website" opportunities
        (Niche Finder Pro's key feature)
        """
        opportunities = []
        
        for city_data in cities:
            city = city_data.get("city", "")
            analysis = self.analyze_serp(category, city, state)
            
            # Find all no-website opportunities
            no_web_organic = [
                r for r in analysis.organic_results 
                if r.url is None and r.position <= 7
            ]
            no_web_map = [
                m for m in analysis.map_pack_results 
                if not m.has_website
            ]
            
            if no_web_organic or no_web_map:
                opportunities.append({
                    "city": city,
                    "state": state,
                    "category": category,
                    "overall_score": analysis.overall_opportunity_score,
                    "no_website_organic": len(no_web_organic),
                    "no_website_map_pack": len(no_web_map),
                    "avg_map_reviews": analysis.avg_map_pack_reviews,
                    "dedicated_sites": analysis.dedicated_site_count,
                    "difficulty": analysis.difficulty_rating,
                    "recommendation": "NO WEBSITE FOUND - Call them!" if no_web_map else "Weak SERP - Good target"
                })
        
        return sorted(opportunities, key=lambda x: x["overall_score"], reverse=True)

# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

serp_analyzer = SERPAnalyzer()
