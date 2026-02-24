"""
RevAudit Integration for RevScore IQ (Module 2)
Anti-Hallucination Framework Integration

Every API call is logged. Every claim is attributed.
Zero tolerance for fabricated data.
"""

import os
import json
import time
import hashlib
import httpx
from typing import Dict, Any, Optional, Callable
from functools import wraps
from datetime import datetime


REVAUDIT_URL = os.getenv('REVAUDIT_URL', 'http://localhost:8710')


class RevAuditClient:
    """
    Client for RevAudit Anti-Hallucination Framework.

    Provides:
    - API call logging with full payloads
    - Claim registration with source attribution
    - Hallucination detection before report generation
    - Verification gate management
    """

    def __init__(self, module_name: str = "MODULE_2_RevScore_IQ"):
        self.module_name = module_name
        self.base_url = REVAUDIT_URL
        self._client = httpx.Client(timeout=30.0)

    def log_api_call(
        self,
        tool: str,
        endpoint: str,
        method: str = "GET",
        request_payload: Optional[Dict] = None,
        response_data: Any = None,
        response_status: int = 200,
        assessment_id: str = None,
        duration_ms: int = None
    ) -> Dict[str, Any]:
        """
        Log an external API call to RevAudit.

        Returns audit record with audit_id for claim attribution.
        """
        try:
            response = self._client.post(
                f"{self.base_url}/api/audit/log-call",
                json={
                    "tool": tool,
                    "endpoint": endpoint,
                    "method": method,
                    "request_payload": request_payload,
                    "response_data": response_data,
                    "response_status": response_status,
                    "called_by_module": self.module_name,
                    "assessment_id": assessment_id,
                    "duration_ms": duration_ms
                }
            )
            return response.json()
        except Exception as e:
            print(f"[RevAudit] Failed to log API call: {e}")
            return {"logged": False, "error": str(e)}

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
        Register a claim with source attribution.

        Every claim in a report must call this to prove it has a source.
        """
        try:
            response = self._client.post(
                f"{self.base_url}/api/audit/register-claim",
                json={
                    "claim_text": claim_text,
                    "source_audit_id": source_audit_id,
                    "source_field": source_field,
                    "source_value": source_value,
                    "claim_type": claim_type,
                    "assessment_id": assessment_id,
                    "report_section": report_section
                }
            )
            return response.json()
        except Exception as e:
            print(f"[RevAudit] Failed to register claim: {e}")
            return {"verified": False, "error": str(e)}

    def validate_content(
        self,
        content: str,
        assessment_id: str = None,
        strict: bool = True
    ) -> Dict[str, Any]:
        """
        Validate content for hallucinations before report generation.

        If strict=True, will raise exception on BLOCKED issues.
        """
        try:
            response = self._client.post(
                f"{self.base_url}/api/audit/validate-content",
                json={
                    "content": content,
                    "assessment_id": assessment_id,
                    "module": self.module_name,
                    "strict": strict
                }
            )
            if response.status_code == 422:
                # Hallucination detected
                data = response.json()
                raise HallucinationError(data.get("detail", {}))
            return response.json()
        except HallucinationError:
            raise
        except Exception as e:
            print(f"[RevAudit] Failed to validate content: {e}")
            return {"valid": False, "error": str(e)}

    def check_text(self, content: str) -> Dict[str, Any]:
        """Quick non-blocking hallucination check."""
        try:
            response = self._client.post(
                f"{self.base_url}/api/audit/check-text",
                json={"content": content}
            )
            return response.json()
        except Exception as e:
            return {"is_clean": False, "error": str(e)}

    def create_verification_gate(
        self,
        assessment_id: str,
        data_type: str,
        data_snapshot: Dict
    ) -> Optional[str]:
        """
        Create a verification gate that user must approve.

        Returns verification_id for tracking.
        """
        try:
            response = self._client.post(
                f"{self.base_url}/api/audit/verification/create",
                json={
                    "assessment_id": assessment_id,
                    "data_type": data_type,
                    "data_snapshot": data_snapshot
                }
            )
            return response.json().get("verification_id")
        except Exception as e:
            print(f"[RevAudit] Failed to create verification gate: {e}")
            return None

    def can_generate_report(self, assessment_id: str) -> bool:
        """Check if report generation is allowed for assessment."""
        try:
            response = self._client.get(
                f"{self.base_url}/api/audit/can-generate-report/{assessment_id}"
            )
            return response.json().get("can_generate", False)
        except Exception as e:
            print(f"[RevAudit] Failed to check report status: {e}")
            return False

    def get_audit_trail(self, assessment_id: str) -> Dict[str, Any]:
        """Get complete audit trail for assessment."""
        try:
            response = self._client.get(
                f"{self.base_url}/api/audit/trail/{assessment_id}"
            )
            return response.json()
        except Exception as e:
            return {"error": str(e)}


class HallucinationError(Exception):
    """Raised when hallucination is detected in content."""
    def __init__(self, details: Dict):
        self.details = details
        super().__init__(f"Hallucination detected: {details.get('reason', 'Unknown')}")


def audit_api_call(tool: str, endpoint: str = None):
    """
    Decorator to automatically audit API calls.

    Usage:
        @audit_api_call("DataForSEO", "/v3/serp/google/organic")
        def call_dataforseo(url, assessment_id):
            response = requests.get(...)
            return response.json()
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            audit_client = RevAuditClient()
            start_time = time.time()

            # Extract assessment_id from kwargs if present
            assessment_id = kwargs.get('assessment_id')

            # Build request payload from args/kwargs
            request_payload = {
                "args": [str(a) for a in args],
                "kwargs": {k: str(v) for k, v in kwargs.items() if k != 'assessment_id'}
            }

            try:
                # Call the actual function
                result = func(*args, **kwargs)
                duration_ms = int((time.time() - start_time) * 1000)

                # Log successful call
                audit_record = audit_client.log_api_call(
                    tool=tool,
                    endpoint=endpoint or func.__name__,
                    method="GET",
                    request_payload=request_payload,
                    response_data=result,
                    response_status=200,
                    assessment_id=assessment_id,
                    duration_ms=duration_ms
                )

                # Attach audit_id to result if it's a dict
                if isinstance(result, dict):
                    result['_audit_id'] = audit_record.get('audit_id')

                return result

            except Exception as e:
                duration_ms = int((time.time() - start_time) * 1000)

                # Log failed call
                audit_client.log_api_call(
                    tool=tool,
                    endpoint=endpoint or func.__name__,
                    method="GET",
                    request_payload=request_payload,
                    response_data={"error": str(e)},
                    response_status=500,
                    assessment_id=assessment_id,
                    duration_ms=duration_ms
                )
                raise

        return wrapper
    return decorator


class AuditedAssessment:
    """
    Context manager for audited assessments.

    Ensures all API calls are logged and claims are attributed.

    Usage:
        with AuditedAssessment(assessment_id) as audit:
            # Make API calls
            result = audit.call_api("DataForSEO", endpoint, response)

            # Register claims
            audit.claim("Score: 85%", result['_audit_id'], "score", 85)

            # Validate before report
            audit.validate_report(report_content)
    """

    def __init__(self, assessment_id: str):
        self.assessment_id = assessment_id
        self.client = RevAuditClient()
        self.api_calls = []
        self.claims = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Create verification gate with all collected data
        if self.api_calls:
            self.client.create_verification_gate(
                assessment_id=self.assessment_id,
                data_type="api_responses",
                data_snapshot={
                    "api_calls": self.api_calls,
                    "claims": self.claims,
                    "collected_at": datetime.utcnow().isoformat()
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
            "source_audit_id": source_audit_id
        })

        return claim_record

    def validate_report(self, content: str, strict: bool = True) -> Dict[str, Any]:
        """Validate report content before generation."""
        return self.client.validate_content(
            content=content,
            assessment_id=self.assessment_id,
            strict=strict
        )


# Singleton client for quick access
audit_client = RevAuditClient()
