"""
╔══════════════════════════════════════════════════════════════════════════════╗
║          NICHE FINDER PRO STYLE API ROUTES                                   ║
║          SERP Analysis, Bookmarks, Turbo Search, Export                      ║
╚══════════════════════════════════════════════════════════════════════════════╝

Enhanced API endpoints inspired by Niche Finder Pro:
- Turbo Search with population/competition filters
- SERP weakness analysis
- Map Pack opportunity detection
- "No Website" finder
- Favorites/bookmarks with tagging
- VA workflow support
- Export to CSV/JSON
"""

from fastapi import APIRouter, HTTPException, Query, Response
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

# Import our services
from services.serp_analyzer import serp_analyzer, SERPAnalysisResult
from services.bookmarks_manager import (
    bookmarks_manager, Bookmark, BookmarkStatus, 
    BookmarkType, PRESET_TAGS
)

# =============================================================================
# ROUTER SETUP
# =============================================================================

router = APIRouter(prefix="/api/nfp", tags=["Niche Finder Pro"])

# =============================================================================
# PYDANTIC MODELS
# =============================================================================

class TurboSearchRequest(BaseModel):
    """Request model for Turbo Search (Niche Finder Pro style)"""
    category: str = Field(..., description="Service category to search")
    state: str = Field(..., description="State code (e.g., TX, FL)")
    cities: Optional[List[str]] = Field(None, description="Specific cities to search, or None for auto")
    
    # Population filters
    min_population: int = Field(25000, ge=5000)
    max_population: int = Field(250000, le=1000000)
    
    # Competition filters
    max_dedicated_sites: int = Field(10, description="Max dedicated sites to consider opportunity")
    max_avg_reviews: int = Field(30, description="Max avg reviews in map pack")
    
    # Scoring filters
    min_opportunity_score: float = Field(3.0, ge=1.0, le=5.0)
    
    # Options
    include_no_website_only: bool = Field(False, description="Only return markets with no-website opportunities")
    limit: int = Field(20, ge=1, le=100)

class SERPAnalysisRequest(BaseModel):
    """Request for single SERP analysis"""
    category: str
    city: str
    state: str

class BookmarkCreateRequest(BaseModel):
    """Request to create a bookmark"""
    type: str = "market_opportunity"
    category: str
    city: str
    state: str
    opportunity_score: float = 0.0
    tags: List[str] = []
    star_rating: int = Field(0, ge=0, le=5)
    notes: str = ""
    dedicated_sites: Optional[int] = None
    weak_competitors: Optional[int] = None
    avg_reviews: Optional[float] = None
    no_website_count: Optional[int] = None
    business_name: Optional[str] = None
    business_phone: Optional[str] = None
    has_website: Optional[bool] = None
    search_query: Optional[str] = None

class BookmarkUpdateRequest(BaseModel):
    """Request to update a bookmark"""
    tags: Optional[List[str]] = None
    star_rating: Optional[int] = None
    notes: Optional[str] = None
    status: Optional[str] = None
    assigned_to: Optional[str] = None

class BulkTagRequest(BaseModel):
    """Request to add tags to multiple bookmarks"""
    bookmark_ids: List[str]
    tag: str

class BulkAssignRequest(BaseModel):
    """Request to assign multiple bookmarks to VA"""
    bookmark_ids: List[str]
    va_name: str

class CreateTagRequest(BaseModel):
    """Request to create a custom tag"""
    label: str
    color: str = "#6b7280"
    icon: str = "🏷️"

# =============================================================================
# TURBO SEARCH ENDPOINTS (Niche Finder Pro Core Feature)
# =============================================================================

@router.post("/turbo-search", summary="Turbo Search - Rapid Market Discovery")
async def turbo_search(request: TurboSearchRequest):
    """
    🚀 TURBO SEARCH - Niche Finder Pro Style
    
    Rapidly scan multiple cities for opportunities based on:
    - Population range
    - Competition levels
    - SERP weakness indicators
    - "No website" opportunities
    
    Returns ranked list of opportunities with full SERP analysis.
    """
    # In production: Would fetch real city data from Census API
    # For now: Use our market database
    from services.market_discovery_engine import MARKET_DATABASE
    
    state_data = MARKET_DATABASE.get(request.state.upper(), {"cities": []})
    cities_to_search = []
    
    if request.cities:
        # User specified cities
        cities_to_search = [
            c for c in state_data.get("cities", [])
            if c["city"] in request.cities
        ]
    else:
        # Filter by population
        cities_to_search = [
            c for c in state_data.get("cities", [])
            if request.min_population <= c["population"] <= request.max_population
        ]
    
    if not cities_to_search:
        return {
            "success": True,
            "results": [],
            "message": f"No cities found matching criteria in {request.state}"
        }
    
    # Analyze each city
    results = []
    for city_data in cities_to_search[:request.limit]:
        analysis = serp_analyzer.analyze_serp(
            request.category, 
            city_data["city"], 
            request.state
        )
        
        # Apply filters
        if analysis.dedicated_site_count > request.max_dedicated_sites:
            continue
        if analysis.avg_map_pack_reviews > request.max_avg_reviews:
            continue
        if analysis.overall_opportunity_score < request.min_opportunity_score:
            continue
        if request.include_no_website_only and analysis.no_website_count == 0:
            continue
        
        results.append({
            "city": city_data["city"],
            "state": request.state,
            "category": request.category,
            "population": city_data["population"],
            "growth_rate": city_data.get("growth", 0),
            "analysis": analysis.to_dict()
        })
    
    # Sort by opportunity score
    results.sort(key=lambda x: x["analysis"]["overall_opportunity_score"], reverse=True)
    
    return {
        "success": True,
        "search_params": request.dict(),
        "total_results": len(results),
        "results": results[:request.limit]
    }

@router.get("/turbo-search/states", summary="Get available states for Turbo Search")
async def get_turbo_search_states():
    """Get list of states available for Turbo Search"""
    from services.market_discovery_engine import MARKET_DATABASE
    
    states = []
    for state, data in MARKET_DATABASE.items():
        states.append({
            "code": state,
            "city_count": len(data.get("cities", [])),
            "sun_belt": data.get("sun_belt", False)
        })
    
    return {"states": states}

@router.get("/turbo-search/cities/{state}", summary="Get cities for a state")
async def get_state_cities(
    state: str,
    min_population: int = Query(0),
    max_population: int = Query(1000000)
):
    """Get cities in a state with population filters"""
    from services.market_discovery_engine import MARKET_DATABASE
    
    state_data = MARKET_DATABASE.get(state.upper(), {"cities": []})
    
    cities = [
        c for c in state_data.get("cities", [])
        if min_population <= c["population"] <= max_population
    ]
    
    return {
        "state": state.upper(),
        "cities": cities,
        "total": len(cities)
    }

# =============================================================================
# SERP ANALYSIS ENDPOINTS
# =============================================================================

@router.post("/serp/analyze", summary="Analyze SERP for a specific market")
async def analyze_serp(request: SERPAnalysisRequest):
    """
    Perform detailed SERP analysis for a category + city + state.
    
    Returns:
    - Organic search results with competitor analysis
    - Map Pack listings with opportunity indicators
    - Dedicated site count
    - Weak competitor identification
    - "No Website" opportunities
    - Opportunity scores and recommendations
    """
    analysis = serp_analyzer.analyze_serp(
        request.category,
        request.city,
        request.state
    )
    
    return {
        "success": True,
        "analysis": analysis.to_dict()
    }

@router.get("/serp/no-website-finder", summary="Find 'No Website' opportunities")
async def find_no_website_opportunities(
    category: str = Query(...),
    state: str = Query(...),
    limit: int = Query(20)
):
    """
    🌐 NO WEBSITE FINDER
    
    Scan markets to find businesses ranking without websites.
    These are prime opportunities for:
    - Direct outreach (become their web presence)
    - Easier ranking (they have GMB but no site to compete with)
    """
    from services.market_discovery_engine import MARKET_DATABASE
    
    state_data = MARKET_DATABASE.get(state.upper(), {"cities": []})
    cities = state_data.get("cities", [])
    
    opportunities = serp_analyzer.find_no_website_opportunities(
        category, cities, state.upper()
    )
    
    return {
        "success": True,
        "category": category,
        "state": state,
        "total_opportunities": len(opportunities),
        "opportunities": opportunities[:limit]
    }

# =============================================================================
# BOOKMARKS / FAVORITES ENDPOINTS
# =============================================================================

@router.get("/bookmarks", summary="Get all bookmarks with filtering")
async def get_bookmarks(
    tags: Optional[str] = Query(None, description="Comma-separated tag IDs"),
    status: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    min_rating: Optional[int] = Query(None, ge=1, le=5),
    min_score: Optional[float] = Query(None),
    assigned_to: Optional[str] = Query(None),
    has_no_website: Optional[bool] = Query(None),
    search: Optional[str] = Query(None)
):
    """
    Get saved bookmarks with optional filtering.
    
    Filter by:
    - Tags (comma-separated)
    - Status (new, reviewing, approved, etc.)
    - Category
    - State
    - Minimum star rating
    - Minimum opportunity score
    - VA assignment
    - "No website" opportunities
    - Search term
    """
    tag_list = tags.split(",") if tags else None
    
    bookmarks = bookmarks_manager.filter(
        tags=tag_list,
        status=status,
        category=category,
        state=state,
        min_rating=min_rating,
        min_score=min_score,
        assigned_to=assigned_to,
        has_no_website=has_no_website,
        search_term=search
    )
    
    # Sort by score descending
    bookmarks.sort(key=lambda b: b.opportunity_score, reverse=True)
    
    return {
        "success": True,
        "total": len(bookmarks),
        "bookmarks": [b.to_dict() for b in bookmarks]
    }

@router.post("/bookmarks", summary="Create a new bookmark")
async def create_bookmark(request: BookmarkCreateRequest):
    """Save an opportunity as a bookmark"""
    bookmark = bookmarks_manager.create(request.dict())
    
    return {
        "success": True,
        "message": "Bookmark created",
        "bookmark": bookmark.to_dict()
    }

@router.get("/bookmarks/{bookmark_id}", summary="Get a specific bookmark")
async def get_bookmark(bookmark_id: str):
    """Get a bookmark by ID"""
    bookmark = bookmarks_manager.get(bookmark_id)
    if not bookmark:
        raise HTTPException(status_code=404, detail="Bookmark not found")
    
    return {
        "success": True,
        "bookmark": bookmark.to_dict()
    }

@router.put("/bookmarks/{bookmark_id}", summary="Update a bookmark")
async def update_bookmark(bookmark_id: str, request: BookmarkUpdateRequest):
    """Update a bookmark's tags, rating, notes, or status"""
    updates = {k: v for k, v in request.dict().items() if v is not None}
    
    bookmark = bookmarks_manager.update(bookmark_id, updates)
    if not bookmark:
        raise HTTPException(status_code=404, detail="Bookmark not found")
    
    return {
        "success": True,
        "message": "Bookmark updated",
        "bookmark": bookmark.to_dict()
    }

@router.delete("/bookmarks/{bookmark_id}", summary="Delete a bookmark")
async def delete_bookmark(bookmark_id: str):
    """Delete a bookmark"""
    success = bookmarks_manager.delete(bookmark_id)
    if not success:
        raise HTTPException(status_code=404, detail="Bookmark not found")
    
    return {"success": True, "message": "Bookmark deleted"}

# =============================================================================
# TAGGING ENDPOINTS
# =============================================================================

@router.get("/tags", summary="Get all available tags")
async def get_tags():
    """Get all preset and custom tags"""
    return {
        "tags": bookmarks_manager.get_all_tags()
    }

@router.post("/tags", summary="Create a custom tag")
async def create_tag(request: CreateTagRequest):
    """Create a new custom tag"""
    tag = bookmarks_manager.create_custom_tag(
        request.label, 
        request.color, 
        request.icon
    )
    
    return {
        "success": True,
        "tag": tag
    }

@router.post("/bookmarks/{bookmark_id}/tags/{tag}", summary="Add tag to bookmark")
async def add_tag_to_bookmark(bookmark_id: str, tag: str):
    """Add a tag to a bookmark"""
    bookmark = bookmarks_manager.add_tag(bookmark_id, tag)
    if not bookmark:
        raise HTTPException(status_code=404, detail="Bookmark not found")
    
    return {
        "success": True,
        "bookmark": bookmark.to_dict()
    }

@router.delete("/bookmarks/{bookmark_id}/tags/{tag}", summary="Remove tag from bookmark")
async def remove_tag_from_bookmark(bookmark_id: str, tag: str):
    """Remove a tag from a bookmark"""
    bookmark = bookmarks_manager.remove_tag(bookmark_id, tag)
    if not bookmark:
        raise HTTPException(status_code=404, detail="Bookmark not found")
    
    return {
        "success": True,
        "bookmark": bookmark.to_dict()
    }

@router.post("/bookmarks/bulk-tag", summary="Add tag to multiple bookmarks")
async def bulk_add_tag(request: BulkTagRequest):
    """Add a tag to multiple bookmarks at once"""
    count = bookmarks_manager.bulk_add_tag(request.bookmark_ids, request.tag)
    
    return {
        "success": True,
        "message": f"Tag '{request.tag}' added to {count} bookmarks"
    }

# =============================================================================
# VA WORKFLOW ENDPOINTS
# =============================================================================

@router.post("/bookmarks/assign", summary="Assign bookmarks to VA")
async def assign_to_va(request: BulkAssignRequest):
    """Assign multiple bookmarks to a VA for review"""
    count = bookmarks_manager.bulk_assign(request.bookmark_ids, request.va_name)
    
    return {
        "success": True,
        "message": f"Assigned {count} bookmarks to {request.va_name}"
    }

@router.get("/va/{va_name}/queue", summary="Get VA's work queue")
async def get_va_queue(va_name: str):
    """Get all bookmarks assigned to a specific VA"""
    bookmarks = bookmarks_manager.get_va_queue(va_name)
    
    return {
        "success": True,
        "va_name": va_name,
        "queue_length": len(bookmarks),
        "bookmarks": [b.to_dict() for b in bookmarks]
    }

@router.put("/bookmarks/{bookmark_id}/status/{status}", summary="Update bookmark status")
async def update_status(bookmark_id: str, status: str):
    """Update the status of a bookmark"""
    try:
        bookmark = bookmarks_manager.update_status(bookmark_id, status)
        if not bookmark:
            raise HTTPException(status_code=404, detail="Bookmark not found")
        
        return {
            "success": True,
            "bookmark": bookmark.to_dict()
        }
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

# =============================================================================
# EXPORT ENDPOINTS
# =============================================================================

@router.get("/bookmarks/export/csv", summary="Export bookmarks to CSV")
async def export_bookmarks_csv(
    tags: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    min_rating: Optional[int] = Query(None)
):
    """Export filtered bookmarks to CSV format"""
    tag_list = tags.split(",") if tags else None
    
    bookmarks = bookmarks_manager.filter(
        tags=tag_list,
        status=status,
        min_rating=min_rating
    )
    
    csv_content = bookmarks_manager.export_to_csv(bookmarks)
    
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=bookmarks_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
        }
    )

@router.get("/bookmarks/export/json", summary="Export bookmarks to JSON")
async def export_bookmarks_json(
    tags: Optional[str] = Query(None),
    status: Optional[str] = Query(None)
):
    """Export filtered bookmarks to JSON format"""
    tag_list = tags.split(",") if tags else None
    
    bookmarks = bookmarks_manager.filter(tags=tag_list, status=status)
    json_content = bookmarks_manager.export_to_json(bookmarks)
    
    return Response(
        content=json_content,
        media_type="application/json",
        headers={
            "Content-Disposition": f"attachment; filename=bookmarks_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
        }
    )

@router.get("/bookmarks/{bookmark_id}/due-diligence", summary="Export due diligence report")
async def export_due_diligence(bookmark_id: str):
    """
    Generate a due diligence report for a specific opportunity.
    (Niche Finder Pro style export template)
    """
    report = bookmarks_manager.export_due_diligence_report(bookmark_id)
    
    if not report:
        raise HTTPException(status_code=404, detail="Bookmark not found")
    
    return {
        "success": True,
        "report": report
    }

# =============================================================================
# STATISTICS ENDPOINTS
# =============================================================================

@router.get("/bookmarks/stats", summary="Get bookmark statistics")
async def get_bookmark_stats():
    """Get aggregate statistics about saved bookmarks"""
    return {
        "success": True,
        "statistics": bookmarks_manager.get_statistics()
    }

# =============================================================================
# QUICK ACTIONS (Convenience endpoints)
# =============================================================================

@router.post("/quick-bookmark", summary="Quick bookmark from SERP analysis")
async def quick_bookmark_from_analysis(
    category: str = Query(...),
    city: str = Query(...),
    state: str = Query(...),
    tags: Optional[str] = Query(None),
    star_rating: int = Query(0, ge=0, le=5),
    notes: str = Query("")
):
    """
    Quick action: Analyze SERP and create bookmark in one call.
    Perfect for rapid prospecting workflow.
    """
    # Run SERP analysis
    analysis = serp_analyzer.analyze_serp(category, city, state)
    
    # Create bookmark with analysis data
    tag_list = tags.split(",") if tags else []
    
    # Auto-add tags based on analysis
    if analysis.no_website_count > 0:
        if "no_website" not in tag_list:
            tag_list.append("no_website")
    
    if analysis.overall_opportunity_score >= 4.0:
        if "high_priority" not in tag_list:
            tag_list.append("high_priority")
    
    bookmark = bookmarks_manager.create({
        "type": "market_opportunity",
        "category": category,
        "city": city,
        "state": state,
        "opportunity_score": analysis.overall_opportunity_score,
        "serp_score": analysis.serp_opportunity_score,
        "map_pack_score": analysis.map_pack_opportunity_score,
        "tags": tag_list,
        "star_rating": star_rating,
        "notes": notes,
        "dedicated_sites": analysis.dedicated_site_count,
        "weak_competitors": analysis.weak_competitor_count,
        "avg_reviews": analysis.avg_map_pack_reviews,
        "no_website_count": analysis.no_website_count + analysis.map_pack_no_website_count,
        "search_query": analysis.search_query
    })
    
    return {
        "success": True,
        "message": "Analyzed and bookmarked",
        "analysis": analysis.to_dict(),
        "bookmark": bookmark.to_dict()
    }
