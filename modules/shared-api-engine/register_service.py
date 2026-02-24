#!/usr/bin/env python3
"""
RevCore Service Registration Script
Registers a service with RevCore's service registry
"""
import sys
import requests
import psycopg2
from datetime import datetime

def register_service(service_config):
    """Register service directly in RevCore database"""
    
    # Database connection
    conn = psycopg2.connect(
        host="localhost",
        port=5432,
        database="revcore",
        user="revcore_user",
        password="revcore_secure_2026"
    )
    
    try:
        cur = conn.cursor()
        
        # Check if service already exists
        cur.execute(
            "SELECT id FROM services WHERE service_id = %s",
            (service_config['service_id'],)
        )
        existing = cur.fetchone()
        
        if existing:
            # Update existing service
            cur.execute("""
                UPDATE services SET
                    name = %s,
                    display_name = %s,
                    description = %s,
                    version = %s,
                    host = %s,
                    port = %s,
                    base_path = %s,
                    health_endpoint = %s,
                    status = 'active',
                    updated_at = CURRENT_TIMESTAMP
                WHERE service_id = %s
                RETURNING id
            """, (
                service_config['name'],
                service_config.get('display_name', service_config['name']),
                service_config.get('description', ''),
                service_config.get('version', '1.0.0'),
                service_config.get('host', 'localhost'),
                service_config['port'],
                service_config.get('base_path', '/api/v1'),
                service_config.get('health_endpoint', '/health'),
                service_config['service_id']
            ))
            service_id = cur.fetchone()[0]
            print(f"✅ Updated service: {service_config['name']} (ID: {service_id})")
        else:
            # Insert new service
            cur.execute("""
                INSERT INTO services (
                    service_id, name, display_name, description, version,
                    host, port, base_path, health_endpoint, status
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'active')
                RETURNING id
            """, (
                service_config['service_id'],
                service_config['name'],
                service_config.get('display_name', service_config['name']),
                service_config.get('description', ''),
                service_config.get('version', '1.0.0'),
                service_config.get('host', 'localhost'),
                service_config['port'],
                service_config.get('base_path', '/api/v1'),
                service_config.get('health_endpoint', '/health')
            ))
            service_id = cur.fetchone()[0]
            print(f"✅ Registered new service: {service_config['name']} (ID: {service_id})")
        
        conn.commit()
        return True
        
    except Exception as e:
        print(f"❌ Registration failed: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    # Example: Register Content Service
    service = {
        'service_id': 'content-service',
        'name': 'Content Service',
        'display_name': 'RevFlow Content Generator',
        'description': 'AI-powered content generation service',
        'version': '1.0.0',
        'host': 'localhost',
        'port': 8006,
        'base_path': '/api/v1',
        'health_endpoint': '/health'
    }
    
    success = register_service(service)
    sys.exit(0 if success else 1)
