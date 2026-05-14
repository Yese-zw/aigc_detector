"""API key management routes."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.dependencies import get_api_key_service
from app.schemas.apikey import APIKeyCreate, APIKeyListResponse, APIKeyResponse
from app.services.apikey_service import APIKeyService

router = APIRouter()


@router.post("/create", response_model=APIKeyResponse, summary="创建 API Key", description="创建一个新的 API Key，用于访问检测接口")
async def create_apikey(create_data: APIKeyCreate, service: APIKeyService = Depends(get_api_key_service)):
    return APIKeyResponse(status="success", data=service.create_apikey(create_data), message="API Key 创建成功")


@router.get("/list", response_model=APIKeyListResponse, summary="获取 API Key 列表", description="获取所有 API Key 的列表")
async def list_apikeys(service: APIKeyService = Depends(get_api_key_service)):
    api_keys = service.list_apikeys()
    return APIKeyListResponse(status="success", data=api_keys, total=len(api_keys))


@router.get("/info/{api_key}", response_model=APIKeyResponse, summary="获取 API Key 信息", description="获取指定 API Key 的详细信息")
async def get_apikey_info(api_key: str, service: APIKeyService = Depends(get_api_key_service)):
    key_data = service.get_apikey(api_key)
    if not key_data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API Key 不存在")
    return APIKeyResponse(status="success", data=key_data, message="查询成功")


@router.get("/usage/{api_key}", summary="获取 API Key 使用统计", description="获取指定 API Key 的使用统计信息")
async def get_apikey_usage(api_key: str, service: APIKeyService = Depends(get_api_key_service)):
    stats = service.get_usage_stats(api_key)
    if not stats:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API Key 不存在")
    return {"status": "success", "data": stats}


@router.put("/update/{api_key}", response_model=APIKeyResponse, summary="更新 API Key", description="更新 API Key 的状态、额度等信息")
async def update_apikey(
    api_key: str,
    is_active: Optional[bool] = Query(None, description="是否激活"),
    add_quota: Optional[int] = Query(None, description="增加的额度（字符数）", gt=0),
    name: Optional[str] = Query(None, description="新的名称"),
    description: Optional[str] = Query(None, description="新的描述"),
    service: APIKeyService = Depends(get_api_key_service),
):
    key_data = service.update_apikey(api_key=api_key, is_active=is_active, quota=add_quota, name=name, description=description)
    if not key_data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API Key 不存在")
    return APIKeyResponse(status="success", data=key_data, message="更新成功")


@router.delete("/delete/{api_key}", summary="删除 API Key", description="删除指定的 API Key")
async def delete_apikey(api_key: str, service: APIKeyService = Depends(get_api_key_service)):
    if not service.delete_apikey(api_key):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API Key 不存在")
    return {"status": "success", "message": "API Key 已删除"}
