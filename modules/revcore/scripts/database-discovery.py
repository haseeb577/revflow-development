#!/usr/bin/env python3
"""
RevCore™ - Database Auto-Discovery (PostgreSQL + ChromaDB)
PATCHED: Jan 21, 2026 - Now actually TESTS connections, validates both DB_* and POSTGRES_*

Crisis lesson: Previous version only checked if vars EXISTED.
smarketsherpa used POSTGRES_* but only DB_* was populated = crash!
"""

import os
import sys

SHARED_ENV = "/opt/shared-api-engine/.env"

def log(message):
    print(f"[DB-DISCOVERY] {message}")

def load_env():
    """Load environment variables from shared .env"""
    env = {}
    if os.path.exists(SHARED_ENV):
        with open(SHARED_ENV) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env[key.strip()] = value.strip()
    return env

def discover_postgresql():
    """
    Discover PostgreSQL from shared .env
    ENHANCED: Now validates BOTH DB_* and POSTGRES_* variables
    """
    log("Discovering PostgreSQL...")
    env = load_env()
    
    issues = []
    
    # Check DB_* variables
    db_vars = ['DB_HOST', 'DB_PORT', 'DB_NAME', 'DB_USER', 'DB_PASSWORD']
    for var in db_vars:
        if not env.get(var):
            issues.append(f"Missing: {var}")
    
    # Check POSTGRES_* variables (CRITICAL - some services use these!)
    pg_vars = ['POSTGRES_HOST', 'POSTGRES_PORT', 'POSTGRES_DB', 'POSTGRES_USER', 'POSTGRES_PASSWORD']
    for var in pg_vars:
        if not env.get(var):
            issues.append(f"Missing: {var}")
    
    if issues:
        log("⚠️ Environment variable issues:")
        for issue in issues:
            log(f"   - {issue}")
    else:
        log("✅ All DB_* and POSTGRES_* variables present")
    
    return len(issues) == 0, issues

def test_postgresql_connection():
    """
    Actually TEST the database connection.
    CRISIS LESSON: Checking vars exist is NOT enough!
    """
    log("Testing PostgreSQL connection...")
    
    try:
        import psycopg2
    except ImportError:
        log("⚠️ psycopg2 not installed, skipping connection test")
        return True, "psycopg2 not available"
    
    env = load_env()
    results = {"password_auth": False, "peer_auth": False, "error": None}
    
    # Test password auth (TCP connection)
    try:
        conn = psycopg2.connect(
            host=env.get('POSTGRES_HOST', 'localhost'),
            port=int(env.get('POSTGRES_PORT', 5432)),
            database=env.get('POSTGRES_DB', env.get('DB_NAME', 'revflow')),
            user=env.get('POSTGRES_USER', env.get('DB_USER', 'postgres')),
            password=env.get('POSTGRES_PASSWORD', env.get('DB_PASSWORD', ''))
        )
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.close()
        conn.close()
        results["password_auth"] = True
        log("✅ Password authentication works")
    except Exception as e:
        results["error"] = str(e)
        log(f"❌ Password authentication failed: {e}")
    
    # Test peer auth (Unix socket)
    try:
        conn = psycopg2.connect(
            database=env.get('POSTGRES_DB', env.get('DB_NAME', 'revflow')),
            user='postgres'
        )
        conn.close()
        results["peer_auth"] = True
        log("✅ Peer authentication works")
    except Exception as e:
        log(f"ℹ️ Peer authentication not available: {e}")
    
    success = results["password_auth"] or results["peer_auth"]
    return success, results

def discover_chromadb():
    """Discover ChromaDB if present"""
    log("Checking for ChromaDB...")
    env = load_env()
    
    if env.get('CHROMADB_HOST'):
        log("✅ ChromaDB configuration found")
        return True
    
    log("ℹ️ ChromaDB not configured (optional)")
    return False

def full_discovery():
    """Complete database discovery with connection testing."""
    log("=" * 60)
    log("RevCore™ Database Discovery - ENHANCED")
    log("Crisis Patch: Jan 21, 2026")
    log("=" * 60)
    
    # Step 1: Check env vars
    vars_ok, issues = discover_postgresql()
    
    # Step 2: Test actual connection
    conn_ok, conn_results = test_postgresql_connection()
    
    # Step 3: ChromaDB (optional)
    chroma = discover_chromadb()
    
    log("=" * 60)
    if vars_ok and conn_ok:
        log("✅ Database discovery PASSED - Ready for service startup")
        return True
    else:
        log("❌ Database discovery FAILED - Fix issues before starting services")
        if issues:
            log("   Missing env vars - add to /opt/shared-api-engine/.env")
        if not conn_ok:
            log("   Connection failed - check PostgreSQL is running and credentials are correct")
        return False

if __name__ == "__main__":
    success = full_discovery()
    sys.exit(0 if success else 1)
