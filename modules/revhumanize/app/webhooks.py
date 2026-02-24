"""
Webhook callbacks for Humanization Pipeline
"""
import httpx
import json
from typing import Dict, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from .database import get_db
from .models.db_models import WebhookLog

class WebhookManager:
    """Manages webhook deliveries"""
    
    def __init__(self):
        self.timeout = 10  # seconds
    
    async def send_webhook(
        self,
        url: str,
        event: str,
        payload: Dict,
        content_id: Optional[str] = None
    ) -> bool:
        """
        Send webhook with automatic logging
        
        Args:
            url: Webhook URL
            event: Event type (e.g., "content.approved")
            payload: Data to send
            content_id: Related content ID
        
        Returns:
            bool: Success status
        """
        log_entry = None
        
        with get_db() as db:
            # Create log entry
            log_entry = WebhookLog(
                url=url,
                event=event,
                payload=payload,
                content_id=content_id,
                attempts=1
            )
            db.add(log_entry)
            db.commit()
            
            try:
                # Send webhook
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        url,
                        json=payload,
                        headers={
                            "Content-Type": "application/json",
                            "X-Webhook-Event": event,
                            "X-Webhook-Timestamp": datetime.utcnow().isoformat()
                        },
                        timeout=self.timeout
                    )
                    
                    # Update log
                    log_entry.status_code = response.status_code
                    log_entry.response = response.text[:1000]  # Truncate
                    log_entry.success = 200 <= response.status_code < 300
                    db.commit()
                    
                    return log_entry.success
            
            except Exception as e:
                # Log failure
                log_entry.success = False
                log_entry.response = str(e)[:1000]
                db.commit()
                return False

# Global instance
webhook_manager = WebhookManager()

async def trigger_webhook(event: str, payload: Dict, content_id: Optional[str] = None):
    """
    Trigger webhooks for an event
    
    This is a placeholder - you should configure webhook URLs in .env:
    WEBHOOK_CONTENT_APPROVED=https://your-app.com/webhooks/content-approved
    WEBHOOK_CONTENT_REJECTED=https://your-app.com/webhooks/content-rejected
    """
    import os
    
    webhook_url = os.getenv(f"WEBHOOK_{event.upper().replace('.', '_')}")
    
    if webhook_url:
        await webhook_manager.send_webhook(
            url=webhook_url,
            event=event,
            payload=payload,
            content_id=content_id
        )
