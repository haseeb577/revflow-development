#!/usr/bin/env python3
"""
RevAudit Universal Integration Script
Adds anti-hallucination framework to ANY FastAPI application

Usage:
    # In any FastAPI app's main.py, add at the top:
    import sys
    sys.path.insert(0, '/opt/shared-api-engine')
    from revaudit.integrate import integrate_revaudit

    app = FastAPI(...)
    integrate_revaudit(app, "MODULE_NAME")
"""

import os
import sys

# Ensure shared path is available
if '/opt/shared-api-engine' not in sys.path:
    sys.path.insert(0, '/opt/shared-api-engine')


def integrate_revaudit(app, module_name: str, strict_mode: bool = False):
    """
    Integrate RevAudit anti-hallucination framework into a FastAPI app.

    Args:
        app: FastAPI application instance
        module_name: Name of the module (e.g., "RevCore_API", "RevCite")
        strict_mode: If True, blocks responses with hallucination indicators

    Returns:
        RevAuditClient instance for manual logging
    """
    os.environ['REVFLOW_MODULE'] = module_name

    try:
        from revaudit.middleware import AuditMiddleware
        from revaudit.client import RevAuditClient, audit_client

        # Add middleware
        app.add_middleware(
            AuditMiddleware,
            module_name=module_name,
            validate_responses=True,
            strict_mode=strict_mode
        )

        # Add audit endpoints
        from fastapi import APIRouter
        audit_router = APIRouter(prefix="/audit", tags=["RevAudit"])

        @audit_router.get("/status")
        async def audit_status():
            """Check RevAudit integration status"""
            client = RevAuditClient(module_name)
            health = client._get("/health")
            return {
                "module": module_name,
                "revaudit_enabled": True,
                "revaudit_health": health.get("status", "unknown"),
                "strict_mode": strict_mode
            }

        @audit_router.get("/trail/{assessment_id}")
        async def get_trail(assessment_id: str):
            """Get audit trail for an assessment"""
            client = RevAuditClient(module_name)
            return client.get_audit_trail(assessment_id)

        app.include_router(audit_router)

        print(f"[RevAudit] ✅ Integrated with {module_name}")
        return audit_client

    except ImportError as e:
        print(f"[RevAudit] ⚠️ Integration skipped for {module_name}: {e}")
        return None
    except Exception as e:
        print(f"[RevAudit] ❌ Integration failed for {module_name}: {e}")
        return None


def get_audit_client(module_name: str = None):
    """Get an audit client for manual logging."""
    from revaudit.client import RevAuditClient
    return RevAuditClient(module_name)


# Quick integration check
if __name__ == "__main__":
    print("RevAudit Integration Module")
    print("=" * 40)
    print("Add to any FastAPI app:")
    print("")
    print("  from revaudit.integrate import integrate_revaudit")
    print("  integrate_revaudit(app, 'YOUR_MODULE_NAME')")
    print("")
