#!/usr/bin/env python3
"""Verify RevCite registration with RevCore"""

import requests
import json

try:
    response = requests.get("http://localhost:8004/api/v1/services", timeout=5)
    data = response.json()
    
    print(f"\n✅ Total Services: {data['total']}")
    print("\n📋 All Registered Services:")
    
    revcite_found = False
    for svc in data['services']:
        if 'revcite' in svc['service_id'].lower():
            icon = '🎯'
            revcite_found = True
        else:
            icon = '  '
        print(f"{icon} • {svc['name']} (port {svc['port']}) - {svc['status']}")
    
    print()
    if revcite_found:
        print("✅ RevCite Status: REGISTERED")
    else:
        print("❌ RevCite Status: NOT FOUND")
    print()
    
except Exception as e:
    print(f"❌ Error: {e}")

