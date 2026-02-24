"""
WordPress Deployment Engine for RevPublish
Handles media sideloading and Elementor page creation
"""
import os
import hashlib
from typing import Dict, Any, Optional
import httpx
from datetime import datetime

# RunPod media storage location
RUNPOD_MEDIA_PATH = os.getenv('RUNPOD_MEDIA_PATH', '/workspace/media')


def get_local_image_path(filename: str) -> Optional[str]:
    """
    Locate image file in RunPod workspace.
    """
    local_path = os.path.join(RUNPOD_MEDIA_PATH, filename)

    if os.path.exists(local_path):
        return local_path

    # Check subdirectories
    for root, dirs, files in os.walk(RUNPOD_MEDIA_PATH):
        if filename in files:
            return os.path.join(root, filename)

    return None


async def sideload_image_to_wp(site: dict, local_path: str, filename: str) -> Optional[int]:
    """
    Upload image from RunPod to WordPress Media Library.

    Args:
        site: WordPress site credentials
        local_path: Full path to image on RunPod
        filename: Desired filename in WordPress

    Returns:
        WordPress attachment ID or None on failure
    """
    if not os.path.exists(local_path):
        return None

    # Determine content type
    extension = filename.lower().split('.')[-1]
    content_types = {
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'png': 'image/png',
        'gif': 'image/gif',
        'webp': 'image/webp',
        'svg': 'image/svg+xml'
    }
    content_type = content_types.get(extension, 'application/octet-stream')

    async with httpx.AsyncClient(timeout=60.0) as client:
        with open(local_path, 'rb') as f:
            file_data = f.read()

        response = await client.post(
            f"{site['wp_api_url']}/wp/v2/media",
            auth=(site['wp_username'], site['wp_app_password']),
            headers={
                'Content-Type': content_type,
                'Content-Disposition': f'attachment; filename="{filename}"'
            },
            content=file_data
        )

        if response.status_code == 201:
            media_data = response.json()
            return media_data.get('id')

        return None


def process_runpod_assets(row_data: dict, doc_data: dict = None) -> Dict[str, Any]:
    """
    Process all assets for a row from RunPod storage.

    Args:
        row_data: Import row with image filenames
        doc_data: Raw Google Doc data (unused - images come from RunPod)

    Returns:
        Map of asset types to local file paths
    """
    assets = {}

    # Hero image
    if row_data.get('hero_image_filename'):
        path = get_local_image_path(row_data['hero_image_filename'])
        if path:
            assets['hero_image'] = {
                'local_path': path,
                'filename': row_data['hero_image_filename']
            }

    # Gallery images (if present)
    if row_data.get('gallery_images'):
        assets['gallery'] = []
        for img_filename in row_data['gallery_images']:
            path = get_local_image_path(img_filename)
            if path:
                assets['gallery'].append({
                    'local_path': path,
                    'filename': img_filename
                })

    return assets


async def deploy_to_elementor(
    site: dict,
    row_data: dict,
    asset_map: Dict[str, Any],
    conflict_action: str = 'create_new'
) -> Dict[str, Any]:
    """
    Deploy content to WordPress with Elementor formatting.

    Args:
        site: WordPress site credentials
        row_data: Merged field data for the page
        asset_map: Map of uploaded media IDs
        conflict_action: 'create_new' or 'override'

    Returns:
        Deployment result with post ID and status
    """
    from .elementor_mapper import generate_elementor_json

    async with httpx.AsyncClient(timeout=60.0) as client:
        # Upload hero image first
        hero_media_id = None
        if asset_map.get('hero_image'):
            hero_media_id = await sideload_image_to_wp(
                site,
                asset_map['hero_image']['local_path'],
                asset_map['hero_image']['filename']
            )

        # Generate Elementor JSON
        merged_fields = row_data.get('merged_fields', row_data.get('csv_fields', {}))
        elementor_json = generate_elementor_json(merged_fields, hero_media_id)

        # Determine slug
        base_slug = row_data.get('slug', 'untitled')
        final_slug = base_slug

        # Check for existing page if not overriding
        if conflict_action == 'create_new':
            # Append version suffix if slug exists
            check_response = await client.get(
                f"{site['wp_api_url']}/wp/v2/pages",
                params={"slug": base_slug},
                auth=(site['wp_username'], site['wp_app_password'])
            )
            if check_response.status_code == 200 and check_response.json():
                final_slug = f"{base_slug}-v2"

        # Create page payload
        page_data = {
            "title": merged_fields.get('hero_headline', merged_fields.get('title', 'Untitled')),
            "slug": final_slug,
            "status": "draft",  # Always create as draft for safety
            "content": "",  # Elementor handles content
            "meta": {
                "_elementor_edit_mode": "builder",
                "_elementor_template_type": "wp-page",
                "_elementor_data": elementor_json
            }
        }

        # Add SEO meta if available
        if merged_fields.get('meta_title'):
            page_data['meta']['_yoast_wpseo_title'] = merged_fields['meta_title']
        if merged_fields.get('meta_description'):
            page_data['meta']['_yoast_wpseo_metadesc'] = merged_fields['meta_description']

        # Create the page
        response = await client.post(
            f"{site['wp_api_url']}/wp/v2/pages",
            auth=(site['wp_username'], site['wp_app_password']),
            json=page_data
        )

        if response.status_code == 201:
            page_result = response.json()
            return {
                "success": True,
                "post_id": page_result.get('id'),
                "slug": final_slug,
                "media_id": hero_media_id,
                "action": "created",
                "edit_url": page_result.get('link', '').replace('?p=', 'wp-admin/post.php?post=') + '&action=elementor'
            }

        return {
            "success": False,
            "error": f"Failed to create page: {response.status_code}",
            "response": response.text[:500]
        }


async def batch_deploy(
    sites: list,
    rows: list,
    conflict_action: str = 'create_new',
    progress_callback=None
) -> Dict[str, Any]:
    """
    Deploy multiple rows to multiple sites.

    Args:
        sites: List of target WordPress sites
        rows: List of import rows with merged fields
        conflict_action: How to handle conflicts
        progress_callback: Optional callback for progress updates

    Returns:
        Summary of deployment results
    """
    results = {
        "total_deployments": 0,
        "successful": 0,
        "failed": 0,
        "details": []
    }

    for row_idx, row in enumerate(rows):
        # Process assets for this row
        asset_map = process_runpod_assets(row)

        for site in sites:
            result = await deploy_to_elementor(site, row, asset_map, conflict_action)
            results["total_deployments"] += 1

            if result.get("success"):
                results["successful"] += 1
            else:
                results["failed"] += 1

            results["details"].append({
                "row": row_idx,
                "site": site.get('domain'),
                "result": result
            })

            if progress_callback:
                progress = (row_idx + 1) / len(rows) * 100
                progress_callback(progress, f"Deployed to {site.get('domain')}")

    return results
