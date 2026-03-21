from typing import Optional
from fastapi import APIRouter, Request, Form, status, Depends, Query
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from app.core.config import settings
from app.core.redis_client import get_redis_client
from app.core.logger import logger
import os
import requests
import json
import jwt
import datetime
from app.services.apikey_service import APIKeyService
from app.models.apikey import APIKeyCreate

router = APIRouter()

# Cookie名称
COOKIE_NAME = "admin_access_token"


def verify_cookie(request: Request) -> bool:
    """验证Cookie是否有效"""
    cookie = request.cookies.get(COOKIE_NAME)
    return cookie == settings.ADMIN_PASSWORD

@router.get("/login", response_class=HTMLResponse)
async def login_page(error: int = Query(0)):
    """登录页面"""
    template_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates", "admin_signin.html")
    with open(template_path, "r", encoding="utf-8") as f:
        html = f.read()

    error_display = "block" if error else "none"
    return HTMLResponse(content=html.replace("__ERROR_DISPLAY__", error_display))

@router.post("/login", response_class=HTMLResponse)
async def login(password: str = Form(...)):
    """处理登录"""
    if password == settings.ADMIN_PASSWORD:
        response = RedirectResponse(url="/admin/dashboard", status_code=status.HTTP_302_FOUND)
        ONE_HOUR = 3600
        ONE_DAY = 24 * ONE_HOUR  # 86400秒
        response.set_cookie(key=COOKIE_NAME, value=password, max_age=ONE_DAY, httponly=True)
        return response
    else:
        return RedirectResponse(url="/admin/login?error=1", status_code=status.HTTP_302_FOUND)

@router.get("/logout")
async def logout():
    """退出登录"""
    response = RedirectResponse(url="/admin/login", status_code=status.HTTP_302_FOUND)
    response.delete_cookie(COOKIE_NAME)
    return response

@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    """Admin Dashboard 页面"""
    if not verify_cookie(request):
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_302_FOUND)

    template_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates", "admin_login.html")
    with open(template_path, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

@router.get("/token/info")
async def get_token_info(request: Request):
    """获取当前Token状态"""
    if not verify_cookie(request): return JSONResponse({"error": "Unauthorized"}, status_code=401)
    
    try:
        redis_client = get_redis_client()
        token = redis_client.get(settings.REDIS_AUTH_KEY)
        
        if not token:
            return {"status": "empty", "message": "未找到有效Token"}
            
        # Decode without verification
        try:
            payload = jwt.decode(token, options={"verify_signature": False})
            exp = payload.get('exp')
            
            if exp:
                exp_dt = datetime.datetime.fromtimestamp(exp)
                now_dt = datetime.datetime.now()
                remaining = (exp_dt - now_dt).total_seconds()
                
                is_expired = remaining <= 0
                
                return {
                    "status": "active" if not is_expired else "expired",
                    "token_preview": f"{token[:15]}...{token[-5:]}",
                    "expires_at": exp_dt.strftime('%Y-%m-%d %H:%M:%S'),
                    "remaining_seconds": int(remaining) if not is_expired else 0,
                    "claims": payload
                }
            else:
                return {
                    "status": "unknown", 
                    "message": "Token无过期时间字段",
                    "claims": payload
                }
        except Exception as e:
            return {"status": "error", "message": f"Token解析失败: {str(e)}"}
            
    except Exception as e:
        logger.error(f"Error getting token info: {e}")
        return {"status": "error", "message": str(e)}

# Token Update
@router.post("/token")
async def update_token(request: Request, token: str = Form(...)):
    if not verify_cookie(request): return {"status": "error", "message": "Unauthorized"}
    try:
        clean_token = token.strip()
        if clean_token.lower().startswith("bearer "):
            clean_token = clean_token[7:].strip()
        redis_client = get_redis_client()
        redis_client.set(settings.REDIS_AUTH_KEY, clean_token)
        logger.info("🔐 管理员通过页面更新了 Auth Token")
        return {"status": "success", "message": f"Token 更新成功！({clean_token[:10]}...)"}
    except Exception as e:
        logger.error(f"Token update failed: {str(e)}")
        return {"status": "error", "message": f"错误: {str(e)}"}

# === New Admin Endpoints ===
@router.get("/logs")
async def get_logs(request: Request):
    """获取今日日志"""
    if not verify_cookie(request): return JSONResponse({"error": "Unauthorized"}, status_code=401)
    
    log_file = settings.LOG_FILE
    if os.path.exists(log_file):
         try:
             # Read user friendly last lines or full file?
             # For now full file, but might be large.
             # Ideally read last N lines.
             with open(log_file, 'r', encoding='utf-8') as f:
                 content = f.read()
             return {"content": content}
         except Exception as e:
             return {"content": f"Error reading log: {str(e)}"}
             
    return {"content": f"Log file not found at {log_file}"}

@router.get("/keys")
async def list_keys(request: Request):
    """List API Keys"""
    if not verify_cookie(request): return JSONResponse({"error": "Unauthorized"}, status_code=401)
    keys = APIKeyService().list_apikeys()
    return {"status": "success", "data": keys}

@router.post("/keys")
async def create_key(request: Request, name: str = Form(...), description: str = Form(""), quota: int = Form(...)):
     """Create API Key"""
     if not verify_cookie(request): return JSONResponse({"error": "Unauthorized"}, status_code=401)
     data = APIKeyCreate(name=name, description=description, quota=quota)
     result = APIKeyService().create_apikey(data)
     return {"status": "success", "data": result}

@router.delete("/keys/{key}")
async def delete_key(request: Request, key: str):
    """Delete API Key"""
    if not verify_cookie(request): return JSONResponse({"error": "Unauthorized"}, status_code=401)
    APIKeyService().delete_apikey(key)
    return {"status": "success"}

@router.put("/keys/{key}")
async def update_key(
    request: Request, 
    key: str,
    name: Optional[str] = Query(None),
    description: Optional[str] = Query(None),
    add_quota: Optional[int] = Query(None),
    is_active: Optional[str] = Query(None) # Receive as string 'true'/'false' from query params
):
    """Update API Key"""
    if not verify_cookie(request): return JSONResponse({"error": "Unauthorized"}, status_code=401)
    
    # Convert 'true'/'false' string to boolean if present
    is_active_bool = None
    if is_active is not None:
        is_active_bool = is_active.lower() == 'true'

    data = APIKeyService().update_apikey(
        api_key=key,
        name=name,
        description=description,
        quota=add_quota,
        is_active=is_active_bool
    )
    if not data:
        return JSONResponse({"status": "error", "message": "Key not found"}, status_code=404)
        
    return {"status": "success", "data": data}

# === WeChat Login Proxy Endpoints ===

@router.post("/wxlogin/start")
async def proxy_wxlogin_start(request: Request):
    """代理微信登录开始接口"""
    if not verify_cookie(request):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    
    url = f"{settings.AI_DETECTOR_BASE_URL}/wxlogin/start"
    headers = {
        "authority": "xrzbk.lanbeike.online",
        "accept": "application/json, text/plain, */*",
        "accept-language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
        "content-type": "application/json",
        "origin": "https://ai.lanbeike.online",
        "referer": "https://ai.lanbeike.online/",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36 Edg/144.0.0.0",
        "sec-ch-ua": '"Not(A:Brand";v="8", "Chromium";v="144", "Microsoft Edge";v="144"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-site",
    }
    
    try:
        # 使用 POST 请求并携带 user-agent 等头信息
        # 注意：这里不发 body，因为抓包显示 content-length 为 0
        response = requests.post(url, headers=headers, timeout=10)
        return response.json()
    except Exception as e:
        logger.error(f"WxLogin start proxy failed: {e}")
        return JSONResponse({"code": 500, "msg": f"代理请求失败: {str(e)}"}, status_code=500)

@router.get("/wxlogin/status")
async def proxy_wxlogin_status(request: Request, request_id: str):
    """代理微信登录状态查询接口"""
    if not verify_cookie(request):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    
    url = f"{settings.AI_DETECTOR_BASE_URL}/wxlogin/status"
    params = {"request_id": request_id}
    headers = {
        "authority": "xrzbk.lanbeike.online",
        "accept": "application/json, text/plain, */*",
        "accept-language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
        "origin": "https://ai.lanbeike.online",
        "referer": "https://ai.lanbeike.online/",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36 Edg/144.0.0.0",
        "sec-ch-ua": '"Not(A:Brand";v="8", "Chromium";v="144", "Microsoft Edge";v="144"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-site",
    }
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        return response.json()
    except Exception as e:
        logger.error(f"WxLogin status proxy failed: {e}")
        return JSONResponse({"code": 500, "msg": f"代理请求失败: {str(e)}"}, status_code=500)
