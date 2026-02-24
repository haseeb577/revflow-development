"""
RevPublish → RevCore Hub Integration
Module 9 integration with Module 17 (RevCore)
"""

import sys
import os
import logging
from typing import Dict, Any, Optional

# Add revcore to Python path
sys.path.insert(0, '/opt/revflow-os')

try:
    import revcore
    from revcore.service_registry import ServiceRegistry
    from revcore.health_check import HealthCheck
except ImportError as e:
    logging.warning(f"RevCore module not found: {e}")
    # Create stub classes for development
    class ServiceRegistry:
        @staticmethod
        def register(service_info):
            logging.info(f"Would register: {service_info}")
            return True
    
    class HealthCheck:
        @staticmethod
        def register_check(name, check_fn):
            logging.info(f"Would register health check: {name}")
            return True

logger = logging.getLogger(__name__)

class RevPublishIntegration:
    """
    Handles integration between RevPublish (Module 9) and RevCore (Module 17)
    """
    
    def __init__(self, app_name: str = "RevPublish", module_number: int = 9):
        self.app_name = app_name
        self.module_number = module_number
        self.service_registry = ServiceRegistry()
        self.health_check = HealthCheck()
        self.registered = False
        
    def register_with_revcore(self, host: str = "localhost", port: int = 8550) -> bool:
        """
        Register RevPublish with RevCore Hub service registry
        """
        try:
            service_info = {
                "module_number": self.module_number,
                "module_name": "revpublish",
                "service_name": self.app_name,
                "host": host,
                "port": port,
                "status": "active",
                "endpoints": [
                    "/api/revpublish/health",
                    "/api/revpublish/dashboard-stats",
                    "/api/revpublish/sites",
                    "/api/revpublish/queue",
                    "/api/revpublish/deploy",
                ],
                "capabilities": [
                    "wordpress_publishing",
                    "content_deployment",
                    "site_management",
                ],
            }
            
            result = self.service_registry.register(service_info)
            self.registered = True
            logger.info(f"✓ Registered {self.app_name} with RevCore Hub")
            return result
            
        except Exception as e:
            logger.error(f"✗ Failed to register with RevCore: {e}")
            return False
    
    def register_health_checks(self, check_functions: Dict[str, callable]) -> None:
        """
        Register health check functions with RevCore monitoring
        """
        for check_name, check_fn in check_functions.items():
            try:
                self.health_check.register_check(
                    f"revpublish_{check_name}",
                    check_fn
                )
                logger.info(f"✓ Registered health check: {check_name}")
            except Exception as e:
                logger.warning(f"⚠ Could not register health check {check_name}: {e}")
    
    def get_module_info(self) -> Dict[str, Any]:
        """
        Return module information for RevCore
        """
        return {
            "module_number": self.module_number,
            "module_name": "RevPublish™",
            "suite": "Lead Generation Suite",
            "status": "active" if self.registered else "starting",
            "version": "2.0.0",
            "description": "WordPress Publishing Automation",
        }

# Global instance
_integration = None

def get_integration() -> RevPublishIntegration:
    """
    Get or create global integration instance
    """
    global _integration
    if _integration is None:
        _integration = RevPublishIntegration()
    return _integration

def init_revcore_integration(app_name: str = "RevPublish", port: int = 8550) -> RevPublishIntegration:
    """
    Initialize RevCore integration on app startup
    """
    integration = get_integration()
    integration.register_with_revcore(port=port)
    return integration
