#!/usr/bin/env python3
"""
Test content quality for 5 sample cities
Run after bootstrap completes: python3 test_quality.py
"""

import psycopg2
import random
import os

DB_CONN = psycopg2.connect(
    dbname=os.getenv("POSTGRES_DB", "revflow"),
    user=os.getenv("POSTGRES_USER", "postgres"),
    password=os.getenv("POSTGRES_PASSWORD", "revflow2026"),
    host="localhost",
    port=5432
)

def get_city_signals(city, state):
    """Fetch all local signals for a city"""
    
    with DB_CONN.cursor() as cur:
        # Get landmarks
        cur.execute("""
            SELECT name, importance 
            FROM local_landmarks 
            WHERE city=%s AND state=%s 
            ORDER BY importance DESC 
            LIMIT 5
        """, (city, state))
        landmarks = [{'name': r[0], 'importance': r[1]} for r in cur.fetchall()]
        
        # Get neighborhoods
        cur.execute("""
            SELECT name 
            FROM local_neighborhoods 
            WHERE city=%s AND state=%s 
            LIMIT 15
        """, (city, state))
        neighborhoods = [r[0] for r in cur.fetchall()]
        
        # Get climate summary
        cur.execute("""
            SELECT climate_summary 
            FROM local_climate 
            WHERE city=%s AND state=%s AND month IS NULL
        """, (city, state))
        result = cur.fetchone()
        climate = result[0] if result else "No climate data"
        
        # Get events
        cur.execute("""
            SELECT title, start_date, venue 
            FROM local_events 
            WHERE city=%s AND state=%s AND is_major=true
            ORDER BY start_date
            LIMIT 3
        """, (city, state))
        events = [{'title': r[0], 'date': r[1], 'venue': r[2]} for r in cur.fetchall()]
    
    return {
        'landmarks': landmarks,
        'neighborhoods': neighborhoods,
        'climate': climate,
        'events': events
    }

def generate_test_content(city, state, service):
    """Generate test landing page content"""
    
    signals = get_city_signals(city, state)
    
    if not signals['neighborhoods'] and not signals['landmarks']:
        return f"\n⚠️  NO DATA FOR {city}, {state}\n   Bootstrap may have failed for this city.\n"
    
    # Select random neighborhoods for intro
    if signals['neighborhoods']:
        intro_hoods = random.sample(
            signals['neighborhoods'], 
            min(3, len(signals['neighborhoods']))
        )
        intro_line = f"Serving {', '.join(intro_hoods)}"
    else:
        intro_line = "Serving the metro area"
    
    # Build content
    content = f"""
{'='*60}
{service.upper()} IN {city.upper()}, {state}
{'='*60}

{service.title()} in {city} - {intro_line}

"""
    
    # Add landmark reference
    if signals['landmarks']:
        content += f"Located near {signals['landmarks'][0]['name']} in {city}, we understand\nthe unique {service} challenges {city} homeowners face.\n\n"
    
    # Add climate context
    if signals['climate'] != "No climate data":
        content += f"🌡️  CLIMATE CONTEXT:\n{signals['climate']}\n\n"
    
    # Add neighborhoods
    if signals['neighborhoods']:
        content += f"🏘️  SERVING THESE {city.upper()} NEIGHBORHOODS:\n"
        for hood in signals['neighborhoods'][:10]:
            content += f"  • {hood}\n"
        content += "\n"
    
    # Add landmarks
    if signals['landmarks']:
        content += f"📍 NEAR YOU:\n"
        for lm in signals['landmarks'][:5]:
            content += f"  • {lm['name']} (importance: {lm['importance']})\n"
        content += "\n"
    
    # Add events
    if signals['events']:
        event = signals['events'][0]
        content += f"🎉 UPCOMING EVENT:\n"
        content += f"With {event['title']} coming up on {event['date']}, now's the perfect\n"
        content += f"time to ensure your {service} systems are ready!\n\n"
    
    # Call to action
    content += f"Call us today for fast, reliable {service} service!\n"
    content += "Phone: (555) 123-4567\n"
    content += "Available 24/7 for emergencies\n"
    
    return content

def analyze_quality(city, state):
    """Analyze data quality for a city"""
    
    signals = get_city_signals(city, state)
    
    score = 0
    max_score = 4
    
    # Check landmarks (25%)
    if len(signals['landmarks']) >= 5:
        score += 1
    
    # Check neighborhoods (25%)
    if len(signals['neighborhoods']) >= 10:
        score += 1
    
    # Check climate (25%)
    if signals['climate'] != "No climate data":
        score += 1
    
    # Check any data (25%)
    if signals['landmarks'] or signals['neighborhoods']:
        score += 1
    
    percentage = (score / max_score) * 100
    
    return {
        'score': score,
        'max_score': max_score,
        'percentage': percentage,
        'landmarks_count': len(signals['landmarks']),
        'neighborhoods_count': len(signals['neighborhoods']),
        'has_climate': signals['climate'] != "No climate data",
        'events_count': len(signals['events'])
    }

def main():
    """Test quality on 5 sample cities"""
    
    print("\n" + "=" * 60)
    print("🧪 QUALITY TEST - 5 SAMPLE CITIES")
    print("=" * 60)
    print()
    
    # Test cities (mix of major and smaller)
    test_cities = [
        ('Dallas', 'TX'),
        ('Plano', 'TX'),
        ('Austin', 'TX'),
        ('McKinney', 'TX'),
        ('Frisco', 'TX')
    ]
    
    all_quality = []
    
    for city, state in test_cities:
        print(f"{'─'*60}")
        print(f"Testing: {city}, {state}")
        print(f"{'─'*60}")
        
        # Analyze quality
        quality = analyze_quality(city, state)
        all_quality.append(quality)
        
        print(f"\n📊 Quality Score: {quality['score']}/{quality['max_score']} ({quality['percentage']:.0f}%)")
        print(f"   Landmarks: {quality['landmarks_count']}")
        print(f"   Neighborhoods: {quality['neighborhoods_count']}")
        print(f"   Climate: {'✅' if quality['has_climate'] else '❌'}")
        print(f"   Events: {quality['events_count']}")
        
        # Generate test content
        content = generate_test_content(city, state, 'plumber')
        print(content)
    
    # Overall summary
    print("=" * 60)
    print("📈 OVERALL QUALITY SUMMARY")
    print("=" * 60)
    
    avg_score = sum(q['percentage'] for q in all_quality) / len(all_quality)
    avg_landmarks = sum(q['landmarks_count'] for q in all_quality) / len(all_quality)
    avg_neighborhoods = sum(q['neighborhoods_count'] for q in all_quality) / len(all_quality)
    
    print(f"\nAverage quality score: {avg_score:.0f}%")
    print(f"Average landmarks per city: {avg_landmarks:.1f}")
    print(f"Average neighborhoods per city: {avg_neighborhoods:.1f}")
    print()
    
    # Pass/fail decision
    if avg_score >= 75:
        print("✅ QUALITY CHECK: PASSED")
        print("   Content shows strong local signals")
        print("   Ready for Module 3 integration")
    elif avg_score >= 50:
        print("⚠️  QUALITY CHECK: MARGINAL")
        print("   Some local signals present but could be stronger")
        print("   Consider adjusting templates or re-running bootstrap")
    else:
        print("❌ QUALITY CHECK: FAILED")
        print("   Insufficient local signals")
        print("   Re-run bootstrap or check API connectivity")
    
    print()
    print("=" * 60)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
