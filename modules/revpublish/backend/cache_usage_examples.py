"""
RevPublish Cache Manager - Usage Examples
Practical patterns for content generation, site configs, and batch processing

Run these examples to understand how to use the cache manager in RevPublish
"""

import asyncio
import time
from core.cache_manager import get_cache


# ============================================================================
# EXAMPLE 1: Cache Expensive Content Generation
# ============================================================================

async def example_1_cache_content_generation():
    """
    Cache AI-generated content to avoid regenerating the same content
    Saves money and time on API calls
    """
    print("\n" + "="*70)
    print("EXAMPLE 1: Caching Content Generation Results")
    print("="*70 + "\n")
    
    cache = get_cache(redis_db=0)  # Use DB 0 for content
    
    async def expensive_content_generation(domain: str) -> dict:
        """Simulate expensive AI content generation"""
        print(f"  💰 Calling AI API for {domain} (costs $0.10, takes 2s)...")
        await asyncio.sleep(2)  # Simulate API call
        return {
            "domain": domain,
            "content": f"Generated content for {domain}",
            "generated_at": time.time()
        }
    
    domain = "dallasplumber.com"
    cache_key = domain
    namespace = "generated_content"
    
    # First call - generates and caches
    print("🔄 First call (cache MISS):")
    start = time.time()
    
    cached_content = cache.get(cache_key, namespace=namespace)
    if cached_content is None:
        content = await expensive_content_generation(domain)
        cache.set(cache_key, content, ttl=86400, namespace=namespace)  # 24 hours
        print(f"  ✅ Generated and cached (took {time.time()-start:.2f}s)")
    else:
        content = cached_content
        print(f"  ⚡ From cache (took {time.time()-start:.2f}s)")
    
    # Second call - from cache
    print("\n🔄 Second call (cache HIT):")
    start = time.time()
    
    cached_content = cache.get(cache_key, namespace=namespace)
    if cached_content is None:
        content = await expensive_content_generation(domain)
        cache.set(cache_key, content, ttl=86400, namespace=namespace)
        print(f"  ✅ Generated and cached (took {time.time()-start:.2f}s)")
    else:
        content = cached_content
        print(f"  ⚡ From cache (took {time.time()-start:.2f}s)")
    
    print(f"\n💡 Savings: $0.10 and 2 seconds on second call!")
    print(f"📊 Cache stats: {cache.get_stats()}")


# ============================================================================
# EXAMPLE 2: Cache Site Configurations
# ============================================================================

def example_2_cache_site_configs():
    """
    Cache site configurations to avoid repeated database queries
    """
    print("\n" + "="*70)
    print("EXAMPLE 2: Caching Site Configurations")
    print("="*70 + "\n")
    
    cache = get_cache(redis_db=1)  # Use DB 1 for configs
    
    def fetch_site_config_from_db(domain: str) -> dict:
        """Simulate database query"""
        print(f"  🗄️  Querying database for {domain}...")
        time.sleep(0.5)  # Simulate DB query
        return {
            "domain": domain,
            "wp_url": f"https://{domain}",
            "wp_username": "admin",
            "city": "Dallas",
            "state": "TX"
        }
    
    # Cache multiple site configs
    sites = ["dallasplumber.com", "friscoplumbing.com", "allenplumber.com"]
    
    print("🔄 First batch - fetching from database:")
    start = time.time()
    configs = {}
    for site in sites:
        cached_config = cache.get(site, namespace="site_configs")
        if cached_config is None:
            config = fetch_site_config_from_db(site)
            cache.set(site, config, ttl=3600, namespace="site_configs")  # 1 hour
            configs[site] = config
        else:
            configs[site] = cached_config
    print(f"  ✅ Fetched 3 configs in {time.time()-start:.2f}s")
    
    print("\n🔄 Second batch - from cache:")
    start = time.time()
    configs = cache.get_many(sites, namespace="site_configs")
    print(f"  ⚡ Retrieved 3 configs in {time.time()-start:.3f}s")
    
    print(f"\n💡 Savings: 1.5 seconds avoided 3 DB queries!")


# ============================================================================
# EXAMPLE 3: Cache with Batch Processing
# ============================================================================

async def example_3_cache_with_batching():
    """
    Integrate cache with batch processor to avoid reprocessing
    """
    print("\n" + "="*70)
    print("EXAMPLE 3: Cache + Batch Processing Integration")
    print("="*70 + "\n")
    
    from core.batch_processor import BatchProcessor
    
    cache = get_cache(redis_db=0)
    processor = BatchProcessor(batch_size=3)
    
    async def process_with_cache(site: dict) -> dict:
        """Process site with cache check"""
        domain = site['domain']
        
        # Check cache first
        cached_result = cache.get(domain, namespace="batch_results")
        if cached_result is not None:
            print(f"  ⚡ {domain}: From cache")
            return cached_result
        
        # Process if not cached
        print(f"  🔄 {domain}: Processing...")
        await asyncio.sleep(1)  # Simulate work
        result = {"domain": domain, "status": "processed", "timestamp": time.time()}
        
        # Cache result
        cache.set(domain, result, ttl=3600, namespace="batch_results")
        return result
    
    sites = [
        {"domain": "site1.com"},
        {"domain": "site2.com"},
        {"domain": "site3.com"},
        {"domain": "site1.com"},  # Duplicate!
        {"domain": "site2.com"},  # Duplicate!
    ]
    
    print("🔄 Processing 5 sites (2 duplicates):")
    start = time.time()
    result = await processor.process_batch(sites, process_with_cache)
    
    print(f"\n✅ Processed {result['total']} sites in {result['elapsed_seconds']:.2f}s")
    print(f"💡 Cache prevented reprocessing 2 duplicate sites!")


# ============================================================================
# EXAMPLE 4: Rate Limiting with Cache
# ============================================================================

def example_4_rate_limiting():
    """
    Use cache to track API rate limits
    """
    print("\n" + "="*70)
    print("EXAMPLE 4: Rate Limiting with Cache")
    print("="*70 + "\n")
    
    cache = get_cache(redis_db=2)  # Use DB 2 for rate limiting
    
    def check_rate_limit(api_name: str, limit: int = 10, window: int = 60) -> bool:
        """
        Check if API call is within rate limit
        
        Args:
            api_name: Name of the API
            limit: Max calls allowed
            window: Time window in seconds
            
        Returns:
            True if call allowed, False if rate limited
        """
        key = f"{api_name}_calls"
        current_count = cache.get(key, namespace="rate_limits", default=0)
        
        if current_count >= limit:
            return False
        
        # Increment counter
        cache.set(key, current_count + 1, ttl=window, namespace="rate_limits")
        return True
    
    print("🔄 Making 12 API calls (limit: 10 per minute):")
    for i in range(12):
        if check_rate_limit("openai_api", limit=10, window=60):
            print(f"  ✅ Call {i+1}: Allowed")
        else:
            print(f"  ❌ Call {i+1}: RATE LIMITED!")
    
    print(f"\n💡 Prevented 2 calls from exceeding rate limit!")


# ============================================================================
# EXAMPLE 5: Cache Invalidation Strategies
# ============================================================================

def example_5_cache_invalidation():
    """
    Demonstrate cache invalidation patterns
    """
    print("\n" + "="*70)
    print("EXAMPLE 5: Cache Invalidation Strategies")
    print("="*70 + "\n")
    
    cache = get_cache()
    
    # Set some test data
    cache.set("user_1", {"name": "John"}, namespace="users", ttl=3600)
    cache.set("user_2", {"name": "Jane"}, namespace="users", ttl=3600)
    cache.set("product_1", {"name": "Widget"}, namespace="products", ttl=3600)
    
    print("📊 Initial cache state:")
    print(f"  Users namespace has data: {cache.exists('user_1', namespace='users')}")
    print(f"  Products namespace has data: {cache.exists('product_1', namespace='products')}")
    
    # Strategy 1: Delete specific key
    print("\n🗑️  Strategy 1: Delete specific key")
    cache.delete("user_1", namespace="users")
    print(f"  user_1 exists: {cache.exists('user_1', namespace='users')}")
    print(f"  user_2 exists: {cache.exists('user_2', namespace='users')}")
    
    # Strategy 2: Clear entire namespace
    print("\n🗑️  Strategy 2: Clear namespace")
    deleted = cache.clear(namespace="users")
    print(f"  Deleted {deleted} keys from users namespace")
    print(f"  Products still exist: {cache.exists('product_1', namespace='products')}")
    
    # Strategy 3: Time-based expiration (already set via TTL)
    print("\n⏱️  Strategy 3: TTL-based expiration")
    print("  All keys set with TTL will auto-expire")
    print("  No manual cleanup needed!")


# ============================================================================
# EXAMPLE 6: Integration with RevPublish Workflow
# ============================================================================

async def example_6_revpublish_workflow():
    """
    Complete RevPublish workflow with caching
    """
    print("\n" + "="*70)
    print("EXAMPLE 6: Complete RevPublish Workflow with Caching")
    print("="*70 + "\n")
    
    from core.gateway_client import GatewayClient
    
    cache = get_cache()
    
    async def generate_content_with_cache(site: dict) -> dict:
        """Generate content with cache layer"""
        domain = site['domain']
        cache_key = f"{domain}_{site.get('page_type', 'home')}"
        
        # Check cache
        cached = cache.get(cache_key, namespace="generated_content")
        if cached:
            print(f"  ⚡ {domain}: Using cached content (saved $0.10, 2s)")
            return cached
        
        # Generate fresh content
        print(f"  🔄 {domain}: Generating fresh content...")
        gateway = GatewayClient()
        try:
            # This would normally call the gateway
            # result = await gateway.generate_single_site(site)
            await asyncio.sleep(0.1)  # Simulate
            result = {
                "domain": domain,
                "content": "Generated content...",
                "generated_at": time.time()
            }
            
            # Cache for 24 hours
            cache.set(cache_key, result, ttl=86400, namespace="generated_content")
            return result
        finally:
            await gateway.close()
    
    sites = [
        {"domain": "dallasplumber.com", "page_type": "home"},
        {"domain": "friscoplumbing.com", "page_type": "home"},
        {"domain": "dallasplumber.com", "page_type": "home"},  # Duplicate!
    ]
    
    print("🔄 Generating content for 3 pages (1 duplicate):")
    results = []
    for site in sites:
        result = await generate_content_with_cache(site)
        results.append(result)
    
    print(f"\n✅ Completed! Cache saved 1 API call ($0.10, 2s)")


# ============================================================================
# MAIN: Run All Examples
# ============================================================================

async def run_all_examples():
    """Run all cache manager examples"""
    print("\n" + "="*70)
    print("🚀 RevPublish Cache Manager - Complete Demo")
    print("="*70)
    
    # Example 1: Content caching
    await example_1_cache_content_generation()
    
    # Example 2: Config caching
    example_2_cache_site_configs()
    
    # Example 3: Batch + cache
    await example_3_cache_with_batching()
    
    # Example 4: Rate limiting
    example_4_rate_limiting()
    
    # Example 5: Invalidation
    example_5_cache_invalidation()
    
    # Example 6: Full workflow
    await example_6_revpublish_workflow()
    
    print("\n" + "="*70)
    print("✅ All examples completed!")
    print("="*70 + "\n")


if __name__ == "__main__":
    # Run the demo
    asyncio.run(run_all_examples())
