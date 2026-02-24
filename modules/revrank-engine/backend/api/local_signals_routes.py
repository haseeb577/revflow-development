"""
RevFlow Local Signals API Routes
Exposes local intelligence data through REST endpoints
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List, Dict, Any
from pydantic import BaseModel

from services.local_signals_service import local_signals_service


router = APIRouter(prefix="/api/local-signals", tags=["Local Signals"])


class ContentEnrichmentRequest(BaseModel):
    """Request for content enrichment"""
    city: str
    state: str
    service_type: str


class CitySignalsResponse(BaseModel):
    """Full city signals response"""
    city: str
    state: str
    landmarks: List[Dict[str, Any]]
    neighborhoods: List[Dict[str, Any]]
    climate: Dict[str, Any]
    events: List[Dict[str, Any]]


@router.get("/health")
async def health_check():
    """Check local signals service health"""
    return local_signals_service.health_check()


@router.get("/cities")
async def get_available_cities():
    """Get list of all cities with local signals data"""
    cities = local_signals_service.get_available_cities()
    return {
        "total": len(cities),
        "cities": cities
    }


@router.get("/city/{state}/{city}")
async def get_city_signals(city: str, state: str):
    """Get all local signals for a specific city"""
    signals = local_signals_service.get_city_signals(city, state)

    # Check if we have any data
    if not signals['landmarks'] and not signals['neighborhoods']:
        raise HTTPException(
            status_code=404,
            detail=f"No local signals found for {city}, {state}"
        )

    return signals


@router.get("/city/{state}/{city}/landmarks")
async def get_landmarks(
    city: str,
    state: str,
    limit: int = Query(10, ge=1, le=50)
):
    """Get landmarks for a city"""
    landmarks = local_signals_service.get_landmarks(city, state, limit)
    return {
        "city": city,
        "state": state,
        "count": len(landmarks),
        "landmarks": landmarks
    }


@router.get("/city/{state}/{city}/neighborhoods")
async def get_neighborhoods(
    city: str,
    state: str,
    limit: int = Query(15, ge=1, le=100)
):
    """Get neighborhoods for a city"""
    neighborhoods = local_signals_service.get_neighborhoods(city, state, limit)
    return {
        "city": city,
        "state": state,
        "count": len(neighborhoods),
        "neighborhoods": neighborhoods
    }


@router.get("/city/{state}/{city}/climate")
async def get_climate(city: str, state: str):
    """Get climate data for a city"""
    climate = local_signals_service.get_climate(city, state)
    return {
        "city": city,
        "state": state,
        "climate": climate
    }


@router.get("/city/{state}/{city}/events")
async def get_events(
    city: str,
    state: str,
    limit: int = Query(5, ge=1, le=20)
):
    """Get events for a city"""
    events = local_signals_service.get_events(city, state, limit)
    return {
        "city": city,
        "state": state,
        "count": len(events),
        "events": events
    }


@router.post("/enrich")
async def enrich_content(request: ContentEnrichmentRequest):
    """
    Get content enrichment data for a service in a city

    This is the main integration endpoint for content generation.
    Returns structured data with ready-to-use content snippets.
    """
    enrichment = local_signals_service.enrich_content(
        request.city,
        request.state,
        request.service_type
    )

    if not enrichment['landmarks']['count'] and not enrichment['neighborhoods']['count']:
        raise HTTPException(
            status_code=404,
            detail=f"No local signals found for {request.city}, {request.state}"
        )

    return enrichment


@router.get("/enrich/{state}/{city}/{service_type}")
async def enrich_content_get(city: str, state: str, service_type: str):
    """
    GET version of content enrichment

    Example: /api/local-signals/enrich/TX/Dallas/plumber
    """
    enrichment = local_signals_service.enrich_content(city, state, service_type)

    if not enrichment['landmarks']['count'] and not enrichment['neighborhoods']['count']:
        raise HTTPException(
            status_code=404,
            detail=f"No local signals found for {city}, {state}"
        )

    return enrichment
