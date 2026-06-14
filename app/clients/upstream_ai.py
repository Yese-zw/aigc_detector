"""Client for xrz.cntcn.com upstream APIs."""

import json
import time
from typing import Any, Optional

import requests

from app.clients.redis import get_redis_client
from app.core.config import settings
from app.core.exceptions import AuthExpiredException, DetectionFailedException
from app.core.logger import logger

FILE_CONTENT_TYPE_MAP = {
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "doc": "application/msword",
    "pdf": "application/pdf",
    "txt": "text/plain",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}
AUTH_ERROR_CODES = {401, 104, 1001, 1002, 1003}


class UpstreamAIClient:
    def __init__(self):
        self.redis = get_redis_client()

    def detect_text(self, text: str, language: str) -> dict[str, Any]:
        return self._request_with_retry(
            "POST",
            "/api/aigc/detect",
            json={"content": text, "language": language},
            timeout=settings.AI_DETECTOR_TIMEOUT,
        )

    def rewrite_text(self, text: str, combination_id: str) -> dict[str, Any]:
        return self._request_with_retry(
            "POST",
            "/api/text/rewrite",
            json={"text": text, "combinationId": combination_id, "saveHistory": False},
            headers=self._timestamp_header(),
            timeout=settings.AI_DETECTOR_TIMEOUT,
        )

    def upload_document(
        self,
        file_content: bytes,
        filename: str,
        language: str,
        mode: str,
        platform: str,
    ) -> dict[str, Any]:
        self._validate_upload_params(language, mode, platform)
        suffix = filename.split(".")[-1].lower() if "." in filename else ""
        content_type = FILE_CONTENT_TYPE_MAP.get(suffix, "application/octet-stream")
        file_size = len(file_content)
        headers = self._timestamp_header()

        policy = self._request_with_retry(
            "POST",
            "/api/document/direct-upload/policy",
            json={"filename": filename, "fileSize": file_size, "contentType": content_type},
            headers=headers,
            timeout=settings.AI_DETECTOR_TIMEOUT,
        )
        if policy.get("code") != 200:
            raise DetectionFailedException(f"获取上传policy失败: {policy}")

        data = policy.get("data", {})
        self._upload_to_oss(data, filename, file_content, content_type)
        return self._request_with_retry(
            "POST",
            "/api/document/direct-upload/commit",
            json={
                "uuid": data.get("uuid"),
                "objectKey": data.get("objectKey"),
                "originalFilename": filename,
                "fileSize": file_size,
                "contentType": content_type,
                "languageId": int(language),
                "modeId": int(mode),
                "platformId": int(platform),
            },
            headers=headers,
            timeout=settings.AI_DETECTOR_TIMEOUT,
        )

    def document_status(self, uuid: str) -> dict[str, Any]:
        return self._request_with_retry(
            "GET",
            f"/api/document/status/{uuid}",
            headers=self._timestamp_header(),
            timeout=settings.AI_DETECTOR_TIMEOUT,
        )

    def supported_data(self) -> dict[str, Any]:
        cached_data = self.redis.get("supported_data_cache")
        if cached_data:
            return json.loads(cached_data if isinstance(cached_data, str) else cached_data.decode("utf-8"))
        return cached_data

    def wxlogin_start(self) -> dict[str, Any]:
        response = requests.post(
            f"{settings.AI_DETECTOR_BASE_URL}/wxlogin/start",
            headers=self._browser_headers(content_type=True),
            timeout=settings.AI_DETECTOR_TIMEOUT,
            verify=settings.AI_DETECTOR_VERIFY_SSL,
        )
        return response.json()

    def wxlogin_status(self, request_id: str) -> dict[str, Any]:
        response = requests.get(
            f"{settings.AI_DETECTOR_BASE_URL}/wxlogin/status",
            headers=self._browser_headers(),
            params={"request_id": request_id},
            timeout=settings.AI_DETECTOR_TIMEOUT,
            verify=settings.AI_DETECTOR_VERIFY_SSL,
        )
        return response.json()

    def _request_with_retry(self, method: str, path: str, **kwargs) -> dict[str, Any]:
        extra_headers = kwargs.pop("headers", None)
        token = self._get_token()

        try:
            return self._request_once(method, path, token, extra_headers, **kwargs)
        except requests.exceptions.HTTPError as exc:
            if not self._is_auth_error(exc):
                raise DetectionFailedException(str(exc))
            logger.warning("检测到 Token 失效，刷新并重试")
            return self._request_once(method, path, self._login(), extra_headers, **kwargs)

    def _request_once(
        self,
        method: str,
        path: str,
        token: str,
        extra_headers: Optional[dict[str, str]] = None,
        **kwargs,
    ) -> dict[str, Any]:
        response = requests.request(
            method,
            f"{settings.AI_DETECTOR_BASE_URL}{path}",
            headers=self._auth_headers(token, extra_headers),
            verify=settings.AI_DETECTOR_VERIFY_SSL,
            **kwargs,
        )
        response.raise_for_status()
        payload = response.json()
        logger.info(payload)
        if payload.get("code") in AUTH_ERROR_CODES:
            raise requests.exceptions.HTTPError("Business auth failed", response=response)
        return payload

    def _get_token(self) -> str:
        token = self.redis.get(settings.REDIS_AUTH_KEY)
        if token:
            return token.decode("utf-8") if isinstance(token, bytes) else str(token)
        return self._login()

    def _login(self) -> str:
        response = requests.post(
            f"{settings.AI_DETECTOR_BASE_URL}/api/index/user/emailLogin",
            headers=self._browser_headers(content_type=True),
            json={"email": settings.UPSTREAM_EMAIL, "password": settings.UPSTREAM_PASSWORD},
            timeout=settings.LOGIN_TIMEOUT,
            verify=settings.AI_DETECTOR_VERIFY_SSL,
        )
        response.raise_for_status()
        payload = response.json()
        token = payload.get("data", {}).get("token")
        if payload.get("code") != 200 or not token:
            raise AuthExpiredException(f"上游登录失败: {payload.get('msg', '未知登录错误')}")
        self.redis.setex(settings.REDIS_AUTH_KEY, settings.AUTH_EXPIRE_SECONDS, token)
        return token

    def _upload_to_oss(self, policy_data: dict[str, Any], filename: str, file_content: bytes, content_type: str) -> None:
        form_data = policy_data.get("formData", {})
        response = requests.post(
            url=policy_data.get("host"),
            data={
                "key": form_data.get("key"),
                "policy": form_data.get("policy"),
                "OSSAccessKeyId": form_data.get("OSSAccessKeyId"),
                "Signature": form_data.get("Signature"),
                "success_action_status": form_data.get("success_action_status"),
            },
            files={"file": (filename, file_content, content_type)},
            timeout=settings.AI_DETECTOR_TIMEOUT,
            verify=True,
        )
        response.raise_for_status()

    def _validate_upload_params(self, language: str, mode: str, platform: str) -> None:
        for name, value in {"languageId": language, "modeId": mode, "platformId": platform}.items():
            if not str(value).isdigit():
                raise ValueError(f"{name}必须传数字字符串！当前值：{value}")

    def _auth_headers(self, token: str, extra_headers: Optional[dict[str, str]]) -> dict[str, str]:
        headers = self._browser_headers(content_type=True)
        if extra_headers:
            headers.update(extra_headers)
        headers["authorization"] = f"Bearer {token}"
        headers.pop("content-length", None)
        return headers

    def _browser_headers(self, content_type: bool = False) -> dict[str, str]:
        headers = {
            "authority": "https://ai.lanbeike.online",
            "accept": "application/json, text/plain, */*",
            "accept-language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
            "origin": "https://ai.lanbeike.online",
            "referer": "https://ai.lanbeike.online/",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36 Edg/144.0.0.0",
            "sec-ch-ua": '"Not(A:Brand";v="8", "Chromium";v="144", "Microsoft Edge";v="144"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-site",
        }
        if content_type:
            headers["content-type"] = "application/json"
        return headers

    def _timestamp_header(self) -> dict[str, str]:
        return {"page-timestamp": str(int(time.time() * 1000))}

    def _is_auth_error(self, exc: requests.exceptions.HTTPError) -> bool:
        response = exc.response
        if response is None:
            return False
        if response.status_code in [401, 403]:
            return True
        try:
            return response.json().get("code") in AUTH_ERROR_CODES
        except Exception:
            return False
