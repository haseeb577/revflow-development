"""
Test script for RevFlow Enrichment Service
Run with: python test_endpoints.py
"""

import httpx
import asyncio
import json
from datetime import datetime


BASE_URL = "http://localhost:8500"


class EnrichmentTester:
    """Test all enrichment endpoints"""
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        self.results = []
    
    async def test_endpoint(self, name: str, method: str, endpoint: str, payload: dict):
        """Test a single endpoint"""
        print(f"\n{'='*60}")
        print(f"Testing: {name}")
        print(f"Endpoint: {method} {endpoint}")
        print(f"{'='*60}")
        
        try:
            if method == "GET":
                response = await self.client.get(f"{BASE_URL}{endpoint}")
            else:
                response = await self.client.post(
                    f"{BASE_URL}{endpoint}",
                    json=payload
                )
            
            status = "✅ PASS" if response.status_code == 200 else "❌ FAIL"
            
            result = {
                "name": name,
                "status": status,
                "status_code": response.status_code,
                "response": response.json() if response.status_code == 200 else response.text
            }
            
            self.results.append(result)
            
            print(f"Status: {status} ({response.status_code})")
            if response.status_code == 200:
                print(f"Response: {json.dumps(response.json(), indent=2)}")
            else:
                print(f"Error: {response.text}")
            
            return result
            
        except Exception as e:
            print(f"❌ ERROR: {str(e)}")
            self.results.append({
                "name": name,
                "status": "❌ ERROR",
                "error": str(e)
            })
    
    async def run_all_tests(self):
        """Run all endpoint tests"""
        
        print("\n" + "="*60)
        print("RevFlow Enrichment Service - Endpoint Tests")
        print("="*60)
        
        # Test 1: Health Check
        await self.test_endpoint(
            name="Health Check",
            method="GET",
            endpoint="/health",
            payload={}
        )
        
        # Test 2: Email Enrichment
        await self.test_endpoint(
            name="Email Enrichment",
            method="POST",
            endpoint="/api/v1/enrich/email",
            payload={
                "first_name": "John",
                "last_name": "Smith",
                "company_domain": "acmeplumbing.com"
            }
        )
        
        # Test 3: Phone Enrichment
        await self.test_endpoint(
            name="Phone Enrichment",
            method="POST",
            endpoint="/api/v1/enrich/phone",
            payload={
                "email": "john@acmeplumbing.com"
            }
        )
        
        # Test 4: Email Validation
        await self.test_endpoint(
            name="Email Validation",
            method="POST",
            endpoint="/api/v1/enrich/validate/email",
            payload={
                "email": "john@acmeplumbing.com"
            }
        )
        
        # Test 5: Phone Validation
        await self.test_endpoint(
            name="Phone Validation",
            method="POST",
            endpoint="/api/v1/enrich/validate/phone",
            payload={
                "phone": "+15551234567"
            }
        )
        
        # Test 6: LinkedIn Person
        await self.test_endpoint(
            name="LinkedIn Person Finder",
            method="POST",
            endpoint="/api/v1/enrich/linkedin/person",
            payload={
                "first_name": "John",
                "last_name": "Smith",
                "company": "ACME Plumbing"
            }
        )
        
        # Test 7: LinkedIn Company
        await self.test_endpoint(
            name="LinkedIn Company Finder",
            method="POST",
            endpoint="/api/v1/enrich/linkedin/company",
            payload={
                "company_domain": "acmeplumbing.com"
            }
        )
        
        # Test 8: Person Enrichment
        await self.test_endpoint(
            name="Person Enrichment",
            method="POST",
            endpoint="/api/v1/enrich/person",
            payload={
                "email": "john@acmeplumbing.com"
            }
        )
        
        # Test 9: Waterfall Enrichment
        await self.test_endpoint(
            name="Waterfall Enrichment",
            method="POST",
            endpoint="/api/v1/enrich/waterfall",
            payload={
                "input": {
                    "first_name": "John",
                    "last_name": "Smith",
                    "company_domain": "acmeplumbing.com"
                },
                "data_points": ["email", "phone"],
                "providers": ["hunter", "prospeo"]
            }
        )
        
        # Test 10: Batch Enrichment
        await self.test_endpoint(
            name="Batch Enrichment",
            method="POST",
            endpoint="/api/v1/enrich/batch",
            payload={
                "contacts": [
                    {
                        "first_name": "John",
                        "last_name": "Smith",
                        "company_domain": "acmeplumbing.com"
                    },
                    {
                        "first_name": "Jane",
                        "last_name": "Doe",
                        "company_domain": "xyzroofing.com"
                    }
                ],
                "data_points": ["email"]
            }
        )
        
        # Test 11: Company Firmographics
        await self.test_endpoint(
            name="Company Firmographics",
            method="POST",
            endpoint="/api/v1/enrich/company/firmographics",
            payload={
                "domain": "acmeplumbing.com"
            }
        )
        
        # Test 12: Company Tech Stack
        await self.test_endpoint(
            name="Company Tech Stack",
            method="POST",
            endpoint="/api/v1/enrich/company/tech-stack",
            payload={
                "domain": "acmeplumbing.com"
            }
        )
        
        # Test 13: Company Backlinks
        await self.test_endpoint(
            name="Company Backlinks",
            method="POST",
            endpoint="/api/v1/enrich/company/backlinks",
            payload={
                "domain": "acmeplumbing.com"
            }
        )
        
        # Test 14: Company Keywords
        await self.test_endpoint(
            name="Company Keywords",
            method="POST",
            endpoint="/api/v1/enrich/company/keywords",
            payload={
                "domain": "acmeplumbing.com"
            }
        )
        
        # Test 15: Company Reviews
        await self.test_endpoint(
            name="Company Reviews",
            method="POST",
            endpoint="/api/v1/enrich/company/reviews",
            payload={
                "business_name": "ACME Plumbing",
                "location": "Dallas, TX"
            }
        )
        
        # Test 16: Hiring Intent
        await self.test_endpoint(
            name="Hiring Intent Detection",
            method="POST",
            endpoint="/api/v1/enrich/intent/hiring",
            payload={
                "domain": "acmeplumbing.com"
            }
        )
        
        # Test 17: Funding Data
        await self.test_endpoint(
            name="Funding Data",
            method="POST",
            endpoint="/api/v1/enrich/intent/funding",
            payload={
                "company_name": "ACME Plumbing"
            }
        )
        
        # Test 18: Behavioral Intent
        await self.test_endpoint(
            name="Behavioral Intent",
            method="POST",
            endpoint="/api/v1/enrich/intent/behavioral",
            payload={
                "domain": "acmeplumbing.com",
                "days": 7
            }
        )
        
        # Print summary
        await self.print_summary()
    
    async def print_summary(self):
        """Print test summary"""
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)
        
        passed = len([r for r in self.results if "✅" in r.get("status", "")])
        failed = len([r for r in self.results if "❌" in r.get("status", "")])
        total = len(self.results)
        
        print(f"\nTotal Tests: {total}")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"Success Rate: {(passed/total*100):.1f}%")
        
        if failed > 0:
            print("\n❌ Failed Tests:")
            for r in self.results:
                if "❌" in r.get("status", ""):
                    print(f"  - {r['name']}")
                    if "error" in r:
                        print(f"    Error: {r['error']}")
        
        print("\n" + "="*60)
    
    async def close(self):
        await self.client.aclose()


async def main():
    """Run all tests"""
    tester = EnrichmentTester()
    
    try:
        await tester.run_all_tests()
    finally:
        await tester.close()


if __name__ == "__main__":
    print("Starting RevFlow Enrichment Service Tests...")
    print("Make sure the service is running on http://localhost:8500\n")
    
    asyncio.run(main())
