"""
RevAudit Flask Integration
Anti-hallucination framework for Flask applications
"""

import os
import sys
import json
from functools import wraps

sys.path.insert(0, '/opt/shared-api-engine')

from revaudit.client import RevAuditClient, audit_client
from revaudit.validators import check_for_hallucination


def integrate_revaudit_flask(app, module_name: str, strict_mode: bool = False):
    """
    Integrate RevAudit into a Flask application.

    Args:
        app: Flask application instance
        module_name: Name of the module
        strict_mode: If True, blocks responses with hallucination indicators
    """
    os.environ['REVFLOW_MODULE'] = module_name

    client = RevAuditClient(module_name)

    @app.after_request
    def audit_response(response):
        """Check responses for hallucination indicators."""
        if response.content_type and 'json' in response.content_type:
            try:
                data = json.loads(response.get_data(as_text=True))

                # Extract text content
                text_content = _extract_text(data)
                if text_content:
                    is_clean, detections = check_for_hallucination(text_content)

                    blocked = [d for d in detections if d['severity'] == 'BLOCKED']

                    if blocked and strict_mode:
                        response.set_data(json.dumps({
                            "error": "HALLUCINATION_BLOCKED",
                            "message": "Response contains unverified claims",
                            "detections": blocked
                        }))
                        response.status_code = 422
                    elif detections:
                        response.headers['X-RevAudit-Warning'] = f"{len(detections)} potential issues"

            except Exception as e:
                pass  # Don't block on errors

        return response

    # Add audit endpoints
    @app.route('/audit/status', methods=['GET'])
    def audit_status():
        health = client._get("/health")
        return {
            "module": module_name,
            "revaudit_enabled": True,
            "revaudit_health": health.get("status", "unknown"),
            "strict_mode": strict_mode
        }

    print(f"[RevAudit] ✅ Flask integration complete for {module_name}")
    return client


def _extract_text(data, max_depth=3):
    """Extract text content from response."""
    texts = []

    def extract(obj, depth=0):
        if depth > max_depth:
            return
        if isinstance(obj, str) and len(obj) > 20:
            texts.append(obj)
        elif isinstance(obj, dict):
            for key, value in obj.items():
                if key in ('content', 'text', 'description', 'summary',
                          'recommendation', 'analysis', 'report', 'message'):
                    if isinstance(value, str):
                        texts.append(value)
                    else:
                        extract(value, depth + 1)
        elif isinstance(obj, list):
            for item in obj[:10]:
                extract(item, depth + 1)

    extract(data)
    return " ".join(texts)


# Decorator for audited API calls
def audit_flask_call(tool: str, endpoint: str = None):
    """Decorator to audit Flask route API calls."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            import time
            from flask import request

            start_time = time.time()
            client = RevAuditClient()

            try:
                result = func(*args, **kwargs)
                duration_ms = int((time.time() - start_time) * 1000)

                # Log the call
                client.log_api_call(
                    tool=tool,
                    endpoint=endpoint or request.path,
                    method=request.method,
                    request_payload=dict(request.args),
                    response_data=result if isinstance(result, dict) else None,
                    response_status=200,
                    duration_ms=duration_ms
                )

                return result

            except Exception as e:
                duration_ms = int((time.time() - start_time) * 1000)
                client.log_api_call(
                    tool=tool,
                    endpoint=endpoint or request.path,
                    method=request.method,
                    response_data={"error": str(e)},
                    response_status=500,
                    duration_ms=duration_ms
                )
                raise

        return wrapper
    return decorator
