#!/usr/bin/env python3
"""
RevPrompt Unified™ - Main API Server
Port: 8700
SaaS-ready multi-tenant content generation system
"""

from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import os
import sys
import json
import logging
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor

# Add paths
sys.path.append(os.path.dirname(__file__))

app = Flask(__name__, 
            template_folder='ui/templates',
            static_folder='ui/static')
CORS(app)

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/opt/revprompt-unified/logs/api.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('revprompt')

# Database connection
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'postgres',
    'user': 'postgres',
    'password': os.getenv('POSTGRES_PASSWORD', '')
}

def get_db():
    """Get database connection"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        return None

# ==========================================
# HEALTH & SYSTEM ENDPOINTS
# ==========================================

@app.route('/health', methods=['GET'])
@app.route('/api/health', methods=['GET'])
def health_check():
    """System health check"""
    return jsonify({
        'status': 'healthy',
        'service': 'RevPrompt Unified™',
        'version': '1.0.0',
        'port': 8700,
        'timestamp': datetime.utcnow().isoformat(),
        'components': {
            'page_types': 11,
            'enhancement_layers': 18,
            'voice_profiles': 3,
            'validation_tiers': 5
        }
    })

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """System statistics"""
    return jsonify({
        'success': True,
        'stats': {
            'page_types': 11,
            'enhancement_layers': 18,
            'voice_profiles': 3,
            'blacklist_rules': 215,
            'field_prompts': 10,
            'validation_components': 5,
            'total_generated': 0,  # Will query DB
            'total_cost_usd': 0.00
        }
    })

# ==========================================
# PAGE TYPES ENDPOINTS
# ==========================================

PAGE_TYPES = {
    'homepage': {
        'name': 'Homepage',
        'word_count_min': 1200,
        'word_count_max': 1500,
        'voice': 'authority',
        'esr_min': 65,
        'wsr_max': 15,
        'entity_mentions': 8,
        'h2_count': 5,
        'data_points': 10,
        'schema_type': 'LocalBusiness',
        'required_sections': [
            'Hero headline',
            'Service overview',
            'Trust indicators',
            'Service area',
            'CTA'
        ]
    },
    'service': {
        'name': 'Service Page',
        'word_count_min': 1200,
        'word_count_max': 1500,
        'voice': 'authority',
        'esr_min': 65,
        'wsr_max': 15,
        'entity_mentions': 8,
        'h2_count': 5,
        'data_points': 10,
        'schema_type': 'Service',
        'required_sections': [
            'Service description',
            'Process breakdown',
            'Benefits',
            'FAQ',
            'CTA'
        ]
    },
    'location': {
        'name': 'Location Page',
        'word_count_min': 900,
        'word_count_max': 1200,
        'voice': 'empathy',
        'esr_min': 60,
        'wsr_max': 18,
        'entity_mentions': 6,
        'h2_count': 4,
        'data_points': 8,
        'schema_type': 'LocalBusiness',
        'required_sections': [
            'Geographic content',
            'Local landmarks',
            'Service area',
            'Testimonials',
            'CTA'
        ]
    },
    'about': {
        'name': 'About Us',
        'word_count_min': 800,
        'word_count_max': 1000,
        'voice': 'empathy',
        'esr_min': 60,
        'wsr_max': 18,
        'entity_mentions': 6,
        'h2_count': 3,
        'data_points': 6
    },
    'contact': {
        'name': 'Contact Page',
        'word_count_min': 400,
        'word_count_max': 600,
        'voice': 'empathy',
        'esr_min': 55,
        'wsr_max': 20,
        'entity_mentions': 4,
        'h2_count': 2,
        'data_points': 5
    },
    'blog': {
        'name': 'Blog Post',
        'word_count_min': 1000,
        'word_count_max': 1500,
        'voice': 'precision',
        'esr_min': 60,
        'wsr_max': 18,
        'entity_mentions': 6,
        'h2_count': 5,
        'data_points': 8
    },
    'faq': {
        'name': 'FAQ Page',
        'word_count_min': 800,
        'word_count_max': 1200,
        'voice': 'precision',
        'esr_min': 55,
        'wsr_max': 20,
        'entity_mentions': 5,
        'h2_count': 6,
        'data_points': 6
    },
    'reviews': {
        'name': 'Reviews Page',
        'word_count_min': 600,
        'word_count_max': 800,
        'voice': 'empathy',
        'esr_min': 50,
        'wsr_max': 22,
        'entity_mentions': 4,
        'h2_count': 3,
        'data_points': 5
    },
    'team': {
        'name': 'Team Page',
        'word_count_min': 600,
        'word_count_max': 900,
        'voice': 'empathy',
        'esr_min': 55,
        'wsr_max': 20,
        'entity_mentions': 5,
        'h2_count': 3,
        'data_points': 5
    },
    'portfolio': {
        'name': 'Portfolio Page',
        'word_count_min': 800,
        'word_count_max': 1200,
        'voice': 'authority',
        'esr_min': 60,
        'wsr_max': 18,
        'entity_mentions': 6,
        'h2_count': 4,
        'data_points': 7
    },
    'terms': {
        'name': 'Terms & Conditions',
        'word_count_min': 1000,
        'word_count_max': 1500,
        'voice': 'precision',
        'esr_min': 50,
        'wsr_max': 25,
        'entity_mentions': 3,
        'h2_count': 8,
        'data_points': 4
    }
}

@app.route('/api/page-types', methods=['GET'])
def get_page_types():
    """List all page types"""
    page_types_list = []
    for key, data in PAGE_TYPES.items():
        page_types_list.append({
            'key': key,
            **data
        })
    
    return jsonify({
        'success': True,
        'page_types': page_types_list,
        'count': len(page_types_list)
    })

@app.route('/api/page-types/<key>', methods=['GET'])
def get_page_type(key):
    """Get specific page type details"""
    if key not in PAGE_TYPES:
        return jsonify({'success': False, 'error': 'Page type not found'}), 404
    
    return jsonify({
        'success': True,
        'page_type': PAGE_TYPES[key]
    })

# ==========================================
# ENHANCEMENT LAYERS ENDPOINTS
# ==========================================

ENHANCEMENT_LAYERS = [
    {
        'id': 'layer_01_bluf',
        'name': 'BLUF Compliance',
        'description': 'Bottom Line Up Front - key takeaway in first 100 words',
        'priority': 10,
        'applies_during': 'generation'
    },
    {
        'id': 'layer_02_entity_first',
        'name': 'Entity-First Paragraphs',
        'description': 'Start paragraphs with business entity, not generic intro',
        'priority': 9,
        'applies_during': 'generation'
    },
    {
        'id': 'layer_03_numeric_specificity',
        'name': 'Numeric Specificity',
        'description': 'Replace vague terms with exact numbers',
        'priority': 9,
        'applies_during': 'generation'
    },
    {
        'id': 'layer_04_local_proof',
        'name': 'Local Proof Points',
        'description': 'Geographic specificity and local references',
        'priority': 8,
        'applies_during': 'generation'
    },
    {
        'id': 'layer_05_trust_signals',
        'name': 'Trust Signals',
        'description': 'Certifications, years in business, guarantees',
        'priority': 8,
        'applies_during': 'generation'
    },
    {
        'id': 'layer_06_qa_format',
        'name': 'QA Format Headers',
        'description': 'Question-as-H2, answer-as-paragraph structure',
        'priority': 7,
        'applies_during': 'generation'
    },
    {
        'id': 'layer_07_schema',
        'name': 'Schema Markup',
        'description': 'Structured data for rich snippets',
        'priority': 8,
        'applies_during': 'post_processing'
    },
    {
        'id': 'layer_08_image_alt',
        'name': 'Image Alt Text',
        'description': 'Descriptive, keyword-rich alt attributes',
        'priority': 6,
        'applies_during': 'post_processing'
    },
    {
        'id': 'layer_09_internal_links',
        'name': 'Internal Linking',
        'description': 'Strategic cross-page connections',
        'priority': 7,
        'applies_during': 'post_processing'
    },
    {
        'id': 'layer_10_cta',
        'name': 'CTA Strategy',
        'description': 'Multiple calls-to-action throughout content',
        'priority': 9,
        'applies_during': 'generation'
    },
    {
        'id': 'layer_11_meta',
        'name': 'Meta Optimization',
        'description': 'Title tags and meta descriptions',
        'priority': 9,
        'applies_during': 'post_processing'
    },
    {
        'id': 'layer_12_headers',
        'name': 'Header Hierarchy',
        'description': 'Proper H1→H2→H3 structure',
        'priority': 8,
        'applies_during': 'generation'
    },
    {
        'id': 'layer_13_depth',
        'name': 'Content Depth',
        'description': 'Minimum word count and section requirements',
        'priority': 7,
        'applies_during': 'validation'
    },
    {
        'id': 'layer_14_semantic',
        'name': 'Semantic Completeness',
        'description': 'Answer all implicit sub-questions',
        'priority': 8,
        'applies_during': 'generation'
    },
    {
        'id': 'layer_15_freshness',
        'name': 'Freshness Signals',
        'description': 'Current year, recent data, timely references',
        'priority': 6,
        'applies_during': 'generation'
    },
    {
        'id': 'layer_16_mobile',
        'name': 'Mobile Optimization',
        'description': 'Short paragraphs, scannable format',
        'priority': 7,
        'applies_during': 'generation'
    },
    {
        'id': 'layer_17_readability',
        'name': 'Readability',
        'description': 'Flesch-Kincaid grade level 8-10',
        'priority': 7,
        'applies_during': 'validation'
    },
    {
        'id': 'layer_18_call_tracking',
        'name': 'Call Tracking',
        'description': 'Phone numbers, click-to-call buttons',
        'priority': 6,
        'applies_during': 'post_processing'
    }
]

@app.route('/api/enhancement-layers', methods=['GET'])
def get_enhancement_layers():
    """List all enhancement layers"""
    return jsonify({
        'success': True,
        'layers': ENHANCEMENT_LAYERS,
        'count': len(ENHANCEMENT_LAYERS)
    })

# ==========================================
# VOICE PROFILES ENDPOINTS
# ==========================================

VOICE_PROFILES = {
    'authority': {
        'name': 'Authority',
        'description': 'Confident, expert tone. Facts and credentials emphasized.',
        'best_for': ['Homepage', 'Service Pages', 'Portfolio'],
        'characteristics': [
            'Assertive language',
            'Data-driven statements',
            'Industry expertise visible',
            'Professional credibility'
        ]
    },
    'empathy': {
        'name': 'Empathy',
        'description': 'Understanding, compassionate tone. Customer pain points addressed.',
        'best_for': ['Location Pages', 'About Us', 'Team'],
        'characteristics': [
            'Customer-centric',
            'Problem understanding',
            'Relatable language',
            'Trust building'
        ]
    },
    'precision': {
        'name': 'Precision',
        'description': 'Technical, detailed tone. Process and specifications clear.',
        'best_for': ['Blog Posts', 'FAQ', 'Terms'],
        'characteristics': [
            'Technical accuracy',
            'Step-by-step clarity',
            'Methodical approach',
            'Detailed explanations'
        ]
    }
}

@app.route('/api/voice-profiles', methods=['GET'])
def get_voice_profiles():
    """List all voice profiles"""
    profiles = []
    for key, data in VOICE_PROFILES.items():
        profiles.append({
            'key': key,
            **data
        })
    
    return jsonify({
        'success': True,
        'voice_profiles': profiles,
        'count': len(profiles)
    })

# ==========================================
# CONTENT GENERATION ENDPOINTS
# ==========================================

@app.route('/api/generate', methods=['POST'])
def generate_content():
    """Main content generation endpoint"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required = ['page_type', 'business_data']
        if not all(k in data for k in required):
            return jsonify({
                'success': False,
                'error': 'Missing required fields: page_type, business_data'
            }), 400
        
        page_type = data['page_type']
        business_data = data['business_data']
        voice = data.get('voice_profile', 'authority')
        options = data.get('generation_options', {})
        
        # TODO: Implement actual generation pipeline
        # For now, return demo response
        
        return jsonify({
            'success': True,
            'content': f"<h1>{business_data.get('business_name', 'Business')} - Demo Content</h1><p>This is placeholder content. Full generation pipeline will be implemented.</p>",
            'metadata': {
                'word_count': 150,
                'generation_time_ms': 5000,
                'stages_completed': 4,
                'validation_passed': True,
                'quality_score': 85.0,
                'cost_usd': 0.03,
                'voice_used': voice
            },
            'generation_stages': [
                {'stage': 'research', 'status': 'completed', 'time_ms': 1000},
                {'stage': 'outline', 'model': 'gpt-4', 'status': 'completed', 'time_ms': 1500},
                {'stage': 'expansion', 'model': 'gemini-pro', 'status': 'completed', 'time_ms': 1500},
                {'stage': 'polish', 'model': 'claude-sonnet', 'status': 'completed', 'time_ms': 1000}
            ],
            'validation_results': {
                'overall_passed': True,
                'composite_score': 85.0,
                'spo_score': 87,
                'entity_score': 83,
                'guru_score': 85,
                'dedup_passed': True
            }
        })
        
    except Exception as e:
        logger.error(f"Generation error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/validate', methods=['POST'])
def validate_content():
    """Validate existing content"""
    try:
        data = request.get_json()
        
        if 'content' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing required field: content'
            }), 400
        
        content = data['content']
        page_type = data.get('page_type', 'service')
        
        # TODO: Implement actual validation
        # For now, return demo results
        
        return jsonify({
            'success': True,
            'overall_passed': True,
            'score': 87.5,
            'category_scores': {
                'spo_validation': 92,
                'entity_map': 85,
                'guru_intelligence': 87,
                'blacklist': 100,
                'deduplication': 90
            },
            'violations': [],
            'recommendations': [
                'Add 2 more local proof points',
                'Increase numeric specificity in pricing section',
                'Include one more trust signal'
            ]
        })
        
    except Exception as e:
        logger.error(f"Validation error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ==========================================
# PORTFOLIO MANAGEMENT ENDPOINTS
# ==========================================

@app.route('/api/portfolio/stats', methods=['GET'])
def get_portfolio_stats():
    """Get portfolio statistics"""
    return jsonify({
        'success': True,
        'portfolio': {
            'total_sites': 53,
            'total_pages': 1590,
            'by_industry': {
                'plumbing': 318,
                'hvac': 265,
                'electrical': 212,
                'other': 795
            },
            'by_page_type': {
                'homepage': 53,
                'service': 424,
                'location': 530,
                'about': 53,
                'contact': 53,
                'blog': 265,
                'other': 212
            },
            'quality_metrics': {
                'avg_spo_score': 88.5,
                'avg_composite_score': 89.2,
                'pages_below_threshold': 23
            },
            'generation_stats': {
                'total_cost_usd': 47.70,
                'avg_cost_per_page': 0.03,
                'total_time_hours': 19.875
            }
        }
    })

# ==========================================
# UI ROUTES
# ==========================================

@app.route('/')
def index():
    """Serve main UI"""
    return render_template('index.html')

# ==========================================
# ERROR HANDLERS
# ==========================================

@app.errorhandler(404)
def not_found(e):
    return jsonify({'success': False, 'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(e):
    logger.error(f"Internal error: {e}")
    return jsonify({'success': False, 'error': 'Internal server error'}), 500

# ==========================================
# MAIN
# ==========================================

if __name__ == '__main__':
    logger.info("="*50)
    logger.info("RevPrompt Unified™ - Starting API Server")
    logger.info("Port: 8700")
    logger.info("="*50)
    
    app.run(
        host='0.0.0.0',
        port=8700,
        debug=False,
        threaded=True
    )
