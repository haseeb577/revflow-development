"""
RevCite API Service
Port: 8600
Provides REST API for citation tracking and optimization
RevAudit: ENABLED
"""
from flask import Flask, request, jsonify
from flask_cors import CORS
import sys
import os
import json
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('/opt/revcite/logs/api.log'), logging.StreamHandler()])
logger = logging.getLogger(__name__)

# Add integrations to path
sys.path.insert(0, '/opt/revcite/integrations')

app = Flask(__name__)
CORS(app)

# RevAudit Anti-Hallucination Integration
sys.path.insert(0, '/opt/shared-api-engine')
try:
    from revaudit.flask_integration import integrate_revaudit_flask
    integrate_revaudit_flask(app, "RevCite_Pro")
    logger.info("[RevAudit] ✅ Integrated with RevCite Pro")
except ImportError as e:
    logger.warning(f"[RevAudit] ⚠️ Not available: {e}")

# Config file path
CONFIG_FILE = '/opt/revcite/config/tracking_config.json'

def load_config():
    """Load configuration"""
    try:
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Could not load config: {e}")
        return {
            "clarity_project_id": "not_configured",
            "indexnow_key": "not_configured",
            "default_host": "example.com",
            "citation_velocity_threshold": 2.0
        }

def get_engine():
    """Get citation optimization engine (lazy load)"""
    try:
        from citation_optimization_engine import CitationOptimizationEngine
        return CitationOptimizationEngine(CONFIG_FILE)
    except Exception as e:
        logger.warning(f"Could not load engine: {e}")
        return None

@app.route('/', methods=['GET'])
def root():
    return jsonify({
        'service': 'RevCite Citation Tracking API',
        'version': '1.0.0',
        'port': 8600,
        'description': 'Unified citation tracking with Clarity + IndexNow',
        'endpoints': {
            'health': '/health',
            'status': '/status',
            'process_citation': '/citation (POST)',
            'velocity_check': '/velocity (POST)',
            'config': '/config'
        }
    }), 200

@app.route('/health', methods=['GET'])
def health_check():
    config = load_config()
    clarity_configured = config.get('clarity_project_id', '') not in ['', 'not_configured', 'REPLACE_WITH_YOUR_CLARITY_PROJECT_ID']
    indexnow_configured = config.get('indexnow_key', '') not in ['', 'not_configured']

    status = 'healthy' if (clarity_configured or indexnow_configured) else 'degraded'

    return jsonify({
        'status': status,
        'service': 'revcite-api',
        'port': 8600,
        'clarity_configured': clarity_configured,
        'indexnow_configured': indexnow_configured,
        'timestamp': datetime.now().isoformat()
    }), 200

@app.route('/status', methods=['GET'])
def get_status():
    config = load_config()

    # Count tracked citations (check log file)
    citations_tracked = 0
    log_file = '/opt/revcite/logs/citations.log'
    if os.path.exists(log_file):
        with open(log_file, 'r') as f:
            citations_tracked = len(f.readlines())

    return jsonify({
        'service': 'RevCite',
        'module': 'Citation Tracking & GEO Optimization',
        'status': 'active',
        'config': {
            'clarity_project_id': config.get('clarity_project_id', 'not_set')[:10] + '...' if config.get('clarity_project_id') else 'not_set',
            'default_host': config.get('default_host', 'not_set'),
            'velocity_threshold': config.get('citation_velocity_threshold', 2.0)
        },
        'stats': {
            'citations_tracked': citations_tracked,
            'last_updated': datetime.now().isoformat()
        },
        'capabilities': [
            'Citation Discovery Processing',
            'Clarity Engagement Tracking',
            'IndexNow Search Notification',
            'Citation Velocity Monitoring',
            'GEO Optimization'
        ]
    }), 200

@app.route('/config', methods=['GET'])
def get_config():
    config = load_config()
    # Mask sensitive values
    safe_config = {
        'clarity_configured': config.get('clarity_project_id', '') not in ['', 'not_configured', 'REPLACE_WITH_YOUR_CLARITY_PROJECT_ID'],
        'indexnow_configured': config.get('indexnow_key', '') not in ['', 'not_configured'],
        'default_host': config.get('default_host', 'not_set'),
        'citation_velocity_threshold': config.get('citation_velocity_threshold', 2.0)
    }
    return jsonify(safe_config), 200

@app.route('/citation', methods=['POST'])
def process_citation():
    """Process a newly discovered citation"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400

        page_url = data.get('page_url')
        ai_engine = data.get('ai_engine', 'unknown')

        if not page_url:
            return jsonify({'error': 'page_url is required'}), 400

        engine = get_engine()
        if engine:
            result = engine.process_new_citation_discovered({
                'page_url': page_url,
                'ai_engine': ai_engine,
                'id': data.get('id', f"cit_{datetime.now().strftime('%Y%m%d%H%M%S')}")
            })
        else:
            # Fallback when engine not available
            result = {
                'citation_id': f"cit_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                'page_url': page_url,
                'ai_engine': ai_engine,
                'status': 'logged',
                'message': 'Citation logged (engine not fully configured)',
                'timestamp': datetime.now().isoformat()
            }

        # Log citation
        log_file = '/opt/revcite/logs/citations.log'
        with open(log_file, 'a') as f:
            f.write(f"{datetime.now().isoformat()}|{page_url}|{ai_engine}\n")

        logger.info(f"Processed citation: {page_url} from {ai_engine}")
        return jsonify(result), 200

    except Exception as e:
        logger.error(f"Citation processing error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/velocity', methods=['POST'])
def check_velocity():
    """Check citation velocity for a site"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400

        site_url = data.get('site_url')
        citation_count = data.get('citation_count', 0)
        days = data.get('days', 7)

        if not site_url:
            return jsonify({'error': 'site_url is required'}), 400

        engine = get_engine()
        if engine:
            result = engine.run_citation_velocity_check(site_url, citation_count, days)
        else:
            config = load_config()
            velocity = citation_count / days if days > 0 else 0
            threshold = config.get('citation_velocity_threshold', 2.0)
            result = {
                'status': 'citation_boost_detected' if velocity >= threshold else 'normal',
                'velocity': velocity,
                'threshold': threshold,
                'notifications_sent': False,
                'message': 'Velocity calculated (engine not fully configured)'
            }

        logger.info(f"Velocity check: {site_url} - {result['status']}")
        return jsonify(result), 200

    except Exception as e:
        logger.error(f"Velocity check error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/citations/recent', methods=['GET'])
def get_recent_citations():
    """Get recent citations from log"""
    try:
        limit = request.args.get('limit', 50, type=int)
        log_file = '/opt/revcite/logs/citations.log'

        citations = []
        if os.path.exists(log_file):
            with open(log_file, 'r') as f:
                lines = f.readlines()[-limit:]
                for line in lines:
                    parts = line.strip().split('|')
                    if len(parts) >= 3:
                        citations.append({
                            'timestamp': parts[0],
                            'page_url': parts[1],
                            'ai_engine': parts[2]
                        })

        return jsonify({
            'citations': citations,
            'count': len(citations),
            'total_tracked': len(citations)
        }), 200

    except Exception as e:
        logger.error(f"Error getting recent citations: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    os.makedirs('/opt/revcite/logs', exist_ok=True)
    logger.info("Starting RevCite API on port 8600")
    app.run(host='0.0.0.0', port=8560, debug=False)
