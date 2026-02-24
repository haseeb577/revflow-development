"""
RevFlow Universal Client - Simplified Version
NO HARDCODED PORTS - All module discovery through gateway
Gateway queries PostgreSQL, client has zero database knowledge
"""
import requests
import os
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class RevFlowClient:
    """
    Simplified client for RevFlow module communication
    
    Features:
    - Zero hardcoded ports
    - Single gateway endpoint
    - No database knowledge
    - Automatic fallback if gateway unavailable
    
    Module discovery is handled by RevCore Gateway which queries PostgreSQL
    """
    
    def __init__(self):
        # Gateway endpoint - the ONLY configuration needed
        self.gateway = os.getenv(
            "REVCORE_GATEWAY",
            "http://localhost:8004/api/gateway"
        )
        
        # Request timeout
        self.timeout = float(os.getenv("REVFLOW_REQUEST_TIMEOUT", "30"))
        
        logger.info(f"RevFlowClient initialized")
        logger.info(f"  Gateway: {self.gateway}")
        logger.info(f"  Timeout: {self.timeout}s")
    
    def call_module(
        self,
        module_name: str,
        endpoint: str,
        method: str = "GET",
        data: Optional[Dict] = None,
    ) -> Dict[Any, Any]:
        """
        Call any module through the gateway
        
        The gateway handles:
        - Module name lookup in PostgreSQL
        - Port discovery
        - Request routing
        - Error handling
        
        Args:
            module_name: "revspy", "revrank", "revpublish", etc.
            endpoint: "/serp-analysis", "/generate", etc.
            method: "GET", "POST", "PUT", "DELETE"
            data: Request body for POST/PUT
        
        Returns:
            Response JSON
        
        Raises:
            requests.exceptions.RequestException: If gateway or module fails
        """
        
        # Ensure endpoint starts with /
        if not endpoint.startswith("/"):
            endpoint = "/" + endpoint
        
        # Build gateway URL
        url = f"{self.gateway}/{module_name}{endpoint}"
        
        logger.info(f"[CLIENT] {method} {module_name}{endpoint}")
        
        try:
            # Call through gateway
            if method == "GET":
                response = requests.get(url, params=data, timeout=self.timeout)
            elif method == "POST":
                response = requests.post(url, json=data, timeout=self.timeout)
            elif method == "PUT":
                response = requests.put(url, json=data, timeout=self.timeout)
            elif method == "DELETE":
                response = requests.delete(url, timeout=self.timeout)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            response.raise_for_status()
            result = response.json()
            
            logger.info(f"[CLIENT] ✓ {response.status_code}")
            return result
            
        except requests.exceptions.Timeout:
            logger.error(f"[CLIENT] ✗ Gateway timeout")
            raise HTTPException(status_code=504, detail="Gateway timeout")
        except requests.exceptions.ConnectionError:
            logger.error(f"[CLIENT] ✗ Gateway unavailable at {self.gateway}")
            raise HTTPException(status_code=503, detail="Gateway unavailable")
        except Exception as e:
            logger.error(f"[CLIENT] ✗ Error: {str(e)}")
            raise


# Singleton pattern
_client = None


def get_revflow_client() -> RevFlowClient:
    """Get or create singleton client"""
    global _client
    if _client is None:
        _client = RevFlowClient()
    return _client


# Convenience functions
def call_revspy(endpoint: str, method: str = "GET", data: dict = None) -> dict:
    """Call RevSPY module"""
    return get_revflow_client().call_module("revspy", endpoint, method, data)


def call_revrank(endpoint: str, method: str = "GET", data: dict = None) -> dict:
    """Call RevRank module"""
    return get_revflow_client().call_module("revrank", endpoint, method, data)


def call_revpublish(endpoint: str, method: str = "GET", data: dict = None) -> dict:
    """Call RevPublish module"""
    return get_revflow_client().call_module("revpublish", endpoint, method, data)


def call_revcore(endpoint: str, method: str = "GET", data: dict = None) -> dict:
    """Call RevCore module"""
    return get_revflow_client().call_module("revcore", endpoint, method, data)


if __name__ == "__main__":
    # Test
    print("Testing RevFlowClient...")
    client = get_revflow_client()
    print(f"✓ Client created: {client.gateway}")
    print("✓ Zero hardcoded ports - all discovery through gateway")
