
"""
Power Prompts Module - Integrated with RevPrompt Unified
The 5 standardized AI visibility tests
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Dict, List, Optional
import os
import logging
import re

from dotenv import load_dotenv
load_dotenv('/opt/shared-api-engine/.env')

logger = logging.getLogger(__name__)

DB_CONFIG = {
    'host': os.getenv('POSTGRES_HOST', 'localhost'),
    'port': int(os.getenv('POSTGRES_PORT', 5432)),
    'database': os.getenv('POSTGRES_DB', 'revflow'),
    'user': os.getenv('POSTGRES_USER', 'revflow'),
    'password': os.getenv('POSTGRES_PASSWORD', '')
}


def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)


def get_all_power_prompts(active_only: bool = True) -> List[Dict]:
    """Get all Power Prompts from database"""
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            if active_only:
                cur.execute("""
                    SELECT * FROM ai_power_prompts 
                    WHERE is_active = TRUE
                    ORDER BY prompt_id
                """)
            else:
                cur.execute("""
                    SELECT * FROM ai_power_prompts 
                    ORDER BY prompt_id
                """)
            return cur.fetchall()
    finally:
        conn.close()


def get_power_prompt(prompt_id: str) -> Optional[Dict]:
    """Get a specific Power Prompt by ID"""
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT * FROM ai_power_prompts 
                WHERE prompt_id = %s
            """, (prompt_id,))
            return cur.fetchone()
    finally:
        conn.close()


def update_power_prompt(prompt_id: str, template: str = None, 
                       description: str = None, is_active: bool = None) -> bool:
    """Update a Power Prompt"""
    conn = get_db_connection()
    try:
        updates = []
        values = []
        
        if template is not None:
            updates.append("template = %s")
            values.append(template)
        if description is not None:
            updates.append("description = %s")
            values.append(description)
        if is_active is not None:
            updates.append("is_active = %s")
            values.append(is_active)
            
        if not updates:
            return False
            
        updates.append("updated_at = NOW()")
        updates.append("version = version + 1")
        
        values.append(prompt_id)
        
        with conn.cursor() as cur:
            cur.execute(f"""
                UPDATE ai_power_prompts 
                SET {', '.join(updates)}
                WHERE prompt_id = %s
            """, values)
            conn.commit()
            return cur.rowcount > 0
    finally:
        conn.close()


def create_power_prompt(prompt_id: str, name: str, template: str,
                       description: str = '', purpose: str = '',
                       tracks: List[str] = None, required_vars: List[str] = None,
                       frequency: str = 'weekly') -> bool:
    """Create a new Power Prompt"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO ai_power_prompts 
                (prompt_id, name, template, description, purpose, 
                 tracks, required_vars, frequency)
                VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s)
                ON CONFLICT (prompt_id) DO UPDATE SET
                    template = EXCLUDED.template,
                    description = EXCLUDED.description,
                    updated_at = NOW(),
                    version = ai_power_prompts.version + 1
            """, (
                prompt_id, name, template, description, purpose,
                str(tracks or []).replace("'", '"'),
                str(required_vars or []).replace("'", '"'),
                frequency
            ))
            conn.commit()
            return True
    except Exception as e:
        logger.error(f"Error creating power prompt: {e}")
        return False
    finally:
        conn.close()


def render_prompt(prompt_id: str, variables: dict) -> str:
    """
    Render a power prompt with provided variables.
    Supports both {{var}} and {var} syntax.
    """
    prompt = get_power_prompt(prompt_id)
    if not prompt:
        raise ValueError(f"Unknown prompt ID: {prompt_id}")
    
    template = prompt['template']
    required_vars = prompt.get('required_vars', [])
    
    # Check required variables
    for var in required_vars:
        if var not in variables:
            raise ValueError(f"Missing required variable: {var}")
    
    # Replace {{var}} syntax
    for key, value in variables.items():
        template = template.replace('{{' + key + '}}', str(value))
        template = template.replace('{' + key + '}', str(value))
    
    return template


def get_prompts_for_site(site_config: dict) -> List[Dict]:
    """
    Generate all applicable power prompts for a site.
    
    Args:
        site_config: {
            'service': 'plumbing',
            'location': 'Dallas, Texas',
            'client_name': 'ABC Plumbing',
            'competitor_name': 'XYZ Plumbing',  # Optional
            'problem': 'water heater repair',
            'use_case': 'residential plumbing repair'
        }
    """
    prompts = []
    all_prompts = get_all_power_prompts(active_only=True)
    
    for prompt in all_prompts:
        prompt_id = prompt['prompt_id']
        required_vars = prompt.get('required_vars', [])
        
        # Build variables dict
        variables = {}
        can_render = True
        
        for var in required_vars:
            if var == 'service':
                variables['service'] = site_config.get('service', '')
            elif var == 'location':
                variables['location'] = site_config.get('location', '')
            elif var == 'client_name':
                variables['client_name'] = site_config.get('client_name', '')
            elif var == 'competitor_name':
                if site_config.get('competitor_name'):
                    variables['competitor_name'] = site_config['competitor_name']
                else:
                    can_render = False  # Skip comparison if no competitor
            elif var == 'problem':
                variables['problem'] = site_config.get('problem') or site_config.get('service', '')
            elif var == 'use_case':
                variables['use_case'] = site_config.get('use_case') or site_config.get('service', '')
            else:
                if var in site_config:
                    variables[var] = site_config[var]
                else:
                    can_render = False
        
        if can_render:
            try:
                rendered = render_prompt(prompt_id, variables)
                prompts.append({
                    'id': prompt_id,
                    'name': prompt['name'],
                    'query': rendered,
                    'purpose': prompt.get('purpose', ''),
                    'tracks': prompt.get('tracks', [])
                })
            except Exception as e:
                logger.warning(f"Could not render prompt {prompt_id}: {e}")
    
    return prompts


# Default prompts (in case database is empty)
DEFAULT_POWER_PROMPTS = [
    {
        "prompt_id": "category_leader",
        "name": "Category Leader",
        "template": "I am looking for the best {{service}} in {{location}}. Who are the top 3-5 providers I should consider and why?",
        "description": "Tests market positioning and entity associations",
        "purpose": "Determine if client appears in 'best of' recommendations",
        "tracks": ["market_position", "brand_recognition", "recommendation_inclusion"],
        "required_vars": ["service", "location"],
        "frequency": "weekly"
    },
    {
        "prompt_id": "citation_source",
        "name": "Citation Source",
        "template": "Give me a detailed guide on {{problem}}. Cite your sources at the end.",
        "description": "Tests content authority and citation frequency",
        "purpose": "Check if client content is cited as authoritative source",
        "tracks": ["content_authority", "expert_status", "citation_frequency"],
        "required_vars": ["problem"],
        "frequency": "weekly"
    },
    {
        "prompt_id": "comparison",
        "name": "Comparison",
        "template": "Compare {{client_name}} vs {{competitor_name}}. What are the pros and cons of each for a customer looking for {{service}}?",
        "description": "Tests brand sentiment and competitive positioning",
        "purpose": "Analyze how AI perceives client vs competitors",
        "tracks": ["brand_sentiment", "competitive_positioning", "pros_cons_balance"],
        "required_vars": ["client_name", "competitor_name", "service"],
        "frequency": "weekly"
    },
    {
        "prompt_id": "trust_verification",
        "name": "Trust & Verification",
        "template": "Is {{client_name}} a reputable company? What do experts and customers say about them online?",
        "description": "Tests digital footprint and reputation signals",
        "purpose": "Verify client reputation in AI responses",
        "tracks": ["reputation", "review_visibility", "expert_endorsement"],
        "required_vars": ["client_name"],
        "frequency": "weekly"
    },
    {
        "prompt_id": "buying_intent",
        "name": "Buying Intent",
        "template": "I need to buy {{service}}. Who offers the best value for {{use_case}} in 2026?",
        "description": "Tests bottom-funnel visibility",
        "purpose": "Check if client appears in purchase recommendations",
        "tracks": ["purchase_recommendation", "value_positioning", "conversion_potential"],
        "required_vars": ["service", "use_case"],
        "frequency": "weekly"
    }
]


def ensure_default_prompts():
    """Ensure default Power Prompts exist in database"""
    for prompt in DEFAULT_POWER_PROMPTS:
        create_power_prompt(**prompt)
