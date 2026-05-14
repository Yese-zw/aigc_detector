"""Per-request logging context."""

from contextvars import ContextVar
from dataclasses import dataclass


@dataclass
class RequestLogContext:
    request_id: str
    api_key_name: str = "-"
    quota_used: int = 0


_request_log_context: ContextVar[RequestLogContext | None] = ContextVar("request_log_context", default=None)


def set_request_log_context(request_id: str):
    return _request_log_context.set(RequestLogContext(request_id=request_id))


def reset_request_log_context(token) -> None:
    _request_log_context.reset(token)


def get_request_log_context() -> RequestLogContext | None:
    return _request_log_context.get()


def set_api_key_name(name: str) -> None:
    context = get_request_log_context()
    if context:
        context.api_key_name = name or "-"


def add_quota_used(amount: int) -> None:
    context = get_request_log_context()
    if context:
        context.quota_used += max(amount, 0)
