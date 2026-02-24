"""
Parallel Conflict Scanner for RevPublish v2.0
Scans all WordPress sites for duplicate/conflicting content before deployment
"""

import asyncio
import aiohttp
import base64
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime
import sys
import os
import re
from difflib import SequenceMatcher

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from database import get_db_connection


@dataclass
class ContentMatch:
    """Represents a potential content conflict"""
    site_id: str
    site_url: str
    post_id: int
    post_title: str
    post_url: str
    match_type: str  # 'exact_title', 'similar_title', 'slug_conflict', 'content_overlap'
    similarity_score: float  # 0.0 to 1.0
    existing_status: str  # 'publish', 'draft', etc.
    created_date: str


@dataclass
class ScanResult:
    """Results from scanning a single site"""
    site_id: str
    site_url: str
    success: bool
    error: Optional[str] = None
    matches: List[ContentMatch] = field(default_factory=list)
    posts_scanned: int = 0
    scan_time_ms: int = 0


@dataclass
class ConflictReport:
    """Aggregated conflict scan report"""
    sites_scanned: int
    sites_with_conflicts: int
    total_conflicts: int
    conflicts_by_type: Dict[str, int]
    conflicts: List[ContentMatch]
    scan_duration_ms: int
    has_blocking_conflicts: bool  # True if any exact matches found

    def to_dict(self) -> Dict:
        return {
            'sites_scanned': self.sites_scanned,
            'sites_with_conflicts': self.sites_with_conflicts,
            'total_conflicts': self.total_conflicts,
            'conflicts_by_type': self.conflicts_by_type,
            'conflicts': [
                {
                    'site_id': c.site_id,
                    'site_url': c.site_url,
                    'post_id': c.post_id,
                    'post_title': c.post_title,
                    'post_url': c.post_url,
                    'match_type': c.match_type,
                    'similarity_score': round(c.similarity_score, 2),
                    'existing_status': c.existing_status,
                    'created_date': c.created_date
                }
                for c in self.conflicts
            ],
            'scan_duration_ms': self.scan_duration_ms,
            'has_blocking_conflicts': self.has_blocking_conflicts
        }


class ParallelConflictScanner:
    """
    Scans WordPress sites in parallel for content conflicts.
    Checks for duplicate titles, similar content, and URL slug conflicts.
    """

    # Similarity thresholds
    EXACT_MATCH_THRESHOLD = 0.95
    SIMILAR_TITLE_THRESHOLD = 0.70
    CONTENT_OVERLAP_THRESHOLD = 0.60

    # Concurrency limits
    MAX_CONCURRENT_SITES = 20
    REQUEST_TIMEOUT = 15

    def __init__(self):
        self.session = None

    async def scan_all_sites(
        self,
        proposed_title: str,
        proposed_content: str,
        proposed_slug: Optional[str] = None,
        target_sites: Optional[List[str]] = None
    ) -> ConflictReport:
        """
        Scan all configured sites for conflicts with proposed content.

        Args:
            proposed_title: Title of content to be deployed
            proposed_content: HTML/text content to be deployed
            proposed_slug: URL slug (optional, derived from title if not provided)
            target_sites: Optional list of site_ids to scan (defaults to all configured)

        Returns:
            ConflictReport with all found conflicts
        """
        start_time = datetime.now()

        # Get sites to scan
        sites = self._get_sites_to_scan(target_sites)

        if not sites:
            return ConflictReport(
                sites_scanned=0,
                sites_with_conflicts=0,
                total_conflicts=0,
                conflicts_by_type={},
                conflicts=[],
                scan_duration_ms=0,
                has_blocking_conflicts=False
            )

        # Derive slug if not provided
        if not proposed_slug:
            proposed_slug = self._generate_slug(proposed_title)

        # Create async session
        connector = aiohttp.TCPConnector(limit=self.MAX_CONCURRENT_SITES)
        timeout = aiohttp.ClientTimeout(total=self.REQUEST_TIMEOUT)

        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            self.session = session

            # Scan sites in parallel with semaphore for rate limiting
            semaphore = asyncio.Semaphore(self.MAX_CONCURRENT_SITES)
            tasks = [
                self._scan_site_with_semaphore(
                    semaphore, site, proposed_title, proposed_content, proposed_slug
                )
                for site in sites
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

        # Aggregate results
        all_conflicts: List[ContentMatch] = []
        sites_with_conflicts = 0
        conflicts_by_type: Dict[str, int] = {}

        for result in results:
            if isinstance(result, Exception):
                continue
            if isinstance(result, ScanResult) and result.success:
                if result.matches:
                    sites_with_conflicts += 1
                    all_conflicts.extend(result.matches)
                    for match in result.matches:
                        conflicts_by_type[match.match_type] = conflicts_by_type.get(match.match_type, 0) + 1

        # Check for blocking conflicts
        has_blocking = any(
            c.match_type == 'exact_title' or c.similarity_score >= self.EXACT_MATCH_THRESHOLD
            for c in all_conflicts
        )

        duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)

        return ConflictReport(
            sites_scanned=len(sites),
            sites_with_conflicts=sites_with_conflicts,
            total_conflicts=len(all_conflicts),
            conflicts_by_type=conflicts_by_type,
            conflicts=all_conflicts,
            scan_duration_ms=duration_ms,
            has_blocking_conflicts=has_blocking
        )

    async def _scan_site_with_semaphore(
        self,
        semaphore: asyncio.Semaphore,
        site: Dict,
        proposed_title: str,
        proposed_content: str,
        proposed_slug: str
    ) -> ScanResult:
        """Scan a site with semaphore for rate limiting"""
        async with semaphore:
            return await self._scan_single_site(site, proposed_title, proposed_content, proposed_slug)

    async def _scan_single_site(
        self,
        site: Dict,
        proposed_title: str,
        proposed_content: str,
        proposed_slug: str
    ) -> ScanResult:
        """Scan a single WordPress site for conflicts"""
        start_time = datetime.now()
        site_id = site['site_id']
        site_url = site['site_url'].rstrip('/')

        try:
            # Build auth header
            credentials = f"{site['wp_username']}:{site['app_password']}"
            auth_token = base64.b64encode(credentials.encode()).decode()
            headers = {
                'Authorization': f'Basic {auth_token}',
                'Content-Type': 'application/json'
            }

            # Fetch recent posts (last 100)
            api_url = f"{site_url}/wp-json/wp/v2/posts?per_page=100&status=any"

            async with self.session.get(api_url, headers=headers) as response:
                if response.status != 200:
                    return ScanResult(
                        site_id=site_id,
                        site_url=site_url,
                        success=False,
                        error=f"HTTP {response.status}"
                    )

                posts = await response.json()

            # Also fetch pages
            pages_url = f"{site_url}/wp-json/wp/v2/pages?per_page=100&status=any"
            try:
                async with self.session.get(pages_url, headers=headers) as response:
                    if response.status == 200:
                        pages = await response.json()
                        posts.extend(pages)
            except:
                pass  # Pages are optional

            # Check for conflicts
            matches: List[ContentMatch] = []

            for post in posts:
                post_title = post.get('title', {}).get('rendered', '')
                post_slug = post.get('slug', '')
                post_content = post.get('content', {}).get('rendered', '')
                post_id = post.get('id', 0)
                post_url = post.get('link', '')
                post_status = post.get('status', 'unknown')
                post_date = post.get('date', '')

                # Check title similarity
                title_similarity = self._calculate_similarity(proposed_title, post_title)

                if title_similarity >= self.EXACT_MATCH_THRESHOLD:
                    matches.append(ContentMatch(
                        site_id=site_id,
                        site_url=site_url,
                        post_id=post_id,
                        post_title=post_title,
                        post_url=post_url,
                        match_type='exact_title',
                        similarity_score=title_similarity,
                        existing_status=post_status,
                        created_date=post_date
                    ))
                elif title_similarity >= self.SIMILAR_TITLE_THRESHOLD:
                    matches.append(ContentMatch(
                        site_id=site_id,
                        site_url=site_url,
                        post_id=post_id,
                        post_title=post_title,
                        post_url=post_url,
                        match_type='similar_title',
                        similarity_score=title_similarity,
                        existing_status=post_status,
                        created_date=post_date
                    ))

                # Check slug conflict
                if self._slugs_conflict(proposed_slug, post_slug):
                    # Avoid duplicate entries
                    if not any(m.post_id == post_id and m.site_id == site_id for m in matches):
                        matches.append(ContentMatch(
                            site_id=site_id,
                            site_url=site_url,
                            post_id=post_id,
                            post_title=post_title,
                            post_url=post_url,
                            match_type='slug_conflict',
                            similarity_score=1.0,
                            existing_status=post_status,
                            created_date=post_date
                        ))

                # Check content overlap (only for significant content)
                if len(proposed_content) > 200 and len(post_content) > 200:
                    content_similarity = self._calculate_similarity(
                        self._strip_html(proposed_content),
                        self._strip_html(post_content)
                    )
                    if content_similarity >= self.CONTENT_OVERLAP_THRESHOLD:
                        if not any(m.post_id == post_id and m.site_id == site_id for m in matches):
                            matches.append(ContentMatch(
                                site_id=site_id,
                                site_url=site_url,
                                post_id=post_id,
                                post_title=post_title,
                                post_url=post_url,
                                match_type='content_overlap',
                                similarity_score=content_similarity,
                                existing_status=post_status,
                                created_date=post_date
                            ))

            scan_time = int((datetime.now() - start_time).total_seconds() * 1000)

            return ScanResult(
                site_id=site_id,
                site_url=site_url,
                success=True,
                matches=matches,
                posts_scanned=len(posts),
                scan_time_ms=scan_time
            )

        except asyncio.TimeoutError:
            return ScanResult(
                site_id=site_id,
                site_url=site_url,
                success=False,
                error="Timeout"
            )
        except Exception as e:
            return ScanResult(
                site_id=site_id,
                site_url=site_url,
                success=False,
                error=str(e)
            )

    def _get_sites_to_scan(self, target_sites: Optional[List[str]]) -> List[Dict]:
        """Get configured sites to scan"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            if target_sites:
                placeholders = ','.join(['%s'] * len(target_sites))
                cursor.execute(f"""
                    SELECT site_id, site_url, wp_username, app_password
                    FROM wordpress_sites
                    WHERE status = 'configured'
                    AND site_id IN ({placeholders})
                """, target_sites)
            else:
                cursor.execute("""
                    SELECT site_id, site_url, wp_username, app_password
                    FROM wordpress_sites
                    WHERE status = 'configured'
                """)
            return [dict(row) for row in cursor.fetchall()]

    def _calculate_similarity(self, str1: str, str2: str) -> float:
        """Calculate string similarity using SequenceMatcher"""
        if not str1 or not str2:
            return 0.0
        return SequenceMatcher(None, str1.lower(), str2.lower()).ratio()

    def _slugs_conflict(self, slug1: str, slug2: str) -> bool:
        """Check if two slugs would conflict"""
        # Normalize slugs
        s1 = slug1.lower().strip('-')
        s2 = slug2.lower().strip('-')

        # Exact match
        if s1 == s2:
            return True

        # WordPress appends -2, -3, etc. for conflicts
        if s1.startswith(s2) or s2.startswith(s1):
            remainder = s1.replace(s2, '') or s2.replace(s1, '')
            if re.match(r'^-?\d*$', remainder):
                return True

        return False

    def _generate_slug(self, title: str) -> str:
        """Generate URL slug from title"""
        slug = title.lower()
        slug = re.sub(r'[^\w\s-]', '', slug)
        slug = re.sub(r'[\s_]+', '-', slug)
        slug = re.sub(r'-+', '-', slug)
        return slug.strip('-')[:50]

    def _strip_html(self, html: str) -> str:
        """Remove HTML tags for content comparison"""
        clean = re.sub(r'<[^>]+>', ' ', html)
        clean = re.sub(r'\s+', ' ', clean)
        return clean.strip()


# Synchronous wrapper for use in FastAPI endpoints
def scan_for_conflicts(
    proposed_title: str,
    proposed_content: str,
    proposed_slug: Optional[str] = None,
    target_sites: Optional[List[str]] = None
) -> ConflictReport:
    """
    Synchronous wrapper for conflict scanning.
    Creates a new event loop if necessary.
    """
    scanner = ParallelConflictScanner()

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If already in async context, create new loop in thread
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    asyncio.run,
                    scanner.scan_all_sites(proposed_title, proposed_content, proposed_slug, target_sites)
                )
                return future.result()
        else:
            return loop.run_until_complete(
                scanner.scan_all_sites(proposed_title, proposed_content, proposed_slug, target_sites)
            )
    except RuntimeError:
        # No event loop exists
        return asyncio.run(
            scanner.scan_all_sites(proposed_title, proposed_content, proposed_slug, target_sites)
        )


# Singleton instance
conflict_scanner = ParallelConflictScanner()
