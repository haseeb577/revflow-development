"""Synchronous wrapper for rule extraction"""
from .rule_extractor import extract_rules_from_content
import logging

logger = logging.getLogger(__name__)

def extract_rules_from_content_sync(content: str, source_type: str, expert: str, domain: str) -> dict:
    """Wrapper that calls the SYNC function with correct parameter order"""
    try:
        # The function is NOT async - just call it directly!
        # Function signature: extract_rules_from_content(content, domain, source_type, expert)
        result = extract_rules_from_content(
            content=content,
            domain=domain,
            source_type=source_type,
            expert=expert
        )
        return result
            
    except Exception as e:
        logger.error(f"Rule extraction failed: {e}", exc_info=True)
        return {'rules_found': 0, 'unique_rules': 0, 'rules': []}
