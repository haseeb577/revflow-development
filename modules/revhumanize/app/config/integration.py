"""
Configuration integration with shared .env
Reads from /opt/shared-api-engine/.env
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load shared .env if it exists
SHARED_ENV = Path("/opt/shared-api-engine/.env")
if SHARED_ENV.exists():
    load_dotenv(SHARED_ENV)
    print(f"✓ Loaded configuration from {SHARED_ENV}")

# Load local .env (overrides shared)
load_dotenv()

# Database configuration
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://revflow:revflow@localhost:5432/humanization_pipeline"
)

# API Keys (from shared .env)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# Webhook URLs (optional)
WEBHOOK_CONTENT_APPROVED = os.getenv("WEBHOOK_CONTENT_APPROVED")
WEBHOOK_CONTENT_REJECTED = os.getenv("WEBHOOK_CONTENT_REJECTED")

# Admin settings
ADMIN_PORT = int(os.getenv("ADMIN_PORT", "8003"))
ADMIN_ENABLE = os.getenv("ADMIN_ENABLE", "true").lower() == "true"

# Email notifications (optional)
SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
NOTIFICATION_EMAIL = os.getenv("NOTIFICATION_EMAIL")

# Slack notifications (optional)
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")

def get_config():
    """Get all configuration as dict"""
    return {
        "database_url": DATABASE_URL,
        "admin_port": ADMIN_PORT,
        "admin_enable": ADMIN_ENABLE,
        "has_openai_key": bool(OPENAI_API_KEY),
        "has_anthropic_key": bool(ANTHROPIC_API_KEY),
        "has_webhooks": bool(WEBHOOK_CONTENT_APPROVED or WEBHOOK_CONTENT_REJECTED),
        "has_email": bool(SMTP_HOST and NOTIFICATION_EMAIL),
        "has_slack": bool(SLACK_WEBHOOK_URL)
    }
