"""
API endpoints
API路由端点
"""
from fastapi import APIRouter, HTTPException, status, Depends, UploadFile, File, Form
from app.models.schemas import (
    AIRewrite,
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
        
        # 先检查额度是否足够（不扣除）
        if not key_data or key_data.quota < text_length:
            logger.error(f"✗ 额度不足: 剩余 {key_data.quota if key_data else 0}, 需要 {text_length}")
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=f"额度不足，剩余: {key_data.quota if key_data else 0} 字符，需要: {text_length} 字符"
            )
        
        # 先执行检测（在扣除额度之前）
        result = ai_detector_service.aigccheck(
            text=request.text,
            language=request.language
        )
        
        # 检测成功后才扣除额度
        verification_result = apikey_service.verify_and_consume_quota(api_key, text_length)
        
        if not verification_result["valid"]:
            # 理论上不应该到这里，因为前面已经检查过了
            logger.warning(f"⚠️ 额度扣除失败: {verification_result['message']}")
        
        logger.info(f"✓ 检测完成")
        logger.info(f"   📊 扣除额度: {text_length}")
        logger.info(f"   💰 剩余额度: {verification_result.get('remaining_quota', key_data.quota - text_length)}")
        logger.info("=" * 70)
        
        # 返回响应，包含额度信息
        return AIDetectorResponse(
            status="success",
            result=result,
            message=None,
            quota_info=QuotaInfo(
                used=text_length,
                remaining=verification_result.get("remaining_quota", key_data.quota - text_length)
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


@router.post(
    "/AIRewrite",
    response_model=AIDetectorResponse,
    summary="AI文本改写",
    description="改写文本",
    responses={
        200: {"description": "检测成功"},
        400: {"description": "请求参数错误", "model": ErrorResponse},
        401: {"description": "未授权，缺少或无效的 API Key", "model": ErrorResponse},
        402: {"description": "额度不足", "model": ErrorResponse},
        500: {"description": "服务器内部错误", "model": ErrorResponse}
    }
)
async def ai_rewrite(
        request: AIRewrite,
        api_key: str = Depends(get_current_api_key)
):
    """
    AI文本改写接口（需要 API Key）

    - **text**: 待改写的文本内容
    - **combination_id**: 改写组合

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
        logger.info(f"📥 收到改写请求")
        logger.info(f"   🔑 API Key: {key_data.name if key_data else '未知'}")
        logger.info(f"   🌐 组合: {request.combination_id}")
        logger.info(f"   📏 文本长度: {text_length} 字符")
        logger.info(f"   💰 剩余额度: {key_data.quota if key_data else 0}")

        # 先检查额度是否足够（不扣除）
        if not key_data or key_data.quota < text_length:
            logger.error(f"✗ 额度不足: 剩余 {key_data.quota if key_data else 0}, 需要 {text_length}")
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=f"额度不足，剩余: {key_data.quota if key_data else 0} 字符，需要: {text_length} 字符"
            )

        # 先执行改写（在扣除额度之前）
        result = ai_detector_service.aigcrewrite(
            text=request.text,
            combination_id=request.combination_id
        )

        # 改写成功后才扣除额度
        verification_result = apikey_service.verify_and_consume_quota(api_key, text_length)

        if not verification_result["valid"]:
            # 理论上不应该到这里，因为前面已经检查过了
            logger.warning(f"⚠️ 额度扣除失败: {verification_result['message']}")

        logger.info(f"✓ 改写完成")
        logger.info(f"   📊 扣除额度: {text_length}")
        logger.info(f"   💰 剩余额度: {verification_result.get('remaining_quota', key_data.quota - text_length)}")
        logger.info("=" * 70)

        # 返回响应，包含额度信息
        return AIDetectorResponse(
            status="success",
            result=result,
            message=None,
            quota_info=QuotaInfo(
                used=text_length,
                remaining=verification_result.get("remaining_quota", key_data.quota - text_length)
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


@router.post(
    "/upload",
    response_model=AIDetectorResponse,
    summary="文件上传",
    description="上传文件到AI服务（需要 API Key 认证）",
    responses={
        200: {"description": "上传成功"},
        400: {"description": "请求参数错误", "model": ErrorResponse},
        401: {"description": "未授权，缺少或无效的 API Key", "model": ErrorResponse},
        402: {"description": "额度不足", "model": ErrorResponse},
        500: {"description": "服务器内部错误", "model": ErrorResponse}
    }
)
async def upload_file(
    file: UploadFile = File(..., description="上传的文件"),
    uuid: str = Form(..., description="UUID"),
    language: str = Form(..., description="语言"),
    mode: str = Form(..., description="模式"),
    platform: str = Form(..., description="平台"),
    api_key: str = Depends(get_current_api_key)
):
    """
    文件上传接口（需要 API Key）
    
    - **file**: 上传的文件（必需）
    - **uuid**: UUID（必需）
    - **language**: 语言（必需）
    - **mode**: 模式（必需）
    - **platform**: 平台（必需）
    
    **认证方式：**
    在请求头中添加 `X-API-Key: your_api_key`
    
    **额度消耗：**
    每次请求会消耗文件大小对应的额度（按 KB 计算，1KB = 1000 额度）
    """
    try:
        # 读取文件内容
        file_content = await file.read()
        file_size_kb = len(file_content) / 1024  # 转换为 KB

        try:
            text_content = file_content.decode("utf-8")  # 解码为字符串
        except UnicodeDecodeError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="文件编码错误，仅支持UTF-8编码的文本文件"
            )

        import re
        # 正则匹配所有Unicode文字（包括中文、英文、数字等，排除空格和标点）
        words = re.findall(r'\w', text_content)  # \w 匹配 [a-zA-Z0-9_]，如需保留中文可调整为 [\u4e00-\u9fa5a-zA-Z0-9]
        quota_cost = len(words)
        

        
        # 获取 API Key 信息
        key_data = apikey_service.get_apikey(api_key)
        
        logger.info("=" * 70)
        logger.info(f"📤 收到文件上传请求")
        logger.info(f"   🔑 API Key: {key_data.name if key_data else '未知'}")
        logger.info(f"   📁 文件名: {file.filename}")
        logger.info(f"   📏 文件大小: {file_size_kb:.2f} KB")
        logger.info(f"   💰 需要额度: {quota_cost}")
        logger.info(f"   💰 剩余额度: {key_data.quota if key_data else 0}")
        logger.info(f"   🌐 语言: {language}")
        logger.info(f"   🔧 模式: {mode}")
        logger.info(f"   📱 平台: {platform}")
        logger.info(f"   🆔 UUID: {uuid}")
        
        # 先检查额度是否足够（不扣除）
        if not key_data or key_data.quota < quota_cost:
            logger.error(f"✗ 额度不足: 剩余 {key_data.quota if key_data else 0}, 需要 {quota_cost}")
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=f"额度不足，剩余: {key_data.quota if key_data else 0}，需要: {quota_cost}"
            )
        
        # 先执行上传（在扣除额度之前）
        result = ai_detector_service.upload_file(
            file_content=file_content,
            filename=file.filename,
            uuid=uuid,
            language=language,
            mode=mode,
            platform=platform
        )
        
        # 上传成功后才扣除额度
        verification_result = apikey_service.verify_and_consume_quota(api_key, quota_cost)
        
        if not verification_result["valid"]:
            # 理论上不应该到这里，因为前面已经检查过了
            logger.warning(f"⚠️ 额度扣除失败: {verification_result['message']}")
        
        logger.info(f"✓ 上传完成")
        logger.info(f"   📊 扣除额度: {quota_cost}")
        logger.info(f"   💰 剩余额度: {verification_result.get('remaining_quota', key_data.quota - quota_cost)}")
        logger.info("=" * 70)
        
        # 返回响应，包含额度信息
        return AIDetectorResponse(
            status="success",
            result=result,
            message=None,
            quota_info=QuotaInfo(
                used=quota_cost,
                remaining=verification_result.get("remaining_quota", key_data.quota - quota_cost)
            )
        )
    
    except HTTPException:
        raise
    
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
        logger.error(f"上传请求失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"文件上传失败: {str(e)}"
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


@router.post(
    "/status_file",
    response_model=AIDetectorResponse,
    summary="文件状态查询",
    description="上传文件到AI服务（需要 API Key 认证）",
    responses={
        200: {"description": "查询成功"},
        400: {"description": "请求参数错误", "model": ErrorResponse},
        401: {"description": "未授权，缺少或无效的 API Key", "model": ErrorResponse},
        402: {"description": "额度不足", "model": ErrorResponse},
        500: {"description": "服务器内部错误", "model": ErrorResponse}
    }
)
async def upload_file(
        uuid: str = Form(..., description="UUID"),
        api_key: str = Depends(get_current_api_key)
):
    """
    文件上传接口（需要 API Key）

    - **uuid**: UUID（必需）

    **认证方式：**
    在请求头中添加 `X-API-Key: your_api_key`

    **额度消耗：**
    每次请求会消耗文件大小对应的额度（按 KB 计算，1KB = 1000 额度）
    """
    try:

        logger.info("=" * 70)
        logger.info(f"📤 收到文件查询请求")
        logger.info(f"   🆔 UUID: {uuid}")

        # 先执行上传（在扣除额度之前）
        result = ai_detector_service.file_status(
            uuid=uuid,
        )
        logger.info(f"✓ 查询完成")
        logger.info("=" * 70)

        # 返回响应，包含额度信息
        return AIDetectorResponse(
            status="success",
            result=result,
            message=None,
        )

    except HTTPException:
        raise

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