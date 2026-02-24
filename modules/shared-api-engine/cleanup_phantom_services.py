#!/usr/bin/env python3
"""Remove services registered but not actually running"""
import psycopg2
import subprocess

conn = psycopg2.connect(
    host="localhost",
    database="revcore",
    user="revcore_user",
    password="revcore_secure_2026"
)

cur = conn.cursor()
cur.execute("SELECT id, service_id, name, port FROM services")

phantom_services = []

for service_id, svc_id, name, port in cur.fetchall():
    # Check if anything is listening on the port
    result = subprocess.run(
        ['lsof', '-i', f':{port}'],
        capture_output=True,
        text=True
    )
    
    if not result.stdout.strip():
        phantom_services.append((service_id, svc_id, name, port))

if phantom_services:
    print("Found phantom services (registered but not running):")
    for sid, svc_id, name, port in phantom_services:
        print(f"  - {name} (:{port}) [{svc_id}]")
    
    response = input("\nRemove these services? (yes/no): ")
    if response.lower() == 'yes':
        ids_to_delete = [str(s[0]) for s in phantom_services]
        cur.execute(f"DELETE FROM services WHERE id IN ({','.join(ids_to_delete)})")
        conn.commit()
        print(f"✅ Removed {len(phantom_services)} phantom services")
else:
    print("✅ No phantom services found")

conn.close()
