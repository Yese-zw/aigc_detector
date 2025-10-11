# API Key 使用指南

## 📖 概述

本 API 使用 **API Key** 进行认证和额度管理。每个 API Key 都有独立的额度，按字符数计费。

## 🔑 API Key 管理

### 1. 创建 API Key

**接口：** `POST /apikey/create`

**请求示例：**

```bash
curl -X POST "http://localhost:8001/apikey/create" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "测试密钥",
    "quota": 100000,
    "description": "用于测试的API Key"
  }'
```

**请求参数：**
- `name`: API Key 名称（必需）
- `quota`: 总额度，单位：字符数（必需）
- `description`: 描述信息（可选）

**响应示例：**
```json
{
  "status": "success",
  "data": {
    "key": "sk_AbC123XyZ...",
    "name": "测试密钥",
    "quota": 100000,
    "total_quota": 100000,
    "is_active": true,
    "created_at": "2024-10-11T10:00:00",
    "last_used_at": null,
    "description": "用于测试的API Key"
  },
  "message": "API Key 创建成功"
}
```

**⚠️ 重要：** 创建后请立即保存 `key` 字段的值，后续无法再次查看完整密钥！

---

### 2. 查看 API Key 列表

**接口：** `GET /apikey/list`

**请求示例：**

```bash
curl -X GET "http://localhost:8001/apikey/list"
```

**响应示例：**
```json
{
  "status": "success",
  "data": [
    {
      "key": "sk_AbC123XyZ...",
      "name": "测试密钥",
      "quota": 95000,
      "total_quota": 100000,
      "is_active": true,
      "created_at": "2024-10-11T10:00:00",
      "last_used_at": "2024-10-11T10:30:00",
      "description": "用于测试的API Key"
    }
  ],
  "total": 1
}
```

---

### 3. 查看 API Key 详细信息

**接口：** `GET /apikey/info/{api_key}`

**请求示例：**

```bash
curl -X GET "http://localhost:8001/apikey/info/sk_AbC123XyZ..."
```

---

### 4. 查看使用统计

**接口：** `GET /apikey/usage/{api_key}`

**请求示例：**

```bash
curl -X GET "http://localhost:8001/apikey/usage/sk_AbC123XyZ..."
```

**响应示例：**
```json
{
  "status": "success",
  "data": {
    "name": "测试密钥",
    "total_quota": 100000,
    "used_quota": 5000,
    "remaining_quota": 95000,
    "usage_percentage": 5.0,
    "is_active": true,
    "created_at": "2024-10-11T10:00:00",
    "last_used_at": "2024-10-11T10:30:00"
  }
}
```

---

### 5. 更新 API Key

**接口：** `PUT /apikey/update/{api_key}`

**请求示例：**

```bash
# 增加额度
curl -X PUT "http://localhost:8001/apikey/update/sk_AbC123XyZ...?add_quota=50000"

# 禁用 API Key
curl -X PUT "http://localhost:8001/apikey/update/sk_AbC123XyZ...?is_active=false"

# 修改名称
curl -X PUT "http://localhost:8001/apikey/update/sk_AbC123XyZ...?name=新名称"
```

**查询参数：**
- `is_active`: 是否激活（true/false）
- `add_quota`: 增加的额度（会累加到现有额度）
- `name`: 新的名称
- `description`: 新的描述

---

### 6. 删除 API Key

**接口：** `DELETE /apikey/delete/{api_key}`

**请求示例：**

```bash
curl -X DELETE "http://localhost:8001/apikey/delete/sk_AbC123XyZ..."
```

**响应示例：**
```json
{
  "status": "success",
  "message": "API Key 已删除"
}
```

---

## 🚀 使用 API Key 进行检测

### AI 文本检测接口

**接口：** `POST /ai/detector`

**认证方式：** 在请求头中添加 `X-API-Key`

**请求示例：**

```bash
curl -X POST "http://localhost:8001/ai/detector" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sk_AbC123XyZ..." \
  -d '{
    "text": "这是一段需要检测的文本内容",
    "language": "zh"
  }'
```

**请求参数：**
- `text`: 待检测的文本内容（必需）
- `language`: 语言类型，`zh`（中文）或 `en`（英文）（必需）

**请求头：**
- `X-API-Key`: 你的 API Key（必需）

**响应示例：**
```json
{
  "status": "success",
  "result": {
    "code": 200,
    "msg": "success",
    "data": {
      "ai_rate": 0.85,
      "human_rate": 0.15
    }
  },
  "quota_info": {
    "used": 15,
    "remaining": 99985
  }
}
```

**额度消耗：**
- 每次请求消耗的额度 = 文本字符数
- 例如：检测 100 字符的文本，消耗 100 额度

---

## 💰 额度管理

### 额度计算规则

- **消耗单位：** 字符数（包括中文、英文、标点符号等）
- **计费方式：** 按实际文本长度扣除
- **最小消耗：** 1 字符 = 1 额度

### 额度不足

当 API Key 额度不足时，会返回 `402 Payment Required` 错误：

```json
{
  "detail": "额度不足，剩余: 10 字符，需要: 100 字符"
}
```

### 充值额度

使用更新接口增加额度：

```bash
curl -X PUT "http://localhost:8001/apikey/update/sk_AbC123XyZ...?add_quota=100000"
```

---

## 🔒 安全建议

### 1. 保护你的 API Key

- ❌ 不要在代码中硬编码 API Key
- ❌ 不要将 API Key 提交到版本控制系统
- ✅ 使用环境变量存储 API Key
- ✅ 定期轮换 API Key

### 2. 使用示例

**Python 示例：**

```python
import os
import requests

API_KEY = os.getenv("AIGC_API_KEY")  # 从环境变量读取
url = "http://localhost:8001/ai/detector"

headers = {
    "Content-Type": "application/json",
    "X-API-Key": API_KEY
}

data = {
    "text": "这是待检测的文本",
    "language": "zh"
}

response = requests.post(url, json=data, headers=headers)
print(response.json())
```

**Node.js 示例：**

```javascript
const axios = require('axios');

const API_KEY = process.env.AIGC_API_KEY;

axios.post('http://localhost:8001/ai/detector', {
  text: '这是待检测的文本',
  language: 'zh'
}, {
  headers: {
    'Content-Type': 'application/json',
    'X-API-Key': API_KEY
  }
})
.then(response => {
  console.log(response.data);
})
.catch(error => {
  console.error(error.response.data);
});
```

### 3. 限制 API Key 权限

- 为不同的应用创建不同的 API Key
- 为每个 API Key 设置合理的额度
- 定期检查 API Key 使用情况
- 及时禁用或删除不再使用的 API Key

---

## 📊 日志记录

每次使用 API Key 时，服务器会记录详细日志：

```
======================================================================
📥 收到检测请求
   🔑 API Key: 测试密钥
   🌐 语言: zh
   📏 文本长度: 120 字符
   💰 剩余额度: 99880
✓ API Key 验证通过 - 名称: 测试密钥, 使用: 120, 剩余: 99880/100000
✓ 检测完成
   📊 扣除额度: 120
   💰 剩余额度: 99760
======================================================================
```

---

## ❓ 常见问题

### Q1: 如何获取 API Key？

A: 使用 `POST /apikey/create` 接口创建。创建后立即保存返回的 `key` 值。

### Q2: API Key 丢失了怎么办？

A: API Key 无法找回。建议：
1. 使用 `PUT /apikey/update/{api_key}?is_active=false` 禁用旧密钥
2. 创建新的 API Key

### Q3: 如何查看剩余额度？

A: 三种方式：
1. 调用 `GET /apikey/info/{api_key}` 查看详情
2. 调用 `GET /apikey/usage/{api_key}` 查看统计
3. 每次检测请求的响应中包含 `quota_info` 字段

### Q4: 额度用完了怎么办？

A: 使用 `PUT /apikey/update/{api_key}?add_quota=额度数量` 增加额度。

### Q5: 可以创建多个 API Key 吗？

A: 可以。每个 API Key 都有独立的额度和统计信息。

### Q6: API Key 会过期吗？

A: 不会。API Key 一旦创建，除非手动删除，否则永久有效。

### Q7: 如何限制某个 API Key 的使用？

A: 两种方式：
1. 禁用：`PUT /apikey/update/{api_key}?is_active=false`
2. 删除：`DELETE /apikey/delete/{api_key}`

---

## 📝 错误代码

| 状态码 | 说明 | 解决方案 |
|--------|------|----------|
| 401 | 未授权，缺少或无效的 API Key | 检查 `X-API-Key` 请求头 |
| 402 | 额度不足 | 充值额度 |
| 403 | API Key 已禁用 | 启用 API Key 或创建新的 |
| 404 | API Key 不存在 | 检查 API Key 是否正确 |

---

## 🔧 管理工具

### Swagger UI

访问 http://localhost:8001/docs 使用交互式 API 文档进行管理。

**特点：**
- 📝 可视化接口测试
- 📚 完整的接口文档
- 🧪 在线调试功能

### 命令行工具（可选）

创建一个简单的管理脚本：

```bash
#!/bin/bash
# apikey-manager.sh

API_BASE="http://localhost:8001"

case "$1" in
  create)
    curl -X POST "$API_BASE/apikey/create" \
      -H "Content-Type: application/json" \
      -d "{\"name\":\"$2\",\"quota\":$3}"
    ;;
  list)
    curl -X GET "$API_BASE/apikey/list"
    ;;
  info)
    curl -X GET "$API_BASE/apikey/info/$2"
    ;;
  *)
    echo "Usage: $0 {create|list|info} [args]"
    exit 1
    ;;
esac
```

使用示例：
```bash
# 创建 API Key
./apikey-manager.sh create "我的密钥" 100000

# 查看列表
./apikey-manager.sh list

# 查看详情
./apikey-manager.sh info sk_AbC123XyZ...
```

---

## 📞 支持

如有问题，请查看：
- [README.md](./README.md) - 项目文档
- [QUICKSTART.md](./QUICKSTART.md) - 快速上手
- Swagger UI - http://localhost:8001/docs

