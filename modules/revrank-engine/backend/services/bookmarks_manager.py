"""
╔══════════════════════════════════════════════════════════════════════════════╗
║          FAVORITES & BOOKMARKS SYSTEM                                        ║
║          Niche Finder Pro Style Opportunity Management                       ║
╚══════════════════════════════════════════════════════════════════════════════╝

Key features from Niche Finder Pro:
- Favorite/bookmark opportunities for later review
- Custom tagging system (e.g., "no website", "high priority", "VA review")
- Star rating for quick prioritization
- Notes for each saved opportunity
- Export to CSV/spreadsheet
- Filter and search saved opportunities
- VA workflow support (assign, review, approve)
"""

from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json
import csv
import io
import uuid

# =============================================================================
# ENUMS & TYPES
# =============================================================================

class BookmarkStatus(str, Enum):
    NEW = "new"
    REVIEWING = "reviewing"
    VA_ASSIGNED = "va_assigned"
    APPROVED = "approved"
    REJECTED = "rejected"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"

class BookmarkType(str, Enum):
    MARKET_OPPORTUNITY = "market_opportunity"
    SERP_RESULT = "serp_result"
    MAP_PACK_LISTING = "map_pack_listing"
    COMPETITOR = "competitor"
    POTENTIAL_RENTER = "potential_renter"

# =============================================================================
# PREDEFINED TAGS (Niche Finder Pro style)
# =============================================================================

PRESET_TAGS = [
    # Opportunity indicators
    {"id": "no_website", "label": "No Website", "color": "#22c55e", "icon": "🌐"},
    {"id": "low_reviews", "label": "Low Reviews", "color": "#3b82f6", "icon": "⭐"},
    {"id": "weak_competition", "label": "Weak Competition", "color": "#10b981", "icon": "💪"},
    {"id": "high_value", "label": "High Value", "color": "#f59e0b", "icon": "💰"},
    
    # Priority levels
    {"id": "high_priority", "label": "High Priority", "color": "#ef4444", "icon": "🔥"},
    {"id": "medium_priority", "label": "Medium Priority", "color": "#f97316", "icon": "⚡"},
    {"id": "low_priority", "label": "Low Priority", "color": "#6b7280", "icon": "📌"},
    
    # Workflow status
    {"id": "needs_research", "label": "Needs Research", "color": "#8b5cf6", "icon": "🔍"},
    {"id": "va_review", "label": "VA Review", "color": "#06b6d4", "icon": "👤"},
    {"id": "call_them", "label": "Call Them!", "color": "#ec4899", "icon": "📞"},
    {"id": "ready_to_build", "label": "Ready to Build", "color": "#22c55e", "icon": "🚀"},
    
    # Categories
    {"id": "tier_1", "label": "Tier 1 Category", "color": "#22c55e", "icon": "1️⃣"},
    {"id": "tier_2", "label": "Tier 2 Category", "color": "#3b82f6", "icon": "2️⃣"},
    {"id": "sun_belt", "label": "Sun Belt", "color": "#f59e0b", "icon": "☀️"},
]

# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class Bookmark:
    """Individual saved opportunity/bookmark"""
    id: str
    type: BookmarkType
    
    # Core data
    category: str
    city: str
    state: str
    
    # Scores
    opportunity_score: float = 0.0
    serp_score: Optional[float] = None
    map_pack_score: Optional[float] = None
    
    # User annotations
    tags: List[str] = field(default_factory=list)
    star_rating: int = 0  # 1-5 stars, 0 = unrated
    notes: str = ""
    
    # SERP details (if applicable)
    dedicated_sites: Optional[int] = None
    weak_competitors: Optional[int] = None
    avg_reviews: Optional[float] = None
    no_website_count: Optional[int] = None
    
    # Map Pack target (if applicable)
    business_name: Optional[str] = None
    business_phone: Optional[str] = None
    has_website: Optional[bool] = None
    
    # Workflow
    status: BookmarkStatus = BookmarkStatus.NEW
    assigned_to: Optional[str] = None
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    created_by: str = "user"
    
    # Search query used
    search_query: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "type": self.type.value,
            "category": self.category,
            "city": self.city,
            "state": self.state,
            "opportunity_score": self.opportunity_score,
            "serp_score": self.serp_score,
            "map_pack_score": self.map_pack_score,
            "tags": self.tags,
            "star_rating": self.star_rating,
            "notes": self.notes,
            "dedicated_sites": self.dedicated_sites,
            "weak_competitors": self.weak_competitors,
            "avg_reviews": self.avg_reviews,
            "no_website_count": self.no_website_count,
            "business_name": self.business_name,
            "business_phone": self.business_phone,
            "has_website": self.has_website,
            "status": self.status if isinstance(self.status, str) else self.status.value,
            "assigned_to": self.assigned_to,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "created_by": self.created_by,
            "search_query": self.search_query,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Bookmark':
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            type=BookmarkType(data.get("type", "market_opportunity")),
            category=data.get("category", ""),
            city=data.get("city", ""),
            state=data.get("state", ""),
            opportunity_score=data.get("opportunity_score", 0.0),
            serp_score=data.get("serp_score"),
            map_pack_score=data.get("map_pack_score"),
            tags=data.get("tags", []),
            star_rating=data.get("star_rating", 0),
            notes=data.get("notes", ""),
            dedicated_sites=data.get("dedicated_sites"),
            weak_competitors=data.get("weak_competitors"),
            avg_reviews=data.get("avg_reviews"),
            no_website_count=data.get("no_website_count"),
            business_name=data.get("business_name"),
            business_phone=data.get("business_phone"),
            has_website=data.get("has_website"),
            status=BookmarkStatus(data.get("status", "new")),
            assigned_to=data.get("assigned_to"),
            created_by=data.get("created_by", "user"),
            search_query=data.get("search_query"),
        )

# =============================================================================
# BOOKMARKS MANAGER
# =============================================================================

class BookmarksManager:
    """
    Manages saved opportunities/bookmarks with full CRUD,
    filtering, tagging, and export capabilities.
    
    In production: Would persist to database (Supabase/PostgreSQL)
    For now: In-memory storage with full functionality
    """
    
    def __init__(self):
        self.bookmarks: Dict[str, Bookmark] = {}
        self.custom_tags: List[Dict] = []
        
        # Initialize with some demo bookmarks
        self._init_demo_data()
    
    def _init_demo_data(self):
        """Initialize with demo bookmarks"""
        demo_bookmarks = [
            {
                "category": "Concrete",
                "city": "Buckeye",
                "state": "AZ",
                "opportunity_score": 4.35,
                "tags": ["high_priority", "tier_1", "sun_belt"],
                "star_rating": 5,
                "notes": "Fastest growing city in AZ. Low competition. Start here!",
                "dedicated_sites": 3,
                "weak_competitors": 5,
                "avg_reviews": 12,
                "no_website_count": 2,
                "status": "approved"
            },
            {
                "category": "Roofing",
                "city": "Cape Coral",
                "state": "FL",
                "opportunity_score": 4.22,
                "tags": ["high_priority", "tier_1", "no_website"],
                "star_rating": 5,
                "notes": "Found 3 roofers without websites in map pack. Call them!",
                "dedicated_sites": 5,
                "avg_reviews": 18,
                "no_website_count": 3,
                "status": "ready_to_build"
            },
            {
                "category": "Water Damage",
                "city": "Palm Bay",
                "state": "FL",
                "opportunity_score": 4.15,
                "tags": ["high_value", "weak_competition"],
                "star_rating": 4,
                "notes": "Insurance jobs = high value. Good opportunity.",
                "dedicated_sites": 4,
                "avg_reviews": 15,
                "status": "reviewing"
            },
            {
                "category": "Electric",
                "city": "Holly Springs",
                "state": "NC",
                "opportunity_score": 3.88,
                "tags": ["va_review", "needs_research"],
                "star_rating": 3,
                "notes": "VA: Please verify licensing requirements for NC",
                "dedicated_sites": 6,
                "avg_reviews": 22,
                "status": "va_assigned",
                "assigned_to": "VA_Maria"
            },
            {
                "category": "Fence",
                "city": "Maricopa",
                "state": "AZ",
                "opportunity_score": 3.82,
                "tags": ["sun_belt", "low_reviews"],
                "star_rating": 4,
                "dedicated_sites": 4,
                "avg_reviews": 8,
                "status": "new"
            },
        ]
        
        for data in demo_bookmarks:
            bookmark = Bookmark(
                id=str(uuid.uuid4()),
                type=BookmarkType.MARKET_OPPORTUNITY,
                **data
            )
            self.bookmarks[bookmark.id] = bookmark
    
    # =========================================================================
    # CRUD OPERATIONS
    # =========================================================================
    
    def create(self, data: Dict) -> Bookmark:
        """Create a new bookmark"""
        bookmark = Bookmark(
            id=str(uuid.uuid4()),
            type=BookmarkType(data.get("type", "market_opportunity")),
            category=data.get("category", ""),
            city=data.get("city", ""),
            state=data.get("state", ""),
            opportunity_score=data.get("opportunity_score", 0.0),
            serp_score=data.get("serp_score"),
            map_pack_score=data.get("map_pack_score"),
            tags=data.get("tags", []),
            star_rating=data.get("star_rating", 0),
            notes=data.get("notes", ""),
            dedicated_sites=data.get("dedicated_sites"),
            weak_competitors=data.get("weak_competitors"),
            avg_reviews=data.get("avg_reviews"),
            no_website_count=data.get("no_website_count"),
            business_name=data.get("business_name"),
            business_phone=data.get("business_phone"),
            has_website=data.get("has_website"),
            search_query=data.get("search_query"),
        )
        self.bookmarks[bookmark.id] = bookmark
        return bookmark
    
    def get(self, bookmark_id: str) -> Optional[Bookmark]:
        """Get a bookmark by ID"""
        return self.bookmarks.get(bookmark_id)
    
    def update(self, bookmark_id: str, updates: Dict) -> Optional[Bookmark]:
        """Update a bookmark"""
        bookmark = self.bookmarks.get(bookmark_id)
        if not bookmark:
            return None
        
        # Update allowed fields
        for field in ['tags', 'star_rating', 'notes', 'status', 'assigned_to']:
            if field in updates:
                setattr(bookmark, field, updates[field])
        
        bookmark.updated_at = datetime.utcnow()
        return bookmark
    
    def delete(self, bookmark_id: str) -> bool:
        """Delete a bookmark"""
        if bookmark_id in self.bookmarks:
            del self.bookmarks[bookmark_id]
            return True
        return False
    
    def list_all(self) -> List[Bookmark]:
        """Get all bookmarks"""
        return list(self.bookmarks.values())
    
    # =========================================================================
    # FILTERING & SEARCH
    # =========================================================================
    
    def filter(
        self,
        tags: Optional[List[str]] = None,
        status: Optional[str] = None,
        category: Optional[str] = None,
        state: Optional[str] = None,
        min_rating: Optional[int] = None,
        min_score: Optional[float] = None,
        assigned_to: Optional[str] = None,
        has_no_website: Optional[bool] = None,
        search_term: Optional[str] = None,
    ) -> List[Bookmark]:
        """Filter bookmarks by various criteria"""
        results = list(self.bookmarks.values())
        
        if tags:
            results = [b for b in results if any(t in b.tags for t in tags)]
        
        if status:
            results = [b for b in results if b.status.value == status]
        
        if category:
            results = [b for b in results if b.category.lower() == category.lower()]
        
        if state:
            results = [b for b in results if b.state.upper() == state.upper()]
        
        if min_rating:
            results = [b for b in results if b.star_rating >= min_rating]
        
        if min_score:
            results = [b for b in results if b.opportunity_score >= min_score]
        
        if assigned_to:
            results = [b for b in results if b.assigned_to == assigned_to]
        
        if has_no_website:
            results = [b for b in results if (b.no_website_count or 0) > 0 or b.has_website == False]
        
        if search_term:
            term = search_term.lower()
            results = [
                b for b in results 
                if term in b.category.lower() 
                or term in b.city.lower() 
                or term in b.notes.lower()
                or term in (b.business_name or "").lower()
            ]
        
        return results
    
    def get_by_tags(self, tags: List[str], match_all: bool = False) -> List[Bookmark]:
        """Get bookmarks by tags"""
        if match_all:
            return [b for b in self.bookmarks.values() if all(t in b.tags for t in tags)]
        else:
            return [b for b in self.bookmarks.values() if any(t in b.tags for t in tags)]
    
    # =========================================================================
    # TAGGING OPERATIONS
    # =========================================================================
    
    def add_tag(self, bookmark_id: str, tag: str) -> Optional[Bookmark]:
        """Add a tag to a bookmark"""
        bookmark = self.bookmarks.get(bookmark_id)
        if bookmark and tag not in bookmark.tags:
            bookmark.tags.append(tag)
            bookmark.updated_at = datetime.utcnow()
        return bookmark
    
    def remove_tag(self, bookmark_id: str, tag: str) -> Optional[Bookmark]:
        """Remove a tag from a bookmark"""
        bookmark = self.bookmarks.get(bookmark_id)
        if bookmark and tag in bookmark.tags:
            bookmark.tags.remove(tag)
            bookmark.updated_at = datetime.utcnow()
        return bookmark
    
    def bulk_add_tag(self, bookmark_ids: List[str], tag: str) -> int:
        """Add a tag to multiple bookmarks"""
        count = 0
        for bid in bookmark_ids:
            if self.add_tag(bid, tag):
                count += 1
        return count
    
    def get_all_tags(self) -> List[Dict]:
        """Get all available tags (preset + custom)"""
        return PRESET_TAGS + self.custom_tags
    
    def create_custom_tag(self, label: str, color: str = "#6b7280", icon: str = "🏷️") -> Dict:
        """Create a custom tag"""
        tag_id = label.lower().replace(" ", "_")
        tag = {"id": tag_id, "label": label, "color": color, "icon": icon, "custom": True}
        self.custom_tags.append(tag)
        return tag
    
    # =========================================================================
    # WORKFLOW / VA SUPPORT
    # =========================================================================
    
    def assign_to_va(self, bookmark_id: str, va_name: str) -> Optional[Bookmark]:
        """Assign a bookmark to a VA for review"""
        bookmark = self.bookmarks.get(bookmark_id)
        if bookmark:
            bookmark.assigned_to = va_name
            bookmark.status = BookmarkStatus.VA_ASSIGNED
            bookmark.updated_at = datetime.utcnow()
        return bookmark
    
    def bulk_assign(self, bookmark_ids: List[str], va_name: str) -> int:
        """Assign multiple bookmarks to a VA"""
        count = 0
        for bid in bookmark_ids:
            if self.assign_to_va(bid, va_name):
                count += 1
        return count
    
    def update_status(self, bookmark_id: str, status: str) -> Optional[Bookmark]:
        """Update bookmark status"""
        bookmark = self.bookmarks.get(bookmark_id)
        if bookmark:
            bookmark.status = BookmarkStatus(status)
            bookmark.updated_at = datetime.utcnow()
        return bookmark
    
    def get_va_queue(self, va_name: str) -> List[Bookmark]:
        """Get all bookmarks assigned to a specific VA"""
        return [b for b in self.bookmarks.values() if b.assigned_to == va_name]
    
    # =========================================================================
    # EXPORT FUNCTIONALITY
    # =========================================================================
    
    def export_to_csv(self, bookmarks: Optional[List[Bookmark]] = None) -> str:
        """Export bookmarks to CSV format"""
        if bookmarks is None:
            bookmarks = list(self.bookmarks.values())
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header row
        writer.writerow([
            'Category', 'City', 'State', 'Score', 'Star Rating', 
            'Tags', 'Status', 'Dedicated Sites', 'Avg Reviews',
            'No Website Count', 'Notes', 'Assigned To', 'Created At'
        ])
        
        # Data rows
        for b in bookmarks:
            writer.writerow([
                b.category,
                b.city,
                b.state,
                b.opportunity_score,
                b.star_rating,
                ', '.join(b.tags),
                b.status.value,
                b.dedicated_sites or '',
                b.avg_reviews or '',
                b.no_website_count or '',
                b.notes,
                b.assigned_to or '',
                b.created_at.strftime('%Y-%m-%d %H:%M')
            ])
        
        return output.getvalue()
    
    def export_to_json(self, bookmarks: Optional[List[Bookmark]] = None) -> str:
        """Export bookmarks to JSON format"""
        if bookmarks is None:
            bookmarks = list(self.bookmarks.values())
        
        return json.dumps([b.to_dict() for b in bookmarks], indent=2)
    
    def export_due_diligence_report(self, bookmark_id: str) -> Dict:
        """
        Export a single bookmark as a due diligence report
        (Niche Finder Pro style export template)
        """
        bookmark = self.bookmarks.get(bookmark_id)
        if not bookmark:
            return {}
        
        return {
            "report_type": "Due Diligence Report",
            "generated_at": datetime.utcnow().isoformat(),
            "opportunity": {
                "category": bookmark.category,
                "city": bookmark.city,
                "state": bookmark.state,
                "search_query": f"{bookmark.category.lower()} {bookmark.city.lower()} {bookmark.state.upper()}"
            },
            "scores": {
                "overall_score": bookmark.opportunity_score,
                "serp_score": bookmark.serp_score,
                "map_pack_score": bookmark.map_pack_score,
                "user_rating": bookmark.star_rating
            },
            "competition_analysis": {
                "dedicated_sites": bookmark.dedicated_sites,
                "weak_competitors": bookmark.weak_competitors,
                "avg_map_pack_reviews": bookmark.avg_reviews,
                "no_website_opportunities": bookmark.no_website_count
            },
            "user_notes": bookmark.notes,
            "tags": bookmark.tags,
            "workflow": {
                "status": bookmark.status.value,
                "assigned_to": bookmark.assigned_to
            },
            "next_steps": self._generate_next_steps(bookmark),
            "roi_estimate": self._calculate_roi_estimate(bookmark)
        }
    
    def _generate_next_steps(self, bookmark: Bookmark) -> List[str]:
        """Generate recommended next steps"""
        steps = []
        
        if "no_website" in bookmark.tags or (bookmark.no_website_count or 0) > 0:
            steps.append("📞 Call businesses without websites - potential renters!")
        
        if bookmark.star_rating >= 4:
            steps.append("🚀 High priority - Begin domain acquisition")
        
        if "needs_research" in bookmark.tags:
            steps.append("🔍 Complete competitor deep-dive research")
        
        if bookmark.status == BookmarkStatus.VA_ASSIGNED:
            steps.append(f"👤 Awaiting VA review from {bookmark.assigned_to}")
        
        if bookmark.opportunity_score >= 4.0:
            steps.append("✅ Run RevFlow competitive analysis")
            steps.append("📝 Generate site content using R&R Automation")
        
        if not steps:
            steps.append("📋 Review opportunity and add notes")
        
        return steps
    
    def _calculate_roi_estimate(self, bookmark: Bookmark) -> Dict:
        """Estimate ROI for the opportunity"""
        # Category-based monthly potential
        category_potential = {
            "Concrete": 2000, "Roofing": 2500, "Water Damage": 2000,
            "Electric": 1500, "Fence": 1500, "Tree Care": 1200,
            "Plumbing": 1500, "Drywall": 1000, "Carpentry": 1000
        }
        monthly = category_potential.get(bookmark.category, 1000)
        
        # Adjust by score
        score_multiplier = bookmark.opportunity_score / 4.0
        adjusted_monthly = int(monthly * score_multiplier)
        
        return {
            "estimated_monthly_revenue": adjusted_monthly,
            "estimated_annual_revenue": adjusted_monthly * 12,
            "estimated_time_to_revenue_months": 4 if bookmark.opportunity_score >= 4 else 6,
            "confidence": "High" if bookmark.opportunity_score >= 4 else "Medium"
        }
    
    # =========================================================================
    # STATISTICS & ANALYTICS
    # =========================================================================
    
    def get_statistics(self) -> Dict:
        """Get statistics about saved bookmarks"""
        all_bookmarks = list(self.bookmarks.values())
        
        if not all_bookmarks:
            return {"total": 0}
        
        # Count by status
        status_counts = {}
        for status in BookmarkStatus:
            status_counts[status.value] = len([b for b in all_bookmarks if b.status == status])
        
        # Count by category
        category_counts = {}
        for b in all_bookmarks:
            category_counts[b.category] = category_counts.get(b.category, 0) + 1
        
        # Count by state
        state_counts = {}
        for b in all_bookmarks:
            state_counts[b.state] = state_counts.get(b.state, 0) + 1
        
        # Tag usage
        tag_counts = {}
        for b in all_bookmarks:
            for tag in b.tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        
        return {
            "total": len(all_bookmarks),
            "by_status": status_counts,
            "by_category": category_counts,
            "by_state": state_counts,
            "by_tag": tag_counts,
            "avg_score": sum(b.opportunity_score for b in all_bookmarks) / len(all_bookmarks),
            "high_priority_count": len([b for b in all_bookmarks if "high_priority" in b.tags]),
            "no_website_opportunities": len([b for b in all_bookmarks if (b.no_website_count or 0) > 0]),
            "assigned_count": len([b for b in all_bookmarks if b.assigned_to]),
        }

# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

bookmarks_manager = BookmarksManager()
