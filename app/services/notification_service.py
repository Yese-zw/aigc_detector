"""
Notification Service
通知服务
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from app.core.config import settings
from app.core.logger import logger
from app.core.redis_client import get_redis_client

class NotificationService:
    """通知服务类"""
    
    def __init__(self):
        self.redis_client = get_redis_client()
        self.cooldown_key = "mail_notification_cooldown"
        
    def send_auth_expired_email(self):
        """发送Auth Key过期通知邮件"""
        if not settings.MAIL_USERNAME or not settings.MAIL_PASSWORD:
            logger.warning("⚠️ 未配置邮件发送相关信息，跳过发送过期通知")
            return
            
        if not settings.MAIL_TO:
            logger.warning("⚠️ 未配置邮件接收者(MAIL_TO)，跳过发送过期通知")
            return
            
        # 检查冷却时间
        if self.redis_client.get(self.cooldown_key):
            logger.info("ℹ️ 邮件通知处于冷却期，跳过发送")
            return
            
        try:
            subject = f"[{settings.APP_NAME}] ⚠️ Auth Key 已过期或失效"
            content = f"""
            <h3>Auth Key 失效通知</h3>
            <p>系统检测到当前的 AIGC Detector Auth Key 已失效或不存在。</p>
            <p><b>时间:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p>请尽快登录服务器或 Redis 更新 <code>{settings.REDIS_AUTH_KEY}</code>。</p>
            <p>https://ai.lanbeike.online/</p>
            </p>124.221.97.191:8001/admin/login</p>
            """
            
            self._send_email(subject, content)
            
            # 设置冷却时间
            self.redis_client.setex(
                self.cooldown_key,
                settings.MAIL_COOLDOWN_SECONDS,
                "1"
            )
            logger.info("✓ 过期通知邮件发送成功")
            
        except Exception as e:
            logger.error(f"✗ 发送邮件失败: {str(e)}")
            
    def _send_email(self, subject: str, content: str):
        """执行发送邮件"""
        message = MIMEMultipart()
        message["From"] = settings.MAIL_FROM or settings.MAIL_USERNAME
        message["To"] = ",".join(settings.MAIL_TO)
        message["Subject"] = subject
        
        message.attach(MIMEText(content, "html", "utf-8"))
        
        try:
            with smtplib.SMTP_SSL(settings.MAIL_SERVER, settings.MAIL_PORT) as server:
                server.login(settings.MAIL_USERNAME, settings.MAIL_PASSWORD)
                server.send_message(message)
        except Exception as e:
            raise e

# 全局实例
notification_service = NotificationService()
