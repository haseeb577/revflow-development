#!/usr/bin/env python3
"""
Scheduled Security Scanner
Runs every 6 hours to check all customer domains
"""

import asyncio
import aiohttp
import sys
from datetime import datetime

async def trigger_scan():
    """Trigger full security scan via API"""
    try:
        async with aiohttp.ClientSession() as session:
            print(f"[{datetime.now()}] Starting scheduled security scan...")
            
            async with session.post(
                'http://localhost:8910/api/security/scan-all',
                json={"force_refresh": False},
                timeout=aiohttp.ClientTimeout(total=3600)  # 1 hour timeout
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"[{datetime.now()}] Scan completed:")
                    print(f"  - Scanned: {data.get('scanned', 0)} domains")
                    print(f"  - Blacklisted: {data.get('blacklisted', 0)}")
                    print(f"  - Warnings: {data.get('warnings', 0)}")
                    print(f"  - Healthy: {data.get('healthy', 0)}")
                    
                    if data.get('blacklisted', 0) > 0:
                        print(f"  ⚠️  ALERT: {data['blacklisted']} domains blacklisted!")
                        print(f"  Domains: {', '.join(data.get('blacklisted_domains', []))}")
                else:
                    print(f"[{datetime.now()}] Scan failed: HTTP {response.status}")
                    sys.exit(1)
                    
    except Exception as e:
        print(f"[{datetime.now()}] Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(trigger_scan())
