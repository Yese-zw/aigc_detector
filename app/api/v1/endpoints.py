"""
API endpoints
API路由端点
"""
from fastapi import APIRouter, HTTPException, status, Depends
from app.models.schemas import (
    AIDetectorRequest,
    AIDetectorResponse,
    QuotaInfo,
    HealthCheckResponse,
    ErrorResponse
)
from app.services.ai_detector_service import AIDetectorService
from app.services.apikey_service import APIKeyService
from app.core.logger import logger
from app.core.auth import get_current_api_key
from app.core.exceptions import (
    AllAccountsFailedException,
    DetectionFailedException,
    InvalidLanguageException,
    RedisConnectionException
)
from app.core.redis_client import get_redis_client
from app import __version__

router = APIRouter()

# 初始化服务（单例）
ai_detector_service = AIDetectorService()
apikey_service = APIKeyService()


@router.get(
    "/health",
    response_model=HealthCheckResponse,
    summary="健康检查",
    description="检查服务和Redis连接状态"
)
async def health_check():
    """健康检查接口"""
    redis_connected = False
    try:
        redis_client = get_redis_client()
        redis_client.ping()
        redis_connected = True
    except Exception as e:
        logger.warning(f"Redis连接检查失败: {str(e)}")
    
    return HealthCheckResponse(
        status="healthy" if redis_connected else "degraded",
        version=__version__,
        redis_connected=redis_connected
    )


@router.post(
    "/detector",
    response_model=AIDetectorResponse,
    summary="AI文本检测",
    description="检测文本是否为AI生成内容（需要 API Key 认证）",
    responses={
        200: {"description": "检测成功"},
        400: {"description": "请求参数错误", "model": ErrorResponse},
        401: {"description": "未授权，缺少或无效的 API Key", "model": ErrorResponse},
        402: {"description": "额度不足", "model": ErrorResponse},
        500: {"description": "服务器内部错误", "model": ErrorResponse}
    }
)
async def ai_detector(
    request: AIDetectorRequest,
    api_key: str = Depends(get_current_api_key)
):
    """
    AI文本检测接口（需要 API Key）
    
    - **text**: 待检测的文本内容
    - **language**: 文本语言类型，支持 zh（中文）或 en（英文）
    
    **认证方式：**
    在请求头中添加 `X-API-Key: your_api_key`
    
    **额度消耗：**
    每次请求会消耗文本长度对应的额度（字符数）
    """
    try:
        text_length = len(request.text)
        
        # 获取 API Key 信息
        key_data = apikey_service.get_apikey(api_key)
        
        logger.info("=" * 70)
        logger.info(f"📥 收到检测请求")
        logger.info(f"   🔑 API Key: {key_data.name if key_data else '未知'}")
        logger.info(f"   🌐 语言: {request.language}")
        logger.info(f"   📏 文本长度: {text_length} 字符")
        logger.info(f"   💰 剩余额度: {key_data.quota if key_data else 0}")
        
        # 验证并扣减额度
        verification_result = apikey_service.verify_and_consume_quota(api_key, text_length)
        
        if not verification_result["valid"]:
            logger.error(f"✗ 额度验证失败: {verification_result['message']}")
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=verification_result["message"]
            )
        
        # 执行检测
        result = ai_detector_service.detect(
            text=request.text,
            language=request.language
        )
        
        logger.info(f"✓ 检测完成")
        logger.info(f"   📊 扣除额度: {text_length}")
        logger.info(f"   💰 剩余额度: {verification_result['remaining_quota']}")
        logger.info("=" * 70)
        
        # 返回响应，包含额度信息
        return AIDetectorResponse(
            status="success",
            result=result,
            message=None,
            quota_info=QuotaInfo(
                used=text_length,
                remaining=verification_result["remaining_quota"]
            )
        )
    
    except InvalidLanguageException as e:
        logger.warning(f"语言类型错误: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    except AllAccountsFailedException as e:
        logger.error(f"所有账号均登录失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="所有账号均登录失败，请稍后重试"
        )
    
    except DetectionFailedException as e:
        logger.error(f"检测请求失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI检测请求失败: {str(e)}"
        )
    
    except RedisConnectionException as e:
        logger.error(f"Redis连接失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="缓存服务连接失败，请稍后重试"
        )
    
    except Exception as e:
        logger.error(f"未知错误: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="服务器内部错误"
        )

