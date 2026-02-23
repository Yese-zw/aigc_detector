"""
AI Detector Service
AI检测服务核心业务逻辑
"""
import requests
import json
import time
from typing import Optional, Dict, Any
from app.core.config import settings
from app.core.logger import logger
from app.core.redis_client import get_redis_client
from app.core.exceptions import (
    DetectionFailedException,
    AuthExpiredException
)
from app.services.notification_service import notification_service

# 映射文件后缀到正确的Content-Type（确保和浏览器一致）
FILE_CONTENT_TYPE_MAP = {
    'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'doc': 'application/msword',
    'pdf': 'application/pdf',
    'txt': 'text/plain',
    'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
}


class AIDetectorService:
    """AI检测服务类"""
    
    def __init__(self):
        self.redis_key = settings.REDIS_AUTH_KEY
        self.redis_client = get_redis_client()
        logger.info("AI检测服务初始化 (Key托管模式)")
    
    def _init_base_headers(self) -> Dict[str, str]:
        """初始化基础请求头"""
        return {
            "authority": "xrzbk.lanbeike.online",
            "method": "POST",
            "scheme": "https",
            "accept": "application/json, text/plain, */*",
            "accept-encoding": "gzip, deflate, br, zstd",
            "accept-language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
            "content-type": "application/json",
            "origin": "https://ai.lanbeike.online",
            "priority": "u=1, i",
            "referer": "https://ai.lanbeike.online/",
            "sec-ch-ua": '"Not(A:Brand";v="8", "Chromium";v="144", "Microsoft Edge";v="144"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-site",
            "user-agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/144.0.0.0 Safari/537.36 Edg/144.0.0.0"
            ),
        }
    
    def _get_shared_auth(self) -> Optional[str]:
        """从Redis获取共享的登录态 (Bearer Token)"""
        try:
            token = self.redis_client.get(self.redis_key)
            if token:
                # 如果是bytes类型（redis Python客户端默认根据decode_responses决定），确保是str
                if isinstance(token, bytes):
                    return token.decode('utf-8')
                return str(token)
        except Exception as e:
            logger.error(f"从Redis获取登录态失败: {str(e)}")
        return None


    
    def _update_header_cookie(self, token: Optional[str]) -> Dict[str, str]:
        """用登录态更新请求头"""
        headers = self._init_base_headers()
        
        if token:
            # 使用Authorization头传递Token
            headers["authorization"] = f"Bearer {token}"
            # 同时保留Cookie以防万一，但根据抓包来看主要是Authorization
            # headers["cookie"] = f"Bearer {token}"
            
        return headers
    
    def _check_auth_and_notify(self) -> str:
        """检查登录态，如果无效则发送通知并抛出异常"""
        token = self._get_shared_auth()
        if not token:
            logger.error("✗ 未找到有效登录态，触发过期通知")
            notification_service.send_auth_expired_email()
            raise AuthExpiredException()
        return token
    
    def aigccheck(self, text: str, language: str) -> Dict[str, Any]:
        """执行AI检测"""

        # 检查Auth
        auth_info = self._check_auth_and_notify()
        
        try:
            logger.info(f"📝 执行检测 - 语言: {language}, 文本长度: {len(text)}")
            result = self._do_aigccheck_request(auth_info, text, language)
            logger.info(f"✓ 检测完成")
            return result
            
        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code in [401, 403]:
                logger.error(f"✗ AI检测认证失败 (401/403)")
                notification_service.send_auth_expired_email()
                raise AuthExpiredException()
            elif e.response is not None and e.response.status_code in [502, 503, 504]:
                logger.error(f"✗ 上游服务器错误 ({e.response.status_code})")
                raise DetectionFailedException(f"上游服务器暂时不可用 ({e.response.status_code})")
            else:
                logger.error(f"✗ AI检测请求失败: {str(e)}")
                raise DetectionFailedException(str(e))
                
        except Exception as e:
            logger.error(f"✗ AI检测未知错误: {str(e)}")
            raise DetectionFailedException(str(e))
    
    def _do_aigccheck_request(self, token: str, text: str, language: str) -> Dict[str, Any]:
        """执行实际的检测请求"""
        headers = self._update_header_cookie(token)
        headers["content-type"] = "application/json"
        
        detector_url = f"{settings.AI_DETECTOR_BASE_URL}/aigc/detect"
        json_data = {"content": text,"language": language}
        headers["content-length"] = str(len(str(json_data)))
        
        response = requests.post(
            url=detector_url,
            headers=headers,
            json=json_data,
            timeout=settings.AI_DETECTOR_TIMEOUT
        )
        response.raise_for_status()
        return response.json()
    

    def aigcrewrite(self, text: str, combination_id: str) -> Dict[str, Any]:
        """执行AI改写"""
        # 检查Auth
        auth_info = self._check_auth_and_notify()
        
        try:
            logger.info(f"📝 执行改写 - 组合: {combination_id}, 文本长度: {len(text)}")
            result = self._do_aigcrewrite_request(auth_info, text, combination_id)
            logger.info(f"✓ 改写完成")
            return result
            
        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code in [401, 403]:
                logger.error(f"✗ AI改写认证失败 (401/403)")
                notification_service.send_auth_expired_email()
                raise AuthExpiredException()
            elif e.response is not None and e.response.status_code in [502, 503, 504]:
                raise DetectionFailedException(f"服务器暂时不可用 ({e.response.status_code})")
            else:
                raise DetectionFailedException(str(e))
        except Exception as e:
            logger.error(f"✗ AI改写错误: {str(e)}")
            raise DetectionFailedException(str(e))

    def _do_aigcrewrite_request(self, token: str, text: str, combination_id: str) -> Dict[str, Any]:
        """执行实际的改写请求"""
        headers = self._update_header_cookie(token)
        headers["content-type"] = "application/json"

        detector_url = f"{settings.AI_DETECTOR_BASE_URL}/text/rewrite"
        json_data = {"text": text, "combinationId": combination_id,  "saveHistory": False}
        headers['page-timestamp'] = str(int(time.time()*1000))
        headers["content-length"] = str(len(str(json_data)))
        print(headers)
        response = requests.post(
            url=detector_url,
            headers=headers,
            json=json_data,
            timeout=settings.AI_DETECTOR_TIMEOUT
        )
        print(response.json())
        response.raise_for_status()
        return response.json()
    
    def upload_file(
        self,
        file_content: bytes,
        filename: str,
        uuid: str,
        language: str,
        mode: str,
        platform: str
    ) -> Dict[str, Any]:
        """上传文件到AI检测服务"""
        auth_info = self._check_auth_and_notify()
        
        try:
            logger.info(f"📤 执行文件上传 - 文件: {filename}")
            result = self._do_upload_request(auth_info, file_content, filename, uuid, language, mode, platform)
            logger.info(f"✓ 上传完成")
            return result
        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code in [401, 403]:
                logger.error(f"✗ 文件上传认证失败 (401/403)")
                notification_service.send_auth_expired_email()
                raise AuthExpiredException()
            elif e.response is not None and e.response.status_code in [502, 503, 504]:
                raise DetectionFailedException(f"服务器暂时不可用 ({e.response.status_code})")
            else:
                raise DetectionFailedException(str(e))
        except Exception as e:
            logger.error(f"✗ 文件上传错误: {str(e)}")
            raise DetectionFailedException(str(e))

    def _do_upload_request(
            self,
            token: str,
            file_content: bytes,
            filename: str,
            uuid: str,
            language: str,  # 允许传zh/en，内部自动映射为数字
            mode: str,  # 必须传数字字符串，如"1"
            platform: str  # 必须传数字字符串，如"1"
    ) -> Dict[str, Any]:
        """执行实际的文件上传请求（自动映射语言标识为数字）"""
        try:
            # 2. 核心：将语言标识（如zh）映射为服务器预期的数字字符串

            # 构建请求头
            headers = self._update_header_cookie(token)
            headers.pop("content-type", None)
            headers['page-timestamp'] = str(int(time.time() * 1000))
            upload_url = f"{settings.AI_DETECTOR_BASE_URL}/document/upload"

            # 构建文件参数
            file_suffix = filename.split('.')[-1].lower() if '.' in filename else ''
            file_type = FILE_CONTENT_TYPE_MAP.get(file_suffix, 'application/octet-stream')
            files = {
                'file': (filename, file_content, file_type)
            }

            # 3. 校验并构建表单数据（最终传给服务器的都是数字字符串）
            # 待校验的参数：languageId（已映射）、modeId、platformId
            params_to_check = {
                'languageId': language,
                'modeId': mode,
                'platformId': platform
            }
            # 统一校验所有参数是否为数字字符串
            for param_name, param_value in params_to_check.items():
                if not param_value.isdigit():
                    raise ValueError(f"{param_name}必须传数字字符串！当前值：{param_value}")

            data = {
                'uuid': uuid,
                'languageId': language,  # 映射后的数字（如1）
                'modeId': mode,
                'platformId': platform
            }

            # 打印请求详情
            logger.info(f"【最终上传请求】")
            logger.info(f"URL: {upload_url}")
            logger.info(f"文件信息：{filename} | {file_type} | {len(file_content)}字节")
            logger.info(f"表单数据：{data}")

            # 发送请求
            response = requests.post(
                url=upload_url,
                headers=headers,
                files=files,
                data=data,
                timeout=settings.AI_DETECTOR_TIMEOUT,
                verify=True
            )

            logger.info(f"响应状态码：{response.status_code}")
            logger.info(f"响应内容：{response.text}")

            response.raise_for_status()
            return response.json()

        except ValueError as e:
            logger.error(f"参数校验失败：{e}")
            raise
        except requests.exceptions.HTTPError as e:
            logger.error(f"上传请求失败：{e}，响应内容：{response.text if 'response' in locals() else '无'}")
            raise Exception(f"AI检测请求失败：{e}")
        except requests.exceptions.RequestException as e:
            logger.error(f"网络异常：{e}")
            raise Exception(f"上传请求网络异常：{e}")
        except Exception as e:
            logger.error(f"上传未知错误：{e}", exc_info=True)
            raise

    def file_status(self, uuid: str) -> Dict[str, Any]:
        """查询文件状态"""
        auth_info = self._check_auth_and_notify()
        
        try:
            logger.info(f"Checking file status - uuid: {uuid}")
            result = self._do_upload_status_request(auth_info, uuid)
            return result
        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code in [401, 403]:
                logger.error(f"✗ 文件状态查询认证失败")
                notification_service.send_auth_expired_email()
                raise AuthExpiredException()
            elif e.response is not None and e.response.status_code in [502, 503, 504]:
                raise DetectionFailedException(f"服务器暂时不可用 ({e.response.status_code})")
            else:
                raise DetectionFailedException(str(e))
        except Exception as e:
            logger.error(f"✗ 文件状态查询错误: {str(e)}")
            raise DetectionFailedException(str(e))

    def _do_upload_status_request(self, token: str, uuid: str) -> Dict[str, Any]:
        """执行实际的文件状态查询请求"""
        headers = self._update_header_cookie(token)
        if "content-type" in headers:
            del headers["content-type"]
        headers['page-timestamp'] = str(int(time.time() * 1000))
        upload_url = f"{settings.AI_DETECTOR_BASE_URL}/document/status/{uuid}"

        response = requests.get(
            url=upload_url,
            headers=headers,
            timeout=settings.AI_DETECTOR_TIMEOUT
        )
        response.raise_for_status()
        return response.json()

    def get_supported_data(self) -> Dict[str, Any]:
        """获取并缓存支持列表"""
        cache_key = "supported_data_cache"
        try:
            # 尝试从缓存获取
            cached_data = self.redis_client.get(cache_key)
            if cached_data:
                logger.info("✓ 从缓存获取支持列表")
                return json.loads(cached_data) if isinstance(cached_data, str) else json.loads(cached_data.decode('utf-8'))
            
            # 缓存不存在，发起请求
            logger.info("📝 发起请求获取支持列表")
            url = "https://api.lanbeike.online/api/supported"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # 保存到缓存，24 小时 (86400 秒)
            self.redis_client.setex(cache_key, 86400, json.dumps(data, ensure_ascii=False))
            logger.info("✓ 支持列表已保存到缓存 (24h)")
            
            return data
        except Exception as e:
            logger.error(f"✗ 获取支持列表失败: {str(e)}")
            raise DetectionFailedException(f"获取支持列表失败: {str(e)}")