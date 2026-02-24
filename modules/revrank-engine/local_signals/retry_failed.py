#!/usr/bin/env python3
"""Retry failed cities with longer delays"""

import os
import sys
import time

# Add parent path for imports
sys.path.insert(0, '/opt/revrank_engine/local_signals')

from bootstrap_all_cities import fetch_landmarks, fetch_neighborhoods, DB_CONN

# Failed cities with their coordinates from cities.csv
FAILED_CITIES = [
    ('Allen', 'TX', 33.1032, -96.6706),
    ('Carrollton', 'TX', 32.9537, -96.8903),
    ('Cedar Park', 'TX', 30.5052, -97.8203),
    ('New Braunfels', 'TX', 29.7030, -98.1245),
    ('Tyler', 'TX', 32.3513, -95.3011),
    ('Longview', 'TX', 32.5007, -94.7405),
]

print("=" * 60)
print("🔄 RETRYING 6 FAILED CITIES (with 10s delay)")
print("=" * 60)
print()

success = 0
for i, (city, state, lat, lon) in enumerate(FAILED_CITIES, 1):
    print(f"[{i}/6] {city}, {state}")
    print("-" * 40)
    
    # Fetch landmarks with retry
    landmarks = fetch_landmarks(city, state, lat, lon)
    time.sleep(10)  # Longer delay to avoid rate limiting
    
    # Fetch neighborhoods
    neighborhoods = fetch_neighborhoods(city, state, lat, lon)
    time.sleep(10)
    
    if landmarks > 0 or neighborhoods > 0:
        success += 1
        print(f"  ✅ Success: {landmarks} landmarks, {neighborhoods} neighborhoods")
    else:
        print(f"  ❌ Still failed")
    print()

print("=" * 60)
print(f"📊 RETRY RESULTS: {success}/6 cities recovered")
print("=" * 60)

DB_CONN.close()
