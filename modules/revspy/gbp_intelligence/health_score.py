"""
RevSPY™ GBP Health Score Calculator
Calculates 0-100 health score based on GBP profile strength
"""
from datetime import datetime
from typing import Dict, Optional

def calculate_gbp_health_score(profile: Dict) -> int:
    """
    Calculate GBP Health Score (0-100)
    
    Scoring Breakdown:
    - Reviews (30 points): Quantity and rating
    - Photos (20 points): Visual content richness
    - Posts (15 points): Engagement and freshness
    - Q&A (10 points): Customer interaction
    - Categories (10 points): Service coverage
    - Completeness (15 points): Profile filled out
    
    Returns: Integer score 0-100
    """
    score = 0
    
    # REVIEWS (30 points max)
    review_count = profile.get('review_count', 0)
    rating = profile.get('rating', 0)
    
    if review_count >= 200:
        score += 15
    elif review_count >= 100:
        score += 12
    elif review_count >= 50:
        score += 9
    elif review_count >= 20:
        score += 6
    elif review_count >= 5:
        score += 3
    
    if rating >= 4.7:
        score += 15
    elif rating >= 4.5:
        score += 12
    elif rating >= 4.2:
        score += 9
    elif rating >= 4.0:
        score += 6
    elif rating >= 3.5:
        score += 3
    
    # PHOTOS (20 points max)
    photo_count = profile.get('photo_count', 0)
    
    if photo_count >= 100:
        score += 20
    elif photo_count >= 50:
        score += 16
    elif photo_count >= 25:
        score += 12
    elif photo_count >= 10:
        score += 8
    elif photo_count >= 5:
        score += 4
    
    # POSTS (15 points max)
    post_count = profile.get('post_count', 0)
    
    if post_count >= 50:
        score += 15
    elif post_count >= 25:
        score += 12
    elif post_count >= 10:
        score += 9
    elif post_count >= 5:
        score += 6
    elif post_count >= 1:
        score += 3
    
    # Q&A ENGAGEMENT (10 points max)
    qa_count = profile.get('qa_count', 0)
    
    if qa_count >= 50:
        score += 10
    elif qa_count >= 20:
        score += 8
    elif qa_count >= 10:
        score += 6
    elif qa_count >= 5:
        score += 4
    elif qa_count >= 1:
        score += 2
    
    # CATEGORIES (10 points max)
    category_count = profile.get('category_count', 0)
    
    if category_count >= 5:
        score += 10
    elif category_count >= 3:
        score += 7
    elif category_count >= 2:
        score += 5
    elif category_count >= 1:
        score += 3
    
    # PROFILE COMPLETENESS (15 points max)
    completeness = 0
    
    if profile.get('has_website'):
        completeness += 3
    if profile.get('has_phone'):
        completeness += 3
    if profile.get('has_hours'):
        completeness += 3
    if profile.get('business_description'):
        completeness += 3
    if profile.get('services_offered'):
        completeness += 3
    
    score += completeness
    
    # Cap at 100
    return min(score, 100)


def calculate_competitive_threat(health_score: int, rank: Optional[int], total_competitors: int) -> str:
    """
    Determine competitive threat level
    
    Returns: "LOW", "MODERATE", "HIGH", "CRITICAL"
    """
    # High health score + good rank = HIGH threat (they're strong)
    if health_score >= 80 and rank and rank <= 3:
        return "CRITICAL"
    elif health_score >= 70 and rank and rank <= 5:
        return "HIGH"
    elif health_score >= 60 and rank and rank <= 10:
        return "MODERATE"
    elif health_score >= 50:
        return "MODERATE"
    else:
        return "LOW"


def get_health_score_breakdown(profile: Dict) -> Dict:
    """
    Get detailed breakdown of health score components
    """
    return {
        "reviews": {
            "count": profile.get('review_count', 0),
            "rating": profile.get('rating', 0),
            "score": _calculate_review_score(profile)
        },
        "photos": {
            "count": profile.get('photo_count', 0),
            "score": _calculate_photo_score(profile)
        },
        "posts": {
            "count": profile.get('post_count', 0),
            "score": _calculate_post_score(profile)
        },
        "engagement": {
            "qa_count": profile.get('qa_count', 0),
            "score": _calculate_qa_score(profile)
        },
        "completeness": {
            "categories": profile.get('category_count', 0),
            "has_website": profile.get('has_website', False),
            "has_phone": profile.get('has_phone', False),
            "score": _calculate_completeness_score(profile)
        },
        "total": calculate_gbp_health_score(profile)
    }


def _calculate_review_score(profile: Dict) -> int:
    """Calculate review component score (max 30)"""
    score = 0
    review_count = profile.get('review_count', 0)
    rating = profile.get('rating', 0)
    
    if review_count >= 200:
        score += 15
    elif review_count >= 100:
        score += 12
    elif review_count >= 50:
        score += 9
    elif review_count >= 20:
        score += 6
    elif review_count >= 5:
        score += 3
    
    if rating >= 4.7:
        score += 15
    elif rating >= 4.5:
        score += 12
    elif rating >= 4.2:
        score += 9
    elif rating >= 4.0:
        score += 6
    elif rating >= 3.5:
        score += 3
    
    return score


def _calculate_photo_score(profile: Dict) -> int:
    """Calculate photo component score (max 20)"""
    photo_count = profile.get('photo_count', 0)
    
    if photo_count >= 100:
        return 20
    elif photo_count >= 50:
        return 16
    elif photo_count >= 25:
        return 12
    elif photo_count >= 10:
        return 8
    elif photo_count >= 5:
        return 4
    return 0


def _calculate_post_score(profile: Dict) -> int:
    """Calculate post component score (max 15)"""
    post_count = profile.get('post_count', 0)
    
    if post_count >= 50:
        return 15
    elif post_count >= 25:
        return 12
    elif post_count >= 10:
        return 9
    elif post_count >= 5:
        return 6
    elif post_count >= 1:
        return 3
    return 0


def _calculate_qa_score(profile: Dict) -> int:
    """Calculate Q&A component score (max 10)"""
    qa_count = profile.get('qa_count', 0)
    
    if qa_count >= 50:
        return 10
    elif qa_count >= 20:
        return 8
    elif qa_count >= 10:
        return 6
    elif qa_count >= 5:
        return 4
    elif qa_count >= 1:
        return 2
    return 0


def _calculate_completeness_score(profile: Dict) -> int:
    """Calculate completeness component score (max 25)"""
    score = 0
    
    # Categories (10 points)
    category_count = profile.get('category_count', 0)
    if category_count >= 5:
        score += 10
    elif category_count >= 3:
        score += 7
    elif category_count >= 2:
        score += 5
    elif category_count >= 1:
        score += 3
    
    # Profile elements (15 points)
    if profile.get('has_website'):
        score += 3
    if profile.get('has_phone'):
        score += 3
    if profile.get('has_hours'):
        score += 3
    if profile.get('business_description'):
        score += 3
    if profile.get('services_offered'):
        score += 3
    
    return score
