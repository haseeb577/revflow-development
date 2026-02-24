"""
QUICK WINS API - Complete Version with GSC OAuth
SmarketSherpa Platform - December 2025
"""
import os, sys, json, re, logging, pickle
from datetime import datetime
from flask import Flask, Blueprint, request, jsonify, g, redirect, session
from flask_cors import CORS
import psycopg2
from psycopg2.extras import RealDictCursor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_db():
    if 'db' not in g:
        g.db = psycopg2.connect(
            host=os.environ.get('DB_HOST', 'localhost'),
            port=os.environ.get('DB_PORT', '5432'),
            database=os.environ.get('DB_NAME', 'knowledge_graph_db'),
            user=os.environ.get('DB_USER', 'knowledge_admin'),
            password=os.environ.get('DB_PASSWORD', ''),
            cursor_factory=RealDictCursor
        )
    return g.db

def close_db(e=None):
    db = g.pop('db', None)
    if db: db.close()

def slugify(t): return re.sub(r'[-\s]+', '-', re.sub(r'[^\w\s-]', '', t.lower().strip()))
def extract_vars(c): return list(set(re.findall(r'\{\{\s*([a-zA-Z_][a-zA-Z0-9_\.]*)\s*\}\}', c)))

# PROMPTS BLUEPRINT
prompt_bp = Blueprint('prompts', __name__, url_prefix='/api/prompts')

@prompt_bp.route('/categories', methods=['GET'])
def list_categories():
    try:
        cur = get_db().cursor()
        cur.execute("SELECT c.*, COUNT(p.id) as prompt_count FROM prompt_categories c LEFT JOIN prompts p ON p.category_id = c.id AND p.is_active = true GROUP BY c.id ORDER BY c.name")
        return jsonify({'success': True, 'categories': cur.fetchall()})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@prompt_bp.route('/', methods=['GET'])
def list_prompts():
    try:
        category = request.args.get('category')
        cur = get_db().cursor()
        query = "SELECT p.*, c.name as category_name FROM prompts p JOIN prompt_categories c ON c.id = p.category_id WHERE p.is_active = true"
        params = []
        if category:
            query += " AND c.name = %s"
            params.append(category)
        query += " ORDER BY c.name, p.name"
        cur.execute(query, params)
        prompts = cur.fetchall()
        return jsonify({'success': True, 'prompts': prompts, 'count': len(prompts)})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@prompt_bp.route('/', methods=['POST'])
def create_prompt():
    try:
        data = request.get_json()
        if not data: return jsonify({'success': False, 'error': 'No data'}), 400
        category_name, name, content = data.get('category'), data.get('name'), data.get('content')
        if not all([category_name, name, content]): return jsonify({'success': False, 'error': 'category, name, content required'}), 400
        slug, variables, metadata = slugify(name), extract_vars(content), data.get('metadata', {})
        db, cur = get_db(), get_db().cursor()
        cur.execute("SELECT id FROM prompt_categories WHERE name = %s", (category_name,))
        cat = cur.fetchone()
        if not cat: return jsonify({'success': False, 'error': f'Category {category_name} not found'}), 404
        cur.execute("SELECT COALESCE(MAX(version), 0) + 1 as v FROM prompts WHERE slug = %s", (slug,))
        version = cur.fetchone()['v']
        cur.execute("INSERT INTO prompts (category_id, name, slug, version, content, variables, metadata, created_by) VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING *",
            (cat['id'], name, slug, version, content, json.dumps(variables), json.dumps(metadata), data.get('created_by', 'api')))
        prompt = cur.fetchone()
        db.commit()
        return jsonify({'success': True, 'prompt': prompt}), 201
    except Exception as e:
        logger.error(f"Error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@prompt_bp.route('/import', methods=['POST'])
def bulk_import():
    try:
        data = request.get_json()
        if not data: return jsonify({'success': False, 'error': 'No data'}), 400
        prompts_data = data.get('prompts', [])
        imported_by = data.get('imported_by', 'bulk_import')
        if not prompts_data: return jsonify({'success': False, 'error': 'No prompts'}), 400
        db, cur = get_db(), get_db().cursor()
        results = {'imported': 0, 'skipped': 0, 'errors': []}
        for p in prompts_data:
            try:
                category_name, name, content = p.get('category'), p.get('name'), p.get('content')
                if not all([category_name, name, content]):
                    results['errors'].append(f"Missing fields: {p.get('name', 'unknown')}")
                    results['skipped'] += 1
                    continue
                slug, variables, metadata = slugify(name), extract_vars(content), p.get('metadata', {})
                cur.execute("SELECT id FROM prompt_categories WHERE name = %s", (category_name,))
                cat = cur.fetchone()
                if not cat:
                    results['errors'].append(f"Category not found: {category_name}")
                    results['skipped'] += 1
                    continue
                cur.execute("SELECT COALESCE(MAX(version), 0) + 1 as v FROM prompts WHERE slug = %s", (slug,))
                version = cur.fetchone()['v']
                cur.execute("INSERT INTO prompts (category_id, name, slug, version, content, variables, metadata, created_by) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                    (cat['id'], name, slug, version, content, json.dumps(variables), json.dumps(metadata), imported_by))
                results['imported'] += 1
            except Exception as e:
                results['errors'].append(f"Error: {p.get('name', 'unknown')}: {str(e)}")
                results['skipped'] += 1
        db.commit()
        return jsonify({'success': True, 'results': results})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@prompt_bp.route('/render', methods=['POST'])
def render_prompt():
    try:
        data = request.get_json()
        category, name, variables = data.get('category'), data.get('name'), data.get('variables', {})
        if not category or not name: return jsonify({'success': False, 'error': 'category and name required'}), 400
        cur = get_db().cursor()
        cur.execute("SELECT p.content, p.version FROM prompts p JOIN prompt_categories c ON c.id = p.category_id WHERE c.name = %s AND p.slug = %s AND p.is_active = true ORDER BY p.version DESC LIMIT 1", (category, slugify(name)))
        prompt = cur.fetchone()
        if not prompt: return jsonify({'success': False, 'error': 'Prompt not found'}), 404
        rendered = prompt['content']
        for key, value in variables.items():
            rendered = re.sub(r'\{\{\s*' + re.escape(key) + r'\s*\}\}', str(value), rendered)
        return jsonify({'success': True, 'rendered': rendered, 'version_used': prompt['version']})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# LEADS BLUEPRINT
leads_bp = Blueprint('leads', __name__, url_prefix='/api/leads')

def calc_budget(f, e):
    score = 5
    rev = (f.get('revenue_range', '') if f else '').lower()
    if '$10m' in rev or '$5m' in rev: score = 35
    elif '$1m' in rev: score = 25
    elif '$500k' in rev: score = 15
    if e and e.get('pages_viewed', 0) > 5: score += 5
    return min(score, 40)

def calc_pain(e):
    if not e: return 10
    score, pages, time_on_site, returns = 0, e.get('pages_viewed', 0), e.get('time_on_site', 0), e.get('return_visits', 0)
    if pages > 10: score += 15
    elif pages > 5: score += 10
    elif pages > 2: score += 5
    if time_on_site > 300: score += 10
    elif time_on_site > 120: score += 7
    elif time_on_site > 60: score += 3
    if returns > 2: score += 10
    elif returns > 0: score += 5
    return min(score, 35)

def calc_icp(f):
    if not f: return 5
    score, industry = 0, f.get('industry', '').lower()
    if any(t in industry for t in ['plumbing', 'hvac', 'electrical', 'roofing', 'pest', 'moving', 'legal', 'law']): score += 15
    emp = f.get('employee_count', '').lower()
    if '10-50' in emp or '50-100' in emp: score += 10
    elif '1-10' in emp: score += 5
    return min(score, 25)

@leads_bp.route('/webhook/simpleaudience', methods=['POST'])
def simpleaudience_webhook():
    try:
        data = request.get_json()
        if not data: return jsonify({'error': 'No data'}), 400
        company_name, company_domain = data.get('company_name'), data.get('company_domain')
        contact_email, contact_name = data.get('contact_email'), data.get('contact_name')
        firmographics, engagement = data.get('firmographics', {}), data.get('engagement_signals', {})
        ghl_contact_id = data.get('ghl_contact_id', data.get('visitor_id'))
        budget_score, pain_score, icp_score = calc_budget(firmographics, engagement), calc_pain(engagement), calc_icp(firmographics)
        total_score = budget_score + pain_score + icp_score
        priority = 'P0' if total_score >= 75 else 'P1' if total_score >= 55 else 'P2' if total_score >= 35 else 'P3'
        synopsis = f"{company_name or 'Unknown'} ({priority}): Score {total_score}/100. Budget: {budget_score}/40, Pain: {pain_score}/35, ICP: {icp_score}/25."
        if firmographics.get('industry'): synopsis += f" Industry: {firmographics['industry']}."
        db, cur = get_db(), get_db().cursor()
        cur.execute("""INSERT INTO lead_synopses (ghl_contact_id, company_name, company_domain, contact_email, contact_name, lead_score_total, budget_likelihood_score, pain_impact_score, icp_fit_score, priority_tier, synopsis, synopsis_generated_at, engagement_signals, firmographics) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, %s, %s) ON CONFLICT (ghl_contact_id) DO UPDATE SET company_name = EXCLUDED.company_name, lead_score_total = EXCLUDED.lead_score_total, budget_likelihood_score = EXCLUDED.budget_likelihood_score, pain_impact_score = EXCLUDED.pain_impact_score, icp_fit_score = EXCLUDED.icp_fit_score, priority_tier = EXCLUDED.priority_tier, synopsis = EXCLUDED.synopsis, synopsis_generated_at = CURRENT_TIMESTAMP, engagement_signals = EXCLUDED.engagement_signals, firmographics = EXCLUDED.firmographics, updated_at = CURRENT_TIMESTAMP RETURNING *""",
            (ghl_contact_id, company_name, company_domain, contact_email, contact_name, total_score, budget_score, pain_score, icp_score, priority, synopsis, json.dumps(engagement), json.dumps(firmographics)))
        lead = cur.fetchone()
        db.commit()
        return jsonify({'success': True, 'lead_id': lead['id'], 'priority_tier': priority, 'total_score': total_score, 'synopsis': synopsis}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@leads_bp.route('/', methods=['GET'])
def list_leads():
    try:
        priority, limit = request.args.get('priority'), int(request.args.get('limit', 50))
        cur = get_db().cursor()
        query, params = "SELECT * FROM lead_synopses WHERE 1=1", []
        if priority: query += " AND priority_tier = %s"; params.append(priority)
        query += " ORDER BY lead_score_total DESC, created_at DESC LIMIT %s"; params.append(limit)
        cur.execute(query, params)
        return jsonify({'success': True, 'leads': cur.fetchall()})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@leads_bp.route('/stats', methods=['GET'])
def lead_stats():
    try:
        cur = get_db().cursor()
        cur.execute("SELECT priority_tier, COUNT(*) as count, AVG(lead_score_total) as avg_score FROM lead_synopses GROUP BY priority_tier ORDER BY priority_tier")
        stats = cur.fetchall()
        cur.execute("SELECT COUNT(*) as total FROM lead_synopses")
        return jsonify({'success': True, 'total_leads': cur.fetchone()['total'], 'by_priority': stats})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# GSC BLUEPRINT
gsc_bp = Blueprint('gsc', __name__, url_prefix='/api/gsc')
GSC_SCOPES = ['https://www.googleapis.com/auth/webmasters.readonly']
GSC_SECRETS_FILE = os.environ.get('GSC_CLIENT_SECRETS', '/opt/config/gsc_credentials.json')
GSC_TOKEN_PATH = os.environ.get('GSC_TOKEN_PATH', '/opt/config/gsc_token.pickle')
GSC_REDIRECT_URI = os.environ.get('GSC_REDIRECT_URI', 'http://217.15.168.106.nip.io:8150/api/gsc/oauth/callback')

def get_gsc_credentials():
    if os.path.exists(GSC_TOKEN_PATH):
        try:
            with open(GSC_TOKEN_PATH, 'rb') as token: return pickle.load(token)
        except: return None
    return None

def save_gsc_credentials(creds):
    os.makedirs(os.path.dirname(GSC_TOKEN_PATH), exist_ok=True)
    with open(GSC_TOKEN_PATH, 'wb') as token: pickle.dump(creds, token)

@gsc_bp.route('/oauth/status', methods=['GET'])
def gsc_oauth_status():
    creds = get_gsc_credentials()
    if creds: return jsonify({'success': True, 'authenticated': True, 'expired': getattr(creds, 'expired', False)})
    return jsonify({'success': True, 'authenticated': False, 'credentials_file_exists': os.path.exists(GSC_SECRETS_FILE), 'message': 'Not authenticated - use /oauth/start'})

@gsc_bp.route('/oauth/start', methods=['GET'])
def gsc_oauth_start():
    try:
        if not os.path.exists(GSC_SECRETS_FILE): return jsonify({'success': False, 'error': f'GSC credentials not found at {GSC_SECRETS_FILE}'}), 400
        from google_auth_oauthlib.flow import Flow
        flow = Flow.from_client_secrets_file(GSC_SECRETS_FILE, scopes=GSC_SCOPES, redirect_uri=GSC_REDIRECT_URI)
        authorization_url, state = flow.authorization_url(access_type='offline', include_granted_scopes='true', prompt='consent')
        session['gsc_oauth_state'] = state
        return jsonify({'success': True, 'authorization_url': authorization_url, 'state': state, 'instructions': 'Visit the authorization_url in your browser'})
    except ImportError:
        return jsonify({'success': False, 'error': 'google-auth-oauthlib not installed'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@gsc_bp.route('/oauth/callback', methods=['GET'])
def gsc_oauth_callback():
    try:
        from google_auth_oauthlib.flow import Flow
        state = session.get('gsc_oauth_state')
        flow = Flow.from_client_secrets_file(GSC_SECRETS_FILE, scopes=GSC_SCOPES, state=state, redirect_uri=GSC_REDIRECT_URI)
        flow.fetch_token(authorization_response=request.url)
        save_gsc_credentials(flow.credentials)
        return jsonify({'success': True, 'message': 'GSC OAuth completed successfully!'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@gsc_bp.route('/properties', methods=['GET'])
def gsc_list_properties():
    try:
        creds = get_gsc_credentials()
        if not creds: return jsonify({'success': False, 'error': 'Not authenticated'}), 401
        from googleapiclient.discovery import build
        service = build('searchconsole', 'v1', credentials=creds)
        site_list = service.sites().list().execute()
        return jsonify({'success': True, 'properties': site_list.get('siteEntry', [])})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@gsc_bp.route('/properties/registered', methods=['GET'])
def gsc_registered_properties():
    try:
        cur = get_db().cursor()
        cur.execute("SELECT * FROM gsc_properties ORDER BY property_url")
        return jsonify({'success': True, 'properties': cur.fetchall()})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# PHOTOS BLUEPRINT
photos_bp = Blueprint('photos', __name__, url_prefix='/api/photos')

@photos_bp.route('/submissions', methods=['GET'])
def photo_submissions():
    try:
        cur = get_db().cursor()
        cur.execute("SELECT * FROM photo_submissions ORDER BY submission_time DESC LIMIT 50")
        return jsonify({'success': True, 'submissions': cur.fetchall()})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@photos_bp.route('/stats', methods=['GET'])
def photo_stats():
    try:
        cur = get_db().cursor()
        cur.execute("SELECT status, COUNT(*) as count FROM photo_submissions GROUP BY status")
        by_status = cur.fetchall()
        cur.execute("SELECT COUNT(*) as total FROM photo_submissions")
        total = cur.fetchone()['total']
        cur.execute("SELECT COUNT(*) as total FROM photos")
        total_photos = cur.fetchone()['total']
        return jsonify({'success': True, 'total_submissions': total, 'total_photos': total_photos, 'by_status': by_status})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# FLASK APP
app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'quick-wins-secret-key-change-in-production')
CORS(app)

# RevAudit Anti-Hallucination Integration
sys.path.insert(0, '/opt/shared-api-engine')
try:
    from revaudit.flask_integration import integrate_revaudit_flask
    integrate_revaudit_flask(app, "RevWins")
    print("[RevAudit] ✅ Integrated with RevWins")
except ImportError as e:
    print(f"[RevAudit] ⚠️ Not available: {e}")

app.register_blueprint(prompt_bp)
app.register_blueprint(leads_bp)
app.register_blueprint(gsc_bp)
app.register_blueprint(photos_bp)

@app.teardown_appcontext
def teardown(e=None): close_db(e)

@app.route('/health')
def health(): return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat(), 'version': '2.0.0'})

@app.route('/api')
def api_docs(): return jsonify({'name': 'Quick Wins API', 'version': '2.0.0', 'endpoints': ['/api/prompts', '/api/leads', '/api/gsc', '/api/photos']})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8100)), debug=True)
