"""
Content Ingestion Routes for RevPublish
Handles file uploads and content conversion from multiple formats
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from typing import List, Optional, Dict
import tempfile
import os
import sys
import shutil

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from converters.content_ingestor import content_ingestor, google_ingestor
from converters.template_engine import template_engine
from deployers.wordpress_client import WordPressClientManager

router = APIRouter()
wp_manager = WordPressClientManager()


class ContentIngestionRequest(BaseModel):
    """Ingest raw content string"""
    content: str
    content_type: str  # 'html', 'json', 'markdown', 'text'
    page_type_id: Optional[str] = None


class GoogleDocRequest(BaseModel):
    """Ingest from Google Doc by ID"""
    document_id: str
    page_type_id: Optional[str] = None


class GoogleSheetRequest(BaseModel):
    """Ingest from Google Sheet"""
    spreadsheet_id: str
    sheet_name: Optional[str] = None
    page_type_id: Optional[str] = None


class IngestAndDeployRequest(BaseModel):
    """Ingest content and deploy in one step"""
    content: str
    content_type: str
    page_type_id: str
    target_sites: List[str]
    status: str = "draft"


# === File Upload Ingestion ===

@router.post("/ingest/file")
async def ingest_file(
    file: UploadFile = File(...),
    page_type_id: Optional[str] = Form(None)
):
    """
    Upload and ingest a file.

    Supported formats:
    - DOCX (MS Word)
    - HTML
    - JSON
    - CSV (Google Sheets export)
    - MD (Markdown)
    - TXT (Plain text)
    """
    # Validate file extension
    filename = file.filename or "upload"
    suffix = os.path.splitext(filename)[1].lower()

    supported = ['.docx', '.html', '.htm', '.json', '.csv', '.md', '.txt']
    if suffix not in supported:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format: {suffix}. Supported: {', '.join(supported)}"
        )

    # Save to temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        result = content_ingestor.ingest_file(tmp_path, page_type_id)

        return {
            "success": True,
            "filename": filename,
            "format": suffix,
            "page_type_id": page_type_id,
            "extracted_data": result.get('data', {}),
            "metadata": result.get('metadata', {}),
            "is_batch": 'multiple_items' in result,
            "batch_count": len(result.get('multiple_items', []))
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Clean up temp file
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


@router.post("/ingest/content")
async def ingest_content(request: ContentIngestionRequest):
    """
    Ingest raw content string.

    content_type options:
    - html: HTML markup
    - json: JSON object or array
    - markdown: Markdown text
    - text: Plain text
    """
    try:
        result = content_ingestor.ingest_content(
            request.content,
            request.content_type,
            request.page_type_id
        )

        return {
            "success": True,
            "content_type": request.content_type,
            "page_type_id": request.page_type_id,
            "extracted_data": result.get('data', {}),
            "metadata": result.get('metadata', {}),
            "is_batch": 'multiple_items' in result,
            "batch_count": len(result.get('multiple_items', []))
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# === Google Integration ===

@router.post("/ingest/google-doc")
async def ingest_google_doc(request: GoogleDocRequest):
    """
    Ingest content from a Google Doc.

    Requires Google API credentials at /opt/revpublish/config/google_credentials.json

    document_id: The ID from the Google Docs URL
    (e.g., from https://docs.google.com/document/d/DOCUMENT_ID/edit)
    """
    try:
        result = google_ingestor.ingest_google_doc(
            request.document_id,
            request.page_type_id
        )

        return {
            "success": True,
            "source": "google_doc",
            "document_id": request.document_id,
            "page_type_id": request.page_type_id,
            "extracted_data": result.get('data', {}),
            "metadata": result.get('metadata', {})
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ingest/google-sheet")
async def ingest_google_sheet(request: GoogleSheetRequest):
    """
    Ingest data from a Google Sheet.

    Requires Google API credentials at /opt/revpublish/config/google_credentials.json

    spreadsheet_id: The ID from the Google Sheets URL
    sheet_name: Optional specific sheet (defaults to first sheet)
    """
    try:
        result = google_ingestor.ingest_google_sheet(
            request.spreadsheet_id,
            request.sheet_name,
            request.page_type_id
        )

        return {
            "success": True,
            "source": "google_sheet",
            "spreadsheet_id": request.spreadsheet_id,
            "sheet_name": request.sheet_name,
            "page_type_id": request.page_type_id,
            "extracted_data": result.get('data', {}),
            "metadata": result.get('metadata', {}),
            "is_batch": 'multiple_items' in result,
            "batch_count": len(result.get('multiple_items', []))
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# === Combined Ingest + Deploy ===

@router.post("/ingest-and-deploy")
async def ingest_and_deploy(request: IngestAndDeployRequest):
    """
    Ingest content and deploy to WordPress sites in one step.

    1. Parses content based on content_type
    2. Maps to page_type fields
    3. Generates page using template
    4. Deploys to target sites
    """
    try:
        # Step 1: Ingest content
        ingested = content_ingestor.ingest_content(
            request.content,
            request.content_type,
            request.page_type_id
        )

        extracted_data = ingested.get('data', {})

        # Step 2: Generate page content using template engine
        page_content = template_engine.generate_page_content(
            request.page_type_id,
            extracted_data
        )

        # Step 3: Deploy to sites
        results = []
        for site_id in request.target_sites:
            try:
                client = wp_manager.get_client(site_id)
                post_data = {
                    'title': page_content['title'],
                    'content_html': page_content['content'],
                    'excerpt': page_content.get('excerpt', ''),
                    'status': request.status
                }
                result = client.deploy_post(post_data, page_content['elementor_data'])
                results.append({
                    'site_id': site_id,
                    **result
                })
            except Exception as e:
                results.append({
                    'site_id': site_id,
                    'success': False,
                    'error': str(e)
                })

        successful = sum(1 for r in results if r.get('success'))

        return {
            "success": successful > 0,
            "ingestion": {
                "content_type": request.content_type,
                "fields_extracted": list(extracted_data.keys())
            },
            "generation": {
                "page_type": request.page_type_id,
                "title": page_content['title']
            },
            "deployment": {
                "total_sites": len(request.target_sites),
                "successful": successful,
                "failed": len(request.target_sites) - successful,
                "results": results
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ingest-file-and-deploy")
async def ingest_file_and_deploy(
    file: UploadFile = File(...),
    page_type_id: str = Form(...),
    target_sites: str = Form(...),  # Comma-separated site IDs
    status: str = Form("draft")
):
    """
    Upload a file, ingest it, and deploy to WordPress sites.

    target_sites: Comma-separated list of site IDs (or 'all' for all configured sites)
    """
    # Parse target sites
    if target_sites.lower() == 'all':
        configured_sites = wp_manager.get_configured_sites()
        site_ids = [s['site_id'] for s in configured_sites]
    else:
        site_ids = [s.strip() for s in target_sites.split(',')]

    if not site_ids:
        raise HTTPException(status_code=400, detail="No target sites specified")

    # Validate file
    filename = file.filename or "upload"
    suffix = os.path.splitext(filename)[1].lower()

    supported = ['.docx', '.html', '.htm', '.json', '.csv', '.md', '.txt']
    if suffix not in supported:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format: {suffix}"
        )

    # Save to temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        # Step 1: Ingest file
        ingested = content_ingestor.ingest_file(tmp_path, page_type_id)
        extracted_data = ingested.get('data', {})

        # Check for batch processing
        if 'multiple_items' in ingested:
            # Multiple items - process each
            all_results = []
            for item in ingested['multiple_items']:
                item_data = item.get('data', {})
                try:
                    page_content = template_engine.generate_page_content(page_type_id, item_data)

                    for site_id in site_ids:
                        try:
                            client = wp_manager.get_client(site_id)
                            post_data = {
                                'title': page_content['title'],
                                'content_html': page_content['content'],
                                'excerpt': page_content.get('excerpt', ''),
                                'status': status
                            }
                            result = client.deploy_post(post_data, page_content['elementor_data'])
                            all_results.append({
                                'title': page_content['title'],
                                'site_id': site_id,
                                **result
                            })
                        except Exception as e:
                            all_results.append({
                                'title': page_content.get('title', 'Unknown'),
                                'site_id': site_id,
                                'success': False,
                                'error': str(e)
                            })
                except Exception as e:
                    all_results.append({
                        'title': 'Error processing item',
                        'success': False,
                        'error': str(e)
                    })

            successful = sum(1 for r in all_results if r.get('success'))
            return {
                "success": successful > 0,
                "batch_mode": True,
                "items_processed": len(ingested['multiple_items']),
                "total_deployments": len(all_results),
                "successful": successful,
                "failed": len(all_results) - successful,
                "results": all_results
            }

        else:
            # Single item
            page_content = template_engine.generate_page_content(page_type_id, extracted_data)

            results = []
            for site_id in site_ids:
                try:
                    client = wp_manager.get_client(site_id)
                    post_data = {
                        'title': page_content['title'],
                        'content_html': page_content['content'],
                        'excerpt': page_content.get('excerpt', ''),
                        'status': status
                    }
                    result = client.deploy_post(post_data, page_content['elementor_data'])
                    results.append({'site_id': site_id, **result})
                except Exception as e:
                    results.append({'site_id': site_id, 'success': False, 'error': str(e)})

            successful = sum(1 for r in results if r.get('success'))
            return {
                "success": successful > 0,
                "batch_mode": False,
                "filename": filename,
                "page_type": page_type_id,
                "generated_title": page_content['title'],
                "total_sites": len(site_ids),
                "successful": successful,
                "failed": len(site_ids) - successful,
                "results": results
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


# === Format Info ===

@router.get("/ingest/formats")
async def get_supported_formats():
    """Get list of supported input formats"""
    return {
        "success": True,
        "formats": {
            "file_formats": [
                {"extension": ".docx", "name": "Microsoft Word", "description": "Word documents with headings, lists, tables"},
                {"extension": ".html", "name": "HTML", "description": "Web pages and HTML content"},
                {"extension": ".json", "name": "JSON", "description": "Structured data with field mappings"},
                {"extension": ".csv", "name": "CSV", "description": "Spreadsheet data (Google Sheets export)"},
                {"extension": ".md", "name": "Markdown", "description": "Markdown formatted text"},
                {"extension": ".txt", "name": "Plain Text", "description": "Simple text content"}
            ],
            "content_types": [
                {"type": "html", "description": "Raw HTML markup"},
                {"type": "json", "description": "JSON object or array"},
                {"type": "markdown", "description": "Markdown formatted text"},
                {"type": "text", "description": "Plain text"}
            ],
            "google_integration": {
                "google_docs": "Import directly from Google Docs using document ID",
                "google_sheets": "Import directly from Google Sheets using spreadsheet ID",
                "credentials_required": "/opt/revpublish/config/google_credentials.json"
            }
        }
    }
