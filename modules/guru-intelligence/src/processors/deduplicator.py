"""Remove duplicate rules"""
import logging

logger = logging.getLogger(__name__)

def remove_duplicates(rules):
    """Simple deduplication by rule_name"""
    seen = set()
    unique = []
    
    for rule in rules:
        key = rule.get('rule_name', '').lower()
        if key not in seen:
            seen.add(key)
            unique.append(rule)
    
    logger.info(f"Deduplicated {len(rules)} rules to {len(unique)} unique")
    return unique
