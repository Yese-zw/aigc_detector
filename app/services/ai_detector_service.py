"""
AI Detector Service
AI检测服务核心业务逻辑
"""
import requests
import re
import json
from typing import Optional, Dict, Any, Tuple
from datetime import timedelta
import time
from app.core.config import settings
from app.core.logger import logger
from app.core.redis_client import get_redis_client
from app.core.exceptions import (
    LoginFailedException,
    AllAccountsFailedException,
    DetectionFailedException
)


class AIDetectorService:
    """AI检测服务类"""
    
    def __init__(self):
        self.account_list = settings.AI_ACCOUNTS
        self.current_account_idx = 0
        self.redis_key = settings.REDIS_AUTH_KEY
        self.redis_client = get_redis_client()
        
        # 启动时记录账号信息
        logger.info("=" * 60)
        logger.info("AI检测服务初始化")
        logger.info(f"可用账号数量: {len(self.account_list)}")
        for idx, (email, _) in enumerate(self.account_list, 1):
            logger.info(f"  账号 {idx}: {email}")
        logger.info("=" * 60)
    
    def _init_base_headers(self) -> Dict[str, str]:
        """初始化基础请求头"""
        return {
            "authority": "ai.lanbeike.online",
            "method": "POST",
            "scheme": "https",
            "accept": "*/*",
            "accept-encoding": "gzip, deflate, br, zstd",
            "accept-language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
            "content-type": "application/x-www-form-urlencoded",
            "origin": settings.AI_DETECTOR_BASE_URL,
            "priority": "u=1, i",
            "referer": f"{settings.AI_DETECTOR_BASE_URL}/index/index/editor?history_id=150751",
            "sec-ch-ua": '"Microsoft Edge";v="141", "Not?A_Brand";v="8", "Chromium";v="141"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "user-agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/141.0.0.0 Safari/537.36 Edg/141.0.0.0"
            ),
            "x-requested-with": "XMLHttpRequest",
        }
    
    def _get_shared_auth(self) -> Optional[Dict[str, str]]:
        """从Redis获取共享的登录态"""
        try:
            auth_str = self.redis_client.get(self.redis_key)
            if auth_str:
                auth_data = json.loads(auth_str)
                # 获取当前使用的账号
                current_account = self.redis_client.get(f"{self.redis_key}_account")
                if current_account:
                    logger.debug(f"从Redis获取登录态成功 - 当前账号: {current_account}")
                return auth_data
        except Exception as e:
            logger.error(f"从Redis获取登录态失败: {str(e)}")
        return None
    
    def _set_shared_auth(self, auth_info: Dict[str, str], account_email: str) -> None:
        """将登录态存入Redis（共享给所有进程）"""
        try:
            if auth_info:
                # 存储登录态
                self.redis_client.setex(
                    self.redis_key,
                    timedelta(seconds=settings.AUTH_EXPIRE_SECONDS),
                    json.dumps(auth_info)
                )
                # 存储当前使用的账号邮箱
                self.redis_client.setex(
                    f"{self.redis_key}_account",
                    timedelta(seconds=settings.AUTH_EXPIRE_SECONDS),
                    account_email
                )
                logger.info(f"✓ 登录态已存入Redis - 账号: {account_email}, UID: {auth_info.get('uid', 'N/A')}")
                logger.info(f"  登录态有效期: {settings.AUTH_EXPIRE_SECONDS}秒 ({settings.AUTH_EXPIRE_SECONDS // 3600}小时)")
        except Exception as e:
            logger.error(f"✗ 存储登录态到Redis失败: {str(e)}")
    
    def _update_header_cookie(self, auth_info: Optional[Dict[str, str]]) -> Dict[str, str]:
        """用登录态更新请求头"""
        headers = self._init_base_headers()
        if auth_info:
            headers["cookie"] = (
                f"SESSION_ID={auth_info['SESSION_ID']}; "
                f"uid={auth_info['uid']}; "
                f"email=1762389546@qq.com; "
                f"token={auth_info['token']}; "
                f"uuid={auth_info['uuid']}"
            )
        return headers
    
    def _get_cookie(self, email: str, password: str) -> Optional[str]:
        """获取登录Cookie"""
        try:
            login_url = f"{settings.AI_DETECTOR_BASE_URL}/index/user/emailLogin"
            form_data = {'email': email, 'password': password}
            headers = self._init_base_headers()
            
            response = requests.post(
                url=login_url,
                data=form_data,
                headers=headers,
                timeout=settings.LOGIN_TIMEOUT
            )
            response.raise_for_status()
            return response.headers.get('Set-Cookie')
        except Exception as e:
            logger.error(f"账号 {email} 获取Cookie失败: {str(e)}")
            return None
    
    def _parse_auth(self, cookie: Optional[str]) -> Optional[Dict[str, str]]:
        """解析Cookie中的登录态"""
        if not cookie:
            return None
        
        auth_pairs = re.findall(r'(\w+)=([^;,\s]+)', cookie)
        auth_info = {}
        required_keys = ['uid', 'token', 'uuid', 'SESSION_ID']
        
        for key, value in auth_pairs:
            if key in required_keys:
                auth_info[key] = value
        
        if all(key in auth_info for key in required_keys):
            return auth_info
        
        missing_fields = [k for k in required_keys if k not in auth_info]
        logger.error(f"Cookie解析不完整，缺失字段: {missing_fields}")
        return None
    
    def login(self, email: Optional[str] = None, password: Optional[str] = None) -> bool:
        """登录并将登录态存入Redis共享"""
        if email is None or password is None:
            email, password = self.account_list[self.current_account_idx]
        
        logger.info(f"🔐 正在登录账号: {email}")
        cookie = self._get_cookie(email, password)
        
        if not cookie:
            logger.error(f"✗ 账号 {email} 登录失败 - 无法获取Cookie")
            raise LoginFailedException(email)
        
        auth_info = self._parse_auth(cookie)
        if not auth_info:
            logger.error(f"✗ 账号 {email} 登录失败 - Cookie解析失败")
            raise LoginFailedException(email)
        
        # 存储登录态（包含账号信息）
        self._set_shared_auth(auth_info, email)
        logger.info(f"✓ 账号 {email} 登录成功")
        return True
    
    def _switch_next_account(self) -> Tuple[str, str]:
        """切换到下一个账号"""
        old_idx = self.current_account_idx
        self.current_account_idx = (self.current_account_idx + 1) % len(self.account_list)
        next_email, next_password = self.account_list[self.current_account_idx]
        logger.warning(f"🔄 切换账号: 第{old_idx + 1}个账号 -> 第{self.current_account_idx + 1}个账号 ({next_email})")
        return next_email, next_password
    
    def aigccheck(self, text: str, language: str) -> Dict[str, Any]:
        """
        执行AI检测
        
        Args:
            text: 待检测文本
            language: 语言类型 (zh/en)
        
        Returns:
            检测结果字典
        """
        # 根据语言类型确定ID
        id_str = "1" if language == "zh" else "3"
        
        # 从Redis获取共享登录态
        auth_info = self._get_shared_auth()
        
        # 首次请求或登录态过期，尝试登录
        if not auth_info:
            logger.info("⚠ 未找到共享登录态，尝试登录...")
            if not self._try_all_accounts():
                raise AllAccountsFailedException()
            # 重新获取登录态
            auth_info = self._get_shared_auth()
            if not auth_info:
                raise AllAccountsFailedException()
        
        # 获取当前使用的账号
        current_account = self.redis_client.get(f"{self.redis_key}_account") or "未知账号"
        
        # 执行检测请求
        try:
            logger.info(f"📝 执行检测 - 使用账号: {current_account}, 语言: {language}, 文本长度: {len(text)}")
            result = self._do_aigccheck_request(auth_info, text, id_str)
            logger.info(f"✓ 检测完成 - 账号: {current_account}")
            return result
        except requests.exceptions.HTTPError as e:
            # HTTP错误 - 检查状态码
            if e.response is not None and e.response.status_code in [401, 403]:
                # 认证错误 - 清除登录态并重试
                logger.error(f"✗ AI检测认证失败 - 账号: {current_account}, 错误: {str(e)}")
                self.redis_client.delete(self.redis_key)
                self.redis_client.delete(f"{self.redis_key}_account")
                logger.warning("⚠ 已清除无效登录态，准备重试...")
                # 尝试切换账号重试
                if not self._try_all_accounts():
                    raise DetectionFailedException(str(e))
                # 再次执行检测
                auth_info = self._get_shared_auth()
                new_account = self.redis_client.get(f"{self.redis_key}_account") or "未知账号"
                logger.info(f"🔄 使用新账号重试 - 账号: {new_account}")
                return self._do_aigccheck_request(auth_info, text, id_str)
            elif e.response is not None and e.response.status_code in [502, 503, 504]:
                # 网关错误/服务不可用/超时 - 不清除登录态，直接抛出异常
                logger.error(f"✗ 上游服务器错误 ({e.response.status_code}) - 账号: {current_account}")
                raise DetectionFailedException(f"上游服务器暂时不可用 ({e.response.status_code}): {str(e)}")
            else:
                # 其他HTTP错误
                logger.error(f"✗ AI检测请求失败 - 账号: {current_account}, 状态码: {e.response.status_code if e.response else 'N/A'}, 错误: {str(e)}")
                raise DetectionFailedException(str(e))
        except requests.exceptions.Timeout as e:
            # 请求超时 - 不清除登录态
            logger.error(f"✗ AI检测请求超时 - 账号: {current_account}, 错误: {str(e)}")
            raise DetectionFailedException(f"请求超时: {str(e)}")
        except Exception as e:
            # 其他未知错误
            logger.error(f"✗ AI检测未知错误 - 账号: {current_account}, 错误: {str(e)}")
            raise DetectionFailedException(str(e))
    
    def _do_aigccheck_request(
        self, 
        auth_info: Dict[str, str], 
        text: str, 
        id_str: str
    ) -> Dict[str, Any]:
        """执行实际的检测请求"""
        headers = self._update_header_cookie(auth_info)
        headers["content-type"] = "application/json"
        
        detector_url = f"{settings.AI_DETECTOR_BASE_URL}/index/index/aigccheck"
        json_data = {"text": text, "id": id_str, "ip": "", "_ajax": True}
        headers["content-length"] = str(len(str(json_data)))
        
        response = requests.post(
            url=detector_url,
            headers=headers,
            json=json_data,
            timeout=settings.AI_DETECTOR_TIMEOUT
        )
        response.raise_for_status()
        return response.json()
    
    def _try_all_accounts(self) -> bool:
        """尝试所有账号登录"""
        original_idx = self.current_account_idx
        current_email = self.account_list[self.current_account_idx][0]
        
        logger.info(f"🔄 开始尝试账号登录 - 当前账号索引: {self.current_account_idx + 1}/{len(self.account_list)}")
        
        # 首先尝试当前账号
        try:
            logger.info(f"  尝试第 {self.current_account_idx + 1} 个账号: {current_email}")
            if self.login():
                return True
        except LoginFailedException:
            logger.warning(f"  ✗ 第 {self.current_account_idx + 1} 个账号登录失败")
        
        # 循环尝试所有账号
        attempts = 0
        max_attempts = len(self.account_list)
        
        while attempts < max_attempts:
            next_email, next_password = self._switch_next_account()
            attempts += 1
            
            # 如果已经尝试了所有账号，退出
            if self.current_account_idx == original_idx:
                logger.error(f"✗ 所有 {len(self.account_list)} 个账号均尝试失败")
                return False
            
            try:
                logger.info(f"  尝试第 {self.current_account_idx + 1} 个账号: {next_email}")
                if self.login(next_email, next_password):
                    logger.info(f"✓ 成功使用第 {self.current_account_idx + 1} 个账号: {next_email}")
                    return True
            except LoginFailedException:
                logger.warning(f"  ✗ 第 {self.current_account_idx + 1} 个账号登录失败")
                continue
        
        return False

    def aigcrewrite(self, text: str, combination_id: str) -> Dict[str, Any]:
        """
        执行AI改写

        Args:
            text: 待改写文本
            combination_id: 改写的组合

        Returns:
            检测结果字典
        """

        # 从Redis获取共享登录态
        auth_info = self._get_shared_auth()

        # 首次请求或登录态过期，尝试登录
        if not auth_info:
            logger.info("⚠ 未找到共享登录态，尝试登录...")
            if not self._try_all_accounts():
                raise AllAccountsFailedException()
            # 重新获取登录态
            auth_info = self._get_shared_auth()
            if not auth_info:
                raise AllAccountsFailedException()
        
        # 获取当前使用的账号
        current_account = self.redis_client.get(f"{self.redis_key}_account") or "未知账号"

        # 执行检测请求
        try:
            logger.info(f"📝 执行改写 - 使用账号: {current_account}, 组合: {combination_id}, 文本长度: {len(text)}")
            result = self._do_aigcrewrite_request(auth_info, text, combination_id)
            logger.info(f"✓ 改写完成 - 账号: {current_account}")
            logger.info(f"✓ 改写完成 - 内容: {result}")
            return result
        except requests.exceptions.HTTPError as e:
            # HTTP错误 - 检查状态码
            if e.response is not None and e.response.status_code in [401, 403]:
                # 认证错误 - 清除登录态并重试
                logger.error(f"✗ AI改写认证失败 - 账号: {current_account}, 错误: {str(e)}")
                self.redis_client.delete(self.redis_key)
                self.redis_client.delete(f"{self.redis_key}_account")
                logger.warning("⚠ 已清除无效登录态，准备重试...")
                # 尝试切换账号重试
                if not self._try_all_accounts():
                    raise DetectionFailedException(str(e))
                # 再次执行检测
                auth_info = self._get_shared_auth()
                new_account = self.redis_client.get(f"{self.redis_key}_account") or "未知账号"
                logger.info(f"🔄 使用新账号重试 - 账号: {new_account}")
                return self._do_aigcrewrite_request(auth_info, text, combination_id)
            elif e.response is not None and e.response.status_code in [502, 503, 504]:
                # 网关错误/服务不可用/超时 - 不清除登录态，直接抛出异常
                logger.error(f"✗ 上游服务器错误 ({e.response.status_code}) - 账号: {current_account}")
                raise DetectionFailedException(f"服务器暂时不可用 ({e.response.status_code}): {str(e)}")
            else:
                # 其他HTTP错误
                logger.error(f"✗ AI改写请求失败 - 账号: {current_account}, 状态码: {e.response.status_code if e.response else 'N/A'}, 错误: {str(e)}")
                raise DetectionFailedException(str(e))
        except requests.exceptions.Timeout as e:
            # 请求超时 - 不清除登录态
            logger.error(f"✗ AI改写请求超时 - 账号: {current_account}, 错误: {str(e)}")
            raise DetectionFailedException(f"请求超时: {str(e)}")
        except Exception as e:
            # 其他未知错误
            logger.error(f"✗ AI改写未知错误 - 账号: {current_account}, 错误: {str(e)}")
            raise DetectionFailedException(str(e))

    def _do_aigcrewrite_request(
            self,
            auth_info: Dict[str, str],
            text: str,
            combination_id: str
    ) -> Dict[str, Any]:
        """执行实际的检测请求"""
        headers = self._update_header_cookie(auth_info)
        headers["content-type"] = "application/json"

        detector_url = f"{settings.AI_DETECTOR_BASE_URL}/index/index/ai"
        json_data = {"text": text, "combination_id": combination_id,  "_ajax": True}
        headers['page-timestamp'] = str(int(time.time()*1000))
        headers["content-length"] = str(len(str(json_data)))
        logger.info(headers)
        response = requests.post(
            url=detector_url,
            headers=headers,
            json=json_data,
            timeout=settings.AI_DETECTOR_TIMEOUT
        )
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
        """
        上传文件到AI检测服务
        
        Args:
            file_content: 文件内容（字节）
            filename: 文件名
            uuid: UUID
            language: 语言
            mode: 模式
            platform: 平台
        
        Returns:
            上传结果字典
        """
        # 从Redis获取共享登录态
        auth_info = self._get_shared_auth()
        
        # 首次请求或登录态过期，尝试登录
        if not auth_info:
            logger.info("⚠ 未找到共享登录态，尝试登录...")
            if not self._try_all_accounts():
                raise AllAccountsFailedException()
            # 重新获取登录态
            auth_info = self._get_shared_auth()
            if not auth_info:
                raise AllAccountsFailedException()
        
        # 获取当前使用的账号
        current_account = self.redis_client.get(f"{self.redis_key}_account") or "未知账号"
        
        # 执行上传请求
        try:
            logger.info(f"📤 执行文件上传 - 使用账号: {current_account}, 文件: {filename}")
            result = self._do_upload_request(auth_info, file_content, filename, uuid, language, mode, platform)
            logger.info(f"✓ 上传完成 - 账号: {current_account}")
            return result
        except requests.exceptions.HTTPError as e:
            # HTTP错误 - 检查状态码
            if e.response is not None and e.response.status_code in [401, 403]:
                # 认证错误 - 清除登录态并重试
                logger.error(f"✗ 文件上传认证失败 - 账号: {current_account}, 错误: {str(e)}")
                self.redis_client.delete(self.redis_key)
                self.redis_client.delete(f"{self.redis_key}_account")
                logger.warning("⚠ 已清除无效登录态，准备重试...")
                # 尝试切换账号重试
                if not self._try_all_accounts():
                    raise DetectionFailedException(str(e))
                # 再次执行上传
                auth_info = self._get_shared_auth()
                new_account = self.redis_client.get(f"{self.redis_key}_account") or "未知账号"
                logger.info(f"🔄 使用新账号重试 - 账号: {new_account}")
                return self._do_upload_request(auth_info, file_content, filename, uuid, language, mode, platform)
            elif e.response is not None and e.response.status_code in [502, 503, 504]:
                # 网关错误/服务不可用/超时 - 不清除登录态，直接抛出异常
                logger.error(f"✗ 上游服务器错误 ({e.response.status_code}) - 账号: {current_account}")
                raise DetectionFailedException(f"服务器暂时不可用 ({e.response.status_code}): {str(e)}")
            else:
                # 其他HTTP错误
                logger.error(f"✗ 文件上传失败 - 账号: {current_account}, 状态码: {e.response.status_code if e.response else 'N/A'}, 错误: {str(e)}")
                raise DetectionFailedException(str(e))
        except requests.exceptions.Timeout as e:
            # 请求超时 - 不清除登录态
            logger.error(f"✗ 文件上传请求超时 - 账号: {current_account}, 错误: {str(e)}")
            raise DetectionFailedException(f"请求超时: {str(e)}")
        except Exception as e:
            # 其他未知错误
            logger.error(f"✗ 文件上传未知错误 - 账号: {current_account}, 错误: {str(e)}")
            raise DetectionFailedException(str(e))
    
    def _do_upload_request(
        self,
        auth_info: Dict[str, str],
        file_content: bytes,
        filename: str,
        uuid: str,
        language: str,
        mode: str,
        platform: str
    ) -> Dict[str, Any]:
        """执行实际的文件上传请求"""
        # 构建请求头（上传文件时不需要 content-type）
        headers = self._update_header_cookie(auth_info)
        # 移除 content-type，让 requests 自动设置
        if "content-type" in headers:
            del headers["content-type"]
        headers['page-timestamp'] = str(int(time.time()*1000))
        upload_url = f"{settings.AI_DETECTOR_BASE_URL}/api/upload"
        
        # 构建文件上传数据
        files = {
            'file': (filename, file_content)
        }
        
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

    def file_status(
            self,
            uuid: str
    ) -> Dict[str, Any]:
        """
        上传文件到AI检测服务-查询

        Args:

            uuid: UUID
        Returns:
            上传结果字典
        """
        # 从Redis获取共享登录态
        auth_info = self._get_shared_auth()

        # 首次请求或登录态过期，尝试登录
        if not auth_info:
            logger.info("⚠ 未找到共享登录态，尝试登录...")
            if not self._try_all_accounts():
                raise AllAccountsFailedException()
            # 重新获取登录态
            auth_info = self._get_shared_auth()
            if not auth_info:
                raise AllAccountsFailedException()

        # 获取当前使用的账号
        current_account = self.redis_client.get(f"{self.redis_key}_account") or "未知账号"

        # 执行上传请求
        try:
            logger.info(f"📤 执行文件查询 - 使用账号: {current_account}, 文件uuid: {uuid}")
            result = self._do_upload_status_request(auth_info, uuid)
            logger.info(f"✓ 上传完成 - 账号: {current_account}")
            return result
        except requests.exceptions.HTTPError as e:
            # HTTP错误 - 检查状态码
            if e.response is not None and e.response.status_code in [401, 403]:
                # 认证错误 - 清除登录态并重试
                logger.error(f"✗ 文件查询认证失败 - 账号: {current_account}, 错误: {str(e)}")
                self.redis_client.delete(self.redis_key)
                self.redis_client.delete(f"{self.redis_key}_account")
                logger.warning("⚠ 已清除无效登录态，准备重试...")
                # 尝试切换账号重试
                if not self._try_all_accounts():
                    raise DetectionFailedException(str(e))
                # 再次执行上传
                auth_info = self._get_shared_auth()
                new_account = self.redis_client.get(f"{self.redis_key}_account") or "未知账号"
                logger.info(f"🔄 使用新账号重试 - 账号: {new_account}")
                return self._do_upload_status_request(auth_info, uuid)
            elif e.response is not None and e.response.status_code in [502, 503, 504]:
                # 网关错误/服务不可用/超时 - 不清除登录态，直接抛出异常
                logger.error(f"✗ 上游服务器错误 ({e.response.status_code}) - 账号: {current_account}")
                raise DetectionFailedException(f"服务器暂时不可用 ({e.response.status_code}): {str(e)}")
            else:
                # 其他HTTP错误
                logger.error(f"✗ 文件查询失败 - 账号: {current_account}, 状态码: {e.response.status_code if e.response else 'N/A'}, 错误: {str(e)}")
                raise DetectionFailedException(str(e))
        except requests.exceptions.Timeout as e:
            # 请求超时 - 不清除登录态
            logger.error(f"✗ 文件查询请求超时 - 账号: {current_account}, 错误: {str(e)}")
            raise DetectionFailedException(f"请求超时: {str(e)}")
        except Exception as e:
            # 其他未知错误
            logger.error(f"✗ 文件查询未知错误 - 账号: {current_account}, 错误: {str(e)}")
            raise DetectionFailedException(str(e))


    def _do_upload_status_request(self, auth_info: Dict[str, str], uuid: str) -> Dict[str, Any]:
        """执行实际的文件上传请求"""
        # 构建请求头（上传文件时不需要 content-type）
        headers = self._update_header_cookie(auth_info)
        # 移除 content-type，让 requests 自动设置
        if "content-type" in headers:
            del headers["content-type"]
        headers['page-timestamp'] = str(int(time.time() * 1000))
        upload_url = f"{settings.AI_DETECTOR_BASE_URL}/index/upload/status?uuid={uuid}"



        response = requests.get(
            url=upload_url,
            headers=headers,
            timeout=settings.AI_DETECTOR_TIMEOUT
        )
        response.raise_for_status()
        return response.json()
    