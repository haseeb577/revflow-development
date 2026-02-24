"""Configuration settings for RevPublish v2.0"""
import os
from dotenv import load_dotenv

load_dotenv('/opt/shared-api-engine/.env')

# Database
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': os.getenv('POSTGRES_DB', 'revflow_db'),
    'user': os.getenv('POSTGRES_USER'),
    'password': os.getenv('POSTGRES_PASSWORD')
}

# Google API
GOOGLE_CREDENTIALS_PATH = '/opt/revpublish/config/google_credentials.json'

# Sites inventory
SITES_INVENTORY_PATH = '/opt/revpublish/config/sites_inventory.json'

# Templates
TEMPLATES_DIR = '/opt/revpublish/templates/elementor'

# Logging
LOG_DIR = '/opt/revpublish/logs'

# Backend Port
BACKEND_PORT = 8550
FRONTEND_PORT = 3550
