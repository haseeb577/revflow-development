"""Webhook Service - Sends notifications to customer endpoints"""
import httpx
import hmac
import hashlib
import json
from typing import Dict, Any, Optional
from datetime import datetime
import asyncio

class WebhookService:
    """Manages webhook deliveries to customers"""
    
    async def send_webhook(
        self,
        webhook_url: str,
        event: str,
        payload: Dict[str, Any],
        secret_key: Optional[str] = None,
        retry_count: int = 3
    ) -> Dict[str, Any]:
        """
        Send webhook with retry logic
        Returns: {"success": bool, "status_code": int, "response": str}
        """
        
        # Add metadata to payload
        payload["event"] = event
        payload["timestamp"] = datetime.utcnow().isoformat()
        
        # Generate signature if secret provided
        headers = {"Content-Type": "application/json"}
        if secret_key:
            signature = self._generate_signature(payload, secret_key)
            headers["X-Webhook-Signature"] = signature
        
        for attempt in range(retry_count):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(
                        webhook_url,
                        json=payload,
                        headers=headers
                    )
                    
                    if response.status_code in [200, 201, 202]:
                        return {
                            "success": True,
                            "status_code": response.status_code,
                            "response": response.text[:1000],
                            "retry_count": attempt
                        }
                    
            except Exception as e:
                if attempt == retry_count - 1:
                    return {
                        "success": False,
                        "status_code": 0,
                        "response": str(e),
                        "retry_count": attempt + 1
                    }
                
                # Exponential backoff
                await asyncio.sleep(2 ** attempt)
        
        return {
            "success": False,
            "status_code": response.status_code if 'response' in locals() else 0,
            "response": "Max retries exceeded",
            "retry_count": retry_count
        }
    
    def _generate_signature(self, payload: Dict[str, Any], secret: str) -> str:
        """Generate HMAC signature for webhook security"""
        payload_bytes = json.dumps(payload, sort_keys=True).encode()
        return hmac.new(
            secret.encode(),
            payload_bytes,
            hashlib.sha256
        ).hexdigest()
