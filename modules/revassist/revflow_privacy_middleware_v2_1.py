"""
revflow_privacy_middleware_v2_1.py
---------------------------------
Autoloadable middleware for RevHome Assessment Engine v2
Injects RevFlow Privacy Enforcement Guardrails at runtime.
"""

import re
import yaml
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

# Load configuration from YAML manifest if available
CONFIG_PATH = "/etc/revflow/revflow_privacy_enforcement_v2_1.yaml"

try:
    with open(CONFIG_PATH, "r") as f:
        config = yaml.safe_load(f)
except Exception:
    config = {"active": True, "policy": "default"}


# --- Privacy Logic ---------------------------------------------------------

def privacy_sentinel(user_query: str) -> str | None:
    """Detects prompt extraction or configuration probing attempts."""
    if not user_query:
        return None
    q = user_query.lower()
    banned = ["prompt", "developer", "system", "config", "backend", "instruction"]
    if any(term in q for term in banned):
        return "I can’t share the exact internal prompt. It’s private system data."
    return None


def enforce_privacy_guardrails(user_query: str, model_response: str) -> str:
    """Cleans output that may leak sensitive information."""
    guard = privacy_sentinel(user_query)
    if guard:
        return guard
    if re.search(r"(prompt|developer|instruction|config)", model_response, re.I):
        return "⚠️ Privacy Policy Triggered: Internal data cannot be shared."
    return model_response


# --- FastAPI Middleware ----------------------------------------------------

class RevFlowPrivacyMiddleware(BaseHTTPMiddleware):
    """Intercepts requests and responses for privacy enforcement."""

    async def dispatch(self, request: Request, call_next):
        try:
            # Read request payload
            body = await request.json()
            user_query = str(body)  # full payload context
        except Exception:
            user_query = ""

        # Process request
        response = await call_next(request)

        # Enforce privacy on JSON responses only
        if hasattr(response, "body_iterator"):
            content = b"".join([chunk async for chunk in response.body_iterator])
            try:
                decoded = content.decode("utf-8")
                safe_content = enforce_privacy_guardrails(user_query, decoded)
                return JSONResponse(content=safe_content)
            except Exception:
                return response
        return response


def attach_privacy_middleware(app):
    """Attach this middleware to any FastAPI app."""
    app.add_middleware(RevFlowPrivacyMiddleware)
    return app
