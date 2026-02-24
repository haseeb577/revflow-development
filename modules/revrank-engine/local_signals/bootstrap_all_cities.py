#!/usr/bin/env python3
"""
RevFlow Local Signals - Full 53 City Bootstrap
Fetches landmarks, neighborhoods, climate data, and events for all cities
Run: python3 bootstrap_all_cities.py
"""

import requests
import psycopg2
import time
import csv
import sys
from datetime import datetime, timedelta
from collections import defaultdict

# Database connection - uses shared .env credentials
import os
DB_CONN = psycopg2.connect(
    dbname=os.getenv("POSTGRES_DB", "revflow"),
    user=os.getenv("POSTGRES_USER", "postgres"),
    password=os.getenv("POSTGRES_PASSWORD", "revflow2026"),
    host="localhost",
    port=5432
)

def fetch_landmarks(city, state, lat, lon):
    """Fetch landmarks from OpenStreetMap Overpass API"""
    
    print(f"  📍 Fetching landmarks for {city}...", end=" ", flush=True)
    
    overpass_url = "https://overpass-api.de/api/interpreter"
    
    # Query for tourism, leisure, historic POIs within 15km radius
    query = f"""
    [out:json][timeout:60];
    (
      node["tourism"~"museum|attraction|viewpoint|gallery"](around:15000,{lat},{lon});
      way["tourism"~"museum|attraction"](around:15000,{lat},{lon});
      node["leisure"~"park|stadium|sports_centre"](around:15000,{lat},{lon});
      way["leisure"~"park|stadium"](around:15000,{lat},{lon});
      node["historic"](around:15000,{lat},{lon});
      node["amenity"="place_of_worship"](around:15000,{lat},{lon});
    );
    out body;
    """
    
    try:
        response = requests.post(overpass_url, data={'data': query}, timeout=90)
        data = response.json()
        
        landmarks = []
        for element in data.get('elements', []):
            name = element.get('tags', {}).get('name')
            if not name:
                continue
            
            # Calculate importance score
            tourism_type = element.get('tags', {}).get('tourism', '')
            leisure_type = element.get('tags', {}).get('leisure', '')
            
            importance = 50
            if tourism_type in ['museum', 'attraction']:
                importance = 85
            elif leisure_type in ['stadium', 'park']:
                importance = 75
            elif element.get('tags', {}).get('wikipedia'):
                importance += 10
            
            landmarks.append({
                'city': city,
                'state': state,
                'name': name,
                'category': tourism_type or leisure_type or 'landmark',
                'osm_type': element.get('type'),
                'osm_id': element.get('id'),
                'latitude': element.get('lat'),
                'longitude': element.get('lon'),
                'importance': importance
            })
        
        # Sort by importance and take top 50
        landmarks = sorted(landmarks, key=lambda x: x['importance'], reverse=True)[:50]
        
        # Store in database
        with DB_CONN.cursor() as cur:
            for landmark in landmarks:
                cur.execute("""
                    INSERT INTO local_landmarks 
                    (city, state, name, category, osm_type, osm_id, latitude, longitude, importance)
                    VALUES (%(city)s, %(state)s, %(name)s, %(category)s, %(osm_type)s, 
                            %(osm_id)s, %(latitude)s, %(longitude)s, %(importance)s)
                    ON CONFLICT (city, state, name) DO NOTHING
                """, landmark)
        
        DB_CONN.commit()
        
        print(f"✅ {len(landmarks)}")
        return len(landmarks)
        
    except Exception as e:
        DB_CONN.rollback()
        print(f"❌ Error: {str(e)[:50]}")
        return 0

def fetch_neighborhoods(city, state, lat, lon):
    """Fetch neighborhoods from OpenStreetMap"""
    
    print(f"  🏘️  Fetching neighborhoods for {city}...", end=" ", flush=True)
    
    overpass_url = "https://overpass-api.de/api/interpreter"
    
    # Query for neighborhoods and administrative boundaries
    query = f"""
    [out:json][timeout:60];
    (
      relation["admin_level"="9"](around:20000,{lat},{lon});
      relation["place"="neighbourhood"](around:20000,{lat},{lon});
      node["place"="neighbourhood"](around:20000,{lat},{lon});
    );
    out center;
    """
    
    try:
        response = requests.post(overpass_url, data={'data': query}, timeout=90)
        data = response.json()
        
        neighborhoods = []
        for element in data.get('elements', []):
            name = element.get('tags', {}).get('name')
            if not name:
                continue
            
            # Get center coordinates
            if 'center' in element:
                lat_val = element['center']['lat']
                lon_val = element['center']['lon']
            elif 'lat' in element:
                lat_val = element['lat']
                lon_val = element['lon']
            else:
                continue
            
            neighborhoods.append({
                'city': city,
                'state': state,
                'name': name,
                'admin_level': element.get('tags', {}).get('admin_level', 10),
                'osm_type': element.get('type'),
                'osm_id': element.get('id'),
                'center_latitude': lat_val,
                'center_longitude': lon_val
            })
        
        # Deduplicate by name
        seen = set()
        unique = []
        for n in neighborhoods:
            if n['name'] not in seen:
                seen.add(n['name'])
                unique.append(n)
        
        # Store in database
        with DB_CONN.cursor() as cur:
            for neighborhood in unique:
                cur.execute("""
                    INSERT INTO local_neighborhoods 
                    (city, state, name, admin_level, osm_type, osm_id, 
                     center_latitude, center_longitude)
                    VALUES (%(city)s, %(state)s, %(name)s, %(admin_level)s, 
                            %(osm_type)s, %(osm_id)s, %(center_latitude)s, 
                            %(center_longitude)s)
                    ON CONFLICT (city, state, name) DO NOTHING
                """, neighborhood)
        
        DB_CONN.commit()
        
        print(f"✅ {len(unique)}")
        return len(unique)

    except Exception as e:
        DB_CONN.rollback()
        print(f"❌ Error: {str(e)[:50]}")
        return 0

def fetch_climate(city, state, lat, lon):
    """Fetch climate data from Open-Meteo API"""
    
    print(f"  🌡️  Fetching climate data for {city}...", end=" ", flush=True)
    
    # Open-Meteo API for historical climate
    url = "https://archive-api.open-meteo.com/v1/archive"
    
    # Get last 5 years of data for monthly averages
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365*5)
    
    params = {
        'latitude': lat,
        'longitude': lon,
        'start_date': start_date.strftime('%Y-%m-%d'),
        'end_date': end_date.strftime('%Y-%m-%d'),
        'daily': 'temperature_2m_max,temperature_2m_min,precipitation_sum',
        'temperature_unit': 'fahrenheit',
        'timezone': 'America/Chicago'
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        data = response.json()
        
        daily_data = data.get('daily', {})
        temps_high = daily_data.get('temperature_2m_max', [])
        temps_low = daily_data.get('temperature_2m_min', [])
        precip = daily_data.get('precipitation_sum', [])
        dates = daily_data.get('time', [])
        
        # Group by month
        monthly = defaultdict(lambda: {'high': [], 'low': [], 'precip': []})
        
        for i, date_str in enumerate(dates):
            month = int(date_str.split('-')[1])
            if temps_high[i] is not None:
                monthly[month]['high'].append(temps_high[i])
            if temps_low[i] is not None:
                monthly[month]['low'].append(temps_low[i])
            if precip[i] is not None:
                monthly[month]['precip'].append(precip[i])
        
        # Calculate monthly averages and store
        with DB_CONN.cursor() as cur:
            for month in range(1, 13):
                if month not in monthly or not monthly[month]['high']:
                    continue
                
                avg_high = sum(monthly[month]['high']) / len(monthly[month]['high'])
                avg_low = sum(monthly[month]['low']) / len(monthly[month]['low'])
                avg_precip = sum(monthly[month]['precip']) / len(monthly[month]['precip'])
                
                # Detect climate risks
                extreme_cold = avg_low < 32
                extreme_heat = avg_high > 95
                freeze_risk = avg_low < 28
                
                cur.execute("""
                    INSERT INTO local_climate 
                    (city, state, month, avg_temp_high, avg_temp_low, precipitation,
                     extreme_cold_risk, extreme_heat_risk, freeze_risk)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (city, state, month) DO UPDATE SET
                        avg_temp_high = EXCLUDED.avg_temp_high,
                        avg_temp_low = EXCLUDED.avg_temp_low,
                        updated_at = NOW()
                """, (city, state, month, round(avg_high, 1), round(avg_low, 1),
                      round(avg_precip, 2), extreme_cold, extreme_heat, freeze_risk))
        
        # Generate climate summary
        winter_months = [m for m in [12, 1, 2] if m in monthly and monthly[m]['low']]
        summer_months = [m for m in [6, 7, 8] if m in monthly and monthly[m]['high']]
        
        if winter_months:
            winter_avg_low = sum(sum(monthly[m]['low']) / len(monthly[m]['low']) for m in winter_months) / len(winter_months)
        else:
            winter_avg_low = 40
            
        if summer_months:
            summer_avg_high = sum(sum(monthly[m]['high']) / len(monthly[m]['high']) for m in summer_months) / len(summer_months)
        else:
            summer_avg_high = 85
        
        summary = f"{city} experiences "
        impacts = []
        
        if summer_avg_high > 95:
            summary += f"extreme summer heat ({int(summer_avg_high)}°F+)"
            impacts.append("hvac: AC systems under extreme strain")
            
        if winter_avg_low < 32:
            if summary.endswith("experiences "):
                summary += f"occasional hard freezes (avg {int(winter_avg_low)}°F in winter)"
            else:
                summary += f" and occasional hard freezes (avg {int(winter_avg_low)}°F)"
            impacts.append("plumbing: Pipe burst risk in winter")
            impacts.append("roofing: Ice dam formation possible")
        
        if not impacts:
            summary += "mild temperatures year-round"
            impacts.append("general: Standard seasonal maintenance")
        
        # Store summary
        import json as json_module
        with DB_CONN.cursor() as cur:
            cur.execute("""
                INSERT INTO local_climate
                (city, state, month, climate_summary, service_impacts)
                VALUES (%s, %s, NULL, %s, %s::jsonb)
                ON CONFLICT (city, state, month) DO UPDATE SET
                    climate_summary = EXCLUDED.climate_summary,
                    updated_at = NOW()
            """, (city, state, summary.strip(), json_module.dumps(impacts)))
        
        DB_CONN.commit()
        
        print(f"✅ 12 months")
        return 12

    except Exception as e:
        DB_CONN.rollback()
        print(f"❌ Error: {str(e)[:50]}")
        return 0

def add_major_events(city, state):
    """Add major city events (hardcoded)"""
    
    # Major events by city
    events_map = {
        'Dallas': [
            ('State Fair of Texas', 'Annual state fair at Fair Park', '2026-09-15', '2026-10-15', 'Fair Park', 'fair', True),
            ('Dallas Cowboys Training Camp', 'NFL training camp open to public', '2026-07-20', '2026-08-15', 'The Star', 'sports', True)
        ],
        'Austin': [
            ('SXSW', 'Music, film and interactive media festival', '2026-03-10', '2026-03-19', 'Downtown Austin', 'festival', True),
            ('Austin City Limits Music Festival', 'Annual music festival', '2026-10-02', '2026-10-11', 'Zilker Park', 'festival', True)
        ],
        'Houston': [
            ('Houston Livestock Show and Rodeo', 'World\'s largest livestock show and rodeo', '2026-02-24', '2026-03-15', 'NRG Stadium', 'fair', True)
        ],
        'San Antonio': [
            ('Fiesta San Antonio', 'Annual cultural celebration', '2026-04-16', '2026-04-26', 'Citywide', 'festival', True)
        ],
        'Fort Worth': [
            ('Fort Worth Stock Show & Rodeo', 'Annual rodeo and livestock show', '2026-01-16', '2026-02-07', 'Will Rogers Memorial Center', 'fair', True)
        ]
    }
    
    events = events_map.get(city, [])
    
    if not events:
        return 0
    
    with DB_CONN.cursor() as cur:
        for title, desc, start, end, venue, event_type, is_major in events:
            cur.execute("""
                INSERT INTO local_events 
                (city, state, title, description, start_date, end_date, 
                 venue, event_type, data_source, is_major)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING
            """, (city, state, title, desc, start, end, venue, event_type, 'hardcoded', is_major))
    
    DB_CONN.commit()
    
    print(f"  🎉 Major events: {len(events)}")
    return len(events)

def bootstrap_city(city, state, lat, lon):
    """Bootstrap single city with all data"""
    
    print(f"\n{'─'*60}")
    print(f"🌆 [{city}, {state}]")
    
    start_time = time.time()
    
    # Fetch all data with rate limiting
    landmarks = fetch_landmarks(city, state, lat, lon)
    time.sleep(2)  # Rate limit for Overpass API
    
    neighborhoods = fetch_neighborhoods(city, state, lat, lon)
    time.sleep(2)
    
    climate = fetch_climate(city, state, lat, lon)
    time.sleep(1)
    
    events = add_major_events(city, state)
    
    elapsed = time.time() - start_time
    
    print(f"  ⏱️  Completed in {elapsed:.1f}s")
    
    return {
        'city': city,
        'state': state,
        'landmarks': landmarks,
        'neighborhoods': neighborhoods,
        'climate': climate,
        'events': events,
        'success': (landmarks > 0 or neighborhoods > 0)
    }

def main():
    """Bootstrap all 53 cities"""
    
    print("\n" + "=" * 60)
    print("🚀 REVFLOW LOCAL SIGNALS - FULL 53 CITY DEPLOYMENT")
    print("=" * 60)
    print()
    
    start_time = time.time()
    
    # Load cities from CSV
    cities = []
    try:
        with open('cities.csv', 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                cities.append({
                    'city': row['city'],
                    'state': row['state'],
                    'lat': float(row['lat']),
                    'lon': float(row['lon'])
                })
    except FileNotFoundError:
        print("❌ ERROR: cities.csv not found in current directory")
        print("   Make sure you're running from /opt/revrank_engine/local_signals/")
        sys.exit(1)
    
    print(f"📋 Loaded {len(cities)} cities from CSV")
    print(f"⏱️  Estimated time: ~{len(cities) * 6 / 60:.1f} hours (6 min per city average)")
    print()
    
    results = []
    for i, city_data in enumerate(cities, 1):
        print(f"[{i}/{len(cities)}]", end=" ")
        
        try:
            result = bootstrap_city(
                city_data['city'],
                city_data['state'],
                city_data['lat'],
                city_data['lon']
            )
            results.append(result)
        except Exception as e:
            DB_CONN.rollback()
            print(f"\n❌ FATAL ERROR for {city_data['city']}: {e}")
            results.append({
                'city': city_data['city'],
                'state': city_data['state'],
                'error': str(e),
                'success': False
            })
        
        # Progress checkpoint every 10 cities
        if i % 10 == 0:
            elapsed = time.time() - start_time
            avg_per_city = elapsed / i
            remaining = (len(cities) - i) * avg_per_city
            
            successful = sum(1 for r in results if r.get('success', False))
            
            print(f"\n{'─'*60}")
            print(f"⏱️  CHECKPOINT [{i}/{len(cities)} cities]")
            print(f"   Elapsed: {elapsed/60:.1f} min | Remaining: {remaining/60:.1f} min")
            print(f"   Success: {successful}/{i} cities")
            print(f"{'─'*60}\n")
    
    # Final summary
    elapsed = time.time() - start_time
    
    print("\n" + "=" * 60)
    print("✅ DEPLOYMENT COMPLETE")
    print("=" * 60)
    print(f"⏱️  Total time: {elapsed/60:.1f} minutes ({elapsed/3600:.1f} hours)")
    print(f"📊 Cities processed: {len(results)}")
    print()
    
    # Statistics
    successful = [r for r in results if r.get('success', False)]
    total_landmarks = sum(r.get('landmarks', 0) for r in successful)
    total_neighborhoods = sum(r.get('neighborhoods', 0) for r in successful)
    total_events = sum(r.get('events', 0) for r in successful)
    
    print(f"✅ Successful: {len(successful)}/{len(results)} cities")
    print(f"📍 Total landmarks: {total_landmarks}")
    print(f"🏘️  Total neighborhoods: {total_neighborhoods}")
    print(f"🎉 Total events: {total_events}")
    print()
    
    # Failed cities
    failed = [r for r in results if not r.get('success', False)]
    if failed:
        print(f"⚠️  Failed cities ({len(failed)}):")
        for f in failed:
            error = f.get('error', 'Unknown error')
            print(f"  • {f['city']}, {f['state']}: {error[:60]}")
        print()
    
    # Database verification
    print("🔍 Database verification:")
    with DB_CONN.cursor() as cur:
        cur.execute("SELECT COUNT(DISTINCT city) FROM local_landmarks")
        cities_with_landmarks = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(DISTINCT city) FROM local_neighborhoods")
        cities_with_neighborhoods = cur.fetchone()[0]
        
        print(f"   Cities with landmarks: {cities_with_landmarks}")
        print(f"   Cities with neighborhoods: {cities_with_neighborhoods}")
    
    print()
    print("🎯 Next steps:")
    print("   1. Review quality: python3 test_quality.py")
    print("   2. View sample data: psql -U revflow -d revflow_db")
    print("   3. Integrate with Module 3 for content enrichment")
    print()
    print("=" * 60)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Bootstrap interrupted by user")
        print("   Data collected so far has been saved to database")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n❌ FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
