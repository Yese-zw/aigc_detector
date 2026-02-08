from typing import Optional
from fastapi import APIRouter, Request, Form, status, Depends, Query
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from app.core.config import settings
from app.core.redis_client import get_redis_client
from app.core.logger import logger
import os
import jwt
import datetime
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
            
            <div id="token-status-box" style="background:#0f172a; padding:1.5rem; border-radius:1rem; margin-bottom:2rem; border:1px solid var(--border-color)">
                <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:1rem">
                    <span style="color:var(--text-secondary); font-weight:500">Token 状态</span>
                    <span id="ts-status" class="tag" style="background:#334155; color:#94a3b8">检测中...</span>
                </div>
                <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap:1.5rem; margin-bottom:1.5rem">
                     <div>
                        <div style="color:var(--text-secondary); font-size:0.85rem; margin-bottom:0.4rem">过期时间</div>
                        <div id="ts-expire" style="font-family:monospace; font-size:1.1rem">--</div>
                     </div>
                     <div>
                        <div style="color:var(--text-secondary); font-size:0.85rem; margin-bottom:0.4rem">剩余有效期</div>
                        <div id="ts-remaining" style="font-family:monospace; font-size:1.1rem; color:#4ade80">--</div>
                     </div>
                </div>
                <div style="background:#1e293b; padding:1rem; border-radius:0.5rem; font-size:0.8rem; color:var(--text-secondary); word-break:break-all; border:1px solid rgba(255,255,255,0.05)">
                    <div style="margin-bottom:0.5rem; opacity:0.7">Payload Preview:</div>
                    <span id="ts-payload" style="font-family:monospace">--</span>
                </div>
            </div>

            <div id="token-msg" class="alert alert-success" style="display:none;"></div>

            <!-- 自动获取 Token 模块 -->
            <div style="background:#0f172a; padding:1.5rem; border-radius:1rem; margin-bottom:2rem; border:1px solid var(--border-color)">
                <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:1rem">
                    <div>
                        <div style="color:var(--text-color); font-weight:600; font-size:1rem">自动获取 Token</div>
                        <div style="color:var(--text-secondary); font-size:0.8rem; margin-top:0.2rem">通过微信扫码快速获取最新认证 Token</div>
                    </div>
                    <button class="action-btn" id="wx-login-btn" onclick="startWxLogin()" style="width:auto; padding:0.6rem 1.2rem; background:linear-gradient(135deg, #07c160, #06ad56); border:none">
                        微信登录获取
                    </button>
                </div>
                <div id="wx-qr-container" style="display:none; text-align:center; margin-top:1rem; border-top:1px solid rgba(255,255,255,0.05); padding-top:1.5rem;">
                    <div style="display:inline-block; background:white; padding:12px; border-radius:12px; box-shadow:0 10px 25px rgba(0,0,0,0.2)">
                        <img id="wx-qr-img" src="" style="width:180px; height:180px; display:block">
                    </div>
                    <div id="wx-status" style="color:var(--text-secondary); font-size:0.9rem; margin-top:1rem; font-weight:500">请使用微信扫码登录</div>
                    <div style="color:#6366f1; font-size:0.75rem; margin-top:0.3rem; cursor:pointer" onclick="startWxLogin()">刷新二维码</div>
                </div>
            </div>
            
            <div class="form-group">
                <label for="token">更新 Token (Bearer Token)</label>
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
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.5rem">
                    <label style="margin-bottom:0">检测文本</label>
                    <span onclick="setNextDefaultText('detect-text')" style="font-size:0.75rem; color:#6366f1; cursor:pointer; font-weight:500">点击更换下一个示例 ></span>
                </div>
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
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.5rem">
                    <label style="margin-bottom:0">改写文本</label>
                    <span onclick="setNextDefaultText('rewrite-text')" style="font-size:0.75rem; color:#6366f1; cursor:pointer; font-weight:500">点击更换下一个示例 ></span>
                </div>
                <textarea id="rewrite-text" placeholder="请输入需要改写的文本..."></textarea>
            </div>
            <div class="form-group">
                <label>组合 ID</label>
                <input type="text" id="rewrite-combo" placeholder="例如: 1" value="20">
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
            if(tabName === 'token') loadTokenInfo();
        }
        
        // Default Texts for rotation
        const defaultTexts = [
            "人工智能技术正在以惊人的速度改变着我们的世界。通过深度学习和神经网络，计算机现在可以识别人脸、翻译语言，甚至创作出优美的艺术作品。然而，随着技术的发展，我们也面临着伦理和透明度方面的挑战。",
            "气候变化是当今人类面临的最严峻挑战之一。全球气温升高导致冰川融化、海平面上升以及极端天气事件频发。为了保护地球家园，各国必须共同努力，减少温室气体排放，并积极转向太阳能等清洁能源。",
            "保持健康的生活方式对于提高生活质量至关重要。均衡的健康饮食、定期的体育锻炼以及充足的高质量睡眠可以增强免疫系统，有效预防多种疾病。同时关注心理健康，学会在快节奏生活中舒缓工作压力。",
            "随着全球化进程的不断深入，跨文化交流变得越来越普遍。了解不同国家的传统习俗和价值观，有助于消除偏见，增进国际间的理解与合作。各民族文化的多元并存，丰富了人类文明的内涵，促进了进步。",
            "数字化转型已成为企业提升竞争力的关键。通过引入大数据分析和云计算技术，企业能够更精准地洞察市场需求，优化业务流程。然而，在这个数字时代，如何保障用户数据安全和隐私仍然是一个核心焦点。",
            "教育是推动社会进步的基石。随着在线学习平台的兴起，知识的获取变得更加民主化和便捷化。不仅学生可以随时随地学习，成年人也可以利用终身学习的机会提升技能。未来的教育将更加注重培养创新能力。",
            "现代医学的进步显著延长了人类的平均寿命。从基因编辑到纳米医疗机器人，许多曾经难以治愈的疾病现在有了新的希望。然而，医疗资源的公平分配仍是一个全球性课题，我们需要建立更完善的公共卫生体系。",
            "城市化进程的加快带来了便利，也带来了交通拥堵和环境污染等问题。建设“智慧城市”利用物联网技术优化城市管理，成为解决这些挑战的一种方案。合理的城市规划和绿色空间的保留对宜居性至关重要。",
            "太空探索一直激励着人类追求未知的梦想。从月球着陆到火星探测，我国航天事业取得了令世人瞩目的成就。深入探索宇宙不仅能拓展人类的生存边界，还能带回地球稀缺的资源，并促进基础科学研究的发展。",
            "人工智能在艺术领域的应用引发了广泛讨论。虽然AI可以生成精美的画面和旋律，但许多人认为其缺乏人类情感中蕴含的独特性。艺术的本质在于表达与沟通，而AI作品更多是复杂算法对已有数据的重组。",
            "区块链技术以其去中心化和不可篡改的特性，在金融、供应链等领域展现出巨大潜力。它不仅提高了交易的透明度，还降低了中介成本，增强了互信。尽管还面临着性能瓶颈，但其长期应用前景非常广阔。",
            "环境保护意识的提升推动了循环经济的发展。通过产品的回收利用和废弃物的减量化，我们能够更有效地保护自然资源，减少对环境的破坏。每个消费者的微小选择，积累起来都能为可持续发展贡献力量。",
            "社交媒体在改变我们社交方式的同时，也对心理健康产生了复杂影响。我们需要警惕“信息茧房”的负面效应，学会筛选真实客观的信息，并注意适度使用电子设备，在现实生活中建立更深刻的情感连接。",
            "量子计算作为下一代计算技术，有望在密码破解、新材料研发等领域实现突破。其运行原理利用了量子叠加和纠缠等特性，拥有远超传统计算机的处理能力。虽然还在实验阶段，但其展示的潜力让人振奋。",
            "可持续农业通过科学的耕作方式，能够在保障粮食产量的同时减少化肥和农药的使用。这不仅保护了土壤质量和生物多样性，还为消费者提供了更健康的食物。支持本地有机农业发展是实现生态平衡的关键。",
            "虚拟现实和增强现实技术正在重新定义娱乐与办公。通过沉浸式的交互体验，用户仿佛身临其境地进入虚拟世界，或是将数字信息叠加在现实中。这些技术将极大地丰富我们的感知，尤其是在远程教学和协作中。",
            "文化遗产保护是每个国家的共同责任。传统手工艺、古建筑以及非物质文化遗产承载着民族的记忆。利用数字化建模技术记录这些财富，不仅能进行有效的修复保护，还能让更多年轻人感受到传统文化的魅力。",
            "机器人技术正在从工厂流水线走向我们的日常生活。从扫地机器人到陪护机器人，智能化设备提升了居家生活的便利程度。未来，具备高度感知和决策能力的机器人将在助残养老和危险搜救等领域发挥更大作用。",
            "海洋是地球上最大的生态系统，但正受到过度捕捞和塑料污染的威胁。保护海洋生物多样性、建立更多保护区已迫在眉睫。海洋不仅调节着全球气候，还为全人类提供了丰富的资源储备，必须科学开发。",
            "网络安全在当今高度联动的世界中显得尤为关键。针对基础设施和金融系统的攻击可能造成巨大的社会动荡。我们需要不断升级防护技术，加强国际合作打击犯罪，并提高公众的防范意识，保障信息资产安全。",
            "生物多样性的丧失正在威胁着地球的生命支持系统。每种生物都在生态圈中发挥着特定作用，保护它们就是保护人类自己。通过建立自然保护区、实施禁捕禁猎等措施，我们能够为后代留下一个生机勃勃的世界。",
            "物联网的发展让“万物互联”成为可能。从智能家居到智慧交通，传感器将设备连接在一起，实现了数据的自动采集和远程控制。这种高效的自动化将显著提高能源效率和生活质量，同时也对协议统一提出了需求。",
            "新能源汽车的推广是交通领域减排的重要途径。随着电池技术的突破和充电设施的完善，越来越多的人选择电动出行。这不仅有助于减少城市尾气污染，还能促进能源结构的转型，降低对化石燃料的依赖程度。",
            "移动支付的普及彻底改变了人们的消费习惯。从现金到刷脸识别，支付变得前所未有的快捷与安全。这种数字化的交易方式不仅提升了商业运作效率，还为普惠金融提供了可能，让偏远地区也能共享便捷服务。",
            "可穿戴设备正在成为个人健康管理的好助手。通过监测心率、血氧以及睡眠数据，用户可以实时了解自己的身体状况。这种预防性的健康管理有助于及早发现潜在问题，并激励人们养成更科学的运动锻炼习惯。",
            "大数据技术的应用让政府治理变得更加精准高效。通过对海量信息的分析，各部门能够更快捷地响应公众需求，优化资源配置。在突发公共事件中，数据驱动的决策机制展现了无可比拟的优势，提升了应急管理力。",
            "远程办工和柔性工时制正在成为职场新趋势。基于云桌面的协作工具让地理位置不再是工作的障碍。这种模式不仅有助于员工平衡职业与生活，还能让企业在全球范围内吸引顶尖人才，同时也减少了通勤排放。",
            "3D打印技术正在引发制造业的革命。通过逐层堆叠材料，我们可以制造出传统工艺难以实现的复杂结构。这项技术在航空航天、医疗器械甚至房屋建造等领域都展现了惊人的应用力，并推动了定制化生产。",
            "心理学在现代生活中的应用日益广泛。从缓解工作焦虑到改善亲子关系，科学的心理指导能帮助我们建立更积极的心态。心理教育的普及有助于构建更和谐的社会网络，减少心理冲突，提升大众的幸福感指标。",
            "科幻小说通过对未来的想象，激发了人类对科学探索的热情。虽然许多奇思妙想尚未实现，但它们预示了技术发展的多种可能，并引导我们思考人机关系和伦理准则。这种思想的实验对预判科技走向具有独特价值。",
            "自动驾驶汽车的研发目标是显著降低由于人为失误导致的交通事故。通过复杂的激光雷达和感知算法，汽车能够实时识别路况。随着技术的成熟和法律法规的完善，未来出行将变得更加自动化、安全且高效简洁。",
            "基因科技的进步让精准医疗变得触手可及。通过对基因序列的分析，医生可以为每位患者制定个性化的治疗方案，提高药物疗效并减少副作用。这一领域仍面临着成本和伦理的考量，但依然是未来医学的重要方向。",
            "微塑料污染已延伸到地球最偏远的角落，包括深海和极地。这些难以察觉的颗粒通过食物链最终可能影响人类健康。减少一次性塑料制品的使用、开发可降解材料是应对这一全球性环境危机的主要手段和共识。",
            "共享经济通过资源整合提高了社会整体效率。从共享单车到共享办公室，这种模式降低了使用门槛并减少了浪费。虽然在管理和规范上遇到过挑战，但其强调“使用权胜过所有权”的理念已深入人心并持续进化。",
            "纳米材料因其独特的物理化学特性，正在电子元件和化工催化领域大显身手。更轻量、更高强度的材料不仅能提升产品性能，还能降低能耗。随着制备工艺的标准化，纳米技术将更广泛地赋能各行各业的升级变革。",
            "极简主义生活方式受到越来越多年轻人的青睐。通过精简物品和欲望，人们试图在物质过剩的时代找回内心的平静。这种理念不仅有助于减少过度消费带来的焦虑，还与可持续发展的环保目标不谋而合。",
            "人工智能翻译的准确度在过去几年中突飞猛进。基于神经网络的翻译引擎能够更好地理解语境和习语，极大地方便了国际旅行和商务往来。然而，对于文学作品中细腻情感的捕捉，人类译者的经验依然不可替代。",
            "体育竞技的核心价值不仅在于胜负，更在于拼搏进取和团队协作的精神。在大赛中展现出的坚韧意志能激励千万人。这种跨国界的文化符号是增进民间交流的桥梁，也为人们提供了健康积极的精神追求和体魄。",
            "电子商务的极速发展促使物流行业全面升级。快递无人机和自动分拣系统的投入使用，让包裹能以更短的时间送达。高效的供应链不仅便利了消费者的生活，也为农产品进城和跨境贸易提供了坚实的物理支撑。",
            "智慧医疗系统利用AI辅助影像诊断，显著提高了早期疾病的检出率。这种技术方案缓解了医疗资源分布不均的问题，特别是在基层医院，能为医生提供可靠的诊断建议。技术赋能医疗在提升效率的同时更具人性化。",
            "传统节日是民族文化记忆的根脉。通过庆祝春节、中秋等佳节，我们传承着尊老爱幼、祈愿和平的优良传统。这些精神财富在现代社会依然发挥着凝聚人心、增强归属感的作用，并连接着海内外的每一位华夏儿微。",
            "电子竞技已成为当下最受年轻人欢迎的竞技项目之一。专业的赛事组织和广泛的观赛群体，让电竞逐渐被承认为正式的体育运动。它不仅考验选手的反应力和战术策略，还背后带动了庞大的文化创意产业集群。",
            "城市公共空间的优化设计能显著提升市民的幸福感。增加公园绿地、建设舒适的步道和露天广场，为人们提供了休闲与社交的场所。宜人的城市景观不仅能美化环境，还能激发城市的活力，并吸引更多游客和创意者。",
            "反电信网络诈骗是保护公民财产安全的重要斗争。通过技术拦截和全民反诈APP的推广，我们正在筑起一道坚实的信息长城。公众需要时刻保持警惕，不轻信陌生来电，并学会用法律武器保障自己的合法权益。",
            "科学普及工作的深入开展，有助于在全社会形成热爱科学、尊重知识的良好氛围。通过趣味性的实验展示和深入浅出的讲解，孩子们可以近距离感受科学的魅力。提高公民的科学素养，是国家实现高质量发展的关键。",
            "新能源储能技术是解决风能、太阳能波动性的关键。通过大规模电池方阵或抽水蓄能，我们可以将多余的清洁能源储存起来在需要时释放。稳定的电网支撑是实现碳中和目标的必要前提，也是当前科研的热点领域。",
            "人工智能辅助写作正在成为创作者的利器。它能提供灵感参考、优化语法结构，并生成不同风格的草稿。虽然它不能完全取代人类的创造性思维，但作为效率工具，它能让写作过程变得更轻松、更有趣、更多样化。",
            "低碳旅行倡导人们在旅游过程中减少碳足迹，例如选择绿色交通工具、入住环保酒店。这种环保的旅行方式不仅能让游客更深入地体验当地生态，还促进了目的地的环境保护。负责任的旅游是实现可持续发展的关键。",
            "增强现实技术在室内设计中的应用，让用户可以在装修前就看到家具摆放后的实际效果。这种直观的交互体验节省了沟通成本，并避免了尺寸选择不当带来的烦恼。AR技术正在各垂直领域解决用户的真实痛点。",
            "人类对宇宙起源的探索从未停止。通过詹姆斯·韦布等太空望远镜，我们能够捕捉到百亿年前的星系影像。这些最基础的探索虽然离日常生活很远，但它定义了人类在宇宙中的位置，并指引着理论物理的前行路线。"
        ];

        let currentDetectIdx = Math.floor(Math.random() * defaultTexts.length);
        let currentRewriteIdx = Math.floor(Math.random() * defaultTexts.length);

        function setNextDefaultText(targetId) {
            const el = document.getElementById(targetId);
            if (!el) return;
            
            if (targetId === 'detect-text') {
                currentDetectIdx = (currentDetectIdx + 1) % defaultTexts.length;
                el.value = defaultTexts[currentDetectIdx];
            } else if (targetId === 'rewrite-text') {
                currentRewriteIdx = (currentRewriteIdx + 1) % defaultTexts.length;
                el.value = defaultTexts[currentRewriteIdx];
            }
        }

        // Load initial data
        window.addEventListener('DOMContentLoaded', () => {
             loadTokenInfo();
             const detText = document.getElementById('detect-text');
             const rewText = document.getElementById('rewrite-text');
             if (detText) detText.value = defaultTexts[currentDetectIdx];
             if (rewText) rewText.value = defaultTexts[currentRewriteIdx];
        });
        
        // File input logic
        var fileInput = document.getElementById('file-input');
        if (fileInput) {
            fileInput.addEventListener('change', function() {
                if (this.files && this.files.length > 0) {
                    document.querySelector('.file-msg').textContent = this.files[0].name;
                }
            });
        }
        
        let wxPollInterval = null;

        async function startWxLogin() {
            const btn = document.getElementById('wx-login-btn');
            const qrContainer = document.getElementById('wx-qr-container');
            const qrImg = document.getElementById('wx-qr-img');
            const statusText = document.getElementById('wx-status');
            
            btn.disabled = true;
            btn.style.opacity = '0.7';
            btn.textContent = '请求中...';
            
            try {
                // 调用后端开始登录接口
                const response = await fetch('https://xrzbk.lanbeike.online/api/wxlogin/start', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' }
                });
                const result = await response.json();
                
                if (result.code === 200) {
                    qrImg.src = result.data.qr_url;
                    qrContainer.style.display = 'block';
                    statusText.textContent = '请打开微信扫码';
                    statusText.style.color = 'var(--text-color)';
                    btn.textContent = '等待扫码中...';
                    
                    // 开始轮询
                    if (wxPollInterval) clearInterval(wxPollInterval);
                    wxPollInterval = setInterval(() => pollWxStatus(result.data.request_id), 2500);
                } else {
                    alert('获取二维码失败: ' + result.msg);
                    btn.disabled = false;
                    btn.style.opacity = '1';
                    btn.textContent = '重新获取';
                }
            } catch (e) {
                console.error(e);
                alert('连接登录服务器失败，请检查网络或稍后再试');
                btn.disabled = false;
                btn.style.opacity = '1';
                btn.textContent = '重新获取';
            }
        }

        async function pollWxStatus(requestId) {
            const statusText = document.getElementById('wx-status');
            const btn = document.getElementById('wx-login-btn');
            
            try {
                const response = await fetch(`https://xrzbk.lanbeike.online/api/wxlogin/status?request_id=${requestId}`);
                const result = await response.json();
                
                if (result.code === 200) {
                    if (result.data.status === 'DONE') {
                        clearInterval(wxPollInterval);
                        wxPollInterval = null;
                        
                        // 填入 token 并更新 UI
                        document.getElementById('token-input').value = result.data.token;
                        statusText.textContent = '登录成功！正在自动更新系统 Token...';
                        statusText.style.color = '#4ade80';
                        
                        document.getElementById('wx-qr-container').style.display = 'none';
                        btn.disabled = false;
                        btn.style.opacity = '1';
                        btn.textContent = '获取成功';
                        btn.style.background = 'var(--success-color)';
                        
                        // 自动触发更新
                        updateToken();
                    } else if (result.data.status === 'EXPIRED') {
                        clearInterval(wxPollInterval);
                        wxPollInterval = null;
                        statusText.textContent = '二维码已过期';
                        statusText.style.color = '#ef4444';
                        btn.disabled = false;
                        btn.style.opacity = '1';
                        btn.textContent = '二维码过期，点击重试';
                    } else if (result.data.status === 'WAITING') {
                        statusText.textContent = '请打开微信扫码...';
                    } else if (result.data.status === 'SCANNED') {
                        statusText.textContent = '已扫码，请在手机上确认登录';
                        statusText.style.color = '#6366f1';
                    }
                }
            } catch (e) {
                console.error('Polling error:', e);
            }
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
        
        async function loadTokenInfo() {
            const statusEl = document.getElementById('ts-status');
            const expireEl = document.getElementById('ts-expire');
            const remainEl = document.getElementById('ts-remaining');
            const payloadEl = document.getElementById('ts-payload');
            
            try {
                const res = await fetch('/admin/token/info');
                const data = await res.json();
                
                if (data.status === 'active') {
                    statusEl.textContent = '有效';
                    statusEl.className = 'tag tag-green';
                    statusEl.style.background = 'rgba(34, 197, 94, 0.2)';
                    statusEl.style.color = '#4ade80';
                    
                    expireEl.textContent = data.expires_at;
                    
                    // Format remaining time nicely
                    const secs = data.remaining_seconds;
                    const hours = Math.floor(secs / 3600);
                    const minutes = Math.floor((secs % 3600) / 60);
                    remainEl.textContent = `${hours}小时 ${minutes}分钟`;
                    
                    if (hours < 1) {
                         remainEl.style.color = '#f87171'; // Red warning
                         statusEl.textContent = '即将过期';
                         statusEl.style.color = '#f87171';
                         statusEl.style.background = 'rgba(239, 68, 68, 0.2)';
                    } else {
                         remainEl.style.color = '#4ade80';
                    }
                    
                    payloadEl.textContent = JSON.stringify(data.claims, null, 2);
                } else if (data.status === 'expired') {
                    statusEl.textContent = '已过期';
                    statusEl.className = 'tag';
                    statusEl.style.background = 'rgba(239, 68, 68, 0.2)';
                    statusEl.style.color = '#f87171';
                    
                    expireEl.textContent = data.expires_at;
                    remainEl.textContent = '0秒';
                    remainEl.style.color = '#f87171';
                    payloadEl.textContent = JSON.stringify(data.claims, null, 2);
                } else {
                    statusEl.textContent = data.message || '未知';
                    statusEl.style.background = '#334155';
                    expireEl.textContent = '--';
                    remainEl.textContent = '--';
                    payloadEl.textContent = '--';
                }
            } catch (e) {
                statusEl.textContent = '加载失败';
                console.error(e);
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
