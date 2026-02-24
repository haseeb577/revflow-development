"""
RevFlow OS™ API Orchestrator
=============================
Central routing layer that implements ALL Gemini cost-saving strategies

Architecture:
    User Request
         ↓
    API Orchestrator ← YOU ARE HERE
     • Check cache first
     • Route to optimized client
     • Log costs to PostgreSQL
     • Cache result
         ↓
    Optimized API Clients
     • DataForSEO (batching, priority)
     • Anthropic (prompt caching)
     • OpenAI (escalation)
         ↓
    PostgreSQL Audit Trail

Usage:
    from core.api_orchestrator import APIOrchestrator
    
    orch = APIOrchestrator()
    
    # All optimization logic handled automatically!
    result = orch.call_api(
        service="openai",
        operation="analyze_industry",
        params={"prompt": "Analyze moving services"},
        industry_tag="moving",
        priority="NORMAL"
    )
"""

import os
import sys
import hashlib
import json
import psycopg2
from typing import Dict, Optional, Literal, Any
from datetime import datetime
import logging

# Import our optimized clients
sys.path.insert(0, '/opt/revpublish/backend')
from core.cache_manager import get_cache

# These will be in /opt/revpublish/backend/services/
try:
    from services.dataforseo_optimized_client import DataForSEOOptimizedClient
    from services.anthropic_optimized_client import AnthropicOptimizedClient
    from services.openai_optimized_client import OpenAIOptimizedClient
except ImportError:
    # Fallback if not yet installed
    DataForSEOOptimizedClient = None
    AnthropicOptimizedClient = None
    OpenAIOptimizedClient = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


import os
from pathlib import Path

def load_env_file(env_file="/opt/shared-api-engine/.env"):
    """Load environment variables from file"""
    if not Path(env_file).exists():
        return
    
    with open(env_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                # Remove quotes
                value = value.strip().strip('"').strip("'")
                os.environ[key] = value

# Load environment on import
load_env_file()



import os
from pathlib import Path

def load_env_file(env_file="/opt/shared-api-engine/.env"):
    """Load environment variables from file"""
    if not Path(env_file).exists():
        return
    
    with open(env_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                # Remove quotes
                value = value.strip().strip('"').strip("'")
                os.environ[key] = value

# Load environment on import
load_env_file()



class APIOrchestrator:
    """
    Central orchestrator implementing ALL cost-saving strategies
    """
    
    def __init__(self, db_url: Optional[str] = None, redis_db: int = 0):
        """
        Initialize orchestrator with cache and database
        
        Args:
            db_url: PostgreSQL connection URL (from env if not provided)
            redis_db: Redis database number for cache
        """
        # Initialize cache manager
        self.cache = get_cache(redis_db=redis_db, default_ttl=3600)
        
        # Initialize database connection
        self.db_url = db_url or os.getenv("DATABASE_URL")
        self.db_conn = None
        
        if self.db_url:
            try:
                self.db_conn = psycopg2.connect(self.db_url)
                logger.info("✓ PostgreSQL connected for cost audit")
            except Exception as e:
                logger.warning(f"⚠️  PostgreSQL connection failed: {e}")
        
        # Initialize client cache (lazy loading)
        self.clients = {}
        
        logger.info("API Orchestrator initialized (clients will load on demand)")
    

    def _get_client(self, service: str):
        """
        Get or initialize client on demand (lazy loading)
        
        Args:
            service: Service name
            
        Returns:
            Client instance
        """
        if service in self.clients:
            return self.clients[service]
        
        # Initialize client on first use
        if service == 'dataforseo' and DataForSEOOptimizedClient:
            try:
                self.clients['dataforseo'] = DataForSEOOptimizedClient()
                logger.info("✓ DataForSEO client initialized")
            except ValueError as e:
                logger.warning(f"⚠️  DataForSEO credentials missing: {e}")
                raise
        
        elif service == 'anthropic' and AnthropicOptimizedClient:
            try:
                self.clients['anthropic'] = AnthropicOptimizedClient()
                logger.info("✓ Anthropic client initialized")
            except ValueError as e:
                logger.warning(f"⚠️  Anthropic credentials missing: {e}")
                raise
        
        elif service == 'openai' and OpenAIOptimizedClient:
            try:
                self.clients['openai'] = OpenAIOptimizedClient()
                logger.info("✓ OpenAI client initialized")
            except ValueError as e:
                logger.warning(f"⚠️  OpenAI credentials missing: {e}")
                raise
        
        else:
            raise ValueError(f"Unknown or unavailable service: {service}")
        
        return self.clients[service]


    def _get_client(self, service: str):
        """
        Get or initialize client on demand (lazy loading)
        
        Args:
            service: Service name
            
        Returns:
            Client instance
        """
        if service in self.clients:
            return self.clients[service]
        
        # Initialize client on first use
        if service == 'dataforseo' and DataForSEOOptimizedClient:
            try:
                self.clients['dataforseo'] = DataForSEOOptimizedClient()
                logger.info("✓ DataForSEO client initialized")
            except ValueError as e:
                logger.warning(f"⚠️  DataForSEO credentials missing: {e}")
                raise
        
        elif service == 'anthropic' and AnthropicOptimizedClient:
            try:
                self.clients['anthropic'] = AnthropicOptimizedClient()
                logger.info("✓ Anthropic client initialized")
            except ValueError as e:
                logger.warning(f"⚠️  Anthropic credentials missing: {e}")
                raise
        
        elif service == 'openai' and OpenAIOptimizedClient:
            try:
                self.clients['openai'] = OpenAIOptimizedClient()
                logger.info("✓ OpenAI client initialized")
            except ValueError as e:
                logger.warning(f"⚠️  OpenAI credentials missing: {e}")
                raise
        
        else:
            raise ValueError(f"Unknown or unavailable service: {service}")
        
        return self.clients[service]

    def call_api(
        self,
        service: Literal["dataforseo", "anthropic", "openai", "gemini", "perplexity"],
        operation: str,
        params: Dict,
        industry_tag: Optional[str] = None,
        priority: Literal["NORMAL", "HIGH", "LIVE"] = "NORMAL",
        use_cache: bool = True,
        cache_ttl: int = 3600
    ) -> Dict:
        """
        Universal API caller with automatic optimization
        
        GEMINI STRATEGIES IMPLEMENTED:
        1. ✓ Cache-first (check before calling)
        2. ✓ Route to optimized client
        3. ✓ Apply priority levels
        4. ✓ Log costs to PostgreSQL
        5. ✓ Cache result
        6. ✓ Track savings
        
        Args:
            service: Which API service to call
            operation: What operation to perform
            params: Operation parameters
            industry_tag: Industry for cost tracking
            priority: NORMAL (cheap) or HIGH (expensive)
            use_cache: Whether to check cache first
            cache_ttl: How long to cache result (seconds)
        
        Returns:
            Dict with result, cost, and cache info
        """
        # Generate cache key
        cache_key = self._generate_cache_key(service, operation, params)
        
        # STRATEGY 1: Check cache first
        if use_cache:
            cached_result = self.cache.get(cache_key, namespace="api_results")
            
            if cached_result is not None:
                logger.info(f"⚡ Cache HIT: {service}/{operation} (saved API call!)")
                
                return {
                    **cached_result,
                    "cache_hit": True,
                    "cost": 0.0,  # No API cost!
                    "savings": cached_result.get('original_cost', 0.0)
                }
        
        # STRATEGY 2: Cache MISS - call API
        logger.info(f"💰 Cache MISS: {service}/{operation} (calling API)")
        
        start_time = datetime.now()
        
        # Route to appropriate client
        result = self._route_to_client(service, operation, params, priority)
        
        elapsed_ms = (datetime.now() - start_time).total_seconds() * 1000
        
        # STRATEGY 3: Log cost to PostgreSQL
        if self.db_conn:
            self._log_to_database(
                service=service,
                operation=operation,
                industry_tag=industry_tag,
                cost=result.get('cost', 0.0),
                usage=result.get('usage', {}),
                model=result.get('model'),
                priority=priority,
                escalated=result.get('escalated', False),
                response_time_ms=int(elapsed_ms)
            )
        
        # STRATEGY 4: Cache result
        if use_cache:
            cache_data = {
                **result,
                "original_cost": result.get('cost', 0.0),
                "cached_at": datetime.now().isoformat()
            }
            
            self.cache.set(
                cache_key,
                cache_data,
                ttl=cache_ttl,
                namespace="api_results"
            )
            
            logger.info(f"✓ Result cached for {cache_ttl}s")
        
        return {
            **result,
            "cache_hit": False
        }
    
    def _route_to_client(
        self,
        service: str,
        operation: str,
        params: Dict,
        priority: str
    ) -> Dict:
        """
        Route request to appropriate optimized client
        
        Args:
            service: Service name
            operation: Operation name
            params: Parameters
            priority: Priority level
        
        Returns:
            Result from client
        """
        # Route to DataForSEO
        if service == "dataforseo":
            client = self._get_client('dataforseo')
            
            if not client:
                raise ValueError("DataForSEO client not initialized")
            
            if operation == "keywords_research":
                return client.get_keywords_optimized(
                    keywords=params.get('keywords', []),
                    location_code=params.get('location_code', 2840),
                    priority=priority
                )
            
            elif operation == "serp_rankings":
                return client.get_serp_rankings(
                    keyword=params.get('keyword'),
                    target_domain=params.get('target_domain'),
                    location_code=params.get('location_code', 2840),
                    depth=params.get('depth', 10),
                    priority=priority
                )
            
            elif operation == "batch_serp":
                return client.batch_serp_tasks(
                    keywords=params.get('keywords', []),
                    location_code=params.get('location_code', 2840),
                    priority=priority,
                    depth=params.get('depth', 10),
                    target_domain=params.get('target_domain')
                )
        
        # Route to Anthropic
        elif service == "anthropic":
            client = self._get_client('anthropic')
            
            if not client:
                raise ValueError("Anthropic client not initialized")
            
            if operation == "analyze_with_caching":
                return client.query_with_caching(
                    prompt=params.get('prompt'),
                    system_prompt=params.get('system_prompt'),
                    model=params.get('model', 'claude-3-5-haiku-20241022'),
                    enable_caching=params.get('enable_caching', True)
                )
            
            elif operation == "analyze_with_escalation":
                return client.query_with_escalation(
                    prompt=params.get('prompt'),
                    system_prompt=params.get('system_prompt')
                )
        
        # Route to OpenAI
        elif service == "openai":
            client = self._get_client('openai')
            
            if not client:
                raise ValueError("OpenAI client not initialized")
            
            if operation == "analyze_with_escalation":
                return client.query_with_escalation(
                    prompt=params.get('prompt'),
                    system_prompt=params.get('system_prompt'),
                    response_schema=params.get('response_schema')
                )
            
            elif operation == "analyze":
                return client.query(
                    prompt=params.get('prompt'),
                    system_prompt=params.get('system_prompt'),
                    model=params.get('model', 'gpt-4o-mini'),
                    response_schema=params.get('response_schema')
                )
        
        else:
            raise ValueError(f"Unknown service: {service}")
    
    def _generate_cache_key(self, service: str, operation: str, params: Dict) -> str:
        """
        Generate deterministic cache key from request
        
        Args:
            service: Service name
            operation: Operation name
            params: Parameters
        
        Returns:
            Cache key string
        """
        # Create deterministic key from params
        params_str = json.dumps(params, sort_keys=True)
        params_hash = hashlib.sha256(params_str.encode()).hexdigest()[:16]
        
        return f"{service}_{operation}_{params_hash}"
    
    def _log_to_database(
        self,
        service: str,
        operation: str,
        industry_tag: Optional[str],
        cost: float,
        usage: Dict,
        model: Optional[str],
        priority: str,
        escalated: bool,
        response_time_ms: int
    ):
        """
        Log API call to PostgreSQL for cost tracking
        
        Args:
            service: Service name
            operation: Operation performed
            industry_tag: Industry tag
            cost: Cost in USD
            usage: Token/credit usage
            model: Model name (if AI service)
            priority: Priority level
            escalated: Whether this was an escalation
            response_time_ms: Response time in milliseconds
        """
        if not self.db_conn:
            return
        
        try:
            cursor = self.db_conn.cursor()
            
            # Extract token info if available
            input_tokens = usage.get('input_tokens') or usage.get('prompt_tokens', 0)
            output_tokens = usage.get('output_tokens') or usage.get('completion_tokens', 0)
            
            cursor.execute("""
                INSERT INTO api_audit_logs (
                    service_name,
                    endpoint,
                    industry_tag,
                    credits_spent,
                    input_tokens,
                    output_tokens,
                    model_name,
                    priority_level,
                    escalated,
                    response_time_ms,
                    status_code
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                service,
                operation,
                industry_tag,
                cost,
                input_tokens,
                output_tokens,
                model,
                1 if priority == "NORMAL" else 2,  # Map to priority code
                escalated,
                response_time_ms,
                'SUCCESS'
            ))
            
            self.db_conn.commit()
            cursor.close()
            
            logger.info(f"✓ Cost logged: {service}/{operation} = ${cost:.6f}")
            
        except Exception as e:
            logger.error(f"Failed to log to database: {e}")
    
    def get_stats(self) -> Dict:
        """
        Get cache and cost statistics
        
        Returns:
            Dict with stats
        """
        cache_stats = self.cache.get_stats()
        
        # Get today's cost from database
        today_cost = 0.0
        if self.db_conn:
            try:
                cursor = self.db_conn.cursor()
                cursor.execute("""
                    SELECT COALESCE(SUM(credits_spent), 0)
                    FROM api_audit_logs
                    WHERE DATE(timestamp) = CURRENT_DATE
                """)
                today_cost = float(cursor.fetchone()[0])
                cursor.close()
            except Exception as e:
                logger.error(f"Failed to get cost stats: {e}")
        
        return {
            "cache": cache_stats,
            "cost": {
                "today_usd": today_cost
            }
        }
    
    def close(self):
        """Close database connection"""
        if self.db_conn:
            self.db_conn.close()
            logger.info("Database connection closed")


# ============================================================================
# Usage Examples
# ============================================================================

if __name__ == "__main__":
    # Example 1: DataForSEO keyword research
    print("Example 1: DataForSEO Keyword Research")
    print("=" * 60)
    
    orch = APIOrchestrator()
    
    result = orch.call_api(
        service="dataforseo",
        operation="keywords_research",
        params={
            "keywords": ["moving", "movers", "local movers"],
            "location_code": 2840
        },
        industry_tag="moving",
        priority="NORMAL",  # 70% cheaper!
        use_cache=True
    )
    
    print(f"  Cache hit: {result['cache_hit']}")
    print(f"  Cost: ${result.get('cost', 0):.4f}")
    print(f"  Keywords processed: {result.get('keywords_processed', 0)}")
    print()
    
    # Example 2: OpenAI with escalation
    print("Example 2: OpenAI with Auto-Escalation")
    print("=" * 60)
    
    result = orch.call_api(
        service="openai",
        operation="analyze_with_escalation",
        params={
            "prompt": "Analyze the plumbing industry",
            "system_prompt": "You are an industry analyst..."
        },
        industry_tag="plumbing",
        priority="NORMAL",
        use_cache=True,
        cache_ttl=86400  # Cache for 24 hours
    )
    
    print(f"  Cache hit: {result['cache_hit']}")
    print(f"  Escalated: {result.get('escalated', False)}")
    print(f"  Cost: ${result.get('cost', 0):.6f}")
    print()
    
    # Show stats
    print("Statistics:")
    print("=" * 60)
    stats = orch.get_stats()
    print(f"  Cache hit rate: {stats['cache']['hit_rate']:.1f}%")
    print(f"  Today's API cost: ${stats['cost']['today_usd']:.2f}")
    print()
    
    orch.close()
