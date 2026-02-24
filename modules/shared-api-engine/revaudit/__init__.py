"""
RevAudit™ Shared Library
Anti-Hallucination Framework for ALL RevFlow OS Modules

ZERO TOLERANCE FOR FABRICATED DATA.

Usage in any module:
    from revaudit import audit_client, AuditMiddleware, audit_api_call

    # Add middleware to FastAPI app
    app.add_middleware(AuditMiddleware)

    # Decorate API call functions
    @audit_api_call("DataForSEO")
    def call_dataforseo(...):
        ...

    # Manual logging
    audit_client.log_api_call(tool="GBP_API", ...)
"""

from .client import (
    RevAuditClient,
    audit_client,
    HallucinationError,
    audit_api_call,
    AuditedAssessment
)

from .middleware import AuditMiddleware

from .validators import (
    validate_content,
    validate_report,
    check_for_hallucination,
    FORBIDDEN_PHRASES
)

from .integrate import integrate_revaudit, get_audit_client

try:
    from .flask_integration import integrate_revaudit_flask, audit_flask_call
except ImportError:
    integrate_revaudit_flask = None
    audit_flask_call = None

__all__ = [
    'RevAuditClient',
    'audit_client',
    'HallucinationError',
    'audit_api_call',
    'AuditedAssessment',
    'AuditMiddleware',
    'validate_content',
    'validate_report',
    'check_for_hallucination',
    'FORBIDDEN_PHRASES'
]

__version__ = "1.0.0"
