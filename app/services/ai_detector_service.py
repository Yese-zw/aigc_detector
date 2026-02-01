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
        language = "chinese" if language == "zh" else "english"
        
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
        language: str,
        mode: str,
        platform: str
    ) -> Dict[str, Any]:
        """执行实际的文件上传请求"""
        headers = self._update_header_cookie(token)
        if "content-type" in headers:
            del headers["content-type"]
        headers['page-timestamp'] = str(int(time.time()*1000))
        upload_url = f"{settings.AI_DETECTOR_BASE_URL}/document/upload"
        
        files = {'file': (filename, file_content)}
        data = {
            'uuid': uuid,
            'language': language,
            'mode': mode,
            'platform': platform
        }
        
        response = requests.post(
            url=upload_url,
            headers=headers,
            files=files,
            data=data,
            timeout=settings.AI_DETECTOR_TIMEOUT
        )
        response.raise_for_status()
        return response.json()

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