"""Domain configurations for intelligence collection"""

INTELLIGENCE_DOMAINS = {
    "seo": {
        "priority": "high",
        "apps": ["R&R Automation", "RevFlow"],
        "update_frequency": "daily",
        "monetization": "internal",
        "auto_approve_threshold": 0.85
    },
    "local_business": {
        "priority": "high",
        "apps": ["R&R Automation"],
        "update_frequency": "daily",
        "monetization": "internal",
        "auto_approve_threshold": 0.80
    },
    "ai_ml": {
        "priority": "medium",
        "apps": ["Future AI Product"],
        "update_frequency": "weekly",
        "monetization": "research_reports",
        "auto_approve_threshold": 0.90
    },
    "marketing_automation": {
        "priority": "medium",
        "apps": ["RevFlow CRM"],
        "update_frequency": "weekly",
        "monetization": "saas",
        "auto_approve_threshold": 0.85
    }
}

# Trusted sources for auto-approval
TRUSTED_SOURCES = {
    "google_trends": 0.90,
    "expert:ahrefs": 0.85,
    "expert:moz": 0.85,
    "expert:backlinko": 0.80,
    "expert:searchengineland": 0.85
}
