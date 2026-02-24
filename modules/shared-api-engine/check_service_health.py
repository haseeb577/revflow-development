#!/usr/bin/env python3
"""Check health of all registered services"""
import psycopg2
import requests

conn = psycopg2.connect(
    host="localhost",
    database="revcore",
    user="revcore_user",
    password="revcore_secure_2026"
)

cur = conn.cursor()
cur.execute("""
    SELECT service_id, name, host, port, health_endpoint 
    FROM services 
    WHERE status = 'active'
""")

print("🏥 Service Health Check")
print("=" * 60)

for row in cur.fetchall():
    service_id, name, host, port, health_endpoint = row
    url = f"http://{host}:{port}{health_endpoint}"
    
    try:
        response = requests.get(url, timeout=2)
        status = "✅ HEALTHY" if response.status_code == 200 else f"⚠️ {response.status_code}"
    except requests.exceptions.ConnectionError:
        status = "❌ OFFLINE"
    except Exception as e:
        status = f"❌ ERROR: {e}"
    
    print(f"{name:30s} (:{port}) {status}")

print("=" * 60)
conn.close()
