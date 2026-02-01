"""
Custom exceptions
自定义异常类
"""


class AIGCDetectorException(Exception):
    """基础异常类"""
    def __init__(self, message: str = "AI检测服务异常"):
        self.message = message
        super().__init__(self.message)


class LoginFailedException(AIGCDetectorException):
    """登录失败异常"""
    def __init__(self, email: str = ""):
        self.message = f"账号 {email} 登录失败"
        super().__init__(self.message)


class AuthExpiredException(AIGCDetectorException):
    """Auth Key过期或无效异常"""
    def __init__(self):
        self.message = "Auth Key已过期或无效，请更新Redis中的凭证"
        super().__init__(self.message)


class DetectionFailedException(AIGCDetectorException):
    """检测请求失败异常"""
    def __init__(self, reason: str = ""):
        self.message = f"AI检测请求失败: {reason}"
        super().__init__(self.message)


class InvalidLanguageException(AIGCDetectorException):
    """不支持的语言类型异常"""
    def __init__(self, language: str):
        self.message = f"不支持的语言类型: {language}，仅支持 zh 或 en"
        super().__init__(self.message)


class RedisConnectionException(AIGCDetectorException):
    """Redis连接异常"""
    def __init__(self):
        self.message = "Redis连接失败"
        super().__init__(self.message)

