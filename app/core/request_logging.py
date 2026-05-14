"""HTTP request logging middleware."""

import time
import uuid

from fastapi import Request
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import Response

from app.core.logger import logger
from app.core.request_context import (
    get_request_log_context,
    reset_request_log_context,
    set_request_log_context,
)


REQUEST_ID_HEADER = "X-Request-ID"


async def request_logging_middleware(request: Request, call_next: RequestResponseEndpoint) -> Response:
    request_id = request.headers.get(REQUEST_ID_HEADER) or uuid.uuid4().hex
    token = set_request_log_context(request_id)
    start_time = time.perf_counter()
    status_code = 500

    try:
        response = await call_next(request)
        status_code = response.status_code
        response.headers[REQUEST_ID_HEADER] = request_id
        return response
    finally:
        duration_ms = (time.perf_counter() - start_time) * 1000
        context = get_request_log_context()
        api_key_name = context.api_key_name if context else "-"
        quota_used = context.quota_used if context else 0
        logger.info(
            "request_id=%s path=%s duration_ms=%.2f status_code=%s api_key_name=%s quota_used=%s",
            request_id,
            request.url.path,
            duration_ms,
            status_code,
            api_key_name,
            quota_used,
        )
        reset_request_log_context(token)
