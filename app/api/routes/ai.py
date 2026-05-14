"""Public AI API routes."""

from fastapi import APIRouter, Depends, File, Form, UploadFile

from app.api.dependencies import get_ai_service, get_current_api_key
from app.schemas.common import AIDetectorRequest, AIDetectorResponse, AIRewrite, ErrorResponse
from app.services.ai_service import AIService

router = APIRouter()


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
        500: {"description": "服务器内部错误", "model": ErrorResponse},
    },
)
async def ai_detector(
    request: AIDetectorRequest,
    api_key: str = Depends(get_current_api_key),
    service: AIService = Depends(get_ai_service),
):
    return service.detect(api_key, request.text, request.language)


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
        500: {"description": "服务器内部错误", "model": ErrorResponse},
    },
)
async def ai_rewrite(
    request: AIRewrite,
    api_key: str = Depends(get_current_api_key),
    service: AIService = Depends(get_ai_service),
):
    return service.rewrite(api_key, request.text, request.combination_id)


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
        500: {"description": "服务器内部错误", "model": ErrorResponse},
    },
)
async def upload_file(
    file: UploadFile = File(..., description="上传的文件"),
    uuid: str = Form(..., description="UUID"),
    language: str = Form(..., description="语言"),
    mode: str = Form(..., description="模式"),
    platform: str = Form(..., description="平台"),
    api_key: str = Depends(get_current_api_key),
    service: AIService = Depends(get_ai_service),
):
    file_content = await file.read()
    return service.upload(api_key, file_content, file.filename, uuid, language, mode, platform)


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
        500: {"description": "服务器内部错误", "model": ErrorResponse},
    },
)
async def upload_file_status(
    uuid: str = Form(..., description="UUID"),
    api_key: str = Depends(get_current_api_key),
    service: AIService = Depends(get_ai_service),
):
    return service.document_status(uuid)


@router.get(
    "/quota",
    response_model=AIDetectorResponse,
    summary="查询额度余额",
    description="查询当前 API Key 的可用点数余额",
    responses={
        200: {"description": "查询成功"},
        401: {"description": "未授权，缺少或无效的 API Key", "model": ErrorResponse},
        500: {"description": "服务器内部错误", "model": ErrorResponse},
    },
)
async def get_quota(
    api_key: str = Depends(get_current_api_key),
    service: AIService = Depends(get_ai_service),
):
    return service.quota_info(api_key)


@router.get(
    "/supported",
    response_model=AIDetectorResponse,
    summary="获取支持列表",
    description="获取AI服务支持的语言和模式列表（带 24 小时缓存）",
    responses={200: {"description": "获取成功"}, 500: {"description": "服务器内部错误", "model": ErrorResponse}},
)
async def get_supported(service: AIService = Depends(get_ai_service)):
    return service.supported()
