"""
RevAudit FastAPI Middleware
Auto-validates all responses for hallucinations
"""

import time
import json
from typing import Callable
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse

from .client import RevAuditClient, HallucinationError


class AuditMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware that automatically:
    1. Logs all API responses
    2. Validates JSON responses for hallucinations
    3. Blocks responses with forbidden phrases

    Usage:
        from revaudit import AuditMiddleware

        app = FastAPI()
        app.add_middleware(AuditMiddleware)
    """

    def __init__(
        self,
        app,
        module_name: str = None,
        validate_responses: bool = True,
        strict_mode: bool = False,
        exempt_paths: list = None
    ):
        super().__init__(app)
        self.client = RevAuditClient(module_name)
        self.validate_responses = validate_responses
        self.strict_mode = strict_mode
        self.exempt_paths = exempt_paths or [
            "/health",
            "/docs",
            "/openapi.json",
            "/redoc",
            "/favicon.ico"
        ]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip exempt paths
        if any(request.url.path.startswith(p) for p in self.exempt_paths):
            return await call_next(request)

        start_time = time.time()

        # Get response
        response = await call_next(request)

        duration_ms = int((time.time() - start_time) * 1000)

        # Only validate JSON responses
        if self.validate_responses and response.headers.get("content-type", "").startswith("application/json"):
            try:
                # Read response body
                body = b""
                async for chunk in response.body_iterator:
                    body += chunk

                # Parse JSON
                try:
                    response_data = json.loads(body.decode())
                except json.JSONDecodeError:
                    response_data = body.decode()

                # Check for hallucinations in response
                if isinstance(response_data, dict):
                    text_to_check = self._extract_text_content(response_data)
                    if text_to_check:
                        check_result = self.client.check_text(text_to_check)

                        if not check_result.get("is_clean", True):
                            detections = check_result.get("detections", [])
                            blocked = [d for d in detections if d.get("severity") == "BLOCKED"]

                            if blocked and self.strict_mode:
                                return JSONResponse(
                                    status_code=422,
                                    content={
                                        "error": "HALLUCINATION_BLOCKED",
                                        "message": "Response contains unverified claims",
                                        "detections": blocked
                                    }
                                )

                            # Add warning header if not strict
                            if detections:
                                response.headers["X-RevAudit-Warning"] = f"{len(detections)} potential issues detected"

                # Rebuild response with original body
                return Response(
                    content=body,
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    media_type=response.media_type
                )

            except Exception as e:
                # Don't block on middleware errors, just log
                print(f"[RevAudit Middleware] Error: {e}")
                return Response(
                    content=body if 'body' in dir() else b"",
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    media_type=response.media_type
                )

        return response

    def _extract_text_content(self, data: dict, max_depth: int = 3) -> str:
        """Extract text content from response for validation."""
        texts = []

        def extract(obj, depth=0):
            if depth > max_depth:
                return

            if isinstance(obj, str) and len(obj) > 20:
                texts.append(obj)
            elif isinstance(obj, dict):
                for key, value in obj.items():
                    # Focus on content-like fields
                    if key in ('content', 'text', 'description', 'summary',
                              'recommendation', 'analysis', 'report', 'message',
                              'findings', 'conclusion', 'explanation'):
                        if isinstance(value, str):
                            texts.append(value)
                        else:
                            extract(value, depth + 1)
            elif isinstance(obj, list):
                for item in obj[:10]:  # Limit list scanning
                    extract(item, depth + 1)

        extract(data)
        return " ".join(texts)
