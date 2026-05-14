"""Quota checking and consumption."""

from app.core.exceptions import QuotaExceededException
from app.core.request_context import add_quota_used
from app.schemas.common import QuotaInfo
from app.services.apikey_service import APIKeyService


class QuotaService:
    def __init__(self, api_key_service: APIKeyService):
        self.api_key_service = api_key_service

    def ensure_enough(self, api_key: str, cost: int, unit: str = " 字符"):
        key_data = self.api_key_service.get_apikey(api_key)
        if not key_data or key_data.quota < cost:
            raise QuotaExceededException(key_data.quota if key_data else 0, cost, unit)
        return key_data

    def consume_after_success(self, api_key: str, cost: int, fallback_remaining: int) -> QuotaInfo:
        result = self.api_key_service.verify_and_consume_quota(api_key, cost)
        add_quota_used(cost)
        return QuotaInfo(used=cost, remaining=result.get("remaining_quota", fallback_remaining))
