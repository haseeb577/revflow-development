#!/usr/bin/env python3
"""
RevFlow OS - Database Connection Helper
Location: /opt/shared-api-engine/db_helper.py

PERMANENT FIX for database connection issues.
All RevFlow scripts should import this instead of creating connections directly.

Usage:
    from db_helper import get_connection
    
    conn = get_connection()
    cursor = conn.cursor()
    # ... do work ...
    conn.close()
"""

import os
import sys
import psycopg2
import psycopg2.extras
from pathlib import Path

# Environment file location
ENV_FILE = "/opt/shared-api-engine/.env"

def load_environment():
    """
    Load environment variables from .env file
    Returns True if successful, False otherwise
    """
    if not os.path.exists(ENV_FILE):
        print(f"❌ Environment file not found: {ENV_FILE}", file=sys.stderr)
        return False
    
    # Read and parse .env file
    with open(ENV_FILE, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                # Remove quotes if present
                value = value.strip('"').strip("'")
                os.environ[key] = value
    
    return True

def get_password():
    """
    Get PostgreSQL password with multiple fallback methods
    Returns password or None if not found
    """
    # Method 1: Check if already in environment
    password = os.getenv('POSTGRES_PASSWORD')
    if password:
        return password
    
    # Method 2: Try to load from .env file
    if load_environment():
        password = os.getenv('POSTGRES_PASSWORD')
        if password:
            return password
    
    # Method 3: Try reading .env directly
    try:
        with open(ENV_FILE, 'r') as f:
            for line in f:
                if line.startswith('POSTGRES_PASSWORD='):
                    password = line.split('=', 1)[1].strip().strip('"').strip("'")
                    return password
    except:
        pass
    
    return None

def get_connection(database='revflow', host='localhost', user='postgres', port=5432, schema=None):
    """
    Get PostgreSQL database connection with automatic password handling

    Args:
        database: Database name or schema alias (default: revflow)
                  - 'revflow': connects to revflow database
                  - 'revcore': connects to revflow with revcore schema
                  - 'revrank': connects to revflow with revrank schema
        host: Database host (default: localhost)
        user: Database user (default: postgres)
        port: Database port (default: 5432)
        schema: Explicit schema to use (overrides database-based schema detection)

    Returns:
        psycopg2 connection object with appropriate search_path

    Raises:
        Exception if connection fails
    """
    password = get_password()

    if not password:
        raise Exception(
            "❌ POSTGRES_PASSWORD not found!\n"
            f"   Checked: environment variable, {ENV_FILE}\n"
            "   Fix: Ensure POSTGRES_PASSWORD is set in /opt/shared-api-engine/.env"
        )

    # Schema mapping: legacy database names → revflow schemas
    # All databases consolidated into single 'revflow' database with schemas
    SCHEMA_MAP = {
        'revcore': 'revcore',           # Service registry (5 tables)
        'revrank': 'revrank',           # RevRank Admin (9 tables)
        'revguard': 'revguard',         # Security (placeholder)
        'revaudit': 'audit',            # Audit system (4 tables)
        'revflow_audit': 'audit',       # Alias
        'revflow_platform': 'platform', # Platform (8 tables)
        'revflow_ui_platform': 'ui_platform',  # UI Platform (7 tables)
        'revrank_portfolio': 'portfolio',      # Portfolio (1 table)
        'revflow_db': 'data',           # Legacy data (41 tables)
    }

    # Determine actual database and schema
    if database in SCHEMA_MAP:
        target_schema = schema or SCHEMA_MAP[database]
        target_database = 'revflow'
    else:
        target_schema = schema
        target_database = database

    try:
        conn = psycopg2.connect(
            host=host,
            database=target_database,
            user=user,
            password=password,
            port=port
        )

        # Set search_path if schema specified
        if target_schema:
            cursor = conn.cursor()
            cursor.execute(f"SET search_path TO {target_schema}, public")
            cursor.close()

        return conn
    except psycopg2.OperationalError as e:
        raise Exception(
            f"❌ Database connection failed: {e}\n"
            "   Check that PostgreSQL is running: systemctl status postgresql"
        )

def get_cursor(dict_cursor=False):
    """
    Get database connection and cursor in one call
    
    Args:
        dict_cursor: If True, return DictCursor for accessing columns by name
    
    Returns:
        tuple: (connection, cursor)
    """
    conn = get_connection()
    if dict_cursor:
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    else:
        cursor = conn.cursor()
    return conn, cursor

def test_connection():
    """Test database connection and return diagnostics"""
    print("🔍 Testing Database Connection...")
    print(f"   Environment file: {ENV_FILE}")
    print(f"   File exists: {os.path.exists(ENV_FILE)}")
    
    password = get_password()
    if password:
        print(f"   ✅ Password loaded: {'*' * len(password)}")
    else:
        print(f"   ❌ Password NOT loaded")
        return False
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        print(f"   ✅ PostgreSQL version: {version[:50]}...")
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"   ❌ Connection failed: {e}")
        return False

if __name__ == "__main__":
    # When run directly, test the connection
    if test_connection():
        print("\n✅ Database connection helper is working correctly!")
        sys.exit(0)
    else:
        print("\n❌ Database connection helper has issues!")
        sys.exit(1)
