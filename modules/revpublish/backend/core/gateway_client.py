"""
RevPublish Gateway Client
Enables parallel content generation across 3 RevRank pipelines

Usage in RevPublish:
    from revpublish_gateway_client import GatewayClient
    
    gateway = GatewayClient()
    results = await gateway.generate_content_parallel(sites)
"""

import asyncio
import httpx
from typing import List, Dict, Any
from datetime import datetime

class GatewayClient:
    """Gateway client for parallel content generation"""
    
    def __init__(self):
        self.gateway_url = "http://localhost:8004"
        self.service_token = "internal-service-token"  # TODO: Load from env
        
        # HTTP client with connection pooling
        self.client = httpx.AsyncClient(
            timeout=30.0,
            limits=httpx.Limits(max_connections=10)
        )
    
    async def generate_content_parallel(
        self,
        sites: List[Dict],
        batch_size: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Generate content for multiple sites in parallel
        
        Args:
            sites: List of site dictionaries
            batch_size: Number of simultaneous requests (default: 3 pipelines)
        
        Returns:
            List of content generation results
        """
        
        results = []
        
        # Split into batches of 3 (one per pipeline)
        batches = [
            sites[i:i+batch_size] 
            for i in range(0, len(sites), batch_size)
        ]
        
        print(f"Processing {len(sites)} sites in {len(batches)} batches...")
        print(f"Batch size: {batch_size} (simultaneous requests)")
        print(f"Estimated time: {len(batches) * 2} seconds")
        print()
        
        start_time = datetime.now()
        
        for batch_num, batch in enumerate(batches, 1):
            print(f"Batch {batch_num}/{len(batches)}: Processing {len(batch)} sites...")
            
            # Create parallel tasks for this batch
            tasks = [
                self._generate_single_site(site)
                for site in batch
            ]
            
            # Execute all tasks in parallel
            # Gateway distributes across 3 pipelines automatically!
            batch_results = await asyncio.gather(
                *tasks,
                return_exceptions=True
            )
            
            # Handle results and errors
            for site, result in zip(batch, batch_results):
                if isinstance(result, Exception):
                    print(f"  ❌ {site['domain']}: {str(result)}")
                    results.append({
                        "site": site['domain'],
                        "success": False,
                        "error": str(result)
                    })
                else:
                    print(f"  ✓ {site['domain']}")
                    results.append(result)
        
        elapsed = (datetime.now() - start_time).total_seconds()
        successful = sum(1 for r in results if r.get('success'))
        
        print()
        print("=" * 60)
        print(f"COMPLETE: {len(sites)} sites in {elapsed:.1f} seconds")
        print(f"Success: {successful}/{len(sites)}")
        print(f"Throughput: {len(sites)/elapsed:.2f} sites/second")
        print("=" * 60)
        
        return results
    
    async def _generate_single_site(self, site: Dict) -> Dict[str, Any]:
        """Generate content for a single site via gateway"""
        
        # Call gateway (NOT direct pipeline!)
        response = await self.client.post(
            f"{self.gateway_url}/api/modules/revrank/generate",
            headers={
                "X-Service-Token": self.service_token,
                "X-Source-Service": "revpublish",
                "Content-Type": "application/json"
            },
            json={
                "site_domain": site['domain'],
                "page_type": site.get('page_type', 'service'),
                "keyword": site.get('keyword', ''),
                "city": site.get('city', ''),
                "state": site.get('state', '')
            }
        )
        
        response.raise_for_status()
        result = response.json()
        
        return {
            "site": site['domain'],
            "success": True,
            "content": result.get('content', ''),
            "quality_score": result.get('quality_score', 0),
            "processed_by_pipeline": result.get('processed_by', 'unknown')
        }
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()


# Example usage
async def main():
    """Example: Generate content for 53 sites in parallel"""
    
    # Mock site data
    sites = [
        {"domain": f"site-{i}.com", "city": "Dallas", "state": "Texas"}
        for i in range(1, 54)  # 53 sites
    ]
    
    gateway = GatewayClient()
    
    try:
        results = await gateway.generate_content_parallel(
            sites=sites,
            batch_size=3  # 3 simultaneous requests
        )
        
        print(f"\n✅ Generated content for {len(results)} sites")
    
    finally:
        await gateway.close()


if __name__ == "__main__":
    asyncio.run(main())
