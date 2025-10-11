"""
API Key management endpoints
API密钥管理接口
"""
from typing import Optional
from fastapi import APIRouter, HTTPException, status, Query

from app.models.apikey import (
    APIKeyCreate,
    APIKeyResponse,
    APIKeyListResponse,
    APIKey
)
from app.services.apikey_service import APIKeyService
from app.core.logger import logger


router = APIRouter()

# 初始化 API Key 服务
apikey_service = APIKeyService()


@router.post(
    "/create",
    response_model=APIKeyResponse,
    summary="创建 API Key",
    description="创建一个新的 API Key，用于访问检测接口"
)
async def create_apikey(create_data: APIKeyCreate):
    """
    创建新的 API Key
    
    - **name**: API Key 名称（必需）
    - **quota**: 总额度，单位：字符数（必需）
    - **description**: 描述信息（可选）
    """
    try:
        logger.info("=" * 70)
        logger.info(f"📝 创建API Key请求 - 名称: {create_data.name}, 额度: {create_data.quota}")
        
        key_data = apikey_service.create_apikey(create_data)
        
        logger.info(f"✓ API Key 创建成功 - Key: {key_data.key[:20]}...")
        logger.info("=" * 70)
        
        return APIKeyResponse(
            status="success",
            data=key_data,
            message="API Key 创建成功"
        )
    
    except Exception as e:
        logger.error(f"✗ 创建 API Key 失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建失败: {str(e)}"
        )


@router.get(
    "/list",
    response_model=APIKeyListResponse,
    summary="获取 API Key 列表",
    description="获取所有 API Key 的列表"
)
async def list_apikeys():
    """获取所有 API Key 列表"""
    try:
        api_keys = apikey_service.list_apikeys()
        
        logger.info(f"📋 查询API Key列表 - 共 {len(api_keys)} 个")
        
        return APIKeyListResponse(
            status="success",
            data=api_keys,
            total=len(api_keys)
        )
    
    except Exception as e:
        logger.error(f"✗ 查询 API Key 列表失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"查询失败: {str(e)}"
        )


@router.get(
    "/info/{api_key}",
    response_model=APIKeyResponse,
    summary="获取 API Key 信息",
    description="获取指定 API Key 的详细信息"
)
async def get_apikey_info(api_key: str):
    """获取 API Key 详细信息"""
    try:
        key_data = apikey_service.get_apikey(api_key)
        
        if not key_data:
            logger.warning(f"⚠️ API Key 不存在: {api_key[:10]}...")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API Key 不存在"
            )
        
        logger.info(f"📊 查询API Key信息 - 名称: {key_data.name}")
        
        return APIKeyResponse(
            status="success",
            data=key_data,
            message="查询成功"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"✗ 查询 API Key 信息失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"查询失败: {str(e)}"
        )


@router.get(
    "/usage/{api_key}",
    summary="获取 API Key 使用统计",
    description="获取指定 API Key 的使用统计信息"
)
async def get_apikey_usage(api_key: str):
    """获取 API Key 使用统计"""
    try:
        stats = apikey_service.get_usage_stats(api_key)
        
        if not stats:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API Key 不存在"
            )
        
        logger.info(f"📊 查询API Key使用统计 - 名称: {stats['name']}")
        
        return {
            "status": "success",
            "data": stats
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"✗ 查询使用统计失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"查询失败: {str(e)}"
        )


@router.put(
    "/update/{api_key}",
    response_model=APIKeyResponse,
    summary="更新 API Key",
    description="更新 API Key 的状态、额度等信息"
)
async def update_apikey(
    api_key: str,
    is_active: Optional[bool] = Query(None, description="是否激活"),
    add_quota: Optional[int] = Query(None, description="增加的额度（字符数）", gt=0),
    name: Optional[str] = Query(None, description="新的名称"),
    description: Optional[str] = Query(None, description="新的描述")
):
    """
    更新 API Key 信息
    
    - **is_active**: 是否激活（可选）
    - **add_quota**: 增加的额度（可选，会累加到现有额度）
    - **name**: 新的名称（可选）
    - **description**: 新的描述（可选）
    """
    try:
        key_data = apikey_service.update_apikey(
            api_key=api_key,
            is_active=is_active,
            quota=add_quota,
            name=name,
            description=description
        )
        
        if not key_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API Key 不存在"
            )
        
        logger.info(f"✓ API Key 更新成功 - 名称: {key_data.name}")
        
        return APIKeyResponse(
            status="success",
            data=key_data,
            message="更新成功"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"✗ 更新 API Key 失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新失败: {str(e)}"
        )


@router.delete(
    "/delete/{api_key}",
    summary="删除 API Key",
    description="删除指定的 API Key"
)
async def delete_apikey(api_key: str):
    """删除 API Key"""
    try:
        success = apikey_service.delete_apikey(api_key)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API Key 不存在"
            )
        
        logger.info(f"✓ API Key 删除成功")
        
        return {
            "status": "success",
            "message": "API Key 已删除"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"✗ 删除 API Key 失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除失败: {str(e)}"
        )

