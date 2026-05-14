"""HTML page routes."""

from fastapi import APIRouter, Depends, Query, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse

from app.api.dependencies import get_template_service, verify_cookie
from app.services.template_service import TemplateService

router = APIRouter()


@router.get("/ping", tags=["健康检查"])
async def ping():
    return {"status": "ok", "message": "pong"}


@router.get("/", tags=["开发者中心"])
async def developer_portal(templates: TemplateService = Depends(get_template_service)):
    return HTMLResponse(content=templates.load("developer.html"))


@router.get("/admin/login", response_class=HTMLResponse)
async def login_page(error: int = Query(0), templates: TemplateService = Depends(get_template_service)):
    error_display = "block" if error else "none"
    return HTMLResponse(content=templates.load("admin_signin.html").replace("__ERROR_DISPLAY__", error_display))


@router.get("/admin/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request, templates: TemplateService = Depends(get_template_service)):
    if not verify_cookie(request):
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_302_FOUND)
    return HTMLResponse(content=templates.load("admin_login.html"))
