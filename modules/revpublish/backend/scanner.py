"""
Parallel Conflict Scanner for RevPublish
Checks all sites for existing slugs before deployment
"""
import asyncio
from typing import Dict, Any, List
import httpx
from datetime import datetime


async def check_site_for_slug(site: dict, slug: str, client: httpx.AsyncClient) -> Dict[str, Any]:
    """
    Check a single WordPress site for existing page with given slug.

    Returns:
        Dict with conflict status and details
    """
    try:
        # Query WP REST API for pages with this slug
        url = f"{site['wp_api_url']}/wp/v2/pages"
        params = {"slug": slug, "per_page": 1}

        response = await client.get(
            url,
            params=params,
            auth=(site.get('wp_username', ''), site.get('wp_app_password', '')),
            timeout=10.0
        )

        if response.status_code == 200:
            pages = response.json()
            if pages:
                page = pages[0]
                return {
                    "domain": site.get('domain', 'unknown'),
                    "has_conflict": True,
                    "existing_page_id": page.get("id"),
                    "existing_title": page.get("title", {}).get("rendered", ""),
                    "last_modified": page.get("modified", ""),
                    "status": page.get("status", ""),
                    "link": page.get("link", "")
                }

        return {
            "domain": site.get('domain', 'unknown'),
            "has_conflict": False
        }

    except httpx.TimeoutException:
        return {
            "domain": site.get('domain', 'unknown'),
            "has_conflict": False,
            "error": "timeout"
        }
    except Exception as e:
        return {
            "domain": site.get('domain', 'unknown'),
            "has_conflict": False,
            "error": str(e)
        }


async def scan_all_sites(sites: List[dict], slug: str) -> Dict[str, Any]:
    """
    Scan all sites in parallel for slug conflicts.
    Designed for speed - must complete in under 5 seconds for good UX.

    Args:
        sites: List of site dictionaries with wp_api_url, wp_username, wp_app_password
        slug: The page slug to check for

    Returns:
        Aggregated conflict report
    """
    start_time = datetime.utcnow()

    async with httpx.AsyncClient() as client:
        # Create tasks for parallel execution
        tasks = [check_site_for_slug(site, slug, client) for site in sites]

        # Execute all checks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

    # Process results
    conflicts = []
    errors = []
    clear_sites = []

    for result in results:
        if isinstance(result, Exception):
            errors.append({"error": str(result)})
        elif result.get("has_conflict"):
            conflicts.append(result)
        elif result.get("error"):
            errors.append(result)
        else:
            clear_sites.append(result.get("domain"))

    elapsed_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

    return {
        "has_conflicts": len(conflicts) > 0,
        "conflict_count": len(conflicts),
        "total_sites_checked": len(sites),
        "clear_count": len(clear_sites),
        "error_count": len(errors),
        "details": conflicts,
        "errors": errors if errors else None,
        "scan_time_ms": round(elapsed_ms, 2)
    }


async def scan_multiple_slugs(sites: List[dict], slugs: List[str]) -> Dict[str, Any]:
    """
    Scan multiple slugs across all sites.
    Useful for batch imports.
    """
    all_results = {}

    for slug in slugs:
        all_results[slug] = await scan_all_sites(sites, slug)

    # Aggregate summary
    total_conflicts = sum(r["conflict_count"] for r in all_results.values())

    return {
        "total_slugs_checked": len(slugs),
        "total_conflicts_found": total_conflicts,
        "has_any_conflicts": total_conflicts > 0,
        "results_by_slug": all_results
    }


# CLI support for manual scanning
if __name__ == "__main__":
    import argparse
    import sys

    sys.path.insert(0, '/opt/revflow-os/modules/revpublish/backend')
    from models import SessionLocal, RevPublishSite

    parser = argparse.ArgumentParser(description='Scan sites for slug conflicts')
    parser.add_argument('--slug', required=True, help='Slug to check for')
    args = parser.parse_args()

    db = SessionLocal()
    sites = db.query(RevPublishSite).filter(RevPublishSite.status == 'active').all()
    site_dicts = [
        {
            "domain": s.domain,
            "wp_api_url": s.wp_api_url,
            "wp_username": s.wp_username,
            "wp_app_password": s.wp_app_password
        }
        for s in sites
    ]
    db.close()

    print(f"Scanning {len(site_dicts)} sites for slug: {args.slug}")
    result = asyncio.run(scan_all_sites(site_dicts, args.slug))

    print(f"\nResults:")
    print(f"  Conflicts found: {result['conflict_count']}")
    print(f"  Sites clear: {result['clear_count']}")
    print(f"  Scan time: {result['scan_time_ms']}ms")

    if result['has_conflicts']:
        print("\nConflicting sites:")
        for c in result['details']:
            print(f"  - {c['domain']}: {c['existing_title']} (modified: {c['last_modified']})")
