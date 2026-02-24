"""Extract rules from content using Claude"""
import os
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def extract_rules_from_content(content: str, domain: str, source_type: str, expert: str):
    """Extract actionable rules using Claude"""
    
    # Import here to avoid initialization issues
    import anthropic
    
    # Create client with ONLY api_key - nothing else
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        logger.error("ANTHROPIC_API_KEY not set")
        return []
    
    try:
        # Minimal client creation
        client = anthropic.Anthropic(api_key=api_key)
        
        prompt = f"""You are analyzing content from a {domain} expert to extract ACTIONABLE, MEASURABLE rules.

Expert: {expert}
Source Type: {source_type}
Domain: {domain}

Content:
{content}

Extract rules that meet ALL these criteria:
1. **Actionable**: Can be implemented in content/code
2. **Measurable**: Has clear success criteria
3. **Specific**: Not generic advice
4. **Evidence-based**: Expert cites data/examples
5. **Novel**: Not obvious best practices

For each rule, return JSON:
{{
    "rule_name": "Short descriptive name (max 50 chars)",
    "category": "content_quality|technical_seo|engagement|conversion|differentiation",
    "definition": "Precise, measurable statement",
    "validation_function": "How to programmatically check",
    "thresholds": {{"key": "value"}},
    "examples": {{"good": ["..."], "bad": ["..."]}},
    "confidence": 0.0-1.0,
    "evidence": "Direct quote supporting this rule",
    "tier": "1|2|3"
}}

**Confidence scoring:**
- 0.9-1.0: Expert cites specific data/study
- 0.7-0.9: Expert has track record, logical reasoning
- 0.5-0.7: Plausible but no hard evidence

Return ONLY valid JSON array of rules. Skip generic advice."""

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
            messages=[{"role": "user", "content": prompt}]
        )
        
        response_text = response.content[0].text
        
        # Extract JSON
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        
        rules = json.loads(response_text.strip())
        
        # Ensure it's a list
        if not isinstance(rules, list):
            rules = [rules]
        
        # Add metadata
        for rule in rules:
            rule['source_type'] = source_type
            rule['expert'] = expert
            rule['domain'] = domain
            rule['discovered_at'] = datetime.utcnow().isoformat()
        
        # Filter by confidence
        high_confidence = [r for r in rules if r.get('confidence', 0) >= 0.7]
        
        logger.info(f"Extracted {len(high_confidence)} high-confidence rules from {expert}")
        return high_confidence
        
    except Exception as e:
        logger.error(f"Rule extraction failed: {e}", exc_info=True)
        return []

def extract_rules_from_content_sync(content: str, source_type: str, expert: str, domain: str) -> dict:
    """Synchronous wrapper for extract_rules_from_content"""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        # Function is NOT async - call directly with correct parameter order
        # Function signature: extract_rules_from_content(content, domain, source_type, expert)
        rules_list = extract_rules_from_content(
            content=content,
            domain=domain,
            source_type=source_type,
            expert=expert
        )
        
        # Convert list response to dict format expected by API
        return {
            'rules_found': len(rules_list),
            'unique_rules': len(rules_list),
            'rules': rules_list
        }
        
    except Exception as e:
        logger.error(f"Rule extraction failed: {e}", exc_info=True)
        return {'rules_found': 0, 'unique_rules': 0, 'rules': []}

