import time
from typing import Any, Dict, Optional, Tuple

from fastapi import Header, HTTPException, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from starlette.responses import Response as StarletteResponse

# In-memory LRU/TTL store for Idempotency keys (24 hours = 86400 seconds)
# Key: (org_id_or_ip, idempotency_key) -> (status_code, headers, body_bytes, timestamp)
_IDEMPOTENCY_STORE: Dict[str, Tuple[int, Dict[str, str], bytes, float]] = {}
TTL_SECONDS = 86400  # 24 hours


class IdempotencyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Only check idempotency on mutating methods (POST, PUT, PATCH, DELETE)
        if request.method not in ("POST", "PUT", "PATCH", "DELETE"):
            return await call_next(request)

        idempotency_key = request.headers.get("idempotency-key")
        if not idempotency_key:
            return await call_next(request)

        client_host = request.client.host if request.client else "unknown"
        cache_key = f"{client_host}:{idempotency_key}"
        now = time.time()

        # Check if cached and not expired
        if cache_key in _IDEMPOTENCY_STORE:
            status_code, headers, body_bytes, cached_at = _IDEMPOTENCY_STORE[cache_key]
            if now - cached_at < TTL_SECONDS:
                resp = StarletteResponse(
                    content=body_bytes,
                    status_code=status_code,
                    headers={**headers, "X-Cache-Lookup": "HIT-IDEMPOTENT"}
                )
                return resp
            else:
                del _IDEMPOTENCY_STORE[cache_key]

        # Execute request
        response = await call_next(request)

        # Cache successful responses (2xx and 4xx, but not 5xx)
        if response.status_code < 500:
            response_body = [chunk async for chunk in response.body_iterator]
            body_bytes = b"".join(response_body)

            headers_dict = dict(response.headers)
            _IDEMPOTENCY_STORE[cache_key] = (response.status_code, headers_dict, body_bytes, now)

            return StarletteResponse(
                content=body_bytes,
                status_code=response.status_code,
                headers=headers_dict,
                media_type=response.media_type
            )

        return response
