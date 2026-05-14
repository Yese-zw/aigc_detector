"""FastAPI dependency providers."""

from typing import Optional

from fastapi import Header, HTTPException, Request, status

from app.clients.lingsi import LingsiClient
from app.clients.upstream_ai import UpstreamAIClient
from app.core.config import settings
from app.core.logger import logger
from app.core.request_context import set_api_key_name
from app.services.admin_service import AdminService
from app.services.ai_service import AIService
from app.services.apikey_service import APIKeyService
from app.services.document_service import DocumentService
from app.services.template_service import TemplateService

COOKIE_NAME = "admin_access_token"


def get_api_key_service() -> APIKeyService:
    return APIKeyService()


def get_document_service() -> DocumentService:
    return DocumentService()


def get_upstream_client() -> UpstreamAIClient:
    return UpstreamAIClient()


def get_lingsi_client() -> LingsiClient:
    return LingsiClient()


def get_ai_service() -> AIService:
    return AIService(
        upstream_client=get_upstream_client(),
        api_key_service=get_api_key_service(),
        document_service=get_document_service(),
    )


def get_admin_service() -> AdminService:
    return AdminService(
        api_key_service=get_api_key_service(),
        upstream_client=get_upstream_client(),
        lingsi_client=get_lingsi_client(),
    )


def get_template_service() -> TemplateService:
    import os

    template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
    return TemplateService(template_dir)


async def get_current_api_key(x_api_key: Optional[str] = Header(None, alias="X-API-Key")) -> str:
    if not x_api_key:
        logger.warning("缺少 API Key")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="缺少 API Key，请在请求头中提供 X-API-Key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    key_data = get_api_key_service().get_apikey(x_api_key)
    if not key_data:
        logger.warning("无效的 API Key")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的 API Key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    if not key_data.is_active:
        set_api_key_name(key_data.name)
        logger.warning(f"API Key 已禁用: {key_data.name}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="API Key 已禁用")
    set_api_key_name(key_data.name)
    return x_api_key


def verify_cookie(request: Request) -> bool:
    return request.cookies.get(COOKIE_NAME) == settings.ADMIN_PASSWORD


def verify_bearer_token(request: Request) -> bool:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return False
    return auth_header[7:].strip() == settings.ADMIN_PASSWORD


async def require_admin(request: Request) -> None:
    if not verify_bearer_token(request) and not verify_cookie(request):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
