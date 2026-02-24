#!/usr/bin/env python3
"""Clean up inactive/duplicate services from RevCore"""
import psycopg2

conn = psycopg2.connect(
    host="localhost",
    database="revcore",
    user="revcore_user",
    password="revcore_secure_2026"
)

cur = conn.cursor()

# Keep only the latest registration for duplicate ports
cur.execute("""
    DELETE FROM services 
    WHERE id NOT IN (
        SELECT MAX(id) 
        FROM services 
        GROUP BY port
    )
    RETURNING service_id, name;
""")

deleted = cur.fetchall()
if deleted:
    print("🗑️  Removed duplicate services:")
    for service_id, name in deleted:
        print(f"   - {name} ({service_id})")
else:
    print("✅ No duplicates found")

conn.commit()
conn.close()
