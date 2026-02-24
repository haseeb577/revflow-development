"""Integration with Knowledge Graph API"""
import requests
import logging
import os

logger = logging.getLogger(__name__)

KG_URL = os.getenv("KNOWLEDGE_GRAPH_URL", "http://localhost:8102")

def insert_rule(rule):
    """Insert rule into Knowledge Graph"""
    try:
        response = requests.post(
            f"{KG_URL}/api/v1/rules",
            json=rule,
            timeout=10
        )
        response.raise_for_status()
        logger.info(f"Inserted rule: {rule.get('rule_name')}")
        return True
    except Exception as e:
        logger.error(f"Failed to insert rule: {e}")
        return False

def get_all_rules():
    """Get all rules from Knowledge Graph"""
    try:
        response = requests.get(f"{KG_URL}/api/v1/rules", timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Failed to get rules: {e}")
        return {"rules": []}
