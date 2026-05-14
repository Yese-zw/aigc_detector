"""Domain exceptions used by services and global handlers."""


class AppException(Exception):
    status_code = 500
    public_message = "服务器内部错误"

    def __init__(self, message: str | None = None):
        self.message = message or self.public_message
        super().__init__(self.message)


class AIGCDetectorException(AppException):
    public_message = "AI检测服务异常"

    def __init__(self, message: str = "AI检测服务异常"):
        self.message = message
        super().__init__(self.message)


class LoginFailedException(AIGCDetectorException):
    def __init__(self, email: str = ""):
        super().__init__(f"账号 {email} 登录失败")


class AuthExpiredException(AIGCDetectorException):
    def __init__(self, message: str = "Auth Key已过期或无效，请更新Redis中的凭证"):
        super().__init__(message)


class DetectionFailedException(AIGCDetectorException):
    def __init__(self, reason: str = ""):
        super().__init__(f"AI检测请求失败: {reason}")


class InvalidLanguageException(AIGCDetectorException):
    def __init__(self, language: str):
        super().__init__(f"不支持的语言类型: {language}，仅支持 zh 或 en")


class RedisConnectionException(AIGCDetectorException):
    def __init__(self):
        super().__init__("Redis连接失败")


class QuotaExceededException(AppException):
    status_code = 402

    def __init__(self, remaining: int, required: int, unit: str = " 字符"):
        super().__init__(f"额度不足，剩余: {remaining}{unit}，需要: {required}{unit}")


class APIKeyNotFoundException(AppException):
    status_code = 404

    def __init__(self):
        super().__init__("API Key 不存在")
