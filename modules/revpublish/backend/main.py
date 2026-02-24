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

import psycopg2
import os
import json
from dotenv import load_dotenv

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
        print(f"⚠️  No WordPress credentials found for {site_url} (normalized: {normalized_input})", flush=True)
        return None
    except Exception as e:
        print(f"❌ Error getting WordPress credentials for {site_url}: {e}", file=sys.stderr, flush=True)
        import traceback
        traceback.print_exc()
        return None


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
    use_elementor: bool = True
) -> Tuple[bool, Optional[str], Optional[int], Optional[str]]:
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
        Tuple of (success, error_message, post_id, edit_url, permalink)
    """
    try:
        # Get WordPress credentials
        creds = get_wordpress_credentials(site_url)
        if not creds:
            return False, f"No WordPress credentials found for {site_url}. Please add credentials in the Sites tab first.", None, None, None
        
        # Prepare API endpoint (pages for Elementor, posts for standard)
        endpoint_type = 'pages' if use_elementor else 'posts'
        api_url = creds['api_url'].rstrip('/') + f'/{endpoint_type}'
        
        # Prepare base payload
        payload = {
            'title': title,
            'content': content,  # HTML content (Bridge Plugin will convert if enabled)
            'status': status
        }
        
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
                
                return True, None, post_id, edit_url, permalink
            
            # Handle various error codes
            elif response.status_code == 401:
                return False, f"Authentication failed for {site_url} (check credentials)", None, None, None
            elif response.status_code == 403:
                return False, f"Permission denied for {site_url} (user lacks publish capability)", None, None, None
            elif response.status_code == 429:
                return False, f"Rate limit exceeded for {site_url} (too many requests)", None, None, None
            else:
                error_msg = f"WordPress API error {response.status_code}: {response.text[:200]}"
                return False, error_msg, None, None, None
                
        except requests.exceptions.Timeout:
            return False, f"Connection timeout to {site_url} (30s exceeded)", None, None, None
        except requests.exceptions.ConnectionError:
            return False, f"Cannot connect to {site_url} (site unreachable)", None, None, None
        except requests.exceptions.RequestException as e:
            return False, f"Network error: {str(e)[:100]}", None, None, None
            
    except Exception as e:
        # Catch-all for unexpected errors
        error_detail = traceback.format_exc()
        print(f"Unexpected error deploying to {site_url}: {error_detail}", file=sys.stderr, flush=True)
        return False, f"Unexpected deployment error: {str(e)[:100]}", None, None, None


@app.post("/api/import")
async def bulk_import_csv_template(
    csv_file: UploadFile = File(...),
    template_file: UploadFile = File(None),
    target_site: Optional[str] = Form(None),  # NEW: Target WordPress site URL
    enable_smart_corrections: bool = Form(True),
    use_llm_assistance: bool = Form(False),
    preview_mode: bool = Form(False),
    post_status: str = Form("draft"),
    use_bridge_plugin: bool = Form(True)  # NEW: Use Bridge Plugin mode (HTML → Bridge Plugin converts)
):
    """
    Bulk import CSV with template merging and deployment.
    
    Supports:
    - Google Doc URLs via page_content_doc_url column (NEW)
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
        if target_site and target_site.strip():
            # Verify the selected site has credentials
            creds = get_wordpress_credentials(target_site.strip())
            if not creds:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Selected site '{target_site}' does not have WordPress credentials. Please add credentials in the Sites tab first."
                )
            print(f"✅ Target site validated: {target_site} - All CSV rows will be published to this site", flush=True)
        
        # Note: site_url column in CSV is optional if target_site is provided from form
        # If target_site is not provided, CSV must have site_url column
        if not target_site and 'site_url' not in df.columns:
            raise HTTPException(
                status_code=400, 
                detail="Either select a WordPress site in the form OR include 'site_url' column in CSV"
            )
        
        results = {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "preview_mode": preview_mode,
            "use_bridge_plugin": use_bridge_plugin,
            "summary": {"total_rows": len(df), "successful_deployments": 0, "failed_deployments": 0, "auto_corrections": 0, "google_docs_fetched": 0, "google_docs_failed": 0},
            "corrections_summary": {"phone_normalized": 0},
            "deployments": []
        }
        
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
            if target_site and target_site.strip():
                # Use the selected site from the form dropdown (publish all rows to this site)
                row_target_site = target_site.strip()
                print(f"📍 Row {row_number}: Using selected site from form: {row_target_site}", flush=True)
            else:
                # Fallback to CSV site_url if no site selected in form
                row_target_site = row_dict.get('site_url', '').strip()
                if not row_target_site:
                    results["deployments"].append({"row_number": row_number, "status": "error", "message": "Missing site_url. Either select a site in the form or include 'site_url' in CSV."})
                    results["summary"]["failed_deployments"] += 1
                    continue
            
            target_site = row_target_site  # Use for deployment
            
            corrections_applied = []
            if enable_smart_corrections and 'phone' in row_dict and row_dict['phone']:
                normalized, changed = normalize_phone_number(row_dict['phone'])
                if changed:
                    corrections_applied.append({"field": "phone", "from": row_dict['phone'], "to": normalized})
                    row_dict['phone'] = normalized
                    results["corrections_summary"]["phone_normalized"] += 1
                    results["summary"]["auto_corrections"] += 1
            
            # NEW: Check for Google Doc URL (priority 1)
            # Safely get doc_url, handling NaN/None values
            doc_url_value = row_dict.get('page_content_doc_url', '')
            if doc_url_value and not pd.isna(doc_url_value):
                doc_url = str(doc_url_value).strip()
            else:
                doc_url = ''
            template_html = None
            template_source = None
            
            if doc_url:
                # Fetch Google Doc content
                try:
                    from integrations.google_integrations import GoogleDocsClient
                    google_docs = GoogleDocsClient()
                    doc_content = google_docs.extract_from_url(doc_url)
                    template_html = doc_content['content_html']
                    template_source = f"Google Doc: {doc_url}"
                    results["summary"]["google_docs_fetched"] += 1
                    print(f"✅ ROW {row_number}: Fetched Google Doc from {doc_url}", flush=True)
                except Exception as e:
                    error_msg = f"Failed to fetch Google Doc {doc_url}: {str(e)}"
                    print(f"❌ ROW {row_number}: {error_msg}", flush=True)
                    results["summary"]["google_docs_failed"] += 1
                    # Fall back to uploaded template or basic structure
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
            
            print(f"🔍 ROW {row_number}: preview_mode={preview_mode}, target={target_site}, source={content_source}", flush=True)
            
            if not preview_mode:
                print(f"🚀 DEPLOYING to {target_site}: {page_title}", flush=True)
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
                success, error_msg, wp_post_id, wp_edit_url, wp_permalink = deploy_to_wordpress(
                    site_url=target_site,
                    title=page_title,
                    content=html_content,  # HTML content (Bridge Plugin will convert if enabled)
                    status=post_status,
                    meta_data=meta_data,
                    use_bridge_plugin=use_bridge_plugin,  # NEW parameter
                    use_elementor=True  # Create Elementor page
                )
                
                if not success:
                    deployment_error = error_msg
                    results["summary"]["failed_deployments"] += 1
                    print(f"❌ DEPLOYMENT FAILED for {target_site}: {error_msg}", flush=True)
                else:
                    results["summary"]["successful_deployments"] += 1
                    print(f"✅ DEPLOYMENT SUCCESS for {target_site}: Post ID {wp_post_id}", flush=True)
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
                    "site_url": target_site,
                    "business_name": business_name,
                    "niche": niche,
                    "city": city,
                    "state": state
                },
                "page_info": {
                    "title": page_title,
                    "slug": page_slug,
                    "page_url": wp_permalink or (f"https://{target_site.rstrip('/')}/{page_slug}/" if wp_post_id else None),
                    "wp_admin_url": wp_edit_url or (f"https://{target_site.rstrip('/')}/wp-admin/post.php?post={wp_post_id}&action=edit" if wp_post_id else None),
                    "post_status": post_status,
                    "wp_post_id": wp_post_id,
                    "uses_elementor": True
                },
                "merged_fields": {k.upper(): (str(v) if not pd.isna(v) and v is not None else '') for k, v in row_dict.items()},
                "corrections_applied": corrections_applied,
                "content_source": content_source,
                "deployment_mode": "Bridge Plugin (HTML)" if use_bridge_plugin else "Direct Elementor JSON",
                "message": "Preview only" if preview_mode else ("Deployed successfully" if wp_post_id else deployment_error)
            }
            
            if deployment_error:
                deployment_result["error"] = deployment_error
            
            results["deployments"].append(deployment_result)
        
        return results
    except Exception as e:
        error_detail = traceback.format_exc()
        print(f"ERROR in /api/import: {error_detail}", file=sys.stderr, flush=True)
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")
