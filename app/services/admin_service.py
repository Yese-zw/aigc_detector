"""Business service for admin APIs."""

import datetime
import os

import jwt

from app.clients.lingsi import LingsiClient
from app.clients.redis import get_redis_client
from app.clients.upstream_ai import UpstreamAIClient
from app.core.config import settings
from app.schemas.apikey import APIKeyCreate
from app.services.apikey_service import APIKeyService


class AdminService:
    def __init__(self, api_key_service: APIKeyService, upstream_client: UpstreamAIClient, lingsi_client: LingsiClient):
        self.api_keys = api_key_service
        self.upstream = upstream_client
        self.lingsi = lingsi_client

    def token_info(self):
        token = get_redis_client().get(settings.REDIS_AUTH_KEY)
        if not token:
            return {"status": "empty", "message": "未找到有效Token"}

        payload = jwt.decode(token, options={"verify_signature": False})
        exp = payload.get("exp")
        if not exp:
            return {"status": "unknown", "message": "Token无过期时间字段", "claims": payload}

        exp_dt = datetime.datetime.fromtimestamp(exp)
        remaining = (exp_dt - datetime.datetime.now()).total_seconds()
        return {
            "status": "active" if remaining > 0 else "expired",
            "token_preview": f"{token[:15]}...{token[-5:]}" if len(token) > 20 else token,
            "expires_at": exp_dt.strftime("%Y-%m-%d %H:%M:%S"),
            "remaining_seconds": int(remaining) if remaining > 0 else 0,
            "claims": payload,
        }

    def update_token(self, token: str):
        clean_token = token.strip()
        if clean_token.lower().startswith("bearer "):
            clean_token = clean_token[7:].strip()
        get_redis_client().set(settings.REDIS_AUTH_KEY, clean_token)
        return {"status": "success", "message": f"Token 更新成功！({clean_token[:10]}...)"}

    def logs(self):
        if not os.path.exists(settings.LOG_FILE):
            return {"content": f"Log file not found at {settings.LOG_FILE}"}
        with open(settings.LOG_FILE, "r", encoding="utf-8") as file:
            return {"content": file.read()}

    def dashboard(self):
        keys = self.api_keys.list_apikeys()
        total_quota = sum(key.total_quota for key in keys)
        remaining_quota = sum(key.quota for key in keys)
        used_quota = total_quota - remaining_quota
        active_keys = sum(1 for key in keys if key.is_active)
        return {
            "status": "success",
            "data": {
                "summary": {
                    "total_keys": len(keys),
                    "active_keys": active_keys,
                    "inactive_keys": len(keys) - active_keys,
                    "total_quota": total_quota,
                    "used_quota": used_quota,
                    "remaining_quota": remaining_quota,
                    "usage_pct": round(used_quota / total_quota * 100, 1) if total_quota > 0 else 0,
                },
                "token_status": self._token_status(),
                "keys": [self._dashboard_key(key) for key in keys],
            },
        }

    def create_key(self, name: str, description: str, quota: int):
        return {"status": "success", "data": self.api_keys.create_apikey(APIKeyCreate(name=name, description=description, quota=quota))}

    def update_key(self, key: str, name: str | None, description: str | None, add_quota: int | None, is_active: str | None):
        is_active_bool = is_active.lower() == "true" if is_active is not None else None
        data = self.api_keys.update_apikey(key, name=name, description=description, quota=add_quota, is_active=is_active_bool)
        return {"status": "success", "data": data} if data else None

    def lingsi_dashboard(self, time_range: str):
        return self.lingsi.dashboard_overview(time_range)

    def _token_status(self) -> str:
        try:
            token = get_redis_client().get(settings.REDIS_AUTH_KEY)
            if not token:
                return "empty"
            payload = jwt.decode(token, options={"verify_signature": False})
            exp = payload.get("exp")
            if not exp:
                return "active"
            remaining = (datetime.datetime.fromtimestamp(exp) - datetime.datetime.now()).total_seconds()
            return "active" if remaining > 0 else "expired"
        except Exception:
            return "error"

    def _dashboard_key(self, key):
        used = key.total_quota - key.quota
        return {
            "key": key.key[:8] + "..." + key.key[-4:],
            "name": key.name,
            "description": key.description or "",
            "quota": key.quota,
            "total_quota": key.total_quota,
            "used_quota": used,
            "usage_pct": round(used / key.total_quota * 100, 1) if key.total_quota > 0 else 0,
            "is_active": key.is_active,
            "created_at": key.created_at,
            "last_used_at": key.last_used_at or "",
        }
