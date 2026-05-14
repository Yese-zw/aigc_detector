"""Admin API routes."""

from typing import Optional

from fastapi import APIRouter, Depends, Form, Query, Request, status
from fastapi.responses import JSONResponse, RedirectResponse

from app.api.dependencies import COOKIE_NAME, get_admin_service, require_admin
from app.core.config import settings
from app.services.admin_service import AdminService

router = APIRouter()


@router.get("/token/info", dependencies=[Depends(require_admin)])
async def get_token_info(service: AdminService = Depends(get_admin_service)):
    return service.token_info()


@router.post("/token", dependencies=[Depends(require_admin)])
async def update_token(token: str = Form(...), service: AdminService = Depends(get_admin_service)):
    return service.update_token(token)


@router.get("/logs", dependencies=[Depends(require_admin)])
async def get_logs(service: AdminService = Depends(get_admin_service)):
    return service.logs()


@router.get("/keys", dependencies=[Depends(require_admin)])
async def list_keys(service: AdminService = Depends(get_admin_service)):
    return {"status": "success", "data": service.api_keys.list_apikeys()}


@router.post("/keys", dependencies=[Depends(require_admin)])
async def create_key(name: str = Form(...), description: str = Form(""), quota: int = Form(...), service: AdminService = Depends(get_admin_service)):
    return service.create_key(name, description, quota)


@router.delete("/keys/{key}", dependencies=[Depends(require_admin)])
async def delete_key(key: str, service: AdminService = Depends(get_admin_service)):
    service.api_keys.delete_apikey(key)
    return {"status": "success"}


@router.put("/keys/{key}", dependencies=[Depends(require_admin)])
async def update_key(
    key: str,
    name: Optional[str] = Query(None),
    description: Optional[str] = Query(None),
    add_quota: Optional[int] = Query(None),
    is_active: Optional[str] = Query(None),
    service: AdminService = Depends(get_admin_service),
):
    data = service.update_key(key, name, description, add_quota, is_active)
    if not data:
        return JSONResponse({"status": "error", "message": "Key not found"}, status_code=404)
    return data


@router.post("/wxlogin/start", dependencies=[Depends(require_admin)])
async def proxy_wxlogin_start(service: AdminService = Depends(get_admin_service)):
    return service.upstream.wxlogin_start()


@router.get("/wxlogin/status", dependencies=[Depends(require_admin)])
async def proxy_wxlogin_status(request_id: str, service: AdminService = Depends(get_admin_service)):
    return service.upstream.wxlogin_status(request_id)


@router.get("/miniapp/dashboard")
async def miniapp_dashboard(service: AdminService = Depends(get_admin_service)):
    return service.dashboard()


@router.get("/lingsi-dashboard")
async def proxy_lingsi_dashboard(time_range: str = Query("30d"), service: AdminService = Depends(get_admin_service)):
    response = service.lingsi_dashboard(time_range)
    if response.status_code == 200:
        return response.json()
    return JSONResponse(
        {"error": f"Lingsi API returned {response.status_code}", "detail": response.text},
        status_code=response.status_code,
    )


@router.post("/login")
async def login(password: str = Form(...)):
    if password == settings.ADMIN_PASSWORD:
        response = RedirectResponse(url="/admin/dashboard", status_code=status.HTTP_302_FOUND)
        response.set_cookie(key=COOKIE_NAME, value=password, max_age=24 * 3600, httponly=True)
        return response
    return RedirectResponse(url="/admin/login?error=1", status_code=status.HTTP_302_FOUND)


@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/admin/login", status_code=status.HTTP_302_FOUND)
    response.delete_cookie(COOKIE_NAME)
    return response
