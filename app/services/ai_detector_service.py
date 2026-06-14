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
    
    def _login(self) -> str:
        """从上游获取新的Token并存入Redis"""
        try:
            logger.info(f"🔄 正在尝试自动登录到上游服务: {settings.UPSTREAM_EMAIL}")
            url = f"{settings.AI_DETECTOR_BASE_URL}/index/user/emailLogin"
            
            headers = self._init_base_headers()
            headers.update({
                "accept": "application/json, text/plain, */*",
                "content-type": "application/json",
                "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36"
            })
            
            data = {
                "email": settings.UPSTREAM_EMAIL,
                "password": settings.UPSTREAM_PASSWORD
            }
            
            response = requests.post(url, headers=headers, json=data, timeout=settings.LOGIN_TIMEOUT)
            response.raise_for_status()
            res_json = response.json()
            
            if res_json.get("code") == 200:
                token = res_json.get("data", {}).get("token")
                if token:
                    # 存入 Redis，设置较长的过期时间（例如 6 小时）
                    self.redis_client.setex(self.redis_key, settings.AUTH_EXPIRE_SECONDS, token)
                    logger.info("✅ 自动登录成功，Token 已保存至 Redis")
                    return token
            
            error_msg = res_json.get("msg", "未知登录错误")
            logger.error(f"❌ 自动登录失败: {error_msg}")
            raise AuthExpiredException(f"上游登录失败: {error_msg}")
            
        except Exception as e:
            logger.error(f"❌ 自动登录过程出错: {str(e)}")
            raise AuthExpiredException(f"自动登录出错: {str(e)}")

    def _get_shared_auth(self) -> str:
        """从Redis获取共享的登录态，如果缺失则尝试登录"""
        try:
            token = self.redis_client.get(self.redis_key)
            if token:
                if isinstance(token, bytes):
                    return token.decode('utf-8')
                return str(token)
            
            # 如果 Redis 中没有 Token，尝试登录
            return self._login()
            
        except AuthExpiredException:
            raise
        except Exception as e:
            logger.error(f"从Redis获取登录态失败: {str(e)}")
            # 即使 Redis 报错，也尝试登录一次
            return self._login()


    
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
        """检查登录态，如果无效则由于 _get_shared_auth 会尝试登录，这里通常能拿到"""
        token = self._get_shared_auth()
        if not token:
            logger.error("✗ 无法获取有效登录态")
            raise AuthExpiredException()
        return token

    def _request_with_retry(self, method: str, url: str, **kwargs) -> Dict[str, Any]:
        """封装请求逻辑，支持 Token 过期自动重试"""
        token = self._get_shared_auth()
        
        # 内部执行函数
        def do_req(current_token):
            # 更新请求头中的 token
            if "headers" not in kwargs:
                kwargs["headers"] = self._update_header_cookie(current_token)
            else:
                kwargs["headers"].update(self._update_header_cookie(current_token))
            
            # 确保 content-length 如果手动传了要删除，让 requests 自动处理
            if "content-length" in kwargs["headers"]:
                del kwargs["headers"]["content-length"]
                
            response = requests.request(method, url, **kwargs)
            # 如果是 401/403，直接抛出 HTTPError 触发重试逻辑
            response.raise_for_status()
            
            res_json = response.json()
            
            # 检查业务逻辑上的 token 失效 (部分接口 200 状态码但 code 为 401/104)
            # 根据抓包分析代码判断失效
            if res_json.get("code") in [401, 104, 1001, 1002, 1003]:  # 104 为多地登录导致失效
                raise requests.exceptions.HTTPError("Business auth failed", response=response)
                
            return res_json

        try:
            # 第一次尝试
            return do_req(token)
        except (requests.exceptions.HTTPError, AuthExpiredException) as e:
            # 判断是否涉及权限/Token 问题
            is_auth_error = False
            if isinstance(e, AuthExpiredException):
                is_auth_error = True
            elif hasattr(e, 'response') and e.response is not None:
                if e.response.status_code in [401, 403]:
                    is_auth_error = True
                else:
                    try:
                        res = e.response.json()
                        if res.get("code") in [401, 104, 1001, 1002, 1003]:
                            is_auth_error = True
                    except:
                        pass
            
            if is_auth_error:
                logger.warning("⚠️ 检测到 Token 可能失效，正在尝试刷新并重试...")
                new_token = self._login()
                # 使用新 token 再次尝试
                # 重新构造 headers 以免复用旧的
                if "headers" in kwargs:
                    del kwargs["headers"] 
                return do_req(new_token)
            else:
                # 其他 HTTP 错误直接抛出
                raise
    
    def aigccheck(self, text: str, language: str) -> Dict[str, Any]:
        """执行AI检测"""

        # 检查Auth
        auth_info = self._check_auth_and_notify()
        
        try:
            result = self._do_aigccheck_request(auth_info, text, language)
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
        """使用封装的重试机制执行检测请求"""
        detector_url = f"{settings.AI_DETECTOR_BASE_URL}/aigc/detect"
        json_data = {"content": text, "language": language}
        
        # 注意：这里不再直接用 token 参数，因为 _request_with_retry 会自己打理
        return self._request_with_retry(
            method="POST",
            url=detector_url,
            json=json_data,
            timeout=settings.AI_DETECTOR_TIMEOUT
        )
    

    def aigcrewrite(self, text: str, combination_id: str) -> Dict[str, Any]:
        """执行AI改写"""
        # 检查Auth
        auth_info = self._check_auth_and_notify()
        
        try:
            result = self._do_aigcrewrite_request(auth_info, text, combination_id)
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
        """使用封装的重试机制执行改写请求"""
        detector_url = f"{settings.AI_DETECTOR_BASE_URL}/text/rewrite"
        json_data = {"text": text, "combinationId": combination_id, "saveHistory": False}
        
        extra_headers = {
            'page-timestamp': str(int(time.time() * 1000))
        }
        
        return self._request_with_retry(
            method="POST",
            url=detector_url,
            json=json_data,
            headers=extra_headers,
            timeout=settings.AI_DETECTOR_TIMEOUT
        )
    
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
            result = self._do_upload_request(auth_info, file_content, filename, uuid, language, mode, platform)
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
            # 统一校验所有参数是否为数字字符串
            params_to_check = {
                'languageId': language,
                'modeId': mode,
                'platformId': platform
            }
            for param_name, param_value in params_to_check.items():
                if not param_value.isdigit():
                    raise ValueError(f"{param_name}必须传数字字符串！当前值：{param_value}")

            # 1. 获取上传 policy
            policy_url = f"{settings.AI_DETECTOR_BASE_URL}/document/direct-upload/policy"
            
            file_suffix = filename.split('.')[-1].lower() if '.' in filename else ''
            file_type = FILE_CONTENT_TYPE_MAP.get(file_suffix, 'application/octet-stream')
            file_size = len(file_content)
            
            policy_request_data = {
                "filename": filename,
                "fileSize": file_size,
                "contentType": file_type
            }
            
            extra_headers = {
                'page-timestamp': str(int(time.time() * 1000))
            }

            # logger.info(f"【第一步】请求上传 policy")
            policy_res_json = self._request_with_retry(
                method="POST",
                url=policy_url,
                json=policy_request_data,
                headers=extra_headers,
                timeout=settings.AI_DETECTOR_TIMEOUT
            )
            
            if policy_res_json.get("code") != 200:
                raise Exception(f"获取上传policy失败: {policy_res_json}")
                
            res_data = policy_res_json.get("data", {})
            remote_uuid = res_data.get("uuid")
            oss_host = res_data.get("host")
            object_key = res_data.get("objectKey")
            form_data = res_data.get("formData", {})

            # 2. 上传文件到 OSS
            # logger.info(f"【第二步】上传文件到 OSS")
            logger.info(f"Host: {oss_host}")
            
            oss_data = {
                "key": form_data.get("key"),
                "policy": form_data.get("policy"),
                "OSSAccessKeyId": form_data.get("OSSAccessKeyId"),
                "Signature": form_data.get("Signature"),
                "success_action_status": form_data.get("success_action_status")
            }
            oss_files = {
                "file": (filename, file_content, file_type)
            }
            
            oss_response = requests.post(
                url=oss_host,
                data=oss_data,
                files=oss_files,
                timeout=settings.AI_DETECTOR_TIMEOUT,
                verify=True
            )
            oss_response.raise_for_status()
            logger.info(f"OSS上传成功，状态码: {oss_response.status_code}")

            # 3. 提交上传 commit
            commit_url = f"{settings.AI_DETECTOR_BASE_URL}/document/direct-upload/commit"
            commit_request_data = {
                "uuid": remote_uuid,
                "objectKey": object_key,
                "originalFilename": filename,
                "fileSize": file_size,
                "contentType": file_type,
                "languageId": int(language),
                "modeId": int(mode),
                "platformId": int(platform)
            }

            # logger.info(f"【第三步】请求上传 commit")
            commit_res_json = self._request_with_retry(
                method="POST",
                url=commit_url,
                json=commit_request_data,
                headers=extra_headers,
                timeout=settings.AI_DETECTOR_TIMEOUT
            )
            
            return commit_res_json

        except ValueError as e:
            logger.error(f"参数校验失败：{e}")
            raise
        except requests.exceptions.HTTPError as e:
            logger.error(f"上传请求失败：{e}，响应内容：{e.response.text if e.response else '无'}")
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
        """使用封装的重试机制执行文件状态查询请求"""
        upload_url = f"{settings.AI_DETECTOR_BASE_URL}/document/status/{uuid}"
        
        extra_headers = {
            'page-timestamp': str(int(time.time() * 1000))
        }

        return self._request_with_retry(
            method="GET",
            url=upload_url,
            headers=extra_headers,
            timeout=settings.AI_DETECTOR_TIMEOUT
        )

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
            response = requests.get(url, timeout=settings.AI_DETECTOR_TIMEOUT)
            response.raise_for_status()
            data = response.json()
            
            # 保存到缓存，24 小时 (86400 秒)
            self.redis_client.setex(cache_key, 86400, json.dumps(data, ensure_ascii=False))
            logger.info("✓ 支持列表已保存到缓存 (24h)")
            
            return data
        except Exception as e:
            logger.error(f"✗ 获取支持列表失败: {str(e)}")
            raise DetectionFailedException(f"获取支持列表失败: {str(e)}")
