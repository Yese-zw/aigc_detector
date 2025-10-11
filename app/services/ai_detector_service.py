"""
AI Detector Service
AI检测服务核心业务逻辑
"""
import requests
import re
import json
from typing import Optional, Dict, Any, Tuple
from datetime import timedelta

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
            "sec-ch-ua": '"Not;A=Brand";v="99", "Microsoft Edge";v="139", "Chromium";v="139"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "user-agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/139.0.0.0 Safari/537.36 Edg/139.0.0.0"
            )
        }
    
    def _get_shared_auth(self) -> Optional[Dict[str, str]]:
        """从Redis获取共享的登录态"""
        try:
            auth_str = self.redis_client.get(self.redis_key)
            if auth_str:
                return json.loads(auth_str)
        except Exception as e:
            logger.error(f"从Redis获取登录态失败: {str(e)}")
        return None
    
    def _set_shared_auth(self, auth_info: Dict[str, str]) -> None:
        """将登录态存入Redis（共享给所有进程）"""
        try:
            if auth_info:
                self.redis_client.setex(
                    self.redis_key,
                    timedelta(seconds=settings.AUTH_EXPIRE_SECONDS),
                    json.dumps(auth_info)
                )
                logger.info("登录态已存入Redis")
        except Exception as e:
            logger.error(f"存储登录态到Redis失败: {str(e)}")
    
    def _update_header_cookie(self, auth_info: Optional[Dict[str, str]]) -> Dict[str, str]:
        """用登录态更新请求头"""
        headers = self._init_base_headers()
        if auth_info:
            headers["cookie"] = (
                f"SESSION_ID={auth_info['SESSION_ID']}; "
                f"uid={auth_info['uid']}; "
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
        
        logger.info(f"正在登录账号: {email}")
        cookie = self._get_cookie(email, password)
        
        if not cookie:
            raise LoginFailedException(email)
        
        auth_info = self._parse_auth(cookie)
        if not auth_info:
            raise LoginFailedException(email)
        
        self._set_shared_auth(auth_info)
        logger.info(f"账号 {email} 登录成功")
        return True
    
    def _switch_next_account(self) -> Tuple[str, str]:
        """切换到下一个账号"""
        self.current_account_idx = (self.current_account_idx + 1) % len(self.account_list)
        next_email, next_password = self.account_list[self.current_account_idx]
        logger.info(f"切换到下一个账号: {next_email}")
        return next_email, next_password
    
    def detect(self, text: str, language: str) -> Dict[str, Any]:
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
            logger.info("未找到共享登录态，尝试登录...")
            if not self._try_all_accounts(text, id_str):
                raise AllAccountsFailedException()
            # 重新获取登录态
            auth_info = self._get_shared_auth()
            if not auth_info:
                raise AllAccountsFailedException()
        
        # 执行检测请求
        try:
            return self._do_detect_request(auth_info, text, id_str)
        except Exception as e:
            logger.error(f"AI检测请求失败: {str(e)}")
            # 清除无效登录态
            self.redis_client.delete(self.redis_key)
            # 尝试切换账号重试
            if not self._try_all_accounts(text, id_str):
                raise DetectionFailedException(str(e))
            # 再次执行检测
            auth_info = self._get_shared_auth()
            return self._do_detect_request(auth_info, text, id_str)
    
    def _do_detect_request(
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
    
    def _try_all_accounts(self, text: str, id_str: str) -> bool:
        """尝试所有账号登录并执行检测"""
        original_idx = self.current_account_idx
        
        # 首先尝试当前账号
        try:
            if self.login():
                return True
        except LoginFailedException:
            pass
        
        # 循环尝试所有账号
        while True:
            next_email, next_password = self._switch_next_account()
            
            # 如果已经尝试了所有账号，退出
            if self.current_account_idx == original_idx:
                logger.error("所有账号均尝试失败")
                return False
            
            try:
                if self.login(next_email, next_password):
                    return True
            except LoginFailedException:
                continue

