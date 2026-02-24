#!/usr/bin/env python3
"""Generate comprehensive service status report"""
import psycopg2
import subprocess
import requests

conn = psycopg2.connect(
    host="localhost",
    database="revcore",
    user="revcore_user",
    password="revcore_secure_2026"
)

cur = conn.cursor()
cur.execute("""
    SELECT service_id, name, host, port, health_endpoint, status
    FROM services 
    ORDER BY port
""")

print("=" * 80)
print("RevFlow Service Status Report")
print("=" * 80)

for service_id, name, host, port, health_endpoint, status in cur.fetchall():
    url = f"http://{host}:{port}{health_endpoint}"
    
    # Check if port is listening
    port_check = subprocess.run(
        ['lsof', '-i', f':{port}'],
        capture_output=True,
        text=True
    )
    port_active = bool(port_check.stdout.strip())
    
    # Try health check
    try:
        response = requests.get(url, timeout=2)
        health_status = f"✅ {response.status_code}"
        if response.status_code != 200:
            health_status += f" (ERROR: {response.text[:50]})"
    except requests.exceptions.ConnectionError:
        health_status = "❌ Connection refused"
    except Exception as e:
        health_status = f"❌ {str(e)[:30]}"
    
    print(f"\n{name} (:{port})")
    print(f"  Service ID: {service_id}")
    print(f"  Port Active: {'✅ Yes' if port_active else '❌ No'}")
    print(f"  Health Check: {health_status}")
    print(f"  Registry Status: {status}")
    
    # If port active but health fails, show what's running
    if port_active and '❌' in health_status or '500' in health_status:
        print(f"  ⚠️  SERVICE ISSUE: Port is active but health check failing")

print("\n" + "=" * 80)
conn.close()
