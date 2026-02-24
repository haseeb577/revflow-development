"""
RevAudit Client Library
Shared across ALL RevFlow OS modules
"""

import os
import json
import time
import hashlib
from typing import Dict, Any, Optional, Callable, List
from functools import wraps
from datetime import datetime

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    import urllib.request
    import urllib.error
    HAS_HTTPX = False


REVAUDIT_URL = os.getenv('REVAUDIT_URL', 'http://localhost:8710')


class HallucinationError(Exception):
    """Raised when hallucination is detected in content."""
    def __init__(self, details: Dict):
        self.details = details
        self.severity = details.get('severity', 'BLOCKED')
        self.reason = details.get('reason', 'Unknown hallucination detected')
        super().__init__(f"HALLUCINATION BLOCKED: {self.reason}")


class RevAuditClient:
    """
    Universal client for RevAudit Anti-Hallucination Framework.

    Every module should use this to:
    1. Log ALL external API calls
    2. Register claims with source attribution
    3. Validate content before output
    4. Create verification gates for user approval
    """

    def __init__(self, module_name: str = None):
        self.module_name = module_name or os.getenv('REVFLOW_MODULE', 'UNKNOWN')
        self.base_url = REVAUDIT_URL
        self._enabled = os.getenv('REVAUDIT_ENABLED', 'true').lower() == 'true'

        if HAS_HTTPX:
            self._client = httpx.Client(timeout=30.0)
        else:
            self._client = None

    def _post(self, endpoint: str, data: Dict) -> Dict:
        """Make POST request to RevAudit API."""
        if not self._enabled:
            return {"skipped": True, "reason": "REVAUDIT_ENABLED=false"}

        url = f"{self.base_url}{endpoint}"

        if HAS_HTTPX:
            try:
                response = self._client.post(url, json=data)
                return response.json()
            except Exception as e:
                return {"error": str(e)}
        else:
            # Fallback to urllib
            try:
                req = urllib.request.Request(
                    url,
                    data=json.dumps(data).encode('utf-8'),
                    headers={'Content-Type': 'application/json'}
                )
                with urllib.request.urlopen(req, timeout=30) as resp:
                    return json.loads(resp.read().decode('utf-8'))
            except Exception as e:
                return {"error": str(e)}

    def _get(self, endpoint: str) -> Dict:
        """Make GET request to RevAudit API."""
        if not self._enabled:
            return {"skipped": True}

        url = f"{self.base_url}{endpoint}"

        if HAS_HTTPX:
            try:
                response = self._client.get(url)
                return response.json()
            except Exception as e:
                return {"error": str(e)}
        else:
            try:
                req = urllib.request.Request(url)
                with urllib.request.urlopen(req, timeout=30) as resp:
                    return json.loads(resp.read().decode('utf-8'))
            except Exception as e:
                return {"error": str(e)}

    # =========================================================================
    # API CALL LOGGING - Every external call MUST be logged
    # =========================================================================

    def log_api_call(
        self,
        tool: str,
        endpoint: str,
        method: str = "GET",
        request_payload: Optional[Dict] = None,
        response_data: Any = None,
        response_status: int = 200,
        assessment_id: str = None,
        session_id: str = None,
        user_id: str = None,
        duration_ms: int = None
    ) -> Dict[str, Any]:
        """
        Log an external API call to RevAudit.

        EVERY external API call (DataForSEO, OpenAI, Google APIs, etc.)
        MUST be logged here for audit trail.

        Returns:
            Dict with audit_id for claim attribution
        """
        return self._post("/api/audit/log-call", {
            "tool": tool,
            "endpoint": endpoint,
            "method": method,
            "request_payload": request_payload,
            "response_data": response_data,
            "response_status": response_status,
            "called_by_module": self.module_name,
            "assessment_id": assessment_id,
            "session_id": session_id,
            "user_id": user_id,
            "duration_ms": duration_ms
        })

    # =========================================================================
    # CLAIM REGISTRATION - Every data point MUST cite its source
    # =========================================================================

    def register_claim(
        self,
        claim_text: str,
        source_audit_id: str,
        source_field: str,
        source_value: Any,
        claim_type: str = "metric",
        assessment_id: str = None,
        report_section: str = None
    ) -> Dict[str, Any]:
        """
        Register a claim with its source attribution.

        EVERY piece of data in a report MUST be registered here
        to prove it came from a real API call.

        Args:
            claim_text: The statement being made (e.g., "Review rate: 94%")
            source_audit_id: The audit_id from log_api_call()
            source_field: JSON path to the value (e.g., "response.rate")
            source_value: The actual value from the API

        Returns:
            Dict with claim_id and confidence level
        """
        return self._post("/api/audit/register-claim", {
            "claim_text": claim_text,
            "source_audit_id": source_audit_id,
            "source_field": source_field,
            "source_value": source_value,
            "claim_type": claim_type,
            "assessment_id": assessment_id,
            "report_section": report_section
        })

    # =========================================================================
    # HALLUCINATION DETECTION - Block fabricated content
    # =========================================================================

    def validate_content(
        self,
        content: str,
        assessment_id: str = None,
        strict: bool = True
    ) -> Dict[str, Any]:
        """
        Validate content for hallucinations BEFORE output.

        Checks for:
        - Forbidden phrases ("studies show", "experts say", etc.)
        - Numeric claims without citations
        - Unverifiable statements

        Args:
            content: Text to validate
            strict: If True, raises HallucinationError on BLOCKED issues

        Raises:
            HallucinationError: If strict=True and BLOCKED issues found
        """
        result = self._post("/api/audit/validate-content", {
            "content": content,
            "assessment_id": assessment_id,
            "module": self.module_name,
            "strict": strict
        })

        if result.get("error") and "HALLUCINATION" in str(result.get("error", "")):
            raise HallucinationError(result.get("detail", result))

        if strict and not result.get("valid", True):
            blocked = result.get("blocked_issues", [])
            if blocked:
                raise HallucinationError({
                    "severity": "BLOCKED",
                    "reason": blocked[0].get("reason", "Content validation failed"),
                    "issues": blocked
                })

        return result

    def check_text(self, content: str) -> Dict[str, Any]:
        """Quick non-blocking hallucination check."""
        return self._post("/api/audit/check-text", {"content": content})

    # =========================================================================
    # VERIFICATION GATES - User must approve data before reports
    # =========================================================================

    def create_verification_gate(
        self,
        assessment_id: str,
        data_type: str,
        data_snapshot: Dict
    ) -> Optional[str]:
        """
        Create a verification gate requiring user approval.

        User MUST review and approve raw data before report generation.
        """
        result = self._post("/api/audit/verification/create", {
            "assessment_id": assessment_id,
            "data_type": data_type,
            "data_snapshot": data_snapshot
        })
        return result.get("verification_id")

    def approve_verification(
        self,
        verification_id: str,
        user_id: str,
        notes: str = None
    ) -> bool:
        """User approves verification gate."""
        result = self._post("/api/audit/verification/approve", {
            "verification_id": verification_id,
            "user_id": user_id,
            "notes": notes
        })
        return result.get("status") == "approved"

    def can_generate_report(self, assessment_id: str) -> bool:
        """Check if report generation is allowed."""
        result = self._get(f"/api/audit/can-generate-report/{assessment_id}")
        return result.get("can_generate", False)

    # =========================================================================
    # AUDIT TRAIL - Complete provenance for any assessment
    # =========================================================================

    def get_audit_trail(self, assessment_id: str) -> Dict[str, Any]:
        """Get complete audit trail for assessment."""
        return self._get(f"/api/audit/trail/{assessment_id}")

    def get_raw_response(self, audit_id: str) -> Dict[str, Any]:
        """Get the raw API response for an audit record."""
        return self._get(f"/api/audit/raw-response/{audit_id}")


def audit_api_call(tool: str, endpoint: str = None):
    """
    Decorator to automatically audit API calls.

    Usage:
        @audit_api_call("DataForSEO", "/v3/serp/google/organic")
        def call_dataforseo(url, assessment_id=None):
            response = requests.get(...)
            return response.json()

    The decorator will:
    1. Log the API call with request/response
    2. Track duration
    3. Attach audit_id to result dict
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            client = RevAuditClient()
            start_time = time.time()

            assessment_id = kwargs.get('assessment_id')
            session_id = kwargs.get('session_id')
            user_id = kwargs.get('user_id')

            request_payload = {
                "function": func.__name__,
                "args": [str(a)[:200] for a in args],
                "kwargs": {k: str(v)[:200] for k, v in kwargs.items()
                          if k not in ('assessment_id', 'session_id', 'user_id')}
            }

            try:
                result = func(*args, **kwargs)
                duration_ms = int((time.time() - start_time) * 1000)

                audit_record = client.log_api_call(
                    tool=tool,
                    endpoint=endpoint or func.__name__,
                    method="GET",
                    request_payload=request_payload,
                    response_data=result,
                    response_status=200,
                    assessment_id=assessment_id,
                    session_id=session_id,
                    user_id=user_id,
                    duration_ms=duration_ms
                )

                if isinstance(result, dict):
                    result['_audit_id'] = audit_record.get('audit_id')
                    result['_audit_timestamp'] = datetime.utcnow().isoformat()

                return result

            except Exception as e:
                duration_ms = int((time.time() - start_time) * 1000)

                client.log_api_call(
                    tool=tool,
                    endpoint=endpoint or func.__name__,
                    method="GET",
                    request_payload=request_payload,
                    response_data={"error": str(e), "type": type(e).__name__},
                    response_status=500,
                    assessment_id=assessment_id,
                    duration_ms=duration_ms
                )
                raise

        return wrapper
    return decorator


class AuditedAssessment:
    """
    Context manager for fully audited assessments.

    Usage:
        with AuditedAssessment(assessment_id, module="RevScore_IQ") as audit:
            # Log API calls
            result = audit.call_api("DataForSEO", "/serp", response_data)

            # Register claims
            audit.claim(
                "Visibility score: 85%",
                source_audit_id=result['audit_id'],
                source_field="visibility.score",
                source_value=85
            )

            # Validate before report
            audit.validate_report(report_text)
    """

    def __init__(self, assessment_id: str, module: str = None):
        self.assessment_id = assessment_id
        self.client = RevAuditClient(module)
        self.api_calls: List[Dict] = []
        self.claims: List[Dict] = []
        self.start_time = datetime.utcnow()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.api_calls:
            self.client.create_verification_gate(
                assessment_id=self.assessment_id,
                data_type="api_responses",
                data_snapshot={
                    "api_calls": self.api_calls,
                    "claims": self.claims,
                    "started_at": self.start_time.isoformat(),
                    "completed_at": datetime.utcnow().isoformat()
                }
            )
        return False

    def call_api(
        self,
        tool: str,
        endpoint: str,
        response_data: Any,
        request_payload: Dict = None,
        duration_ms: int = None
    ) -> Dict[str, Any]:
        """Log an API call and return audit record."""
        audit_record = self.client.log_api_call(
            tool=tool,
            endpoint=endpoint,
            request_payload=request_payload,
            response_data=response_data,
            assessment_id=self.assessment_id,
            duration_ms=duration_ms
        )

        self.api_calls.append({
            "tool": tool,
            "endpoint": endpoint,
            "audit_id": audit_record.get("audit_id"),
            "timestamp": datetime.utcnow().isoformat()
        })

        return audit_record

    def claim(
        self,
        claim_text: str,
        source_audit_id: str,
        source_field: str,
        source_value: Any,
        report_section: str = None
    ) -> Dict[str, Any]:
        """Register a claim with source attribution."""
        claim_record = self.client.register_claim(
            claim_text=claim_text,
            source_audit_id=source_audit_id,
            source_field=source_field,
            source_value=source_value,
            assessment_id=self.assessment_id,
            report_section=report_section
        )

        self.claims.append({
            "claim_text": claim_text,
            "claim_id": claim_record.get("claim_id"),
            "confidence": claim_record.get("confidence")
        })

        return claim_record

    def validate_report(self, content: str) -> Dict[str, Any]:
        """Validate report content - raises HallucinationError on issues."""
        return self.client.validate_content(
            content=content,
            assessment_id=self.assessment_id,
            strict=True
        )


# Global singleton for quick access
audit_client = RevAuditClient()
