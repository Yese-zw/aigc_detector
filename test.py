import requests

from app.api.routes.admin import proxy_wxlogin_status


def _browser_headers() -> dict[str, str]:
    return {
        "accept": "application/json, text/plain, */*",
        "accept-language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
        "content-type": "application/json",
        "origin": "https://xrz.cntcn.com",
        "referer": "https://xrz.cntcn.com/",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36 Edg/144.0.0.0",
    }


response = requests.post(
    f"https://ai.lanbeike.online/api/index/user/emailLogin",
    headers=_browser_headers(),
    json={"email": "1762389546@qq.com", "password": "xrz1762389546"},
    timeout=120,
)

print(response.status_code)
print(response.json())