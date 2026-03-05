from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes.dashboard import router as dashboard_router
from routes.deployment_enhanced import router as deploy_router
from routes.v2_routes import router as v2_router
from routes.hostinger import router as hostinger_router
from routes.wordpress_discovery import router as wordpress_discovery_router
from fastapi import UploadFile, File, Form, HTTPException
from typing import Optional, List, Dict, Any, Tuple
import pandas as pd
import io
import re
from datetime import datetime
import requests
from requests.auth import HTTPBasicAuth
import sys
import traceback
import copy
import builtins

import psycopg2
import os
import json
from urllib.parse import urlparse, parse_qs
from dotenv import load_dotenv

# Ensure backend logging does not crash on Windows charmap consoles.
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    # Non-fatal: keep default streams if reconfigure is unavailable.
    pass

# Final fallback: ensure print() never crashes request flow on cp1252/charmap consoles.
_ORIGINAL_PRINT = builtins.print

def _safe_print(*args, **kwargs):
    try:
        _ORIGINAL_PRINT(*args, **kwargs)
    except UnicodeEncodeError:
        normalized_args = []
        for value in args:
            text = str(value)
            text = text.encode("ascii", errors="backslashreplace").decode("ascii")
            normalized_args.append(text)
        _ORIGINAL_PRINT(*normalized_args, **kwargs)

builtins.print = _safe_print

# Load environment variables from .env file
# Try multiple locations for .env file
env_paths = [
    '../../.env',  # Project root
    '../.env',     # Module root
    '.env'         # Backend folder
]
for path in env_paths:
    if os.path.exists(path):
        load_dotenv(path)
        break

# RevAudit Anti-Hallucination Integration
sys.path.insert(0, '/opt/shared-api-engine')
try:
    from revaudit.integrate import integrate_revaudit
    REVAUDIT_AVAILABLE = True
except ImportError:
    REVAUDIT_AVAILABLE = False

app = FastAPI(title="RevPublish API v2.1", version="2.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global exception handler to ensure JSON responses
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "status": "error"}
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    return JSONResponse(
        status_code=422,
        content={"detail": str(exc), "status": "error"}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    import traceback
    error_detail = traceback.format_exc()
    print(f"Unhandled exception: {error_detail}", file=sys.stderr, flush=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": f"Internal server error: {str(exc)}",
            "status": "error",
            "type": type(exc).__name__
        }
    )

# RevAudit Integration
if REVAUDIT_AVAILABLE:
    integrate_revaudit(app, "RevPublish")

@app.get("/")
async def root():
    return {
        "app": "RevPublish™ v2.1",
        "status": "operational",
        "backend_port": 8550
    }

@app.get("/api/test")
async def test_endpoint():
    """Test endpoint to verify API routing works"""
    return {
        "status": "success",
        "message": "API routing is working",
        "endpoint": "/api/test"
    }

@app.get("/health")
async def health():
    """Health check endpoint with database status"""
    health_status = {
        "status": "healthy",
        "service": "revpublish",
        "backend_port": 8550
    }
    
    # Check database connection
    try:
        from routes.dashboard import get_db
        conn = get_db()
        cursor = conn.cursor()
        
        # Check if wordpress_sites table exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'wordpress_sites'
            )
        """)
        table_exists = cursor.fetchone()[0]
        
        cursor.close()
        conn.close()
        
        health_status["database"] = "connected"
        health_status["table_exists"] = table_exists
        if not table_exists:
            health_status["warning"] = "wordpress_sites table does not exist. Run setup_db.py to create it."
    except Exception as e:
        health_status["database"] = "disconnected"
        health_status["error"] = str(e)
        health_status["status"] = "degraded"
    
    return health_status

# TOP-LEVEL routes (NO prefix doubling!)
app.include_router(dashboard_router, prefix="/api", tags=["dashboard"])
app.include_router(hostinger_router, prefix="/api", tags=["hostinger"])
app.include_router(wordpress_discovery_router, prefix="/api", tags=["wordpress-discovery"])

# DEPLOYMENT routes (fixed prefixes)
app.include_router(deploy_router, tags=["deployment"])

# V2 routes (AI, conflicts, OAuth)
app.include_router(v2_router, tags=["v2.0"])
# ═══════════════════════════════════════════════
  # BULK IMPORT ENDPOINT
  # ═══════════════════════════════════════════════


# ═══════════════════════════════════════════════════════════════
# BULK IMPORT ENDPOINT
# ═══════════════════════════════════════════════════════════════

def normalize_phone_number(phone: str) -> tuple[str, bool]:
    if not phone or pd.isna(phone):
        return "", False
    original = str(phone)
    digits = re.sub(r'\D', '', original)
    if len(digits) == 11 and digits.startswith('1'):
        digits = digits[1:]
    if len(digits) != 10:
        return original, False
    normalized = f"{digits[0:3]}-{digits[3:6]}-{digits[6:10]}"
    return normalized, (normalized != original)

def merge_template_fields(template: str, row_data: Dict[str, Any]) -> str:
    """
    Merge template fields with CSV data.
    
    Supports:
    - Basic merge: [FIELD_NAME] → CSV value
    - Phone formatting: [PHONE] → formatted phone number
    - Email links: [EMAIL] → clickable mailto link
    - Phone links: [PHONE_LINK] → clickable tel link
    - List generation: [SERVICES_LIST] → HTML list from pipe-delimited field
    - Conditional blocks: [IF field=value]content[/IF]
    - Markdown: # Heading, **bold**, etc.
    """
    merged = template
    
    # Format phone numbers if present
    if 'phone' in row_data and row_data['phone']:
        phone = str(row_data['phone'])
        # Normalize phone format (remove non-digits, format as XXX-XXX-XXXX)
        digits = re.sub(r'\D', '', phone)
        if len(digits) == 10:
            formatted_phone = f"{digits[0:3]}-{digits[3:6]}-{digits[6:10]}"
            row_data['phone'] = formatted_phone
        elif len(digits) == 11 and digits.startswith('1'):
            formatted_phone = f"{digits[1:4]}-{digits[4:7]}-{digits[7:11]}"
            row_data['phone'] = formatted_phone
    
    # Replace basic merge fields first
    for field_name, field_value in row_data.items():
        field_placeholder = f"[{field_name.upper()}]"
        # Safely handle NaN, None, and empty values
        if pd.isna(field_value) or field_value is None:
            field_value = ""
        elif isinstance(field_value, float) and pd.isna(field_value):
            field_value = ""
        else:
            field_value = str(field_value)
        merged = merged.replace(field_placeholder, field_value)
    
    # Enhanced: Email link generation ([EMAIL] → clickable mailto link)
    if 'email' in row_data and row_data['email']:
        email_val = row_data['email']
        if email_val and not pd.isna(email_val):
            email = str(email_val).strip()
            if email and '@' in email:
                email_link = f'<a href="mailto:{email}">{email}</a>'
                merged = re.sub(r'\[EMAIL\]', email_link, merged, flags=re.IGNORECASE)
    
    # Enhanced: Phone link generation ([PHONE_LINK] → clickable tel link)
    if 'phone' in row_data and row_data['phone']:
        phone_val = row_data['phone']
        if phone_val and not pd.isna(phone_val):
            phone = str(phone_val)
            # Remove formatting for tel: link (digits only)
            phone_digits = re.sub(r'\D', '', phone)
            if len(phone_digits) == 10 or (len(phone_digits) == 11 and phone_digits.startswith('1')):
                if len(phone_digits) == 11:
                    phone_digits = phone_digits[1:]  # Remove leading 1
                phone_link = f'<a href="tel:{phone_digits}">{phone}</a>'
                merged = re.sub(r'\[PHONE_LINK\]', phone_link, merged, flags=re.IGNORECASE)
    
    # Enhanced: List generation from pipe-delimited fields
    # [SERVICES_LIST] → <ul><li>Service 1</li><li>Service 2</li></ul>
    services_pattern = r'\[SERVICES_LIST\]'
    if 'services_offered' in row_data and row_data['services_offered']:
        services_val = row_data['services_offered']
        if services_val and not pd.isna(services_val):
            services_str = str(services_val)
            if services_str and '|||' in services_str:
                services = [s.strip() for s in services_str.split('|||') if s.strip()]
                if services:
                    services_html = '<ul>' + ''.join([f'<li>{s}</li>' for s in services]) + '</ul>'
                    merged = re.sub(services_pattern, services_html, merged, flags=re.IGNORECASE)
    
    # Enhanced: Testimonials list generation
    testimonials_pattern = r'\[TESTIMONIALS_LIST\]'
    names_val = row_data.get('testimonial_names')
    texts_val = row_data.get('testimonial_texts')
    if names_val and not pd.isna(names_val) and texts_val and not pd.isna(texts_val):
        names_str = str(names_val)
        texts_str = str(texts_val)
        names = names_str.split('|||') if '|||' in names_str else [names_str]
        texts = texts_str.split('|||') if '|||' in texts_str else [texts_str]
        if names and texts:
            testimonials_html = '<div class="testimonials">'
            for i in range(min(len(names), len(texts))):
                name = names[i].strip() if i < len(names) else ''
                text = texts[i].strip() if i < len(texts) else ''
                if name and text:
                    testimonials_html += f'<div class="testimonial"><strong>{name}</strong><p>{text}</p></div>'
            testimonials_html += '</div>'
            merged = re.sub(testimonials_pattern, testimonials_html, merged, flags=re.IGNORECASE)
    
    # Conditional blocks: [IF field=value]content[/IF]
    def evaluate_condition(match):
        condition = match.group(1)
        content_if_true = match.group(2)
        if '=' in condition:
            field, expected_value = condition.split('=', 1)
            field = field.strip()
            expected_value = expected_value.strip()
            actual_value = str(row_data.get(field.lower(), '')).strip().lower()
            expected_value = expected_value.lower()
            if actual_value == expected_value:
                return content_if_true
        return ""
    
    merged = re.sub(r'\[IF\s+([^\]]+)\](.*?)\[/IF\]', evaluate_condition, merged, flags=re.DOTALL | re.IGNORECASE)
    
    # Markdown to HTML conversion
    merged = re.sub(r'^### (.+)$', r'<h3>\1</h3>', merged, flags=re.MULTILINE)
    merged = re.sub(r'^## (.+)$', r'<h2>\1</h2>', merged, flags=re.MULTILINE)
    merged = re.sub(r'^# (.+)$', r'<h1>\1</h1>', merged, flags=re.MULTILINE)
    merged = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', merged)
    
    return merged


def normalize_url(url: str) -> str:
    """Normalize URL for comparison (remove protocol, trailing slashes, www)"""
    if not url:
        return ""
    # Remove protocol
    url = url.replace('https://', '').replace('http://', '')
    # Remove trailing slash
    url = url.rstrip('/')
    # Remove www. prefix for comparison
    if url.startswith('www.'):
        url = url[4:]
    return url.lower().strip()

def get_wordpress_credentials(site_url: str) -> Optional[Dict[str, str]]:
    """
    Get WordPress credentials from database for a given site URL.
    Returns dict with username, password, api_url or None if not found.
    
    Credentials should be stored in wordpress_sites table:
    - wp_username: WordPress admin username
    - app_password: Application password (NOT regular password!)
    
    URL matching is normalized (removes http/https, trailing slashes, www)
    """
    try:
        # Use same database connection pattern as dashboard routes
        password = os.getenv("POSTGRES_PASSWORD") or "revflow2026"
        host = os.getenv("POSTGRES_HOST", "localhost")
        port = int(os.getenv("POSTGRES_PORT", "5432"))
        
        # Try Docker port if localhost
        if host == "localhost" and port == 5432:
            try:
                test_conn = psycopg2.connect(
                    host=host,
                    port=5433,
                    database=os.getenv("POSTGRES_DB", "revflow"),
                    user=os.getenv("POSTGRES_USER", "revflow"),
                    password=password,
                    connect_timeout=2
                )
                test_conn.close()
                port = 5433
            except:
                pass
        
        conn = psycopg2.connect(
            host=host,
            port=port,
            database=os.getenv("POSTGRES_DB", "revflow"),
            user=os.getenv("POSTGRES_USER", "revflow"),
            password=password
        )
        cursor = conn.cursor()
        
        # Normalize the input URL for comparison
        normalized_input = normalize_url(site_url)
        
        # Query wordpress_sites table - try exact match first, then normalized match
        # First try exact match
        cursor.execute("""
            SELECT wp_username, app_password, site_url 
            FROM wordpress_sites 
            WHERE site_url = %s OR site_url = %s OR site_url = %s
            LIMIT 1
        """, (site_url, f"https://{normalized_input}", f"http://{normalized_input}"))
        
        row = cursor.fetchone()
        
        # If no exact match, try normalized comparison
        if not row:
            cursor.execute("""
                SELECT wp_username, app_password, site_url 
                FROM wordpress_sites
            """)
            all_rows = cursor.fetchall()
            for db_row in all_rows:
                db_url = db_row[2]
                if normalize_url(db_url) == normalized_input:
                    row = db_row
                    break
        
        cursor.close()
        conn.close()
        
        if row and row[0] and row[1]:  # Ensure username and password exist
            # Use the stored site_url from database, but normalize for API URL
            stored_url = row[2]
            clean_url = normalize_url(stored_url)
            
            # Determine protocol (prefer https)
            if stored_url.startswith('http://'):
                protocol = 'http://'
            else:
                protocol = 'https://'
            
            return {
                'username': row[0],
                'password': row[1],
                'api_url': f"{protocol}{clean_url}/wp-json/wp/v2"
            }
        
        # No credentials found
        print(f"[WARN] No WordPress credentials found for {site_url} (normalized: {normalized_input})", flush=True)
        return None
    except Exception as e:
        print(f"[ERROR] Error getting WordPress credentials for {site_url}: {e}", file=sys.stderr, flush=True)
        import traceback
        traceback.print_exc()
        return None


def _parse_int(value: Any) -> Optional[int]:
    """Safely parse integer values from CSV/form inputs."""
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if text.isdigit():
        parsed = int(text)
        return parsed if parsed > 0 else None
    return None


def _extract_slug_from_page_url(page_url: str) -> Optional[str]:
    """Extract slug from a WordPress page URL when possible."""
    if not page_url:
        return None
    parsed = urlparse(str(page_url).strip())
    path = parsed.path.strip("/")
    if not path:
        return None
    # Ignore wp-admin and API style paths.
    if path.startswith("wp-") or "/wp-" in path:
        return None
    parts = [p for p in path.split("/") if p]
    if not parts:
        return None
    return parts[-1].strip() or None


def _find_page_id_by_slug(site_url: str, slug: str) -> Optional[int]:
    """Find a WordPress page ID by slug on the selected site."""
    creds = get_wordpress_credentials(site_url)
    if not creds:
        return None

    try:
        response = requests.get(
            f"{creds['api_url'].rstrip('/')}/pages",
            params={"slug": slug, "per_page": 1, "_fields": "id"},
            auth=(creds["username"], creds["password"]),
            timeout=15
        )
        if response.status_code == 200:
            pages = response.json()
            if pages and isinstance(pages, list):
                return _parse_int(pages[0].get("id"))
        return None
    except Exception:
        return None


def resolve_target_page_id(row_data: Dict[str, Any], site_url: str) -> Tuple[Optional[int], Optional[str]]:
    """
    Resolve a target WordPress page ID from CSV row fields.
    Priority:
    1) explicit page ID columns
    2) page URL columns (supports ?page_id=123 and slug lookup)
    3) slug columns
    """
    id_columns = ["existing_page_id", "target_page_id", "page_id", "wp_post_id", "wordpress_page_id"]
    for col in id_columns:
        parsed = _parse_int(row_data.get(col))
        if parsed:
            return parsed, col

    url_columns = ["existing_page_url", "target_page_url", "page_url", "wp_page_url"]
    for col in url_columns:
        raw_url = str(row_data.get(col, "")).strip()
        if not raw_url:
            continue
        parsed = urlparse(raw_url)
        q = parse_qs(parsed.query)
        page_id_from_query = _parse_int((q.get("page_id") or [None])[0])
        if page_id_from_query:
            return page_id_from_query, f"{col}:page_id"

        slug = _extract_slug_from_page_url(raw_url)
        if slug:
            matched_id = _find_page_id_by_slug(site_url, slug)
            if matched_id:
                return matched_id, f"{col}:slug"

    slug_columns = ["existing_page_slug", "target_page_slug", "page_slug", "slug"]
    for col in slug_columns:
        raw_slug = str(row_data.get(col, "")).strip().strip("/")
        if not raw_slug:
            continue
        matched_id = _find_page_id_by_slug(site_url, raw_slug)
        if matched_id:
            return matched_id, col

    return None, None


def _extract_google_doc_urls(value: Any) -> List[str]:
    """Extract Google Docs URLs from a free-form cell value."""
    if value is None:
        return []
    raw = str(value).strip()
    if not raw:
        return []
    # Accept values that may contain one or more doc URLs separated by spaces/commas/new lines.
    matches = re.findall(r"https?://docs\.google\.com/document/d/[^\s,;]+", raw, flags=re.IGNORECASE)
    return [m.strip() for m in matches if m and m.strip()]


def collect_google_doc_urls_from_row(row_data: Dict[str, Any]) -> List[str]:
    """
    Collect Google Doc URLs from common CSV columns.
    Supports single or multiple docs per row and de-duplicates while preserving order.
    """
    candidate_columns = [
        "page_content_doc_url",
        "page_content_doc_url_1",
        "page_content_doc_url_2",
        "doc_url",
        "doc_url_1",
        "doc_url_2",
        "google_doc_url",
        "google_doc_url_1",
        "google_doc_url_2",
        "content_doc_url",
    ]

    # Include any additional columns that look like doc-url fields.
    for key in row_data.keys():
        key_l = str(key).strip().lower()
        if key_l in candidate_columns:
            continue
        if "doc" in key_l and "url" in key_l:
            candidate_columns.append(key)

    ordered_urls: List[str] = []
    seen: set = set()
    for column in candidate_columns:
        if column not in row_data:
            continue
        for url in _extract_google_doc_urls(row_data.get(column)):
            norm = url.strip()
            if not norm:
                continue
            if norm in seen:
                continue
            seen.add(norm)
            ordered_urls.append(norm)

    return ordered_urls


@app.get("/api/site-pages")
async def list_site_pages(site_url: str, per_page: int = 100):
    """List pages for a registered WordPress site to support page-targeted updates."""
    creds = get_wordpress_credentials(site_url)
    if not creds:
        raise HTTPException(status_code=400, detail=f"No WordPress credentials found for {site_url}")

    try:
        response = requests.get(
            f"{creds['api_url'].rstrip('/')}/pages",
            params={
                "per_page": per_page,
                "orderby": "modified",
                "order": "desc",
                "_fields": "id,title,slug,link,status"
            },
            auth=(creds["username"], creds["password"]),
            timeout=20
        )
        if response.status_code != 200:
            raise HTTPException(
                status_code=502,
                detail=f"WordPress API returned {response.status_code}: {response.text[:180]}"
            )

        pages = response.json() if isinstance(response.json(), list) else []
        normalized = []
        for p in pages:
            page_id = _parse_int(p.get("id"))
            if not page_id:
                continue
            title = (p.get("title") or {}).get("rendered", "") or "(Untitled)"
            slug = p.get("slug", "")
            status = p.get("status", "")
            normalized.append({
                "id": page_id,
                "title": title,
                "slug": slug,
                "status": status,
                "link": p.get("link"),
                "display_name": f"{title} (ID: {page_id})"
            })

        return {"status": "success", "site_url": site_url, "total": len(normalized), "pages": normalized}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch pages for {site_url}: {str(e)}")


def _count_elementor_widgets(data: Any) -> int:
    count = 0
    if isinstance(data, list):
        for item in data:
            count += _count_elementor_widgets(item)
    elif isinstance(data, dict):
        if data.get("elType") == "widget":
            count += 1
        for v in data.values():
            count += _count_elementor_widgets(v)
    return count


def fetch_elementor_template_from_site(site_url: str, page_id: int) -> Optional[Any]:
    """
    Fetch Elementor JSON for an existing WordPress page.
    Tries native WP v2 meta first, then RevPublish connector fallback.
    """
    creds = get_wordpress_credentials(site_url)
    if not creds:
        return None

    auth = (creds["username"], creds["password"])
    api_v2 = creds["api_url"].rstrip("/")
    wp_json_base = api_v2.replace("/wp/v2", "")
    site_base = wp_json_base.replace("/wp-json", "")

    candidates = [
        f"{api_v2}/pages/{page_id}?context=edit&_fields=id,title,meta",
        f"{api_v2}/posts/{page_id}?context=edit&_fields=id,title,meta",
        f"{site_base}/index.php?rest_route=/wp/v2/pages/{page_id}&context=edit&_fields=id,title,meta",
        f"{site_base}/?rest_route=/wp/v2/pages/{page_id}&context=edit&_fields=id,title,meta",
    ]

    for url in candidates:
        try:
            r = requests.get(url, auth=auth, timeout=20, headers={"Accept": "application/json"})
            if r.status_code != 200:
                continue
            payload = r.json()
            if not isinstance(payload, dict):
                continue
            meta = payload.get("meta", {})
            raw = meta.get("_elementor_data") if isinstance(meta, dict) else None
            if raw is None:
                continue
            if isinstance(raw, str):
                raw = json.loads(raw)
            if isinstance(raw, (list, dict)):
                return raw
        except Exception:
            continue

    # Connector fallback endpoint (plugin exposes elementor-json, not elementor-template)
    fallback_candidates = [
        f"{wp_json_base}/revpublish/v1/elementor-json?page_id={page_id}",
        f"{site_base}/index.php?rest_route=/revpublish/v1/elementor-json&page_id={page_id}",
        f"{site_base}/?rest_route=/revpublish/v1/elementor-json&page_id={page_id}",
    ]
    for url in fallback_candidates:
        try:
            r = requests.get(url, auth=auth, timeout=20, headers={"Accept": "application/json"})
            if r.status_code != 200:
                continue
            data = r.json()
            raw = data.get("elementor_data") if isinstance(data, dict) else None
            if isinstance(raw, str):
                raw = json.loads(raw)
            if isinstance(raw, (list, dict)):
                return raw
        except Exception:
            continue

    return None


def _strip_html_to_text(value: str) -> str:
    text = re.sub(r"<[^>]+>", " ", str(value or ""))
    text = re.sub(r"\s+", " ", text).strip()
    return text


_HEADING_KEYS = {"title", "heading", "subtitle", "sub_title", "heading_title", "title_text"}
_PARAGRAPH_KEYS = {"editor", "description", "content", "text", "paragraph", "caption", "desc", "description_text"}
_BUTTON_KEYS = {"button_text", "btn_text", "cta_text", "label", "button_label", "text"}

# Instructional labels that appear in user raw content as guides only — never place these as slot content.
_INSTRUCTIONAL_PHRASES = frozenset({
    "page content:", "hero section", "headline:", "short paragraph:", "button:",
    "main heading:", "paragraph:", "small label:", "intro text:", "services list:",
    "feature 1:", "feature 2:", "example:", "project titles:", "testimonial 1:", "testimonial 2:",
    "counters (update properly):", "blog titles (improved):", "left side:", "right side:",
    "about section", "detailed services section (blue background)", "expert team section",
    "projects section", "testimonials section", "blog section", "quote section",
    "call to action section", "service highlights (3 boxes section)", "read more", "learn more",
    "submit request", "heading:", "label:", "small label", "main heading", "paragraph",
    "intro text", "services list", "button", "headline", "short paragraph",
})
# Lines that are only a section/label (e.g. "Hero Section (Main Banner)", "Headline:") — treat as instructional
_INSTRUCTIONAL_LINE_PATTERN = re.compile(
    r"^(?:hero\s+section|headline|short\s+paragraph|button|main\s+heading|paragraph|small\s+label|intro\s+text|services\s+list|feature\s+[12]|example|project\s+titles|testimonial\s+[12]|about\s+section|expert\s+team\s+section|projects\s+section|testimonials\s+section|blog\s+section|quote\s+section|call\s+to\s+action|service\s+highlights|page\s+content)(?:\s*\([^)]*\))?\s*:?\s*$",
    re.IGNORECASE
)

def _is_instructional_only(text: str) -> bool:
    """True if the text is empty or is only an instructional label (e.g. 'Headline:', 'Hero Section (Main Banner)')."""
    t = (text or "").strip()
    if not t:
        return True
    t_lower = t.lower()
    if t_lower in _INSTRUCTIONAL_PHRASES:
        return True
    if _INSTRUCTIONAL_LINE_PATTERN.match(t):
        return True
    # Single line that is only a label: ends with colon or "Label (Something)" and is short (e.g. "Main Heading:", "Hero Section (Main Banner)")
    if len(t) < 60 and (t.rstrip().endswith(":") or re.search(r"\([^)]+\)\s*:?\s*$", t)):
        if re.match(r"^[A-Za-z][A-Za-z0-9\s\-&']*(?:\s*\([^)]*\))?\s*:?\s*$", t):
            return True
    return False


def _strip_instructional_from_content(content: str) -> str:
    """
    Remove instructional lines from content so only actual copy remains.
    Used so 'Headline:', 'Short Paragraph:', 'Hero Section' etc. never end up as slot values.
    """
    if not (content or "").strip():
        return ""
    lines = []
    for line in (content or "").splitlines():
        stripped = line.strip()
        if not stripped:
            lines.append(line)
            continue
        if _is_instructional_only(stripped):
            continue
        lines.append(line)
    result = "\n".join(lines).strip()
    # Also strip leading "Page content:" line if present
    result = re.sub(r"(?im)^\s*page\s+content\s*:?\s*[\r\n]+", "", result, count=1).strip()
    return result


_IGNORE_KEY_FRAGMENTS = {
    "color", "typography", "font", "margin", "padding", "background", "border",
    "size", "icon", "image", "url", "link", "class", "id", "align", "width", "height",
    "animation", "style", "shadow", "overlay"
}


def _classify_text_key(key: str, value: str) -> Optional[str]:
    k = str(key or "").strip().lower()
    if not k or k.startswith("_"):
        return None
    if any(part in k for part in _IGNORE_KEY_FRAGMENTS):
        return None
    raw_val = str(value or "").strip().lower()
    if raw_val.startswith("{") or "http" in raw_val:
        return None
    if k in _HEADING_KEYS or ("title" in k and "button" not in k):
        return "heading"
    if k in _BUTTON_KEYS or "button" in k or "cta" in k:
        return "button"
    if k in _PARAGRAPH_KEYS:
        return "paragraph"
    return None


def _extract_slot_value_map_from_html(content_html: str) -> Dict[str, str]:
    """
    Parse content that follows SLOT_### labels and return slot -> value.
    """
    html = str(content_html or "")
    normalized = re.sub(r"(?i)<\s*br\s*/?\s*>", "\n", html)
    normalized = re.sub(r"(?i)</\s*(p|li|h[1-6]|div)\s*>", "\n", normalized)
    normalized = re.sub(r"<[^>]+>", "", normalized)
    normalized = re.sub(r"\r\n?", "\n", normalized)
    slot_map: Dict[str, str] = {}
    # Allow optional [Label] after slot ID so "SLOT_001 [About US]:" is recognized
    pattern = r"(?ims)(?:^|\n)\s*(SLOT_\d{3})\s*(?:\[[^\]]*\])?\s*:\s*(.*?)(?=(?:\n\s*SLOT_\d{3}\s*(?:\[[^\]]*\])?\s*:)|\Z)"
    for m in re.finditer(pattern, normalized):
        slot_id = str(m.group(1)).strip().upper()
        value = _strip_html_to_text(m.group(2))
        if value:
            value = re.sub(r"(?im)^\s*page\s+content\s*:?\s*[\r\n]+", "", value, count=1).strip()
            value = re.sub(r"(?im)^\s*page\s+image\s+url\s*:?\s*[\r\n]+", "", value, count=1).strip()
        if value:
            slot_map[slot_id] = value
    return slot_map


def _slot_label_from_page_content(current_value: str, widget_type: str, field_key: str, max_length: int = 42) -> str:
    """
    Derive slot label from the page JSON content only (dynamic, no static strings).
    Uses the slot's current text, cleaned and truncated. Fallback to widget/field when empty.
    """
    raw = _strip_html_to_text(current_value or "")
    # Decode common HTML entities so label is readable
    raw = raw.replace("&hellip;", "…").replace("&mdash;", "—").replace("&ldquo;", '"').replace("&rdquo;", '"')
    raw = raw.replace("&rsquo;", "'").replace("&amp;", "&").replace("&#10024;", "✨")
    raw = re.sub(r"&#\d+;", " ", raw)  # numeric entities -> space
    raw = re.sub(r"\s+", " ", raw).strip()
    if raw and len(raw) > max_length:
        raw = raw[: max_length - 1].rstrip() + "…"
    if raw:
        return raw
    # Empty slot: use widget/field from page JSON so it's still dynamic
    w = (widget_type or "").strip() or "widget"
    f = (field_key or "").strip() or "content"
    return f"{w} ({f})"


def _collect_template_slots(template_data: Any) -> List[Dict[str, Any]]:
    """
    Collect editable text slots from Elementor JSON using depth-first search (DFS).
    Elementor data is a recursive tree: Document -> Section -> Column -> Widget -> Inner Section -> ...
    DFS ensures we find every content field at any depth (e.g. a button inside a nested inner section).
    """
    slots: List[Dict[str, Any]] = []
    slot_counter = 0

    def add_slot(kind: str, widget_type: str, field_key: str, current_value: str) -> None:
        nonlocal slot_counter
        slot_counter += 1
        slot_id = f"SLOT_{slot_counter:03d}"
        stripped = _strip_html_to_text(current_value or "")
        label = _slot_label_from_page_content(current_value or "", widget_type, field_key)
        slots.append({
            "slot_id": slot_id,
            "kind": kind,
            "widget_type": widget_type or "unknown",
            "field_key": field_key,
            "current_value": stripped,
            "label": label,
        })

    def process_elementor_data(data: Any) -> None:
        """DFS: process list of elements; for each, read settings content then recurse into elements."""
        if isinstance(data, list):
            for element in data:
                process_elementor_data(element)
            return
        if not isinstance(data, dict):
            return
        # 1. If this node is a widget, extract content from settings (title, editor, text, etc.)
        if data.get("elType") == "widget":
            widget_type = (data.get("widgetType") or "").strip()
            settings = data.get("settings")
            if isinstance(settings, dict):
                if widget_type == "heading" and isinstance(settings.get("title"), str):
                    add_slot("heading", widget_type, "title", settings.get("title", ""))
                elif widget_type == "text-editor" and isinstance(settings.get("editor"), str):
                    add_slot("paragraph", widget_type, "editor", settings.get("editor", ""))
                elif widget_type == "button" and isinstance(settings.get("text"), str):
                    add_slot("button", widget_type, "text", settings.get("text", ""))
                elif widget_type == "image":
                    img_url = None
                    if isinstance(settings.get("image"), dict) and (settings.get("image") or {}).get("url"):
                        img_url = (settings["image"].get("url") or "").strip()
                    if not img_url and isinstance(settings.get("url"), str):
                        img_url = (settings.get("url") or "").strip()
                    if img_url:
                        add_slot("image", widget_type, "image", img_url)
                elif widget_type == "dit-button" and isinstance(settings.get("button_text"), str):
                    add_slot("button", widget_type, "button_text", settings.get("button_text", ""))
                elif widget_type == "iconbox":
                    if isinstance(settings.get("title_text"), str) and settings.get("title_text", "").strip():
                        add_slot("heading", widget_type, "title_text", settings.get("title_text", ""))
                    if isinstance(settings.get("description_text"), str) and settings.get("description_text", "").strip():
                        add_slot("paragraph", widget_type, "description_text", settings.get("description_text", ""))
                elif widget_type == "section-title":
                    for key in ("title", "subtitle", "title_two", "highlight_text", "description"):
                        if isinstance(settings.get(key), str) and settings.get(key, "").strip():
                            add_slot("heading" if key != "description" else "paragraph", widget_type, key, settings.get(key, ""))
                elif widget_type == "service":
                    for key in ("title_text", "title_tex_two", "description_text", "button_text"):
                        if isinstance(settings.get(key), str) and settings.get(key, "").strip():
                            add_slot("button" if key == "button_text" else ("heading" if "title" in key else "paragraph"), widget_type, key, settings.get(key, ""))
                else:
                    for k, v in settings.items():
                        if isinstance(v, str) and v.strip():
                            kind = _classify_text_key(k, v)
                            if kind:
                                add_slot(kind, widget_type, k, v)
                        elif isinstance(v, list):
                            for item in v:
                                if not isinstance(item, dict):
                                    continue
                                for rk, rv in item.items():
                                    if isinstance(rv, str) and rv.strip() and rk != "_id":
                                        kind = _classify_text_key(rk, rv)
                                        if kind:
                                            add_slot(kind, widget_type, rk, rv)
        # 2. Recurse into children (Section -> Column -> Widget | Inner Section -> ...)
        elements = data.get("elements")
        if isinstance(elements, list) and elements:
            process_elementor_data(elements)

    process_elementor_data(template_data)
    return slots


def _build_slot_template_text(slots: List[Dict[str, Any]]) -> str:
    lines = [
        "Fill content using exact SLOT labels. Do not rename slot IDs.",
        "Text slots: replace 'Page content' with your text. Image slots: replace 'Page image URL' with your image URL.",
        ""
    ]
    for s in slots:
        label = (s.get("label") or "Content").strip()
        kind = (s.get("kind") or "paragraph").lower()
        lines.append(f"{s['slot_id']} [{label}]:")
        if kind == "image":
            lines.append("Page image URL:")
            current = (s.get("current_value") or "").strip()
            lines.append(current if current else "[No image URL - add image URL here]")
        else:
            lines.append("Page content:")
            current = (s.get("current_value") or "").strip()
            lines.append(current if current else "[No content on page - add your text here]")
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def _build_filled_slot_template_text(slots: List[Dict[str, Any]], slot_value_map: Dict[str, str]) -> str:
    """
    Build template text with slot values filled. No instructional header lines;
    only SLOT_xxx blocks so the same text can be sent to deploy without stripping.
    """
    lines = []
    for s in slots:
        slot_id = (s.get("slot_id") or "").strip().upper()
        label = (s.get("label") or "Content").strip()
        kind = (s.get("kind") or "paragraph").lower()
        lines.append(f"{s['slot_id']} [{label}]:")
        raw_filled = (slot_value_map or {}).get(slot_id, "") or ""
        if kind == "image":
            value = (raw_filled or "").strip()
            if not value or not (value.startswith("http://") or value.startswith("https://")):
                value = (s.get("current_value") or "").strip() or "[No image URL - add URL here]"
        else:
            filled = _clean_slot_value(raw_filled)
            current = (s.get("current_value") or "").strip()
            value = filled if filled else (current if current else "[No content - add your text here]")
        lines.append(value)
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def _chunks_to_slot_value_map(slots: List[Dict[str, Any]], content_chunks: Dict[str, List[str]]) -> Dict[str, str]:
    """Map content chunks to slots by kind and order (same logic as _replace_elementor_content_only)."""
    headings = list(content_chunks.get("headings", []))
    paragraphs = list(content_chunks.get("paragraphs", []))
    buttons = list(content_chunks.get("buttons", []))
    slot_value_map: Dict[str, str] = {}
    hi, pi, bi = 0, 0, 0
    for s in slots:
        slot_id = (s.get("slot_id") or "").strip().upper()
        kind = (s.get("kind") or "paragraph").lower()
        if not slot_id:
            continue
        if kind == "heading":
            if hi < len(headings):
                slot_value_map[slot_id] = headings[hi].strip()
                hi += 1
            elif pi < len(paragraphs) and len(paragraphs[pi].split()) <= 12:
                slot_value_map[slot_id] = paragraphs[pi].strip()
                pi += 1
        elif kind == "button":
            if bi < len(buttons):
                slot_value_map[slot_id] = buttons[bi].strip()
                bi += 1
            elif hi < len(headings) and len(headings[hi].split()) <= 8:
                slot_value_map[slot_id] = headings[hi].strip()
                hi += 1
        else:
            if pi < len(paragraphs):
                slot_value_map[slot_id] = paragraphs[pi].strip()
                pi += 1
            elif hi < len(headings):
                slot_value_map[slot_id] = headings[hi].strip()
                hi += 1
    return slot_value_map


def _clean_slot_value(val: str) -> str:
    """Remove 'Page content:' and instructional-only lines from a slot value so it never appears on the page."""
    if not (val or "").strip():
        return ""
    val = re.sub(r"(?im)^\s*page\s+content\s*:?\s*[\r\n]*", "", val, count=1).strip()
    val = re.sub(r"(?im)^\s*page\s+image\s+url\s*:?\s*[\r\n]*", "", val, count=1).strip()
    val = _strip_instructional_from_content(val)
    return val.strip() if not _is_instructional_only(val) else ""


def _normalize_for_similarity(text: str) -> str:
    """Normalize text for duplicate/similarity check."""
    if not text:
        return ""
    t = re.sub(r"\s+", " ", _strip_html_to_text(text)).strip().lower()
    return t[:500]


def _is_similar_content(a: str, b: str, threshold: float = 0.85) -> bool:
    """
    Return True if the two strings are similar enough to avoid duplication.
    When template already has this content, we skip re-adding it.
    """
    na, nb = _normalize_for_similarity(a), _normalize_for_similarity(b)
    if not na or not nb:
        return False
    if na == nb:
        return True
    if len(na) < 10 or len(nb) < 10:
        return na == nb
    # One contains the other (e.g. same phrase)
    if na in nb or nb in na:
        return True
    # Simple word overlap: majority of words in shorter string appear in longer
    wa, wb = set(na.split()), set(nb.split())
    if not wa:
        return False
    overlap = len(wa & wb) / len(wa)
    return overlap >= threshold


def _enforce_slot_kind(slot_id: str, kind: str, value: str) -> str:
    """
    Ensure value matches slot kind: heading = short phrase, button = short text,
    paragraph = can be long. Prevents putting a full paragraph into a heading slot.
    """
    if not (value or "").strip():
        return ""
    v = (value or "").strip()
    words = v.split()
    kind = (kind or "paragraph").lower()
    if kind == "heading":
        # Max ~15 words or first sentence so it stays a heading
        if len(words) > 15:
            first_sentence = re.split(r"[.!?]\s+", v, maxsplit=1)[0].strip()
            if len(first_sentence.split()) <= 15:
                return first_sentence
            return " ".join(words[:15]).strip()
        if len(v) > 120 and " " in v:
            return " ".join(words[:15]).strip()
        return v
    if kind == "button":
        if len(words) > 8 or len(v) > 60:
            return " ".join(words[:8]).strip()
        return v
    return v


def _enforce_slot_length_by_template(
    slots: List[Dict[str, Any]],
    slot_value_map: Dict[str, str],
    slot_kind: Dict[str, str],
) -> None:
    """
    Strict: cap each slot's mapped value to template length (current_value word count + 2 max).
    So if the page had 50 words in a slot, we never send more than 52 — layout stays the same.
    """
    for s in slots:
        sid = (s.get("slot_id") or "").strip().upper()
        if not sid or sid not in slot_value_map:
            continue
        current = (s.get("current_value") or "").strip()
        current_words = len(current.split())
        max_extra = 2
        max_words = current_words + max_extra if current_words else 999
        kind = slot_kind.get(sid, "paragraph")
        if kind == "heading":
            max_words = min(max_words, 15)
        elif kind == "button":
            max_words = min(max_words, 8)
        val = (slot_value_map.get(sid) or "").strip()
        if not val or len(val.split()) <= max_words:
            continue
        words = val.split()
        truncated = " ".join(words[:max_words])
        for sep in (". ", "! ", "? "):
            last = truncated.rfind(sep)
            if last != -1:
                truncated = truncated[: last + 1].strip()
                break
        slot_value_map[sid] = truncated


def _content_to_slot_value_map(
    slots: List[Dict[str, Any]],
    template_data: Any,
    content: str,
    use_llm: bool = False,
) -> Tuple[Dict[str, str], Dict[str, Any]]:
    """
    Build slot_value_map from raw content. Tries: (1) SLOT_xxx in content, (2) Groq LLM if use_llm, (3) chunk-based.
    All slot values are cleaned so 'Page content:' and instructional labels never appear as content.
    Returns (slot_value_map, diagnostics).
    """
    slot_value_map = _extract_slot_value_map_from_html(content)
    source = "slot_labels_in_content" if slot_value_map else None
    if not slot_value_map and use_llm:
        try:
            from integrations.groq_slot_mapper import map_content_to_slots
            content_for_llm = _strip_instructional_from_content(content)
            llm_map = map_content_to_slots(slots, content_for_llm or content)
            if llm_map:
                slot_value_map = llm_map
                source = "groq_llm"
        except Exception as e:
            print(f"[WARN] LLM slot mapping failed: {e}", flush=True)
    if not slot_value_map:
        raw_chunks = _extract_content_chunks_from_html(content)
        adjusted_chunks, _ = _adjust_content_chunks_for_template(raw_chunks, template_data)
        slot_value_map = _chunks_to_slot_value_map(slots, adjusted_chunks)
        source = "chunk_based"
    judge_corrections = 0
    if use_llm and slot_value_map:
        try:
            from integrations.groq_slot_mapper import judge_and_adjust_slots
            corrections = judge_and_adjust_slots(slots, slot_value_map, content)
            for sid, new_val in (corrections or {}).items():
                if sid and new_val:
                    slot_value_map[sid] = new_val
                    judge_corrections += 1
        except Exception as e:
            print(f"[WARN] LLM judge step skipped: {e}", flush=True)
    # Clean every slot value so "Page content:" and instructional labels never end up on the page
    cleaned = {}
    for sid, v in (slot_value_map or {}).items():
        cleaned[sid] = _clean_slot_value(str(v or ""))
    slot_value_map = cleaned

    # Build slot lookup for kind (and current_value only for optional logic)
    slot_kind = { (s.get("slot_id") or "").strip().upper(): (s.get("kind") or "paragraph").lower() for s in slots }

    # Deduplication only when we did NOT use LLM (e.g. chunk-based): if mapped value is same as template, avoid duplicate. When LLM is used, it may keep or slightly adjust template so we do not blank similar content.
    if source != "groq_llm":
        slot_current = { (s.get("slot_id") or "").strip().upper(): (s.get("current_value") or "").strip() for s in slots }
        for sid, val in list(slot_value_map.items()):
            if not val:
                continue
            current = slot_current.get(sid) or ""
            if current and _is_similar_content(val, current):
                slot_value_map[sid] = ""

    # Enforce slot kind: heading slots get short phrases only, not full paragraphs; button slots get short text
    for sid in slot_value_map:
        kind = slot_kind.get(sid, "paragraph")
        slot_value_map[sid] = _enforce_slot_kind(sid, kind, slot_value_map.get(sid) or "")

    # Strict length: cap each slot to template's current word count + 2 so layout stays the same as the existing page
    _enforce_slot_length_by_template(slots, slot_value_map, slot_kind)

    # Whenever a slot is empty, use the template's existing content so we never leave "[No content - add your text here]" when the page already has text (template-first, fill all slots)
    slot_current = { (s.get("slot_id") or "").strip().upper(): (s.get("current_value") or "").strip() for s in slots }
    for sid, current in slot_current.items():
        if not sid:
            continue
        if not (slot_value_map.get(sid) or "").strip() and (current or "").strip():
            slot_value_map[sid] = current

    diagnostics = {
        "source": source or "none",
        "slots_filled": sum(1 for v in slot_value_map.values() if (v or "").strip()),
    }
    if judge_corrections:
        diagnostics["judge_corrections_applied"] = judge_corrections
    return slot_value_map, diagnostics


def _extract_content_chunks_from_html(content_html: str) -> Dict[str, List[str]]:
    """
    Build a lightweight content JSON from imported HTML.
    Focuses on meaningful text units only.
    """
    html = str(content_html or "")
    chunks = {"headings": [], "paragraphs": [], "buttons": []}

    for tag_match in re.finditer(r"<h[1-6][^>]*>(.*?)</h[1-6]>", html, flags=re.IGNORECASE | re.DOTALL):
        txt = _strip_html_to_text(tag_match.group(1))
        if txt and not _is_instructional_only(txt):
            chunks["headings"].append(txt)

    for tag_match in re.finditer(r"<p[^>]*>(.*?)</p>", html, flags=re.IGNORECASE | re.DOTALL):
        txt = _strip_html_to_text(tag_match.group(1))
        if txt and not _is_instructional_only(txt):
            chunks["paragraphs"].append(txt)

    for tag_match in re.finditer(r"<li[^>]*>(.*?)</li>", html, flags=re.IGNORECASE | re.DOTALL):
        txt = _strip_html_to_text(tag_match.group(1))
        if txt and not _is_instructional_only(txt):
            chunks["paragraphs"].append(f"• {txt}")

    for label, value in re.findall(
        r"(Primary CTA Button|Secondary CTA|CTA|Button)\s*:\s*([^\n<]+)",
        _strip_html_to_text(html),
        flags=re.IGNORECASE
    ):
        v = str(value).strip()
        if v and not _is_instructional_only(v):
            chunks["buttons"].append(v)

    for tag_match in re.finditer(r"<a[^>]*>(.*?)</a>", html, flags=re.IGNORECASE | re.DOTALL):
        txt = _strip_html_to_text(tag_match.group(1))
        if txt and len(txt.split()) <= 8 and not _is_instructional_only(txt):
            chunks["buttons"].append(txt)

    # Labeled-text fallback for plain-doc outputs.
    plain_with_breaks = re.sub(r"(?i)<\s*br\s*/?\s*>", "\n", html)
    plain_with_breaks = re.sub(r"(?i)</\s*(p|li|h[1-6]|div)\s*>", "\n", plain_with_breaks)
    plain_text = _strip_html_to_text(plain_with_breaks)
    labeled_patterns = [
        (r"(?i)main heading\s*:\s*(.+?)(?=\s+[A-Za-z][A-Za-z \-]{1,30}\s*:|$)", "headings"),
        (r"(?i)sub[- ]heading\s*:\s*(.+?)(?=\s+[A-Za-z][A-Za-z \-]{1,30}\s*:|$)", "headings"),
        (r"(?i)hero section\s*:\s*(.+?)(?=\s+[A-Za-z][A-Za-z \-]{1,30}\s*:|$)", "headings"),
        (r"(?i)primary cta button\s*:\s*(.+?)(?=\s+[A-Za-z][A-Za-z \-]{1,30}\s*:|$)", "buttons"),
        (r"(?i)secondary cta\s*:\s*(.+?)(?=\s+[A-Za-z][A-Za-z \-]{1,30}\s*:|$)", "buttons"),
        (r"(?i)description\s*:\s*(.+?)(?=\s+[A-Za-z][A-Za-z \-]{1,30}\s*:|$)", "paragraphs"),
    ]
    for pattern, target in labeled_patterns:
        for m in re.finditer(pattern, plain_text, flags=re.DOTALL):
            txt = _strip_html_to_text(m.group(1))
            if txt and not _is_instructional_only(txt):
                chunks[target].append(txt)

    # If no paragraph tags were found, split plain text into useful lines.
    if not chunks["paragraphs"]:
        rough_lines = [seg.strip(" -\t") for seg in re.split(r"[\r\n]+|\s{2,}", plain_with_breaks)]
        for line in rough_lines:
            txt = _strip_html_to_text(line)
            if not txt or _is_instructional_only(txt):
                continue
            if len(txt) < 30:
                continue
            chunks["paragraphs"].append(txt)

    # Deduplicate while preserving order
    for key in ("headings", "paragraphs", "buttons"):
        seen = set()
        deduped = []
        for item in chunks[key]:
            norm = item.strip()
            if not norm or norm in seen:
                continue
            seen.add(norm)
            deduped.append(norm)
        chunks[key] = deduped

    return chunks


def _split_paragraph_for_mapping(text: str, max_words: int = 28) -> List[str]:
    """Split long paragraph into mapper-friendly chunks while preserving meaning."""
    base = _strip_html_to_text(text)
    if not base:
        return []
    parts = [p.strip() for p in re.split(r"(?<=[.!?])\s+|;\s+", base) if p.strip()]
    out: List[str] = []
    for part in parts:
        words = part.split()
        if len(words) <= max_words:
            out.append(part)
            continue
        i = 0
        while i < len(words):
            out.append(" ".join(words[i:i + max_words]))
            i += max_words
    return out if out else [base]


def _count_template_text_capacity(template_data: Any) -> Dict[str, int]:
    """
    Count text-capable slots from Elementor JSON using same DFS as _collect_template_slots.
    """
    counts = {"heading": 0, "paragraph": 0, "button": 0}

    def classify_key(key: str, value: str) -> Optional[str]:
        return _classify_text_key(key, value)

    def process_elementor_data(data: Any) -> None:
        if isinstance(data, list):
            for element in data:
                process_elementor_data(element)
            return
        if not isinstance(data, dict):
            return
        if data.get("elType") == "widget":
            widget_type = (data.get("widgetType") or "").strip()
            settings = data.get("settings")
            if isinstance(settings, dict):
                if widget_type == "heading":
                    counts["heading"] += 1
                elif widget_type == "text-editor":
                    counts["paragraph"] += 1
                elif widget_type == "button":
                    counts["button"] += 1
                else:
                    for k, v in settings.items():
                        if isinstance(v, str) and v.strip():
                            kind = classify_key(k, v)
                            if kind:
                                counts[kind] += 1
                        elif isinstance(v, list):
                            for item in v:
                                if isinstance(item, dict):
                                    for rk, rv in item.items():
                                        if isinstance(rv, str) and rv.strip():
                                            kind = classify_key(rk, rv)
                                            if kind:
                                                counts[kind] += 1
        elements = data.get("elements")
        if isinstance(elements, list) and elements:
            process_elementor_data(elements)

    process_elementor_data(template_data)
    return counts


def _adjust_content_chunks_for_template(
    raw_chunks: Dict[str, List[str]],
    template_data: Any
) -> Tuple[Dict[str, List[str]], Dict[str, Any]]:
    """
    Format imported content according to selected page JSON text capacity.
    """
    capacity = _count_template_text_capacity(template_data)
    headings = list(raw_chunks.get("headings", []))
    paragraphs = list(raw_chunks.get("paragraphs", []))
    buttons = list(raw_chunks.get("buttons", []))

    # Expand paragraphs for pages that have many content slots.
    expanded_paragraphs: List[str] = []
    for p in paragraphs:
        expanded_paragraphs.extend(_split_paragraph_for_mapping(p))
    if expanded_paragraphs:
        paragraphs = expanded_paragraphs

    # Fill missing heading slots from short paragraph candidates.
    heading_target = max(capacity.get("heading", 0), 1)
    if len(headings) < heading_target:
        promoted = []
        for p in paragraphs:
            if len(p.split()) <= 12 and p not in headings:
                promoted.append(p)
            if len(headings) + len(promoted) >= heading_target:
                break
        headings.extend(promoted)

    # Fill button slots from CTA-like heading content if needed.
    button_target = max(capacity.get("button", 0), 1)
    if len(buttons) < button_target:
        for h in headings:
            if len(h.split()) <= 8 and h not in buttons:
                buttons.append(h)
            if len(buttons) >= button_target:
                break

    # If still short on paragraphs, reuse remaining medium-length headings.
    para_target = max(capacity.get("paragraph", 0), 1)
    if len(paragraphs) < para_target:
        for h in headings:
            if len(h.split()) >= 6 and h not in paragraphs:
                paragraphs.append(h)
            if len(paragraphs) >= para_target:
                break

    # Trim excessive content to improve usage and focus.
    headings = headings[: max(heading_target * 2, heading_target)]
    paragraphs = paragraphs[: max(para_target * 2, para_target)]
    buttons = buttons[: max(button_target * 2, button_target)]

    adjusted = {
        "headings": headings,
        "paragraphs": paragraphs,
        "buttons": buttons
    }
    plan = {
        "template_capacity": capacity,
        "raw_counts": {
            "headings": len(raw_chunks.get("headings", [])),
            "paragraphs": len(raw_chunks.get("paragraphs", [])),
            "buttons": len(raw_chunks.get("buttons", []))
        },
        "adjusted_counts": {
            "headings": len(headings),
            "paragraphs": len(paragraphs),
            "buttons": len(buttons)
        }
    }
    return adjusted, plan


def _replace_elementor_content_only(
    template_data: Any,
    content_chunks: Dict[str, List[str]],
    slot_value_map: Optional[Dict[str, str]] = None
) -> Tuple[Any, Dict[str, Any]]:
    """
    Preserve Elementor structure (recursive tree: Section -> Column -> Widget | Inner Section -> ...)
    and replace only textual content in settings (title, editor, text). Uses same DFS as
    _collect_template_slots so slot order matches and no data is lost or corrupted.
    """
    merged = copy.deepcopy(template_data)
    heading_idx = 0
    paragraph_idx = 0
    button_idx = 0
    replaced = {"heading": 0, "paragraph": 0, "button": 0, "image": 0}
    found = {"heading": 0, "paragraph": 0, "button": 0, "image": 0}

    headings = content_chunks.get("headings", [])
    paragraphs = content_chunks.get("paragraphs", [])
    buttons = content_chunks.get("buttons", [])

    slot_map = {str(k).upper(): str(v) for k, v in (slot_value_map or {}).items() if str(v).strip()}
    use_slot_mode = bool(slot_map)
    slot_counter = 0

    def classify_key(key: str, value: str) -> Optional[str]:
        return _classify_text_key(key, value)

    def next_slot_value() -> Optional[str]:
        nonlocal slot_counter
        slot_counter += 1
        slot_id = f"SLOT_{slot_counter:03d}"
        return slot_map.get(slot_id)

    def next_content(kind: str) -> Optional[str]:
        nonlocal heading_idx, paragraph_idx, button_idx
        if kind == "heading":
            if heading_idx < len(headings):
                val = headings[heading_idx]
                heading_idx += 1
                return val
            # fallback from paragraphs
            if paragraph_idx < len(paragraphs):
                val = paragraphs[paragraph_idx]
                paragraph_idx += 1
                return val
            return None
        if kind == "button":
            if button_idx < len(buttons):
                val = buttons[button_idx]
                button_idx += 1
                return val
            # short heading fallback
            while heading_idx < len(headings):
                candidate = headings[heading_idx]
                heading_idx += 1
                if len(candidate.split()) <= 8:
                    return candidate
            return None
        if paragraph_idx < len(paragraphs):
            val = paragraphs[paragraph_idx]
            paragraph_idx += 1
            return val
        # fallback from remaining headings
        if heading_idx < len(headings):
            val = headings[heading_idx]
            heading_idx += 1
            return val
        return None

    def process_elementor_data(data: Any) -> None:
        """DFS: same order as _collect_template_slots. Process settings (replace content), then recurse into elements."""
        nonlocal heading_idx, paragraph_idx, button_idx
        if isinstance(data, list):
            for element in data:
                process_elementor_data(element)
            return
        if not isinstance(data, dict):
            return

        if data.get("elType") == "widget":
            widget_type = (data.get("widgetType") or "").strip()
            settings = data.get("settings")
            if not isinstance(settings, dict):
                settings = {}
                data["settings"] = settings

            if widget_type == "heading":
                found["heading"] += 1
                replacement = next_slot_value() if use_slot_mode else next_content("heading")
                if replacement:
                    settings["title"] = replacement
                    replaced["heading"] += 1
            elif widget_type == "text-editor":
                found["paragraph"] += 1
                replacement = next_slot_value() if use_slot_mode else next_content("paragraph")
                if replacement:
                    settings["editor"] = f"<p>{replacement}</p>"
                    replaced["paragraph"] += 1
            elif widget_type == "button":
                found["button"] += 1
                replacement = next_slot_value() if use_slot_mode else next_content("button")
                if replacement:
                    settings["text"] = replacement
                    replaced["button"] += 1
            elif widget_type == "dit-button":
                found["button"] += 1
                replacement = next_slot_value() if use_slot_mode else next_content("button")
                if replacement:
                    if "button_text" in settings:
                        settings["button_text"] = replacement
                    else:
                        settings["text"] = replacement
                    replaced["button"] += 1
            elif widget_type == "image":
                found["image"] += 1
                replacement = next_slot_value() if use_slot_mode else None
                if replacement and isinstance(replacement, str) and replacement.strip() and (replacement.startswith("http://") or replacement.startswith("https://")):
                    if "image" in settings and isinstance(settings["image"], dict):
                        settings["image"]["url"] = replacement.strip()
                        if "id" in settings["image"]:
                            settings["image"]["id"] = ""
                    else:
                        settings["url"] = replacement.strip()
                    replaced["image"] += 1
            else:
                for k, v in list(settings.items()):
                    if isinstance(v, str) and v.strip():
                        kind = classify_key(k, v)
                        if kind:
                            found[kind] += 1
                            replacement = next_slot_value() if use_slot_mode else next_content(kind)
                            if replacement:
                                settings[k] = f"<p>{replacement}</p>" if (k in {"editor", "content", "description"} and "<" in v) else replacement
                                replaced[kind] += 1
                    elif isinstance(v, list):
                        for item in v:
                            if not isinstance(item, dict):
                                continue
                            for rk, rv in list(item.items()):
                                if isinstance(rv, str) and rv.strip():
                                    kind = classify_key(rk, rv)
                                    if kind:
                                        found[kind] += 1
                                        replacement = next_slot_value() if use_slot_mode else next_content(kind)
                                        if replacement:
                                            item[rk] = replacement
                                            replaced[kind] += 1

        elements = data.get("elements")
        if isinstance(elements, list) and elements:
            process_elementor_data(elements)

    process_elementor_data(merged)

    found_total = sum(found.values())
    replaced_total = sum(replaced.values())
    content_total = len(slot_map) if use_slot_mode else (len(headings) + len(paragraphs) + len(buttons))
    match_score = round((replaced_total / found_total) * 100, 2) if found_total else 0.0
    content_usage = round((replaced_total / content_total) * 100, 2) if content_total else 0.0

    diagnostics = {
        "found_targets": found,
        "replaced_targets": replaced,
        "content_chunks": {
            "headings": len(headings),
            "paragraphs": len(paragraphs),
            "buttons": len(buttons),
            "total": content_total
        },
        "replaced_total": replaced_total,
        "found_total": found_total,
        "template_match_percent": match_score,
        "content_usage_percent": content_usage,
        "mapping_mode": "slot_template" if use_slot_mode else "adaptive_auto"
    }
    return merged, diagnostics


@app.get("/api/page-content-template")
async def get_page_content_template(site_url: str, page_id: int):
    """
    Build a downloadable slot template from selected page JSON.
    Users fill this template in their doc for exact placement mapping.
    """
    creds = get_wordpress_credentials(site_url)
    if not creds:
        raise HTTPException(
            status_code=400,
            detail=f"No WordPress credentials for this site. Add the site in the Sites tab with WordPress username and Application Password (not regular password)."
        )
    selected_json = fetch_elementor_template_from_site(site_url, page_id)
    if not selected_json:
        raise HTTPException(
            status_code=404,
            detail=f"Elementor data not found for page {page_id}. Ensure: 1) The page is built with Elementor, 2) Your user has edit permission, 3) RevPublish Connector plugin is active on the site (if required)."
        )

    slots = _collect_template_slots(selected_json)
    template_text = _build_slot_template_text(slots)
    return {
        "status": "success",
        "site_url": site_url,
        "page_id": page_id,
        "slot_count": len(slots),
        "slots": slots,
        "template_text": template_text,
        "template_filename": f"page-{page_id}-content-template.txt"
    }


def _normalize_content_source_columns(rows: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[str], Optional[str], Optional[str], Optional[str]]:
    """
    Normalize rows from CSV/Sheet: lowercase keys, map common names to doc_url, site_url, page_id.
    Returns (rows_with_normalized_keys, column_list, doc_url_col, site_url_col, page_id_col).
    """
    if not rows:
        return [], [], None, None, None
    import csv as csv_module
    from io import StringIO
    # Build mapping from various column names to standard names
    doc_url_aliases = ["doc_url", "doc link", "google_doc_url", "document url", "doc_link", "content_url", "page_content_doc_url", "doc"]
    site_url_aliases = ["site_url", "site", "site url", "wordpress_url", "wp_url", "url"]
    page_id_aliases = ["page_id", "page id", "target_page_id", "page", "pageid"]
    def find_standard_key(keys: List[str], aliases: List[str]) -> Optional[str]:
        keys_lower = {k.strip().lower(): k for k in keys}
        for a in aliases:
            for k, orig in keys_lower.items():
                if a in k or k in a:
                    return orig
        return None
    first_row = rows[0]
    orig_keys = list(first_row.keys())
    doc_url_col = find_standard_key(orig_keys, doc_url_aliases)
    site_url_col = find_standard_key(orig_keys, site_url_aliases)
    page_id_col = find_standard_key(orig_keys, page_id_aliases)
    normalized = []
    for row in rows:
        out = {}
        for k, v in row.items():
            key = (k or "").strip()
            val = v if v is None else (str(v).strip() if isinstance(v, str) else str(v))
            out[key] = val
        # Add standard keys if we detected them
        if doc_url_col and doc_url_col in out:
            out["doc_url"] = out.get(doc_url_col) or ""
        if site_url_col and site_url_col in out:
            out["site_url"] = out.get(site_url_col) or ""
        if page_id_col and page_id_col in out:
            out["page_id"] = out.get(page_id_col) or ""
        normalized.append(out)
    columns = list(normalized[0].keys()) if normalized else []
    return normalized, columns, doc_url_col or "doc_url", site_url_col or "site_url", page_id_col or "page_id"


@app.post("/api/parse-content-source")
async def parse_content_source(
    csv_file: Optional[UploadFile] = File(None),
    sheet_url: str = Form(""),
):
    """
    Parse CSV upload or Google Spreadsheet URL into rows. Doc URLs (and site_url, page_id) are read from the sheet/CSV.
    Use this to load rows, then pick a row and pass its doc_url (and site_url, page_id) to map-doc-to-template.
    """
    sheet_url = (sheet_url or "").strip()
    csv_content: Optional[str] = None
    if csv_file and csv_file.filename:
        try:
            raw = await csv_file.read()
            csv_content = raw.decode("utf-8-sig", errors="replace")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Could not read CSV file: {e}")
    elif sheet_url:
        match = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", sheet_url)
        if not match:
            raise HTTPException(status_code=400, detail="Invalid Google Spreadsheet URL.")
        sheet_id = match.group(1)
        csv_export_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
        try:
            resp = requests.get(csv_export_url, timeout=15)
            if resp.status_code != 200:
                raise HTTPException(status_code=400, detail=f"Could not export sheet as CSV: {resp.status_code}")
            csv_content = resp.text
        except requests.RequestException as e:
            raise HTTPException(status_code=400, detail=f"Could not fetch Google Sheet: {e}")
    else:
        raise HTTPException(status_code=400, detail="Provide either a CSV file upload or a Google Spreadsheet URL.")
    if not csv_content or not csv_content.strip():
        raise HTTPException(status_code=400, detail="No data in CSV or sheet.")
    import csv as csv_module
    from io import StringIO
    try:
        reader = csv_module.DictReader(StringIO(csv_content))
        rows = list(reader)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid CSV: {e}")
    if not rows:
        raise HTTPException(status_code=400, detail="CSV or sheet has no data rows.")
    normalized_rows, columns, doc_col, site_col, page_col = _normalize_content_source_columns(rows)
    return {
        "status": "success",
        "rows": normalized_rows,
        "columns": columns,
        "doc_url_column": doc_col,
        "site_url_column": site_col,
        "page_id_column": page_col,
        "row_count": len(normalized_rows),
    }


@app.post("/api/map-doc-to-template")
async def map_doc_to_template(
    site_url: str = Form(...),
    page_id: str = Form(...),
    doc_content: str = Form(""),
    doc_url: str = Form(""),
    use_llm_assistance: bool = Form(False),
):
    """
    Map doc content into the page slot template. Content can be pasted (doc_content)
    or fetched from a Google Doc URL (doc_url). Returns filled template for preview/copy.
    Uses: SLOT_xxx in content, else Groq LLM (if use_llm_assistance) + optional judge step, else chunk-based.
    """
    page_id_str = (page_id or "").strip()
    if not page_id_str or not page_id_str.isdigit():
        raise HTTPException(
            status_code=400,
            detail="page_id must be a number (WordPress page ID). If you loaded a row from CSV/Sheet, ensure that row has a numeric page_id column and the sheet column order is correct (doc_url, site_url, page_id)."
        )
    page_id_int = int(page_id_str)
    creds = get_wordpress_credentials(site_url)
    if not creds:
        raise HTTPException(
            status_code=400,
            detail="No WordPress credentials for this site. Add the site in the Sites tab with WordPress username and Application Password."
        )
    selected_json = fetch_elementor_template_from_site(site_url, page_id_int)
    if not selected_json:
        raise HTTPException(
            status_code=404,
            detail=f"Elementor data not found for page {page_id_int}. Ensure the page is built with Elementor and your user has edit permission."
        )
    slots = _collect_template_slots(selected_json)
    if not slots:
        template_text = _build_slot_template_text(slots)
        return {
            "status": "success",
            "site_url": site_url,
            "page_id": page_id_int,
            "slot_count": 0,
            "template_text": template_text,
            "template_filename": f"page-{page_id_int}-content-filled.txt",
            "slot_value_map": {},
            "diagnostics": {"source": "none", "slots_filled": 0, "message": "No editable slots on this page."},
        }
    content_fetched_from_url = False
    doc_content_clean = (doc_content or "").strip()
    if not doc_content_clean and (doc_url or "").strip():
        try:
            from integrations.google_integrations import GoogleDocsClient
            fetched = GoogleDocsClient().extract_from_url((doc_url or "").strip())
            doc_content_clean = (fetched.get("content_html") or fetched.get("content") or "").strip()
            content_fetched_from_url = bool(doc_content_clean)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Could not fetch Google Doc: {e}")
    if not doc_content_clean:
        template_text = _build_slot_template_text(slots)
        return {
            "status": "success",
            "site_url": site_url,
            "page_id": page_id_int,
            "slot_count": len(slots),
            "template_text": template_text,
            "template_filename": f"page-{page_id_int}-content-filled.txt",
            "slot_value_map": {},
            "diagnostics": {"source": "none", "slots_filled": 0, "message": "Provide pasted content or a Google Doc URL."},
        }
    slot_value_map, diagnostics = _content_to_slot_value_map(
        slots, selected_json, doc_content_clean, use_llm=use_llm_assistance
    )
    filled_text = _build_filled_slot_template_text(slots, slot_value_map)
    out = {
        "status": "success",
        "site_url": site_url,
        "page_id": page_id_int,
        "slot_count": len(slots),
        "slots": slots,
        "template_text": filled_text,
        "template_filename": f"page-{page_id_int}-content-filled.txt",
        "slot_value_map": slot_value_map,
        "diagnostics": diagnostics,
    }
    if content_fetched_from_url:
        out["content_fetched_from_url"] = True
    return out


def _strip_filled_template_headers(text: str) -> str:
    """Remove instructional header lines from filled template so only SLOT_xxx blocks remain."""
    if not text or not text.strip():
        return text
    lines = text.strip().split("\n")
    for i, line in enumerate(lines):
        if line.strip().startswith("SLOT_"):
            return "\n".join(lines[i:]).strip()
    return text.strip()


@app.post("/api/deploy-filled-template")
@app.post("/revflow_os/revpublish/api/deploy-filled-template")
async def deploy_filled_template(
    site_url: str = Form(...),
    page_id: str = Form(...),
    filled_content: str = Form(...),
    post_status: str = Form("draft"),
    preview_mode: bool = Form(False),
):
    """
    Deploy the filled template content directly to the WordPress page.
    Uses same pipeline as Start Import (Bridge Plugin, content-only replace).
    Options: post_status (draft, publish, pending), preview_mode (no deploy, dry run).
    """
    page_id_str = (page_id or "").strip()
    if not page_id_str or not page_id_str.isdigit():
        raise HTTPException(status_code=400, detail="page_id must be a number (WordPress page ID).")
    target_page_id = int(page_id_str)
    content = _strip_filled_template_headers((filled_content or "").strip())
    if not content:
        raise HTTPException(status_code=400, detail="filled_content is required (the filled template text).")
    status = (post_status or "draft").strip().lower()
    if status not in ("draft", "publish", "pending", "private"):
        status = "draft"
    creds = get_wordpress_credentials(site_url)
    if not creds:
        raise HTTPException(
            status_code=400,
            detail="No WordPress credentials for this site. Add the site in the Sites tab first."
        )
    if preview_mode:
        selected_json = fetch_elementor_template_from_site(site_url, target_page_id)
        if not selected_json:
            raise HTTPException(status_code=404, detail=f"Elementor data not found for page {target_page_id}.")
        slot_value_map = _extract_slot_value_map_from_html(content)
        slots = _collect_template_slots(selected_json)
        return {
            "status": "success",
            "preview_mode": True,
            "message": "Preview only — no changes were made to WordPress.",
            "site_url": site_url,
            "page_id": target_page_id,
            "post_status_requested": status,
            "slots_matched": len(slot_value_map),
            "total_slots": len(slots),
        }
    success, error_msg, wp_post_id, wp_edit_url, wp_permalink, diagnostics = deploy_to_wordpress(
        site_url=site_url,
        title="",
        content=content,
        status=status,
        use_bridge_plugin=True,
        use_elementor=True,
        target_page_id=target_page_id,
        preserve_existing_title=True,
        use_llm_assistance=False,
    )
    if not success:
        raise HTTPException(status_code=400, detail=error_msg or "Deployment failed.")
    return {
        "status": "success",
        "message": f"Content deployed to WordPress as '{status}'.",
        "site_url": site_url,
        "page_id": target_page_id,
        "post_status": status,
        "wp_post_id": wp_post_id,
        "edit_url": wp_edit_url,
        "permalink": wp_permalink,
        "diagnostics": diagnostics,
    }


@app.post("/api/content-json-preview")
async def content_json_preview(
    site_url: str = Form(...),
    target_page_id: int = Form(...),
    csv_file: UploadFile = File(...)
):
    """
    Preview-only endpoint:
    1) Fetch selected page Elementor JSON
    2) Read CSV first row and fetch linked Google Doc content
    3) Build content JSON
    4) Merge content into selected JSON (content-only replacement)
    5) Return comparison metrics for UI
    """
    selected_json = fetch_elementor_template_from_site(site_url, target_page_id)
    if not selected_json:
        raise HTTPException(status_code=404, detail=f"Elementor data not found for page {target_page_id}")

    csv_content = await csv_file.read()
    if not csv_content:
        raise HTTPException(status_code=400, detail="CSV file is empty.")

    try:
        df = pd.read_csv(io.BytesIO(csv_content))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid CSV: {str(e)}")
    if df.empty:
        raise HTTPException(status_code=400, detail="CSV has no rows.")

    row_dict = df.iloc[0].to_dict()
    cleaned_row = {}
    for key, value in row_dict.items():
        if pd.isna(value) or value is None:
            cleaned_row[key] = ""
        else:
            cleaned_row[key] = str(value).strip() if isinstance(value, str) else str(value)

    doc_urls = collect_google_doc_urls_from_row(cleaned_row)
    if not doc_urls:
        raise HTTPException(
            status_code=400,
            detail=(
                "No Google Doc URL found in CSV first row. Add a doc URL in "
                "page_content_doc_url (or doc_url/google_doc_url variants)."
            )
        )

    fetched_docs_html: List[str] = []
    fetch_errors: List[str] = []
    try:
        from integrations.google_integrations import GoogleDocsClient
        google_docs = GoogleDocsClient()
        for doc_url in doc_urls:
            try:
                doc_content = google_docs.extract_from_url(doc_url)
                content_html = str(doc_content.get("content_html", "")).strip()
                if content_html:
                    fetched_docs_html.append(content_html)
                else:
                    fetch_errors.append(f"Empty content: {doc_url}")
            except Exception as doc_err:
                fetch_errors.append(f"{doc_url}: {str(doc_err)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Google Docs integration failed: {str(e)}")

    if not fetched_docs_html:
        raise HTTPException(
            status_code=400,
            detail=f"Could not fetch content from provided docs. Errors: {' | '.join(fetch_errors[:3])}"
        )

    merged_content_html = "\n\n<hr />\n\n".join(fetched_docs_html)
    slot_value_map = _extract_slot_value_map_from_html(merged_content_html)
    raw_content_json = _extract_content_chunks_from_html(merged_content_html)
    adjusted_content_json, formatting_plan = _adjust_content_chunks_for_template(raw_content_json, selected_json)
    merged_json, diagnostics = _replace_elementor_content_only(selected_json, adjusted_content_json, slot_value_map=slot_value_map)
    diagnostics["slot_map_count"] = len(slot_value_map)
    diagnostics["formatting_plan"] = formatting_plan
    diagnostics["slot_template_available"] = bool(slot_value_map)

    return {
        "status": "success",
        "site_url": site_url,
        "target_page_id": target_page_id,
        "doc_urls": doc_urls,
        "doc_fetch_errors": fetch_errors,
        "selected_page_json": selected_json,
        "content_json": adjusted_content_json,
        "slot_value_map": slot_value_map,
        "raw_content_json": raw_content_json,
        "merged_preview_json": merged_json,
        "comparison": diagnostics
    }


@app.get("/api/page-elementor-json")
async def get_page_elementor_json(site_url: str, page_id: int):
    """Return raw Elementor JSON for the selected page (UI preview panel)."""
    data = fetch_elementor_template_from_site(site_url, page_id)
    if not data:
        raise HTTPException(status_code=404, detail=f"Elementor data not found for page {page_id}")
    return {
        "status": "success",
        "site_url": site_url,
        "page_id": page_id,
        "widgets_count": _count_elementor_widgets(data),
        "elementor_data": data
    }


def build_elementor_page_content(row_data: Dict[str, Any]) -> str:
    """
    Build basic HTML content for non-Elementor fallback.
    This is used when Elementor data is not available.
    
    For full Elementor integration, use build_elementor_json() instead.
    """
    business_name = row_data.get('business_name', 'Professional Services')
    niche = row_data.get('niche', 'Services')
    city = row_data.get('city', '')
    state = row_data.get('state', '')
    phone = row_data.get('phone', '')
    
    # Basic HTML content
    html = f"""
    <div class="service-page">
        <h1>{business_name}</h1>
        <h2>Professional {niche} in {city}, {state}</h2>
        
        <div class="contact-info">
            <p><strong>Phone:</strong> {phone}</p>
        </div>
        
        <div class="services">
            <h3>Our Services</h3>
            <p>We provide professional {niche.lower()} services in {city} and surrounding areas.</p>
        </div>
    </div>
    """
    
    return html.strip()


def build_elementor_json(row_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build Elementor JSON structure from CSV row data following the documented mapping.
    
    Creates Elementor page with sections:
    1. HERO: H1 heading, subheading, CTA button with phone
    2. INTRO: Welcome text with business info
    3. SERVICES: Services list with icon-list widget
    4. WHY CHOOSE US: Benefits list with icon-list widget
    5. CONTACT: Contact information with text-editor widget
    
    CSV Field Mapping:
    - business_name → heading widgets (titles)
    - niche → heading widgets (titles)
    - city, state → text-editor widgets (address blocks)
    - phone → button widget (tel: link)
    - address, email → text-editor widgets (contact section)
    - years_experience → icon-list widget (why choose us)
    - license_number → icon-list widget (why choose us)
    - service_area → text-editor widget (intro)
    - hours_of_operation → text-editor widget (contact)
    - emergency_available → conditional icon-list item
    
    Returns: List of Elementor sections (will be JSON-serialized for _elementor_data meta field)
    """
    # Extract CSV fields with safe defaults
    def safe_get(key, default=''):
        val = row_data.get(key, default)
        if val is None:
            return default
        # Handle pandas NaN values
        try:
            if isinstance(val, float) and pd.isna(val):
                return default
        except (NameError, AttributeError):
            # If pandas not available, just check for None
            pass
        return str(val).strip() if isinstance(val, str) else str(val)
    
    business_name = safe_get('business_name', 'Professional Services')
    niche = safe_get('niche', 'Services')
    city = safe_get('city', '')
    state = safe_get('state', '')
    zip_code = safe_get('zip_code', '')
    phone = safe_get('phone', '')
    email = safe_get('email', '')
    address = safe_get('address', '')
    years_experience = safe_get('years_experience', '')
    license_number = safe_get('license_number', '')
    service_area = safe_get('service_area', '')
    hours_of_operation = safe_get('hours_of_operation', '')
    emergency_available = safe_get('emergency_available', '').lower()
    
    # Parse services if available (pipe-delimited or comma-separated)
    services = []
    if row_data.get('services_offered'):
        services_str = str(row_data.get('services_offered', ''))
        if '|||' in services_str:
            services = [s.strip() for s in services_str.split('|||') if s.strip()]
        elif ',' in services_str:
            services = [s.strip() for s in services_str.split(',') if s.strip()]
        else:
            services = [services_str.strip()] if services_str.strip() else []
    
    elementor_data = []
    
    # ============================================
    # SECTION 1: HERO
    # ============================================
    hero_h1 = f"#1 {niche} in {city}" if niche and city else business_name
    hero_subheading = f"Trusted by {city} Residents for {years_experience} Years" if city and years_experience else f"Professional {niche} Services in {city}, {state}"
    
    hero_section = {
        "id": "hero",
        "elType": "section",
        "settings": {
            "background_background": "gradient",
            "background_color": "#667eea",
            "background_color_b": "#764ba2",
            "padding": {
                "unit": "px",
                "top": 80,
                "bottom": 80,
                "left": 20,
                "right": 20
            }
        },
        "elements": [{
            "id": "hero-col",
            "elType": "column",
            "elements": [
                {
                    "id": "h1",
                    "elType": "widget",
                    "widgetType": "heading",
                    "settings": {
                        "title": hero_h1,
                        "header_size": "h1",
                        "align": "center",
                        "color": "#ffffff"
                    }
                },
                {
                    "id": "hero-sub",
                    "elType": "widget",
                    "widgetType": "heading",
                    "settings": {
                        "title": hero_subheading,
                        "header_size": "h2",
                        "align": "center",
                        "color": "#ffffff"
                    }
                }
            ]
        }]
    }
    
    # Add CTA button if phone is available
    if phone:
        hero_section["elements"][0]["elements"].append({
            "id": "cta-btn",
            "elType": "widget",
            "widgetType": "button",
            "settings": {
                "text": f"📞 Call Now: {phone}",
                "link": {"url": f"tel:{phone.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')}"},
                "align": "center",
                "button_text_color": "#ffffff",
                "background_color": "#10b981"
            }
        })
    
    elementor_data.append(hero_section)
    
    # ============================================
    # SECTION 2: INTRO CONTENT
    # ============================================
    intro_text = f"<h2>Welcome to {business_name}</h2>"
    if city and niche:
        intro_text += f"<p>Welcome to {business_name}, {city}'s premier {niche} company."
    if years_experience:
        intro_text += f" Since {years_experience}, we've been providing exceptional services"
    if service_area:
        intro_text += f" throughout {service_area}."
    else:
        intro_text += f" in {city} and surrounding areas."
    intro_text += "</p>"
    
    intro_section = {
        "id": "intro",
        "elType": "section",
        "settings": {
            "padding": {
                "unit": "px",
                "top": 60,
                "bottom": 60,
                "left": 20,
                "right": 20
            }
        },
        "elements": [{
            "id": "intro-col",
            "elType": "column",
            "elements": [{
                "id": "intro-text",
                "elType": "widget",
                "widgetType": "text-editor",
                "settings": {
                    "editor": intro_text
                }
            }]
        }]
    }
    elementor_data.append(intro_section)
    
    # ============================================
    # SECTION 3: SERVICES LIST
    # ============================================
    if services:
        service_items = []
        for service in services[:10]:  # Limit to 10 services
            service_items.append({
                "text": service,
                "icon": {"value": "fa fa-check", "library": "fa-solid"}
            })
        
        services_section = {
            "id": "services",
            "elType": "section",
            "settings": {
                "padding": {
                    "unit": "px",
                    "top": 60,
                    "bottom": 60,
                    "left": 20,
                    "right": 20
                }
            },
            "elements": [{
                "id": "services-col",
                "elType": "column",
                "elements": [
                    {
                        "id": "services-title",
                        "elType": "widget",
                        "widgetType": "heading",
                        "settings": {
                            "title": f"Our {niche} Services" if niche else "Our Services",
                            "header_size": "h2",
                            "align": "center"
                        }
                    },
                    {
                        "id": "services-list",
                        "elType": "widget",
                        "widgetType": "icon-list",
                        "settings": {
                            "icon_list": service_items
                        }
                    }
                ]
            }]
        }
        elementor_data.append(services_section)
    
    # ============================================
    # SECTION 4: WHY CHOOSE US
    # ============================================
    why_choose_items = []
    
    if years_experience:
        why_choose_items.append({
            "text": f"{years_experience}+ Years of Experience",
            "icon": {"value": "fa fa-check", "library": "fa-solid"}
        })
    
    if license_number:
        why_choose_items.append({
            "text": f"Licensed & Insured (License #{license_number})",
            "icon": {"value": "fa fa-check", "library": "fa-solid"}
        })
    elif license_number == '' and business_name:
        # Still show licensed if we have business name
        why_choose_items.append({
            "text": "Licensed & Insured",
            "icon": {"value": "fa fa-check", "library": "fa-solid"}
        })
    
    if city:
        why_choose_items.append({
            "text": f"Local Experts in {city}",
            "icon": {"value": "fa fa-check", "library": "fa-solid"}
        })
    
    if emergency_available in ['yes', 'true', '1', 'y']:
        why_choose_items.append({
            "text": "24/7 Emergency Service Available",
            "icon": {"value": "fa fa-check", "library": "fa-solid"}
        })
    
    if why_choose_items:
        why_choose_section = {
            "id": "why-choose",
            "elType": "section",
            "settings": {
                "padding": {
                    "unit": "px",
                    "top": 60,
                    "bottom": 60,
                    "left": 20,
                    "right": 20
                }
            },
            "elements": [{
                "id": "why-col",
                "elType": "column",
                "elements": [
                    {
                        "id": "why-title",
                        "elType": "widget",
                        "widgetType": "heading",
                        "settings": {
                            "title": f"Why Choose {business_name}?" if business_name else "Why Choose Us?",
                            "header_size": "h2",
                            "align": "center"
                        }
                    },
                    {
                        "id": "why-list",
                        "elType": "widget",
                        "widgetType": "icon-list",
                        "settings": {
                            "icon_list": why_choose_items
                        }
                    }
                ]
            }]
        }
        elementor_data.append(why_choose_section)
    
    # ============================================
    # SECTION 5: CONTACT
    # ============================================
    contact_info_parts = []
    if phone:
        contact_info_parts.append(f"<p style='text-align:center;color:#fff;font-size:1.2em;'><strong>📞 {phone}</strong></p>")
    if email:
        contact_info_parts.append(f"<p style='text-align:center;color:#fff;'><a href='mailto:{email}' style='color:#fff;text-decoration:none;'>✉️ {email}</a></p>")
    if address or city or state or zip_code:
        full_address = ", ".join(filter(None, [address, city, state, zip_code]))
        if full_address:
            contact_info_parts.append(f"<p style='text-align:center;color:#fff;'>📍 {full_address}</p>")
    if hours_of_operation:
        contact_info_parts.append(f"<p style='text-align:center;color:#fff;'>🕐 Hours: {hours_of_operation}</p>")
    
    if contact_info_parts:
        contact_section = {
            "id": "contact",
            "elType": "section",
            "settings": {
                "background_background": "gradient",
                "background_color": "#764ba2",
                "background_color_b": "#667eea",
                "padding": {
                    "unit": "px",
                    "top": 80,
                    "bottom": 80,
                    "left": 20,
                    "right": 20
                }
            },
            "elements": [{
                "id": "contact-col",
                "elType": "column",
                "elements": [
                    {
                        "id": "contact-title",
                        "elType": "widget",
                        "widgetType": "heading",
                        "settings": {
                            "title": f"Contact {business_name} Today" if business_name else "Contact Us Today",
                            "header_size": "h2",
                            "color": "#ffffff",
                            "align": "center"
                        }
                    },
                    {
                        "id": "contact-info",
                        "elType": "widget",
                        "widgetType": "text-editor",
                        "settings": {
                            "editor": "".join(contact_info_parts)
                        }
                    }
                ]
            }]
        }
        elementor_data.append(contact_section)
    
    return elementor_data


def deploy_to_wordpress(
    site_url: str,
    title: str,
    content: str,
    status: str = "draft",
    meta_data: Optional[Dict[str, Any]] = None,
    use_bridge_plugin: bool = True,
    use_elementor: bool = True,
    target_page_id: Optional[int] = None,
    preserve_formatting: bool = True,
    preserve_existing_title: bool = False,
    use_llm_assistance: bool = False,
) -> Tuple[bool, Optional[str], Optional[int], Optional[str], Optional[str], Optional[Dict[str, Any]]]:
    """
    Deploy content to WordPress site with Elementor support.
    
    Supports two deployment modes:
    1. Bridge Plugin Mode (use_bridge_plugin=True): Send HTML content, Bridge Plugin converts to Elementor
    2. Direct Elementor Mode (use_bridge_plugin=False): Send Elementor JSON directly
    
    IMPROVED VERSION based on Gemini's code review:
    - Handles Elementor metadata correctly (_elementor_data as JSON string)
    - Better error handling (returns status instead of raising exceptions)
    - Supports both pages and posts
    - Network timeout protection
    - Bridge Plugin mode support (NEW)
    
    Args:
        site_url: Target WordPress site URL
        title: Page/Post title
        content: Page/Post content (HTML or merged template)
        status: Post status (draft, publish, pending, private)
        meta_data: Optional metadata dict
                   - For Bridge Plugin mode: HTML content, Bridge Plugin handles conversion
                   - For Direct mode: Must include 'elementor_data' for Elementor pages
        use_bridge_plugin: If True, send HTML and let Bridge Plugin convert to Elementor.
                          If False, send Elementor JSON directly (backward compatibility).
        use_elementor: If True, creates Elementor page; if False, creates standard post
    
    Returns:
        Tuple of (success, error_message, post_id, edit_url, permalink, diagnostics)
    """
    try:
        # Get WordPress credentials
        creds = get_wordpress_credentials(site_url)
        if not creds:
            return False, f"No WordPress credentials found for {site_url}. Please add credentials in the Sites tab first.", None, None, None, None
        
        # Prepare API endpoint (pages for Elementor, posts for standard)
        endpoint_type = 'pages' if use_elementor else 'posts'
        api_base_url = creds['api_url'].rstrip('/') + f'/{endpoint_type}'
        api_url = f"{api_base_url}/{target_page_id}" if target_page_id else api_base_url

        # For "update specific page" mode, use Bridge Plugin endpoint first to preserve layout/styles.
        if target_page_id and use_bridge_plugin:
            normalized = normalize_url(site_url)
            protocol = "http://" if str(site_url).strip().startswith("http://") else "https://"
            bridge_url = f"{protocol}{normalized}/wp-json/revpublish/v1/elementor-update"
            preview_diagnostics: Optional[Dict[str, Any]] = None
            elementor_override_payload: Optional[Any] = None
            slot_mode_requested = False

            # Use the same content->json->merge pipeline used by preview for real import updates.
            try:
                selected_json = fetch_elementor_template_from_site(site_url, target_page_id)
                if selected_json:
                    slot_value_map = _extract_slot_value_map_from_html(content)
                    if not slot_value_map and use_llm_assistance:
                        try:
                            from integrations.groq_slot_mapper import map_content_to_slots
                            slots = _collect_template_slots(selected_json)
                            llm_map = map_content_to_slots(slots, content)
                            if llm_map:
                                slot_value_map = llm_map
                                print("[OK] LLM (Groq) mapped raw content to template slots for accuracy", flush=True)
                        except Exception as llm_err:
                            print(f"[WARN] LLM slot mapping skipped: {llm_err}", flush=True)
                    slot_mode_requested = bool(slot_value_map)
                    raw_content_json = _extract_content_chunks_from_html(content)
                    adjusted_content_json, formatting_plan = _adjust_content_chunks_for_template(raw_content_json, selected_json)
                    merged_json, merge_diagnostics = _replace_elementor_content_only(
                        selected_json,
                        adjusted_content_json,
                        slot_value_map=slot_value_map
                    )
                    merge_diagnostics["slot_map_count"] = len(slot_value_map)
                    merge_diagnostics["formatting_plan"] = formatting_plan
                    preview_diagnostics = {
                        "raw_content_json": raw_content_json,
                        "content_json": adjusted_content_json,
                        "comparison": merge_diagnostics
                    }
                    elementor_override_payload = merged_json
            except Exception as merge_exc:
                print(f"[WARN] Merge pipeline failed; falling back to plugin mapper: {merge_exc}", flush=True)

            bridge_payload = {
                "page_id": target_page_id,
                "content_html": content,
                "status": status,
                "preserve_layout": True,
                "allow_title_update": (not preserve_existing_title),
                "replace_existing_text_only": True,
                # Content-only replacement mode: keep layout/styles and skip strict section contract.
                "strict_labeled_mapping": False
            }
            if elementor_override_payload is not None:
                bridge_payload["elementor_data_override"] = elementor_override_payload
            if not preserve_existing_title and title:
                bridge_payload["title"] = title
            try:
                bridge_response = requests.post(
                    bridge_url,
                    json=bridge_payload,
                    auth=(creds['username'], creds['password']),
                    headers={'Content-Type': 'application/json'},
                    timeout=30
                )
                if bridge_response.status_code in [200, 201]:
                    bridge_result = bridge_response.json() if bridge_response.text else {}
                    bridge_page_id = _parse_int(bridge_result.get("id"))
                    if bridge_page_id and int(bridge_page_id) != int(target_page_id):
                        return (
                            False,
                            f"Bridge updated unexpected page ID {bridge_page_id} (expected {target_page_id})",
                            None,
                            None,
                            None,
                            {"bridge_result": bridge_result}
                        )
                    updated_text_widgets = _parse_int(bridge_result.get("updated_text_widgets")) or 0
                    override_applied = bool(bridge_result.get("override_applied"))
                    if slot_mode_requested and not override_applied:
                        plugin_version = str(bridge_result.get("plugin_version") or "unknown")
                        return (
                            False,
                            (
                                "Selected-page slot template import requires connector support for "
                                "'elementor_data_override', but site plugin did not apply override "
                                f"(plugin_version={plugin_version}). Please update/activate latest "
                                "RevPublish Connector on target WordPress site."
                            ),
                            None,
                            None,
                            None,
                            {"bridge_result": bridge_result, "slot_mode_requested": True}
                        )
                    if updated_text_widgets <= 0 and not override_applied:
                        return (
                            False,
                            (
                                "Bridge returned success but updated 0 content fields. "
                                "No visible content was replaced. Check mapping_debug."
                            ),
                            None,
                            None,
                            None,
                            {"bridge_result": bridge_result}
                        )
                    permalink = bridge_result.get("link")
                    edit_url = f"{protocol}{normalized}/wp-admin/post.php?post={target_page_id}&action=edit"
                    diagnostics_payload: Dict[str, Any] = {"bridge_result": bridge_result}
                    if preview_diagnostics:
                        diagnostics_payload["content_merge_preview"] = preview_diagnostics
                    return True, None, target_page_id, edit_url, permalink, diagnostics_payload

                if preserve_formatting:
                    return (
                        False,
                        f"Bridge update failed {bridge_response.status_code} at {bridge_url}: {bridge_response.text[:220]}",
                        None,
                        None,
                        None,
                        {"bridge_status_code": bridge_response.status_code}
                    )

                print(
                    f"[WARN] Bridge endpoint failed, trying direct fallback: "
                    f"{bridge_response.status_code} {bridge_response.text[:180]}",
                    flush=True
                )
            except Exception as bridge_exc:
                if preserve_formatting:
                    return False, f"Bridge update failed: {str(bridge_exc)[:200]}", None, None, None, None
                print(f"[WARN] Bridge exception, trying direct fallback: {bridge_exc}", flush=True)
        
        # Prepare base payload
        payload = {
            'content': content,  # HTML content (Bridge Plugin will convert if enabled)
            'status': status
        }
        # In strict update flow, keep existing page title untouched.
        if not (target_page_id and preserve_existing_title):
            payload['title'] = title
        
        # Initialize meta dict
        payload['meta'] = {}
        
        # Handle Elementor metadata based on deployment mode
        if use_elementor:
            if use_bridge_plugin:
                # Mode 1: Bridge Plugin Mode
                # Send HTML content, Bridge Plugin will detect and convert to Elementor
                # Set minimal Elementor flags to indicate this should be an Elementor page
                payload['meta'] = {
                    '_elementor_edit_mode': 'builder',
                    '_elementor_template_type': 'page'
                }
                # Bridge Plugin will handle the actual Elementor JSON conversion
            else:
                # Mode 2: Direct Elementor JSON Mode (backward compatibility)
                if meta_data and 'elementor_data' in meta_data:
                    # CRITICAL: Elementor requires _elementor_data as JSON STRING, not dict
                    elementor_json_string = json.dumps(meta_data['elementor_data'])
                    payload['meta'] = {
                        '_elementor_data': elementor_json_string,  # Must be stringified!
                        '_elementor_edit_mode': 'builder',
                        '_elementor_template_type': 'page'
                    }
        
        # Add other metadata if provided
        if meta_data:
            if 'categories' in meta_data:
                payload['categories'] = meta_data['categories']
            if 'tags' in meta_data:
                payload['tags'] = meta_data['tags']
            if 'excerpt' in meta_data:
                payload['excerpt'] = meta_data['excerpt']
            if 'custom_meta' in meta_data:
                # Merge custom meta into existing meta dict
                if 'meta' not in payload:
                    payload['meta'] = {}
                payload['meta'].update(meta_data['custom_meta'])
        
        # Make API request with improved error handling
        try:
            response = requests.post(
                api_url,
                json=payload,
                auth=(creds['username'], creds['password']),
                headers={'Content-Type': 'application/json'},
                timeout=30  # Network timeout protection
            )
            
            # Handle success
            if response.status_code in [200, 201]:
                result = response.json()
                post_id = result.get('id')
                permalink = result.get('link')  # WordPress returns the actual page URL
                
                # For draft pages, WordPress might not return a permalink in 'link' field
                # Try to construct it from the slug or use preview link
                if not permalink and post_id:
                    # Try to get slug from response
                    slug = result.get('slug', '')
                    if slug:
                        clean_site_url = site_url.rstrip('/')
                        permalink = f"{clean_site_url}/{slug}/"
                    else:
                        # Fallback: use preview link for drafts
                        clean_site_url = site_url.replace('https://', '').replace('http://', '').rstrip('/')
                        permalink = f"https://{clean_site_url}/wp-admin/post.php?post={post_id}&action=edit"
                
                # Build edit URL
                clean_site_url = site_url.replace('https://', '').replace('http://', '').rstrip('/')
                edit_url = f"https://{clean_site_url}/wp-admin/post.php?post={post_id}&action=edit"
                
                return True, None, post_id, edit_url, permalink, None
            
            # Handle various error codes
            elif response.status_code == 401:
                return False, f"Authentication failed for {site_url} (check credentials)", None, None, None, None
            elif response.status_code == 403:
                return False, f"Permission denied for {site_url} (user lacks publish capability)", None, None, None, None
            elif response.status_code == 429:
                return False, f"Rate limit exceeded for {site_url} (too many requests)", None, None, None, None
            else:
                error_msg = f"WordPress API error {response.status_code}: {response.text[:200]}"
                return False, error_msg, None, None, None, None
                
        except requests.exceptions.Timeout:
            return False, f"Connection timeout to {site_url} (30s exceeded)", None, None, None, None
        except requests.exceptions.ConnectionError:
            return False, f"Cannot connect to {site_url} (site unreachable)", None, None, None, None
        except requests.exceptions.RequestException as e:
            return False, f"Network error: {str(e)[:100]}", None, None, None, None
            
    except Exception as e:
        # Catch-all for unexpected errors
        error_detail = traceback.format_exc()
        print(f"Unexpected error deploying to {site_url}: {error_detail}", file=sys.stderr, flush=True)
        return False, f"Unexpected deployment error: {str(e)[:100]}", None, None, None, None


@app.post("/api/import")
async def bulk_import_csv_template(
    csv_file: UploadFile = File(...),
    template_file: UploadFile = File(None),
    target_site: Optional[str] = Form(None),  # NEW: Target WordPress site URL
    target_page_id: Optional[str] = Form(None),  # Optional: update this exact page for all rows
    update_selected_page_only: bool = Form(True),
    enable_smart_corrections: bool = Form(True),
    use_llm_assistance: bool = Form(False),
    preview_mode: bool = Form(False),
    post_status: str = Form("draft"),
    use_bridge_plugin: bool = Form(True),  # NEW: Use Bridge Plugin mode (HTML → Bridge Plugin converts)
    preserve_formatting: bool = Form(True)
):
    """
    Bulk import CSV with template merging and deployment.
    
    Supports:
    - Google Doc URLs via page_content_doc_url (+ multi-doc columns) (NEW)
    - Uploaded template files (existing)
    - CSV-only mode with basic Elementor structure (existing)
    - Bridge Plugin mode: Send HTML, let Bridge Plugin convert to Elementor (NEW)
    - Direct Elementor JSON mode: Send Elementor JSON directly (existing)
    """
    try:
        csv_content = await csv_file.read()
        df = pd.read_csv(io.BytesIO(csv_content))
        
        # Load uploaded template file if provided (for backward compatibility)
        uploaded_template_text = ''
        if template_file is not None:
            template_content = await template_file.read()
            uploaded_template_text = template_content.decode('utf-8')
        
        # Validate target site if provided from form
        form_selected_site = target_site.strip() if target_site and target_site.strip() else None
        if form_selected_site:
            creds = get_wordpress_credentials(form_selected_site)
            if not creds:
                raise HTTPException(
                    status_code=400,
                    detail=f"Selected site '{form_selected_site}' does not have WordPress credentials. Please add credentials in the Sites tab first."
                )
            print(f"[OK] Target site validated: {form_selected_site} - All CSV rows will be published to this site", flush=True)

        # site_url column in CSV is optional if form selected a site
        if not form_selected_site and 'site_url' not in df.columns:
            raise HTTPException(
                status_code=400,
                detail="Either select a WordPress site in the form OR include 'site_url' column in CSV"
            )

        # Guardrail inputs derived from form state.
        form_target_page_id = _parse_int(target_page_id)
        if form_target_page_id:
            update_selected_page_only = True

        results = {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "preview_mode": preview_mode,
            "use_bridge_plugin": use_bridge_plugin,
            "preserve_formatting": preserve_formatting,
            "update_selected_page_only": update_selected_page_only,
            "summary": {"total_rows": len(df), "successful_deployments": 0, "failed_deployments": 0, "auto_corrections": 0, "google_docs_fetched": 0, "google_docs_failed": 0},
            "corrections_summary": {"phone_normalized": 0},
            "deployments": []
        }

        # Guardrail: avoid accidentally overwriting one selected page with many CSV rows.
        if update_selected_page_only and form_target_page_id and len(df) > 1:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Update Selected Page Only is enabled and a single target_page_id is selected, "
                    "but CSV has multiple rows. Use a single-row CSV for page replacement, or disable "
                    "Update Selected Page Only."
                )
            )
        
        for index, row in df.iterrows():
            row_number = index + 1
            row_dict = row.to_dict()
            
            # Clean row_dict: convert NaN/float values to empty strings
            cleaned_row_dict = {}
            for key, value in row_dict.items():
                if pd.isna(value) or value is None:
                    cleaned_row_dict[key] = ''
                elif isinstance(value, (int, float)) and pd.isna(value):
                    cleaned_row_dict[key] = ''
                else:
                    cleaned_row_dict[key] = str(value).strip() if isinstance(value, str) else str(value)
            
            row_dict = cleaned_row_dict
            
            # Get target site: use form parameter if provided, otherwise use CSV row
            if form_selected_site:
                # Use the selected site from the form dropdown (publish all rows to this site)
                row_target_site = form_selected_site
                print(f"[INFO] Row {row_number}: Using selected site from form: {row_target_site}", flush=True)
            else:
                # Fallback to CSV site_url if no site selected in form
                row_target_site = row_dict.get('site_url', '').strip()
                if not row_target_site:
                    results["deployments"].append({"row_number": row_number, "status": "error", "message": "Missing site_url. Either select a site in the form or include 'site_url' in CSV."})
                    results["summary"]["failed_deployments"] += 1
                    continue
            
            deployment_site = row_target_site
            csv_target_page_id, csv_target_source = resolve_target_page_id(row_dict, deployment_site)
            active_target_page_id = form_target_page_id or csv_target_page_id
            if active_target_page_id:
                print(
                    f"[INFO] Row {row_number}: update target resolved => "
                    f"form_target_page_id={form_target_page_id}, "
                    f"csv_target_page_id={csv_target_page_id}, "
                    f"active_target_page_id={active_target_page_id}, "
                    f"source={csv_target_source}",
                    flush=True
                )
            elif update_selected_page_only:
                results["deployments"].append({
                    "row_number": row_number,
                    "status": "failed",
                    "message": (
                        "No target page resolved. Select a target page in the form or provide "
                        "existing_page_id/target_page_id/page_id in CSV."
                    ),
                    "site_info": {"site_url": deployment_site}
                })
                results["summary"]["failed_deployments"] += 1
                continue
            
            corrections_applied = []
            if enable_smart_corrections and 'phone' in row_dict and row_dict['phone']:
                normalized, changed = normalize_phone_number(row_dict['phone'])
                if changed:
                    corrections_applied.append({"field": "phone", "from": row_dict['phone'], "to": normalized})
                    row_dict['phone'] = normalized
                    results["corrections_summary"]["phone_normalized"] += 1
                    results["summary"]["auto_corrections"] += 1
            
            template_html = None
            template_source = None

            # Priority 1: Google Docs from CSV row (supports multiple docs).
            doc_urls = collect_google_doc_urls_from_row(row_dict)
            if doc_urls:
                try:
                    from integrations.google_integrations import GoogleDocsClient
                    google_docs = GoogleDocsClient()
                    fetched_docs_html: List[str] = []
                    for doc_url in doc_urls:
                        try:
                            doc_content = google_docs.extract_from_url(doc_url)
                            content_html = str(doc_content.get("content_html", "")).strip()
                            if content_html:
                                fetched_docs_html.append(content_html)
                                results["summary"]["google_docs_fetched"] += 1
                                print(f"[OK] ROW {row_number}: Fetched Google Doc from {doc_url}", flush=True)
                            else:
                                results["summary"]["google_docs_failed"] += 1
                                print(f"[WARN] ROW {row_number}: Empty Google Doc content for {doc_url}", flush=True)
                        except Exception as single_doc_error:
                            results["summary"]["google_docs_failed"] += 1
                            print(
                                f"[ERROR] ROW {row_number}: Failed to fetch Google Doc {doc_url}: {str(single_doc_error)}",
                                flush=True
                            )

                    if fetched_docs_html:
                        # Join docs in order so plugin can map content progressively into text widgets.
                        template_html = "\n\n<hr />\n\n".join(fetched_docs_html)
                        template_source = f"Google Docs ({len(fetched_docs_html)} of {len(doc_urls)} fetched)"
                    elif uploaded_template_text:
                        template_html = uploaded_template_text
                        template_source = "Uploaded template file (fallback)"
                    else:
                        template_html = None
                        template_source = None
                except Exception as e:
                    print(f"[ERROR] ROW {row_number}: Google Docs client error: {str(e)}", flush=True)
                    if uploaded_template_text:
                        template_html = uploaded_template_text
                        template_source = "Uploaded template file (fallback)"
                    else:
                        template_html = None
                        template_source = None
            
            # Fallback: Use uploaded template file (priority 2, backward compatibility)
            elif uploaded_template_text:
                template_html = uploaded_template_text
                template_source = "Uploaded template file"
            
            # Merge fields in template if we have one
            if template_html:
                merged_content = merge_template_fields(template_html, row_dict)
                content_source = template_source
            else:
                # Fallback: CSV-only mode - use basic HTML structure (backward compatibility)
                merged_content = build_elementor_page_content(row_dict)
                content_source = "Basic HTML structure (CSV-only mode)"
            # Generate page title - safely handle NaN values
            def safe_get(key, default=''):
                val = row_dict.get(key, default)
                if pd.isna(val) or val is None:
                    return default
                return str(val).strip() if isinstance(val, str) else str(val)
            
            niche = safe_get('niche', 'Services')
            city = safe_get('city', '')
            state = safe_get('state', '')
            business_name = safe_get('business_name', '')
            
            # Smart page title generation
            if business_name:
                page_title = f"{business_name} - {niche} in {city}, {state}".strip()
            else:
                page_title = f"Professional {niche} Services in {city}, {state}".strip()
            
            page_slug = f"{niche.lower().replace(' ', '-')}-{city.lower().replace(' ', '-')}-{state.lower()}".strip('-')
            
            # Prepare content for deployment
            # If using Bridge Plugin mode, send HTML directly
            # If using direct Elementor mode, build Elementor JSON
            if use_bridge_plugin:
                # Mode 1: HTML → Bridge Plugin converts to Elementor
                html_content = merged_content
                elementor_data = None  # Bridge Plugin will generate this
            else:
                # Mode 2: Direct Elementor JSON (backward compatibility)
                elementor_data = build_elementor_json(row_dict)
                html_content = merged_content  # Also send HTML as fallback
            
            # Deploy to WordPress if not in preview mode
            wp_post_id = None
            wp_edit_url = None
            wp_permalink = None
            deployment_error = None
            deployment_diagnostics: Optional[Dict[str, Any]] = None
            
            print(f"[INFO] ROW {row_number}: preview_mode={preview_mode}, target={deployment_site}, source={content_source}", flush=True)
            
            if not preview_mode:
                action_label = "UPDATING" if active_target_page_id else "DEPLOYING"
                print(f"[RUN] {action_label} on {deployment_site}: {page_title}", flush=True)
                print(f"   Mode: {'Bridge Plugin (HTML)' if use_bridge_plugin else 'Direct Elementor JSON'}", flush=True)
                
                # Prepare meta_data based on mode
                meta_data = {
                    'excerpt': f"{niche} services in {city}, {state}",
                    'custom_meta': {
                        'business_name': business_name,
                        'phone': safe_get('phone', ''),
                        'email': safe_get('email', ''),
                        'city': city,
                        'state': state,
                        'niche': niche
                    }
                }
                
                # Add Elementor data only if NOT using Bridge Plugin mode
                if not use_bridge_plugin and elementor_data:
                    meta_data['elementor_data'] = elementor_data
                
                # Deploy to WordPress
                preserve_existing_title = bool(active_target_page_id and update_selected_page_only)
                success, error_msg, wp_post_id, wp_edit_url, wp_permalink, deployment_diagnostics = deploy_to_wordpress(
                    site_url=deployment_site,
                    title=page_title,
                    content=html_content,  # HTML content (Bridge Plugin will convert if enabled)
                    status=post_status,
                    meta_data=meta_data,
                    use_bridge_plugin=use_bridge_plugin,  # NEW parameter
                    use_elementor=True,  # Create Elementor page
                    target_page_id=active_target_page_id,
                    preserve_formatting=preserve_formatting,
                    preserve_existing_title=preserve_existing_title,
                    use_llm_assistance=use_llm_assistance,
                )
                
                if not success:
                    deployment_error = error_msg
                    results["summary"]["failed_deployments"] += 1
                    print(f"[ERROR] DEPLOYMENT FAILED for {deployment_site}: {error_msg}", flush=True)
                else:
                    # Strict mode: never allow accidental new-page creation when update is intended.
                    if update_selected_page_only and active_target_page_id and wp_post_id and int(wp_post_id) != int(active_target_page_id):
                        deployment_error = (
                            f"Update mode violation: expected page ID {active_target_page_id}, "
                            f"but WordPress returned page ID {wp_post_id}."
                        )
                        results["summary"]["failed_deployments"] += 1
                        print(f"[ERROR] {deployment_error}", flush=True)
                    else:
                        results["summary"]["successful_deployments"] += 1
                        print(f"[OK] DEPLOYMENT SUCCESS for {deployment_site}: Post ID {wp_post_id}", flush=True)
                        print(f"   Edit URL: {wp_edit_url}", flush=True)
                        if wp_permalink:
                            print(f"   Page URL: {wp_permalink}", flush=True)
            else:
                # Preview mode - just validation
                results["summary"]["successful_deployments"] += 1
            
            # Build deployment result
            deployment_result = {
                "row_number": row_number,
                "status": "preview" if preview_mode else ("deployed" if wp_post_id else "failed"),
                "site_info": {
                    "site_url": deployment_site,
                    "business_name": business_name,
                    "niche": niche,
                    "city": city,
                    "state": state
                },
                "page_info": {
                    "title": page_title,
                    "slug": page_slug,
                    "page_url": wp_permalink or (f"https://{deployment_site.rstrip('/')}/{page_slug}/" if wp_post_id else None),
                    "wp_admin_url": wp_edit_url or (f"https://{deployment_site.rstrip('/')}/wp-admin/post.php?post={wp_post_id}&action=edit" if wp_post_id else None),
                    "post_status": post_status,
                    "wp_post_id": wp_post_id,
                    "uses_elementor": True,
                    "update_mode": bool(active_target_page_id),
                    "target_page_id": active_target_page_id,
                    "target_page_source": "form" if form_target_page_id else (csv_target_source or None)
                },
                "merged_fields": {k.upper(): (str(v) if not pd.isna(v) and v is not None else '') for k, v in row_dict.items()},
                "corrections_applied": corrections_applied,
                "content_source": content_source,
                "deployment_mode": "Bridge Plugin (HTML)" if use_bridge_plugin else "Direct Elementor JSON",
                "message": "Preview only" if preview_mode else ("Deployed successfully" if wp_post_id else deployment_error)
            }
            
            if deployment_error:
                deployment_result["error"] = deployment_error
            if deployment_diagnostics:
                deployment_result["diagnostics"] = deployment_diagnostics
            
            results["deployments"].append(deployment_result)
        
        return results
    except Exception as e:
        error_detail = traceback.format_exc()
        print(f"ERROR in /api/import: {error_detail}", file=sys.stderr, flush=True)
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")
