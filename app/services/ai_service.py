"""Business service for public AI APIs."""

from typing import Any, Callable

from fastapi import HTTPException, status

from app.clients.upstream_ai import UpstreamAIClient
from app.core.logger import logger
from app.schemas.common import AIDetectorResponse
from app.services.apikey_service import APIKeyService
from app.services.document_service import DocumentService
from app.services.quota_service import QuotaService


class AIService:
    double_quota_combinations = {"30", "31", "32", "33", "34", "35", "36", "37", "38", "39", "60", "61", "62"}

    def __init__(
        self,
        upstream_client: UpstreamAIClient,
        api_key_service: APIKeyService,
        document_service: DocumentService,
    ):
        self.upstream = upstream_client
        self.api_keys = api_key_service
        self.documents = document_service
        self.quota = QuotaService(api_key_service)

    def detect(self, api_key: str, text: str, language: str) -> AIDetectorResponse:
        return self._run_billable_operation(
            api_key=api_key,
            cost=len(text),
            upstream_call=lambda: self.upstream.detect_text(text, language),
            error_detail_template="AI检测服务返回错误: {message}",
        )

    def rewrite(self, api_key: str, text: str, combination_id: str) -> AIDetectorResponse:
        real_combination_id = self.normalize_combination_id(combination_id)
        cost = len(text) * (2 if real_combination_id in self.double_quota_combinations else 1)
        return self._run_billable_operation(
            api_key=api_key,
            cost=cost,
            upstream_call=lambda: self.upstream.rewrite_text(text, real_combination_id),
            error_detail_template="AI改写服务返回错误: {message}",
        )

    def upload(
        self,
        api_key: str,
        file_content: bytes,
        filename: str,
        uuid: str,
        language: str,
        mode: str,
        platform: str,
    ) -> AIDetectorResponse:
        text = self.documents.extract_text(file_content, filename)
        cost = self.documents.upload_quota_cost(text, mode)
        return self._run_billable_operation(
            api_key=api_key,
            cost=cost,
            upstream_call=lambda: self.upstream.upload_document(file_content, filename, language, mode, platform),
            error_detail_template="文件处理失败: {message}",
            quota_unit="",
        )

    def document_status(self, uuid: str) -> AIDetectorResponse:
        return AIDetectorResponse(status="success", result=self.upstream.document_status(uuid), message=None)

    def quota_info(self, api_key: str) -> AIDetectorResponse:
        key_data = self.api_keys.get_apikey(api_key)
        quota = key_data.quota if key_data else 0
        return AIDetectorResponse(
            status="success",
            result={"quota": quota},
            message=None,
            quota_info={"used": 0, "remaining": quota},
        )

    def supported(self) -> AIDetectorResponse:
        return AIDetectorResponse(status="success", result=self.upstream.supported_data(), message=None)

    def normalize_combination_id(self, combination_id: str) -> str:
        try:
            value = int(combination_id)
            return str(value - 10000 if value > 10000 else value)
        except ValueError:
            return str(combination_id)

    def _run_billable_operation(
        self,
        api_key: str,
        cost: int,
        upstream_call: Callable[[], dict[str, Any]],
        error_detail_template: str,
        quota_unit: str = " 字符",
    ) -> AIDetectorResponse:
        key_data = self.quota.ensure_enough(api_key, cost, quota_unit)
        result = upstream_call()
        if result.get("code") != 200:
            logger.error(f"上游服务返回错误: {result}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=error_detail_template.format(message=result.get("msg", "未知错误")),
            )

        quota_info = self.quota.consume_after_success(api_key, cost, key_data.quota - cost)
        return AIDetectorResponse(status="success", result=result, message=None, quota_info=quota_info)
