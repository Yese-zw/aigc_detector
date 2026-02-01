from typing import Optional
from fastapi import APIRouter, Request, Form, status, Depends, Query
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from app.core.config import settings
from app.core.redis_client import get_redis_client
from app.core.logger import logger
import os
from app.services.apikey_service import APIKeyService
from app.models.apikey import APIKeyCreate

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
            flex-wrap: wrap;
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

        /* Logs & Tables */
        .log-box {
            background-color: #0d1117;
            color: #d1d5db;
            font-family: monospace;
            padding: 1rem;
            border-radius: 0.5rem;
            height: 600px;
            overflow-y: auto;
            white-space: pre-wrap;
            border: 1px solid var(--border-color);
            font-size: 0.85rem;
        }
        
        .table-responsive {
            width: 100%;
            overflow-x: auto;
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
            color: var(--text-color);
            font-size: 0.9rem;
        }
        
        th, td {
            text-align: left;
            padding: 1rem;
            border-bottom: 1px solid var(--border-color);
        }
        
        th {
            color: var(--text-secondary);
            font-weight: 500;
            background-color: rgba(0,0,0,0.2);
        }
        
        tr:hover td {
            background-color: rgba(255,255,255,0.02);
        }
        
        .tag {
            padding: 0.25rem 0.5rem;
            border-radius: 0.25rem;
            font-size: 0.75rem;
            font-weight: 600;
        }
        .tag-green { background: rgba(34, 197, 94, 0.2); color: #4ade80; }
        .tag-gray { background: rgba(148, 163, 184, 0.2); color: #94a3b8; }
        
        .btn-sm {
            padding: 0.4rem 0.8rem;
            font-size: 0.8rem;
            border-radius: 0.3rem;
            background-color: rgba(239, 68, 68, 0.2);
            color: #f87171;
            border: 1px solid rgba(239, 68, 68, 0.3);
            cursor: pointer;
            transition: all 0.2s;
        }
        .btn-sm:hover {
            background-color: rgba(239, 68, 68, 0.3);
        }

        /* Modal */
        .modal-overlay {
            display:none; 
            position:fixed; 
            top:0; 
            left:0; 
            width:100%; 
            height:100%; 
            background:rgba(0,0,0,0.6); 
            backdrop-filter: blur(4px);
            align-items:center; 
            justify-content:center; 
            z-index:9999;
        }
        .modal-container {
            width:90%;
            max-width:450px; 
            background:var(--card-bg);
            padding: 2rem;
            border-radius: 1rem;
            border: 1px solid var(--border-color);
            box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.3);
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
            <button class="nav-tab" onclick="switchNav('logs', this)">系统日志</button>
            <button class="nav-tab" onclick="switchNav('keys', this)">Key 管理</button>
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

        <!-- Logs Tab -->
        <div id="logs-card" class="card">
            <div class="header" style="margin-bottom: 1rem;">
                <h2 style="margin:0">今日系统日志</h2>
                <button onclick="loadLogs()" class="action-btn" style="width: auto; padding: 0.5rem 1rem;">刷新日志</button>
            </div>
            <div id="log-content" class="log-box">点击上方按钮加载日志...</div>
        </div>

        <!-- Keys Tab -->
        <div id="keys-card" class="card">
            <div class="header" style="margin-bottom: 2rem;">
                <h2 style="margin:0">API Key 管理</h2>
                <div style="display:flex; gap:1rem;">
                     <button onclick="loadKeys()" class="action-btn" style="width: auto; padding: 0.5rem 1rem; background: transparent; border: 1px solid var(--border-color);">刷新列表</button>
                     <button onclick="document.getElementById('create-key-modal').style.display='flex'" class="action-btn" style="width: auto; padding: 0.5rem 1rem;">+ 新建 Key</button>
                </div>
            </div>

            <div class="table-responsive">
                <table id="keys-table">
                    <thead>
                        <tr>
                            <th>名称</th>
                            <th>API Key / 描述</th>
                            <th>额度 (已用 / 总额)</th>
                            <th>状态</th>
                            <th>操作</th>
                        </tr>
                    </thead>
                    <tbody id="keys-table-body">
                        <tr><td colspan="5" style="text-align:center; color:var(--text-secondary)">加载中...</td></tr>
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Create Key Modal -->
        <div id="create-key-modal" class="modal-overlay">
            <div class="modal-container">
               <h2 style="margin-bottom:1.5rem">新建 API Key</h2>
               <div class="form-group">
                   <label>Key 名称</label>
                   <input type="text" id="new-key-name" placeholder="例如: web-client-01">
               </div>
               <div class="form-group">
                   <label>描述信息</label>
                   <input type="text" id="new-key-desc" placeholder="可选备注">
               </div>
               <div class="form-group">
                   <label>字符配额</label>
                   <input type="number" id="new-key-quota" value="1000000">
               </div>
               <div style="display:flex; gap:1rem; margin-top:2rem;">
                   <button class="action-btn" onclick="createKey()">立即创建</button>
                   <button class="action-btn" style="background:transparent; border:1px solid var(--border-color);" onclick="document.getElementById('create-key-modal').style.display='none'">取消</button>
               </div>
            </div>
        </div>

        <!-- Edit Key Modal -->
        <div id="edit-key-modal" class="modal-overlay">
            <div class="modal-container">
               <h2 style="margin-bottom:1.5rem">修改 API Key</h2>
               <input type="hidden" id="edit-key-id">
               <div class="form-group">
                   <label>Key 名称</label>
                   <input type="text" id="edit-key-name">
               </div>
               <div class="form-group">
                   <label>描述信息</label>
                   <input type="text" id="edit-key-desc">
               </div>
               <div class="form-group">
                   <label>增加额度 (正数增加，负数减少，0不处理)</label>
                   <input type="number" id="edit-key-quota-add" value="0">
                   <p style="font-size:0.8rem; color:var(--text-secondary); margin-top:0.5rem">当前剩余: <span id="edit-key-current-quota"></span></p>
               </div>
               <div class="form-group">
                   <label>状态</label>
                   <select id="edit-key-active">
                       <option value="true">正常</option>
                       <option value="false">禁用</option>
                   </select>
               </div>
               <div style="display:flex; gap:1rem; margin-top:2rem;">
                   <button class="action-btn" onclick="submitEditKey()">保存修改</button>
                   <button class="action-btn" style="background:transparent; border:1px solid var(--border-color);" onclick="document.getElementById('edit-key-modal').style.display='none'">取消</button>
               </div>
            </div>
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

            // Auto-load data
            if(tabName === 'logs') loadLogs();
            if(tabName === 'keys') loadKeys();
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
        
        function getApiKey() {
            var element = document.getElementById('detect-api-key');
            if (element) {
                return element.value.trim();
            }
            return '';
        }

        async function makeRequest(url, method, data, loadingId, resultId, isFileUpload = false) {
            const apiKey = getApiKey();
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

        /* Logs & Keys Logic */
        async function loadLogs() {
            const logContent = document.getElementById('log-content');
            logContent.textContent = "加载中...";
            try {
                const res = await fetch('/admin/logs');
                const data = await res.json();
                // Ensure newlines are preserved
                logContent.textContent = data.content; 
                // Auto scroll to bottom
                logContent.scrollTop = logContent.scrollHeight;
            } catch(e) {
                logContent.textContent = "加载日志失败: " + e;
            }
        }

        async function loadKeys() {
            const tbody = document.getElementById('keys-table-body');
            tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;">加载中...</td></tr>';
            try {
                const res = await fetch('/admin/keys');
                const json = await res.json();
                if(json.status === 'success') {
                    const list = json.data;
                    tbody.innerHTML = '';
                    if(list.length === 0) {
                         tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;">暂无数据</td></tr>';
                         return;
                    }
                    list.forEach(item => {
                        const tr = document.createElement('tr');
                        
                        const statusTag = item.is_active 
                            ? '<span class="tag tag-green">正常</span>' 
                            : '<span class="tag tag-gray">禁用</span>';
                            
                        // quota is remaining, total_quota is history total
                        const remaining = item.quota || 0;
                        const total = item.total_quota || 0;
                        const used = total - remaining;
                        // Percent of USAGE (how much is gone)
                        const percent = total > 0 ? ((used / total) * 100).toFixed(1) : 0;
                        // Or percent of REMAINING? Usually bars show remaining or used. 
                        // Let's show Remaining bar (green).
                        const remainingPercent = total > 0 ? ((remaining / total) * 100).toFixed(1) : 0;
                        
                        tr.innerHTML = `
                            <td><div style="font-weight:600">${item.name}</div></td>
                            <td>
                                <div style="font-family:monospace; color:var(--primary-color)">${item.key}</div>
                                <div style="font-size:0.8rem; color:var(--text-secondary)">${item.description || '-'}</div>
                            </td>
                            <td>
                                <div style="display:flex; justify-content:space-between; font-size:0.85rem">
                                    <span>剩余: ${remaining}</span>
                                    <span style="color:var(--text-secondary)">总: ${total}</span>
                                </div>
                                <div style="width:100%; height:4px; background:#334155; border-radius:2px; margin-top:4px;" title="剩余额度占比">
                                    <div style="width:${remainingPercent}%; height:100%; background:var(--primary-color); border-radius:2px;"></div>
                                </div>
                            </td>
                            <td>${statusTag}</td>
                            <td>
                                <button class="btn-sm" style="margin-right:0.5rem; background:rgba(99,102,241,0.2); color:#818cf8; border-color:rgba(99,102,241,0.3)" onclick='openEditModal(${JSON.stringify(item)})'>修改</button>
                                <button class="btn-sm" onclick="deleteKey('${item.key}')">删除</button>
                            </td>
                        `;
                        tbody.appendChild(tr);
                    });
                } else {
                     tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;color:red;">加载失败</td></tr>';
                }
            } catch(e) {
                 tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;color:red;">' + e + '</td></tr>';
            }
        }

        async function createKey() {
            const name = document.getElementById('new-key-name').value;
            const desc = document.getElementById('new-key-desc').value;
            const quota = document.getElementById('new-key-quota').value;
            
            if(!name) return alert('请输入名称');
            
            const formData = new FormData();
            formData.append('name', name);
            formData.append('description', desc);
            formData.append('quota', quota);
            
            try {
                const res = await fetch('/admin/keys', { method:'POST', body:formData });
                const json = await res.json();
                if(json.status === 'success') {
                    alert('创建成功: ' + json.data.key);
                    document.getElementById('create-key-modal').style.display = 'none';
                    loadKeys();
                    // Clear inputs
                    document.getElementById('new-key-name').value = '';
                    document.getElementById('new-key-desc').value = '';
                } else {
                    alert('创建失败: ' + (json.detail || json.message));
                }
            } catch(e) {
                alert('系统错误: ' + e);
            }
        }

        async function deleteKey(key) {
            if(!confirm('确定要删除这个 Key 吗？无法恢复！')) return;
            try {
                const res = await fetch('/admin/keys/' + key, { method:'DELETE' });
                const json = await res.json();
                if(json.status === 'success') {
                    loadKeys();
                } else {
                    alert('删除失败');
                }
            } catch(e) {
                alert('删除失败: ' + e);
            }
        }

        function openEditModal(item) {
            document.getElementById('edit-key-id').value = item.key;
            document.getElementById('edit-key-name').value = item.name;
            document.getElementById('edit-key-desc').value = item.description || '';
            document.getElementById('edit-key-quota-add').value = 0;
            document.getElementById('edit-key-current-quota').textContent = item.quota;
            document.getElementById('edit-key-active').value = item.is_active ? 'true' : 'false';
            
            document.getElementById('edit-key-modal').style.display = 'flex';
        }

        async function submitEditKey() {
            const key = document.getElementById('edit-key-id').value;
            const name = document.getElementById('edit-key-name').value;
            const desc = document.getElementById('edit-key-desc').value;
            const addQuota = document.getElementById('edit-key-quota-add').value;
            const isActive = document.getElementById('edit-key-active').value;

            const url = '/admin/keys/' + key + '?name=' + encodeURIComponent(name) + 
                        '&description=' + encodeURIComponent(desc) + 
                        '&add_quota=' + addQuota + 
                        '&is_active=' + isActive;

            try {
                const res = await fetch(url, { method:'PUT' });
                const json = await res.json();
                if(json.status === 'success') {
                    alert('修改成功');
                    document.getElementById('edit-key-modal').style.display = 'none';
                    loadKeys();
                } else {
                    alert('修改失败: ' + (json.detail || json.message));
                }
            } catch(e) {
                alert('修改失败: ' + e);
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
