"""
RevFlow Local Signals Service
Module 3 Integration - Provides local intelligence for content enrichment

Fetches landmarks, neighborhoods, climate data, and events from PostgreSQL
to enrich rank & rent content with hyperlocal signals.
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Dict, List, Optional, Any
from functools import lru_cache
import json


class LocalSignalsService:
    """Service for fetching local intelligence data"""

    def __init__(self):
        self.db_config = {
            'dbname': os.getenv('POSTGRES_DB', 'revflow'),
            'user': os.getenv('POSTGRES_USER', 'postgres'),
            'password': os.getenv('POSTGRES_PASSWORD', 'revflow2026'),
            'host': 'localhost',
            'port': 5432
        }

    def _get_connection(self):
        """Get database connection"""
        return psycopg2.connect(**self.db_config)

    def get_city_signals(self, city: str, state: str) -> Dict[str, Any]:
        """
        Get all local signals for a city

        Returns:
            Dict with landmarks, neighborhoods, climate, and events
        """
        return {
            'city': city,
            'state': state,
            'landmarks': self.get_landmarks(city, state),
            'neighborhoods': self.get_neighborhoods(city, state),
            'climate': self.get_climate(city, state),
            'events': self.get_events(city, state)
        }

    def get_landmarks(self, city: str, state: str, limit: int = 10) -> List[Dict]:
        """Get top landmarks for a city"""
        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        SELECT name, category, importance, latitude, longitude
                        FROM local_landmarks
                        WHERE city = %s AND state = %s
                        ORDER BY importance DESC
                        LIMIT %s
                    """, (city, state, limit))
                    return [dict(row) for row in cur.fetchall()]
        except Exception as e:
            print(f"[LocalSignals] Error fetching landmarks: {e}")
            return []

    def get_neighborhoods(self, city: str, state: str, limit: int = 15) -> List[Dict]:
        """Get neighborhoods for a city"""
        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        SELECT name, admin_level, center_latitude, center_longitude
                        FROM local_neighborhoods
                        WHERE city = %s AND state = %s
                        ORDER BY name
                        LIMIT %s
                    """, (city, state, limit))
                    return [dict(row) for row in cur.fetchall()]
        except Exception as e:
            print(f"[LocalSignals] Error fetching neighborhoods: {e}")
            return []

    def get_climate(self, city: str, state: str) -> Dict[str, Any]:
        """Get climate summary for a city"""
        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    # Get summary (month=NULL)
                    cur.execute("""
                        SELECT climate_summary, service_impacts
                        FROM local_climate
                        WHERE city = %s AND state = %s AND month IS NULL
                    """, (city, state))
                    row = cur.fetchone()

                    if row:
                        return {
                            'summary': row['climate_summary'],
                            'service_impacts': row['service_impacts'] or []
                        }
                    return {'summary': None, 'service_impacts': []}
        except Exception as e:
            print(f"[LocalSignals] Error fetching climate: {e}")
            return {'summary': None, 'service_impacts': []}

    def get_events(self, city: str, state: str, limit: int = 5) -> List[Dict]:
        """Get upcoming events for a city"""
        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        SELECT title, description, start_date, end_date, venue, event_type, is_major
                        FROM local_events
                        WHERE city = %s AND state = %s
                        ORDER BY start_date
                        LIMIT %s
                    """, (city, state, limit))
                    results = []
                    for row in cur.fetchall():
                        r = dict(row)
                        # Convert dates to strings
                        if r.get('start_date'):
                            r['start_date'] = r['start_date'].isoformat()
                        if r.get('end_date'):
                            r['end_date'] = r['end_date'].isoformat()
                        results.append(r)
                    return results
        except Exception as e:
            print(f"[LocalSignals] Error fetching events: {e}")
            return []

    def enrich_content(self, city: str, state: str, service_type: str) -> Dict[str, Any]:
        """
        Generate content enrichment for a service in a city

        This is the main integration point for Module 3.
        Returns structured data for content generation.
        """
        signals = self.get_city_signals(city, state)

        # Build neighborhood list for "serving X, Y, Z" text
        neighborhood_names = [n['name'] for n in signals['neighborhoods'][:10]]

        # Get top landmarks for "near X" text
        top_landmarks = signals['landmarks'][:5]

        # Get climate impacts relevant to service
        climate = signals['climate']

        # Get upcoming major events
        major_events = [e for e in signals['events'] if e.get('is_major')]

        return {
            'city': city,
            'state': state,
            'service_type': service_type,
            'neighborhoods': {
                'list': neighborhood_names,
                'text': ', '.join(neighborhood_names[:3]) if neighborhood_names else city,
                'count': len(signals['neighborhoods'])
            },
            'landmarks': {
                'list': [{'name': l['name'], 'importance': l['importance']} for l in top_landmarks],
                'primary': top_landmarks[0]['name'] if top_landmarks else None,
                'count': len(signals['landmarks'])
            },
            'climate': {
                'summary': climate.get('summary'),
                'impacts': climate.get('service_impacts', [])
            },
            'events': {
                'upcoming': major_events[:3],
                'has_major': len(major_events) > 0
            },
            'content_snippets': self._generate_snippets(city, state, service_type, signals)
        }

    def _generate_snippets(self, city: str, state: str, service_type: str, signals: Dict) -> Dict[str, str]:
        """Generate ready-to-use content snippets"""
        snippets = {}

        # Neighborhood snippet
        neighborhoods = signals['neighborhoods'][:3]
        if neighborhoods:
            names = [n['name'] for n in neighborhoods]
            snippets['neighborhoods'] = f"Serving {', '.join(names)} and surrounding areas"
        else:
            snippets['neighborhoods'] = f"Serving {city} and surrounding areas"

        # Landmark snippet
        if signals['landmarks']:
            primary = signals['landmarks'][0]['name']
            snippets['location'] = f"Located near {primary} in {city}"
        else:
            snippets['location'] = f"Located in {city}, {state}"

        # Climate snippet
        climate = signals['climate']
        if climate.get('summary'):
            snippets['climate'] = climate['summary']

        # Event snippet
        major_events = [e for e in signals['events'] if e.get('is_major')]
        if major_events:
            event = major_events[0]
            snippets['event'] = f"With {event['title']} coming up, now's the perfect time to ensure your {service_type} needs are handled!"

        return snippets

    def get_available_cities(self) -> List[Dict[str, str]]:
        """Get list of all cities with local signals data"""
        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        SELECT DISTINCT city, state,
                               COUNT(*) as landmark_count
                        FROM local_landmarks
                        GROUP BY city, state
                        ORDER BY city
                    """)
                    return [dict(row) for row in cur.fetchall()]
        except Exception as e:
            print(f"[LocalSignals] Error fetching cities: {e}")
            return []

    def health_check(self) -> Dict[str, Any]:
        """Check service health"""
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT COUNT(*) FROM local_landmarks")
                    landmarks = cur.fetchone()[0]
                    cur.execute("SELECT COUNT(*) FROM local_neighborhoods")
                    neighborhoods = cur.fetchone()[0]
                    cur.execute("SELECT COUNT(DISTINCT city) FROM local_landmarks")
                    cities = cur.fetchone()[0]

            return {
                'status': 'healthy',
                'service': 'LocalSignalsService',
                'data': {
                    'cities': cities,
                    'landmarks': landmarks,
                    'neighborhoods': neighborhoods
                }
            }
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e)
            }


# Singleton instance
local_signals_service = LocalSignalsService()
