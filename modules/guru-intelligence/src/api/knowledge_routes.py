"""Knowledge Graph API endpoints for RAG search and rule queries"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict
import psycopg2
import os
import re

router = APIRouter()

# Database connection
# DB_CONFIG = {
#     'host': '172.23.0.2',
#     'port': 5432,
#     'database': 'knowledge_graph_db',
#     'user': 'knowledge_admin',
#     'password': 'ZYsCjjdy2dzIwrKKM4TY7Vc0Z8ryoR1V'
# }

def get_db_connection():
#     return psycopg2.connect(**DB_CONFIG)

# Request/Response models
class SearchRequest(BaseModel):
    query: str
    domain: Optional[str] = None
    limit: int = 10

class RulesRequest(BaseModel):
    category: Optional[str] = None
    page_type: Optional[str] = None
    enforcement_level: Optional[str] = None
    limit: int = 50

class AssessRequest(BaseModel):
    content: str
    page_type: str = "service"


# Known cities for LOCAL-001 detection
AZ_CITIES = {
    'phoenix', 'scottsdale', 'tempe', 'mesa', 'gilbert', 'chandler', 'glendale',
    'peoria', 'tucson', 'surprise', 'avondale', 'goodyear', 'buckeye', 'casa grande',
    'flagstaff', 'yuma', 'prescott', 'lake havasu', 'sierra vista', 'apache junction',
    'maricopa', 'queen creek', 'sun city', 'fountain hills', 'paradise valley',
    'oro valley', 'san tan valley', 'anthem', 'cave creek', 'carefree', 'litchfield park',
    'el mirage', 'tolleson', 'youngtown', 'wickenburg', 'payson', 'show low', 'sedona'
}

MAJOR_US_CITIES = {
    'new york', 'los angeles', 'chicago', 'houston', 'dallas', 'san antonio',
    'san diego', 'san jose', 'austin', 'jacksonville', 'fort worth', 'columbus',
    'charlotte', 'san francisco', 'indianapolis', 'seattle', 'denver', 'washington',
    'boston', 'nashville', 'baltimore', 'oklahoma city', 'louisville', 'portland',
    'las vegas', 'milwaukee', 'albuquerque', 'kansas city', 'fresno', 'sacramento',
    'atlanta', 'miami', 'tampa', 'orlando', 'minneapolis', 'cleveland', 'pittsburgh'
}

ALL_KNOWN_CITIES = AZ_CITIES | MAJOR_US_CITIES

def find_city_mentions(text: str) -> List[str]:
    text_lower = text.lower()
    found_cities = []
    for city in ALL_KNOWN_CITIES:
        pattern = r'\b' + re.escape(city) + r'\b'
        if re.search(pattern, text_lower):
            found_cities.append(city.title())
    return found_cities


@router.get("/stats")
async def get_stats():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM knowledge_chunks")
    chunks = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM extracted_rules")
    rules = cur.fetchone()[0]
    cur.execute("SELECT rule_category, COUNT(*) FROM extracted_rules GROUP BY rule_category ORDER BY COUNT(*) DESC")
    categories = {row[0]: row[1] for row in cur.fetchall()}
    cur.close()
    conn.close()
    return {"total_chunks": chunks, "total_rules": rules, "rules_by_category": categories, "status": "operational"}


@router.post("/rules")
async def get_rules(request: RulesRequest):
    conn = get_db_connection()
    cur = conn.cursor()
    query = "SELECT rule_id, rule_name, rule_category, rule_description, enforcement_level, priority_score FROM extracted_rules WHERE 1=1"
    params = []
    if request.category:
        query += " AND (rule_category ILIKE %s OR rule_id ILIKE %s)"
        params.extend([f"%{request.category}%", f"%{request.category}%"])
    if request.enforcement_level:
        query += " AND enforcement_level = %s"
        params.append(request.enforcement_level)
    query += " ORDER BY priority_score DESC LIMIT %s"
    params.append(request.limit)
    cur.execute(query, params)
    rows = cur.fetchall()
    rules = [{"rule_id": row[0], "rule_name": row[1], "category": row[2], "description": row[3], "enforcement_level": row[4], "priority_score": row[5]} for row in rows]
    cur.close()
    conn.close()
    return {"rules": rules, "count": len(rules), "filters": {"category": request.category, "enforcement_level": request.enforcement_level}}


@router.post("/search")
async def search_knowledge(request: SearchRequest):
    conn = get_db_connection()
    cur = conn.cursor()
    query = "SELECT chunk_id, source_file, section_title, content, ts_rank(to_tsvector('english', content), plainto_tsquery('english', %s)) as rank FROM knowledge_chunks WHERE to_tsvector('english', content) @@ plainto_tsquery('english', %s) ORDER BY rank DESC LIMIT %s"
    cur.execute(query, [request.query, request.query, request.limit])
    rows = cur.fetchall()
    results = [{"chunk_id": row[0], "source": row[1], "section": row[2], "content": row[3][:500] + "..." if len(row[3]) > 500 else row[3], "relevance": float(row[4]) if row[4] else 0} for row in rows]
    cur.close()
    conn.close()
    return {"query": request.query, "results": results, "count": len(results)}


@router.post("/assess")
async def assess_content(request: AssessRequest):
    content = request.content
    page_type = request.page_type
    violations = []
    passed = []
@router.post("/knowledge/assess/shimon")
async def assess_content_shimon(request: ContentRequest):
    """
    Assess content using Shimon's methodology + 359 Guru rules.
    """
    scorer = ShimonScorer(db_config)
    result = scorer.score_content(request.content, request.page_type)
    return result
    
    word_count = len(content.split())
    
    # BLUF-002: Word count
    if word_count < 40:
        violations.append({"rule": "BLUF-002", "name": "40-60 Word Snippet", "issue": f"Content too short ({word_count} words). Minimum 40 words.", "severity": "medium", "category": "BLUF & Answer-First"})
    else:
        passed.append("BLUF-002: Word count acceptable")
    
    # BLUF-003: Throat-clearing
    throat_clearing = [r'\b(in this article|in this guide|let\'s explore|we will discuss)\b', r'\b(as you may know|it\'s important to note|it goes without saying)\b', r'\b(first and foremost|at the end of the day|when it comes to)\b']
    throat_clear_found = []
    for pattern in throat_clearing:
        matches = re.findall(pattern, content.lower())
        throat_clear_found.extend(matches)
    if throat_clear_found:
        violations.append({"rule": "BLUF-003", "name": "No Throat-Clearing", "issue": f"Found throat-clearing phrases: {', '.join(set(throat_clear_found))}", "severity": "medium", "category": "BLUF & Answer-First"})
    else:
        passed.append("BLUF-003: No Throat-Clearing")
    
    # NUM-001: Numbers
    numbers = re.findall(r'\$?\d+(?:,\d{3})*(?:\.\d+)?%?', content)
    if len(numbers) >= 1:
        passed.append(f"NUM-001: Contains {len(numbers)} numeric values")
    else:
        violations.append({"rule": "NUM-001", "name": "Numeric Specificity", "issue": "No specific numbers found. Add prices, stats, years.", "severity": "medium", "category": "Numeric Specificity"})
    
    # NUM-002: Prices for service pages
    if page_type == "service":
        prices = re.findall(r'\$\d+(?:,\d{3})*', content)
        if prices:
            passed.append(f"NUM-002: Contains {len(prices)} price points")
        else:
            violations.append({"rule": "NUM-002", "name": "Price Transparency", "issue": "Service page missing price ranges.", "severity": "low", "category": "Numeric Specificity"})
    
    # LOCAL-001: Local proof (FIXED - uses city database)
    local_signals = []
    local_count = 0
    
    found_cities = find_city_mentions(content)
    if found_cities:
        local_signals.append(f"cities: {', '.join(found_cities[:5])}")
        local_count += len(found_cities)
    
    phones = re.findall(r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', content)
    if phones:
        local_signals.append("phone")
        local_count += 1
    
    licenses = re.findall(r'(?:ROC|license|lic|contractor)[-#\s]*\d+', content, re.IGNORECASE)
    if licenses:
        local_signals.append("license")
        local_count += 1
    
    years = re.findall(r'(?:since|established|founded)\s+\d{4}|\d+\+?\s*years', content, re.IGNORECASE)
    if years:
        local_signals.append("years")
        local_count += 1
    
    service_counts = re.findall(r'\d{1,3}(?:,\d{3})*\+?\s*(?:jobs|projects|customers|repairs|homes)', content, re.IGNORECASE)
    if service_counts:
        local_signals.append("service count")
        local_count += 1
    
    if local_count >= 3:
        passed.append(f"LOCAL-001: Strong local proof ({local_count} signals: {', '.join(local_signals)})")
    elif local_count >= 1:
        passed.append(f"LOCAL-001: Some local proof ({local_count} signals)")
    else:
        violations.append({"rule": "LOCAL-001", "name": "Local Proof Signals", "issue": "No local proof found. Add: city names, phone, license, years in business.", "severity": "high", "category": "Local Proof"})
    
    # EEAT-001: Trust signals
    expertise = re.findall(r'\b(?:certified|licensed|experienced|professional|expert)\b', content, re.IGNORECASE)
    trust = re.findall(r'\b(?:guaranteed|warranty|insured|bonded|BBB|accredited)\b', content, re.IGNORECASE)
    brands = re.findall(r'\b(?:American Standard|Kohler|Moen|Rheem|Carrier|Trane|Lennox)\b', content, re.IGNORECASE)
    eeat_count = (1 if expertise else 0) + (1 if trust else 0) + (1 if brands else 0)
    if eeat_count >= 2:
        passed.append(f"EEAT-001: Good E-E-A-T signals")
    elif eeat_count == 1:
        passed.append(f"EEAT-001: Some E-E-A-T signals")
    else:
        violations.append({"rule": "EEAT-001", "name": "E-E-A-T Signals", "issue": "Missing expertise/trust indicators.", "severity": "medium", "category": "E-E-A-T Signals"})
    
    # Calculate score
    total_checks = len(violations) + len(passed)
    severity_weights = {"high": 15, "medium": 10, "low": 5}
    penalty = sum(severity_weights.get(v.get("severity", "medium"), 10) for v in violations)
    score = max(0, min(100, 100 - penalty))
    
    return {"overall_score": score, "passed": score >= 70, "rules_checked": total_checks, "rules_passed": len(passed), "violations": violations, "passed_rules": passed, "recommendations": [v["issue"] for v in violations], "page_type": page_type, "word_count": word_count}
