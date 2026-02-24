"""
WordPress REST API Client with PostgreSQL Storage
RevPublish Module 9 - RevFlow OS
"""

import requests
from typing import Dict, List, Optional
import base64
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from database import get_db_connection


class WordPressClient:
    """WordPress REST API client"""

    def __init__(self, site_url: str, username: str, app_password: str):
        self.site_url = site_url.rstrip('/')
        self.api_base = f"{self.site_url}/wp-json/wp/v2"
        self.username = username
        self.app_password = app_password
        self.session = requests.Session()

        # Set up authentication
        credentials = f"{username}:{app_password}"
        token = base64.b64encode(credentials.encode()).decode()
        self.session.headers.update({
            'Authorization': f'Basic {token}',
            'Content-Type': 'application/json'
        })

    def test_connection(self) -> Dict:
        """Test WordPress connection"""
        try:
            response = self.session.get(f"{self.site_url}/wp-json/", timeout=10)
            return {'success': response.status_code == 200, 'status': response.status_code}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def deploy_post(self, post_data: Dict, elementor_json: Dict) -> Dict:
        """Deploy post with Elementor data"""
        wp_post = {
            'title': post_data.get('title', ''),
            'content': post_data.get('content_html', ''),
            'excerpt': post_data.get('excerpt', ''),
            'status': post_data.get('status', 'draft')
        }

        try:
            response = self.session.post(f"{self.api_base}/posts", json=wp_post, timeout=30)
            if response.status_code == 201:
                post_id = response.json()['id']
                post_url = response.json().get('link', '')
                # Update with Elementor meta if provided
                if elementor_json:
                    self._update_elementor_meta(post_id, elementor_json)
                return {'success': True, 'post_id': post_id, 'post_url': post_url}
            else:
                return {'success': False, 'error': response.text, 'status_code': response.status_code}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _update_elementor_meta(self, post_id: int, elementor_json: Dict):
        """Update post with Elementor meta data"""
        import json
        meta_data = {
            '_elementor_data': json.dumps(elementor_json),
            '_elementor_edit_mode': 'builder',
            '_elementor_version': '3.0.0'
        }

        for key, value in meta_data.items():
            try:
                self.session.post(
                    f"{self.api_base}/posts/{post_id}/meta",
                    json={'key': key, 'value': value},
                    timeout=10
                )
            except:
                pass  # Non-critical if meta update fails


class WordPressClientManager:
    """Manages multiple WordPress clients with PostgreSQL persistence"""

    def __init__(self):
        self._clients_cache = {}

    def add_site(self, site_id: str, site_url: str, username: str, app_password: str) -> Dict:
        """Add or update a WordPress site in database"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO wordpress_sites (site_id, site_url, wp_username, app_password, status, updated_at)
                VALUES (%s, %s, %s, %s, 'configured', NOW())
                ON CONFLICT (site_id) DO UPDATE SET
                    site_url = EXCLUDED.site_url,
                    wp_username = EXCLUDED.wp_username,
                    app_password = EXCLUDED.app_password,
                    status = 'configured',
                    updated_at = NOW()
                RETURNING id
            """, (site_id, site_url, username, app_password))
            result = cursor.fetchone()

            # Test connection
            client = WordPressClient(site_url, username, app_password)
            test_result = client.test_connection()

            cursor.execute("""
                UPDATE wordpress_sites
                SET last_connection_test = NOW(),
                    connection_status = %s
                WHERE site_id = %s
            """, ('success' if test_result.get('success') else 'failed', site_id))

            return {
                'id': result['id'],
                'site_id': site_id,
                'connection_test': test_result
            }

    def get_client(self, site_id: str) -> WordPressClient:
        """Get WordPress client for site"""
        # Check cache first
        if site_id in self._clients_cache:
            return self._clients_cache[site_id]

        # Load from database
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT site_url, wp_username, app_password
                FROM wordpress_sites
                WHERE site_id = %s AND status = 'configured'
            """, (site_id,))
            row = cursor.fetchone()

            if not row:
                raise ValueError(f"Site not configured: {site_id}")

            if not row['wp_username'] or not row['app_password']:
                raise ValueError(f"Site {site_id} missing credentials")

            client = WordPressClient(row['site_url'], row['wp_username'], row['app_password'])
            self._clients_cache[site_id] = client
            return client

    def list_sites(self, status: Optional[str] = None) -> List[Dict]:
        """List all WordPress sites"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            if status:
                cursor.execute("""
                    SELECT id, site_id, site_url, site_name, status,
                           connection_status, last_connection_test, created_at
                    FROM wordpress_sites
                    WHERE status = %s
                    ORDER BY site_name
                """, (status,))
            else:
                cursor.execute("""
                    SELECT id, site_id, site_url, site_name, status,
                           connection_status, last_connection_test, created_at
                    FROM wordpress_sites
                    ORDER BY site_name
                """)
            return [dict(row) for row in cursor.fetchall()]

    def get_configured_sites(self) -> List[Dict]:
        """Get sites that have credentials configured"""
        return self.list_sites(status='configured')

    def delete_site(self, site_id: str) -> bool:
        """Delete a site from database"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM wordpress_sites WHERE site_id = %s", (site_id,))
            if site_id in self._clients_cache:
                del self._clients_cache[site_id]
            return cursor.rowcount > 0

    def test_all_connections(self) -> List[Dict]:
        """Test connections to all configured sites"""
        results = []
        sites = self.get_configured_sites()

        for site in sites:
            try:
                client = self.get_client(site['site_id'])
                test = client.test_connection()

                with get_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        UPDATE wordpress_sites
                        SET last_connection_test = NOW(),
                            connection_status = %s
                        WHERE site_id = %s
                    """, ('success' if test.get('success') else 'failed', site['site_id']))

                results.append({
                    'site_id': site['site_id'],
                    'site_url': site['site_url'],
                    **test
                })
            except Exception as e:
                results.append({
                    'site_id': site['site_id'],
                    'site_url': site.get('site_url', 'unknown'),
                    'success': False,
                    'error': str(e)
                })

        return results
