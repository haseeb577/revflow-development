#!/usr/bin/env python3
"""
Register all RevFlow services with RevCore
"""
import sys
sys.path.insert(0, '/opt/shared-api-engine')
from register_service import register_service

# Define all your services
SERVICES = [
    {
        'service_id': 'content-service',
        'name': 'Content Service',
        'display_name': 'RevFlow Content Generator',
        'description': 'AI-powered content generation',
        'port': 8006,
        'health_endpoint': '/health'
    },
    {
        'service_id': 'scoring-service',
        'name': 'Scoring Service',
        'display_name': 'RevFlow Quality Scoring',
        'description': 'Content quality assessment',
        'port': 8005,
        'health_endpoint': '/api/v1/scoring/health'
    },
    {
        'service_id': 'internal-linking',
        'name': 'Internal Linking API',
        'display_name': 'RevFlow Link Intelligence',
        'description': 'Intelligent internal linking',
        'port': 8001,
        'health_endpoint': '/health'
    },
    {
        'service_id': 'citations-service',
        'name': 'Citations Service',
        'display_name': 'RevFlow AI Citations',
        'description': 'AI citation tracking and optimization',
        'port': 8007,
        'health_endpoint': '/health'
    }
]

def main():
    print("🚀 Registering RevFlow Services with RevCore\n")
    
    success_count = 0
    failed_count = 0
    
    for service in SERVICES:
        print(f"Registering {service['name']}...")
        if register_service(service):
            success_count += 1
        else:
            failed_count += 1
        print()
    
    print("=" * 50)
    print(f"✅ Successfully registered: {success_count}")
    print(f"❌ Failed: {failed_count}")
    print("=" * 50)

if __name__ == "__main__":
    main()
