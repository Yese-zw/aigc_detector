from fastapi import APIRouter, Request, Form, status, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from app.core.config import settings
from app.core.redis_client import get_redis_client
from app.core.logger import logger

router = APIRouter()

# Cookie名称
COOKIE_NAME = "admin_access_token"

HTML_TEMPLATE_LOGIN = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AIGC Admin Login</title>
    <style>
        :root {
            --primary-color: #6366f1;
            --primary-hover: #4f46e5;
            --bg-color: #0f172a;
            --card-bg: #1e293b;
            --text-color: #f8fafc;
            --text-secondary: #94a3b8;
            --border-color: #334155;
        }
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background-color: var(--bg-color);
            color: var(--text-color);
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            margin: 0;
        }
        .container {
            background-color: var(--card-bg);
            padding: 2rem;
            border-radius: 1rem;
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
            width: 100%;
            max-width: 400px;
            border: 1px solid var(--border-color);
            text-align: center;
        }
        h1 {
            font-size: 1.5rem;
            margin-bottom: 1.5rem;
            color: var(--text-color);
        }
        .form-group {
            margin-bottom: 1.5rem;
            text-align: left;
        }
        label {
            display: block;
            margin-bottom: 0.5rem;
            font-size: 0.875rem;
            color: var(--text-secondary);
        }
        input[type="password"] {
            width: 100%;
            padding: 0.75rem;
            background-color: #0f172a;
            border: 1px solid var(--border-color);
            border-radius: 0.5rem;
            color: var(--text-color);
            font-size: 0.875rem;
            box-sizing: border-box;
        }
        button {
            width: 100%;
            background-color: var(--primary-color);
            color: white;
            padding: 0.75rem;
            border: none;
            border-radius: 0.5rem;
            cursor: pointer;
            transition: background-color 0.2s;
        }
        button:hover {
            background-color: var(--primary-hover);
        }
        .error {
            color: #ef4444;
            font-size: 0.875rem;
            margin-bottom: 1rem;
            display: none;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>后台登录</h1>
        <div id="error-msg" class="error">密码错误</div>
        <form method="post" action="/admin/login">
            <div class="form-group">
                <label for="password">请输入管理员密码</label>
                <input type="password" id="password" name="password" required autofocus>
            </div>
            <button type="submit">登录</button>
        </form>
    </div>
</body>
</html>
"""

HTML_TEMPLATE_ADMIN = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AIGC Admin Dashboard</title>
    <style>
        :root {
            --primary-color: #6366f1;
            --primary-hover: #4f46e5;
            --bg-color: #0f172a;
            --card-bg: #1e293b;
            --text-color: #f8fafc;
            --text-secondary: #94a3b8;
            --border-color: #334155;
            --success-color: #22c55e;
            --error-color: #ef4444;
        }
        
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background-color: var(--bg-color);
            color: var(--text-color);
            display: flex;
            min-height: 100vh;
            margin: 0;
            padding: 2rem;
            box-sizing: border-box;
        }
        
        .container {
            width: 100%;
            max-width: 1200px;
            margin: 0 auto;
        }
        
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 2rem;
        }

        h1 {
            font-size: 1.75rem;
            font-weight: 700;
            margin: 0;
            background: linear-gradient(to right, #818cf8, #c084fc);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        
        .logout {
            font-size: 0.875rem;
            color: var(--text-secondary);
            text-decoration: none;
            padding: 0.5rem 1rem;
            border: 1px solid var(--border-color);
            border-radius: 0.25rem;
            transition: all 0.2s;
        }
        .logout:hover {
            color: var(--text-color);
            border-color: var(--text-color);
        }
        
        .nav-tabs {
            display: flex;
            gap: 1rem;
            margin-bottom: 1.5rem;
        }
        
        .nav-tab {
            background-color: transparent;
            border: 1px solid var(--border-color);
            color: var(--text-secondary);
            padding: 0.75rem 1.5rem;
            border-radius: 0.5rem;
            cursor: pointer;
            transition: all 0.2s;
            font-size: 1rem;
        }
        
        .nav-tab.active {
            background-color: var(--primary-color);
            color: white;
            border-color: var(--primary-color);
        }
        
        .card {
            background-color: var(--card-bg);
            padding: 2rem;
            border-radius: 1rem;
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
            border: 1px solid var(--border-color);
            display: none;
        }
        
        .card.active {
            display: block;
        }
        
        .form-group {
            margin-bottom: 1.5rem;
        }
        
        label {
            display: block;
            margin-bottom: 0.5rem;
            font-size: 0.875rem;
            color: var(--text-secondary);
        }
        
        input[type="text"], input[type="password"], textarea, select {
            width: 100%;
            padding: 0.75rem;
            background-color: #0f172a;
            border: 1px solid var(--border-color);
            border-radius: 0.5rem;
            color: var(--text-color);
            font-family: inherit;
            font-size: 0.875rem;
            box-sizing: border-box;
        }
        
        textarea {
            resize: vertical;
            min-height: 120px;
        }
        
        button.action-btn {
            width: 100%;
            background-color: var(--primary-color);
            color: white;
            padding: 0.75rem;
            border: none;
            border-radius: 0.5rem;
            font-weight: 500;
            cursor: pointer;
            transition: background-color 0.2s;
        }
        
        button.action-btn:hover {
            background-color: var(--primary-hover);
        }
        
        .alert {
            padding: 0.75rem;
            border-radius: 0.5rem;
            margin-bottom: 1rem;
            font-size: 0.875rem;
        }
        
        .alert-success {
            background-color: rgba(34, 197, 94, 0.1);
            color: #4ade80;
            border: 1px solid rgba(34, 197, 94, 0.2);
        }
        
        .result-box {
            margin-top: 2rem;
            padding: 1rem;
            background-color: #0f172a;
            border-radius: 0.5rem;
            border: 1px solid var(--border-color);
            white-space: pre-wrap;
            display: none;
            font-family: monospace;
            max-height: 500px;
            overflow-y: auto;
        }
        
        .loading {
            display: inline-block;
            width: 1rem;
            height: 1rem;
            border: 2px solid rgba(255,255,255,0.3);
            border-radius: 50%;
            border-top-color: white;
            animation: spin 1s ease-in-out infinite;
            margin-left: 0.5rem;
            vertical-align: middle;
            display: none;
        }
        
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
        
        /* File Upload */
        .file-drop-area {
            position: relative;
            display: flex;
            align-items: center;
            justify-content: center;
            width: 100%;
            padding: 25px;
            border: 2px dashed var(--border-color);
            border-radius: 5px;
            transition: 0.2s;
            background-color: #0f172a;
            box-sizing: border-box;
        }
        
        .choose-file-btn {
            background-color: rgba(255, 255, 255, 0.04);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 3px;
            padding: 8px 15px;
            margin-right: 10px;
            font-size: 12px;
            text-transform: uppercase;
        }
        
        .file-input {
            position: absolute;
            left: 0;
            top: 0;
            height: 100%;
            width: 100%;
            cursor: pointer;
            opacity: 0;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>AIGC Admin Dashboard</h1>
            <a href="/admin/logout" class="logout">退出登录</a>
        </div>
        
        <div class="nav-tabs">
            <button class="nav-tab active" onclick="switchNav('token', this)">Token 管理</button>
            <button class="nav-tab" onclick="switchNav('detect', this)">AI 检测</button>
            <button class="nav-tab" onclick="switchNav('rewrite', this)">AI 改写</button>
            <button class="nav-tab" onclick="switchNav('file', this)">文件检测</button>
        </div>
        
        <!-- Token Tab -->
        <div id="token-card" class="card active">
            <h2>更新认证 Token</h2>
            <div id="token-msg" class="alert alert-success" style="display:none;"></div>
            
            <div class="form-group">
                <label for="token">Bearer Token (不包含 "Bearer " 前缀)</label>
                <textarea id="token-input" name="token" placeholder="eyJhbGciOiJIUzM4NCJ9..." required></textarea>
            </div>
            <button class="action-btn" onclick="updateToken()">更新 Token</button>
        </div>
        
        <!-- Detect Tab -->
        <div id="detect-card" class="card">
            <h2>AI 文本检测</h2>
            <div class="form-group">
                <label>API Key (Optional, 默认使用后端配置的Key)</label>
                <input type="password" id="detect-api-key" placeholder="如不填则无需鉴权(仅限Admin内网)" value="sk__YWPFq0Dpwsk8Tk-sBYfrqgMCGTGts6sEpOlE6E30IQ">
            </div>
            <div class="form-group">
                <label>检测文本</label>
                <textarea id="detect-text" placeholder="请输入需要检测的文本..."></textarea>
            </div>
            <div class="form-group">
                <label>语言</label>
                <select id="detect-lang">
                    <option value="zh">中文</option>
                    <option value="en">English</option>
                </select>
            </div>
            <button class="action-btn" onclick="performDetect()">
                开始检测 <span class="loading" id="detect-loading"></span>
            </button>
            <div id="detect-result" class="result-box"></div>
        </div>
        
        <!-- Rewrite Tab -->
        <div id="rewrite-card" class="card">
            <h2>AI 文本改写</h2>
            <div class="form-group">
                <label>改写文本</label>
                <textarea id="rewrite-text" placeholder="请输入需要改写的文本..."></textarea>
            </div>
            <div class="form-group">
                <label>组合 ID</label>
                <input type="text" id="rewrite-combo" placeholder="例如: 1" value="1">
            </div>
            <button class="action-btn" onclick="performRewrite()">
                开始改写 <span class="loading" id="rewrite-loading"></span>
            </button>
            <div id="rewrite-result" class="result-box"></div>
        </div>
        
        <!-- File Tab -->
        <div id="file-card" class="card">
            <h2>文件检测</h2>
            <div class="form-group">
                <label>选择文件 (支持 .txt, .docx)</label>
                <div class="file-drop-area">
                    <span class="choose-file-btn">选择文件</span>
                    <span class="file-msg">或将文件拖到这里</span>
                    <input class="file-input" type="file" id="file-input" accept=".txt,.docx">
                </div>
            </div>
            <div class="form-group">
                <label>语言</label>
                <select id="file-lang">
                    <option value="zh">chinese (zh)</option>
                    <option value="en">english (en)</option>
                </select>
            </div>
            <div class="form-group">
                <label>模式 (Mode)</label>
                <input type="text" id="file-mode" value="1" placeholder="Mode">
            </div>
            <div class="form-group">
                <label>平台 (Platform)</label>
                <input type="text" id="file-platform" value="web" placeholder="Platform">
            </div>
            <button class="action-btn" onclick="performFileUpload()">
                上传并检测 <span class="loading" id="file-loading"></span>
            </button>
            <div id="file-result" class="result-box"></div>
        </div>
    </div>

    <script>
        function switchNav(tabName, btnElement) {
            // Remove active class from all cards
            var cards = document.getElementsByClassName('card');
            for(var i=0; i<cards.length; i++) {
                cards[i].classList.remove('active');
            }
            
            // Remove active class from all nav-tabs
            var tabs = document.getElementsByClassName('nav-tab');
            for(var i=0; i<tabs.length; i++) {
                tabs[i].classList.remove('active');
            }
            
            // Activate selected card
            var card = document.getElementById(tabName + '-card');
            if(card) card.classList.add('active');
            
            // Activate selected tab button
            if (btnElement) {
                btnElement.classList.add('active');
            }
        }
        
        // File input logic
        var fileInput = document.getElementById('file-input');
        if (fileInput) {
            fileInput.addEventListener('change', function() {
                if (this.files && this.files.length > 0) {
                    document.querySelector('.file-msg').textContent = this.files[0].name;
                }
            });
        }
        
        function generateUUID() {
            return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
                var r = Math.random() * 16 | 0, v = c == 'x' ? r : (r & 0x3 | 0x8);
                return v.toString(16);
            });
        }

        async function updateToken() {
            const token = document.getElementById('token-input').value;
            if (!token) return alert('Token不能为空');
            
            const formData = new FormData();
            formData.append('token', token);
            
            try {
                const response = await fetch('/admin/token', {
                    method: 'POST',
                    body: formData
                });
                const result = await response.json();
                const msgBox = document.getElementById('token-msg');
                msgBox.textContent = result.message;
                msgBox.style.display = 'block';
                if (result.status === 'success') {
                    msgBox.className = 'alert alert-success';
                } else {
                    msgBox.className = 'alert';
                    msgBox.style.backgroundColor = 'rgba(239,68,68,0.1)';
                    msgBox.style.color = '#f87171';
                }
            } catch (e) {
                alert('更新失败: ' + e);
            }
        }
        
        // Use a designated API Key if provided, otherwise assume we are calling through admin proxy or public endpoint
        // NOTE: In this admin panel, we are calling the public endpoints directly. 
        // For security, you might normally want to proxy these through admin endpoints, 
        // but for a demo/debug tool, calling the public API is fine, assuming you have a key or the endpoint is open.
        // If your endpoints require an API Key, you MUST input it.
        function getApiKey() {
            var element = document.getElementById('detect-api-key');
            if (element) {
                return element.value.trim();
            }
            return '';
        }

        async function makeRequest(url, method, data, loadingId, resultId, isFileUpload = false) {
            const apiKey = getApiKey();
            // If API key is mandatory for your public endpoints, you'll need it.
            // If you want to bypass API key check for admin, you need to modify backend.
            // For now we assume user puts in key or backend allows it.
            
            if (!apiKey && !confirm("未输入API Key，请求可能会失败(403)。是否继续？")) return;
            
            const loading = document.getElementById(loadingId);
            const resultBox = document.getElementById(resultId);
            
            loading.style.display = 'inline-block';
            resultBox.textContent = '';
            resultBox.style.display = 'none';
            
            try {
                const headers = { 'accept': 'application/json' };
                if (apiKey) headers['X-API-Key'] = apiKey;
                
                if (!isFileUpload) {
                    headers['Content-Type'] = 'application/json';
                }
                
                const response = await fetch(url, {
                    method: method,
                    headers: headers,
                    body: isFileUpload ? data : JSON.stringify(data)
                });
                
                const result = await response.json();
                resultBox.textContent = JSON.stringify(result, null, 2);
                resultBox.style.display = 'block';
                resultBox.style.borderColor = response.ok ? 'var(--border-color)' : 'var(--error-color)';
                return result;
                
            } catch (error) {
                resultBox.textContent = 'Error: ' + error.message;
                resultBox.style.display = 'block';
                resultBox.style.borderColor = 'var(--error-color)';
                return null;
            } finally {
                loading.style.display = 'none';
            }
        }

        async function performDetect() {
            const text = document.getElementById('detect-text').value;
            const lang = document.getElementById('detect-lang').value;
            if (!text) return alert('请输入文本');
            await makeRequest('/ai/detector', 'POST', { text, language: lang }, 'detect-loading', 'detect-result');
        }
        
        async function performRewrite() {
            const text = document.getElementById('rewrite-text').value;
            const combo = document.getElementById('rewrite-combo').value;
            if (!text) return alert('请输入文本');
            await makeRequest('/ai/AIRewrite', 'POST', { text, combination_id: combo }, 'rewrite-loading', 'rewrite-result');
        }
        
        async function performFileUpload() {
            const fileInput = document.getElementById('file-input');
            if (fileInput.files.length === 0) return alert('请选择文件');
            
            const file = fileInput.files[0];
            const uuid = generateUUID();
            const lang = document.getElementById('file-lang').value;
            const mode = document.getElementById('file-mode').value;
            const platform = document.getElementById('file-platform').value;
            
            const formData = new FormData();
            formData.append('file', file);
            formData.append('uuid', uuid);
            formData.append('language', lang);
            formData.append('mode', mode);
            formData.append('platform', platform);
            
            const result = await makeRequest('/ai/upload', 'POST', formData, 'file-loading', 'file-result', true);
            if (result) setTimeout(() => checkFileStatus(uuid), 1000);
        }
        
        async function checkFileStatus(uuid) {
            const formData = new FormData();
            formData.append('uuid', uuid);
            const loading = document.getElementById('file-loading');
            loading.style.display = 'inline-block';
            
            try {
                const headers = { 'accept': 'application/json' };
                const apiKey = getApiKey();
                if (apiKey) headers['X-API-Key'] = apiKey;
                
                const response = await fetch('/ai/status_file', {
                    method: 'POST',
                    headers: headers,
                    body: formData
                });
                const result = await response.json();
                const resultBox = document.getElementById('file-result');
                resultBox.textContent = "=== STATUS UPDATE ===\\n" + JSON.stringify(result, null, 2);
            } catch (e) {
                console.error(e);
            } finally {
                loading.style.display = 'none';
            }
        }
    </script>
</body>
</html>
"""

def verify_cookie(request: Request) -> bool:
    """验证Cookie是否有效"""
    cookie = request.cookies.get(COOKIE_NAME)
    return cookie == settings.ADMIN_PASSWORD

@router.get("/login", response_class=HTMLResponse)
async def login_page():
    """登录页面"""
    return HTML_TEMPLATE_LOGIN

@router.post("/login", response_class=HTMLResponse)
async def login(password: str = Form(...)):
    """处理登录"""
    if password == settings.ADMIN_PASSWORD:
        response = RedirectResponse(url="/admin/dashboard", status_code=status.HTTP_302_FOUND)
        response.set_cookie(key=COOKIE_NAME, value=password, max_age=3600, httponly=True)
        return response
    else:
        return HTML_TEMPLATE_LOGIN.replace('display: none;', 'display: block;')

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
    return HTML_TEMPLATE_ADMIN

# 保留 /token 接口作为 JSON API 处理，或者为了兼容性，处理表单提交返回 HTML 片段或 JSON
@router.post("/token")
async def update_token(request: Request, token: str = Form(...)):
    """处理Token更新 (Ajax)"""
    if not verify_cookie(request):
        return {"status": "error", "message": "Unauthorized"}

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
