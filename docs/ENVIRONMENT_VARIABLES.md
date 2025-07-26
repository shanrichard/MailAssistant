# MailAssistant 环境变量配置指南

本文档详细说明了 MailAssistant 生产环境所需的所有环境变量配置。

## 📋 Railway 后端环境变量

复制以下变量到 Railway 项目的 "Variables" 标签页：

### 🔴 必需变量（必须配置）

```bash
# 数据库配置
DATABASE_URL=postgresql://postgres:password@hostname:5432/railway

# Google OAuth 认证
GOOGLE_CLIENT_ID=123456789-abcdefgh.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-your-secret-here
GOOGLE_REDIRECT_URI=https://your-app.vercel.app/auth/callback

# 安全密钥（使用生成工具创建）
SECRET_KEY=your-32-character-secret-key-here
ENCRYPTION_KEY=your-32-byte-encryption-key-here

# LLM API（至少配置一个）
OPENAI_API_KEY=sk-your-openai-key-here
DEFAULT_LLM_PROVIDER=openai
DEFAULT_LLM_MODEL=gpt-4o

# 生产环境标识
ENVIRONMENT=production
DEBUG=false

# CORS 配置（重要：替换为您的域名）
CORS_ALLOWED_ORIGINS=["https://your-app.vercel.app"]
```

### 🟡 可选 LLM 变量（提高功能性）

```bash
# 可选的其他 LLM 提供商
ANTHROPIC_API_KEY=sk-ant-your-anthropic-key-here
GEMINI_API_KEY=your-gemini-key-here
```

### 🟢 系统配置变量（可使用默认值）

```bash
# 服务器配置
HOST=0.0.0.0
PORT=$PORT  # Railway 自动设置

# 应用信息
APP_NAME=MailAssistant
APP_VERSION=1.0.0

# 数据库连接池
DATABASE_POOL_SIZE=10
DATABASE_MAX_OVERFLOW=20

# JWT 配置
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=1440

# 日志配置
LOG_LEVEL=INFO

# 任务配置
TASK_RETRY_TIMES=3
TASK_RETRY_DELAY=60
DAILY_REPORT_DEFAULT_TIME=08:00
AUTO_SYNC_INTERVAL_HOURS=6

# Agent 性能配置
EMAIL_PROCESSOR_TIMEOUT=300
EMAIL_PROCESSOR_MAX_RETRIES=3
EMAIL_PROCESSOR_TEMPERATURE=0.1

CONVERSATION_HANDLER_TIMEOUT=180
CONVERSATION_HANDLER_MAX_RETRIES=2
CONVERSATION_HANDLER_TEMPERATURE=0.3
CONVERSATION_HANDLER_SESSION_TIMEOUT=3600

# 消息管理
MESSAGE_PRUNING_ENABLED=true
MAX_MESSAGES_COUNT=50
MAX_TOKENS_COUNT=3000

# WebSocket 配置
WEBSOCKET_HEARTBEAT_INTERVAL=30
WEBSOCKET_MAX_CONNECTIONS_PER_USER=3

# 缓存配置
PREFERENCE_CACHE_TTL=300
REPORT_CACHE_TTL=900

# API 性能监控
ENABLE_API_PERFORMANCE_MONITORING=true
API_PERFORMANCE_REPORT_THRESHOLD=1.0
```

## 🌐 Vercel 前端环境变量

复制以下变量到 Vercel 项目的 "Settings" → "Environment Variables"：

### 🔴 必需变量

```bash
# API 端点（替换为您的 Railway URL）
REACT_APP_API_URL=https://your-backend.railway.app
REACT_APP_WS_URL=https://your-backend.railway.app

# Google OAuth（与后端相同）
REACT_APP_GOOGLE_CLIENT_ID=123456789-abcdefgh.apps.googleusercontent.com

# 生产环境标识
REACT_APP_DEBUG=false
```

## 🔧 密钥生成工具

### SECRET_KEY 生成

```bash
# 方法 1：Python
python -c "import secrets; print(secrets.token_urlsafe(32))"

# 方法 2：OpenSSL
openssl rand -base64 32

# 方法 3：在线工具
# 访问：https://randomkeygen.com/ 选择 "Fort Knox Passwords"
```

### ENCRYPTION_KEY 生成

```bash
# 生成 32 字节密钥
python -c "import secrets; print(secrets.token_urlsafe(32))"

# 注意：必须是32字节，用于数据加密
```

## 🔍 配置验证清单

### Railway 后端检查

- [ ] `DATABASE_URL` 连接测试成功
- [ ] `GOOGLE_CLIENT_ID` 格式正确（.apps.googleusercontent.com 结尾）
- [ ] `GOOGLE_REDIRECT_URI` 指向 Vercel 域名
- [ ] `SECRET_KEY` 长度至少 32 字符
- [ ] `ENCRYPTION_KEY` 32 字节长度
- [ ] `OPENAI_API_KEY` 以 `sk-` 开头
- [ ] `CORS_ALLOWED_ORIGINS` JSON 数组格式
- [ ] `ENVIRONMENT=production` 已设置

### Vercel 前端检查

- [ ] `REACT_APP_API_URL` 指向 Railway URL
- [ ] `REACT_APP_WS_URL` 与 API URL 一致
- [ ] `REACT_APP_GOOGLE_CLIENT_ID` 与后端一致
- [ ] `REACT_APP_DEBUG=false` 已设置

## 🔐 安全最佳实践

### 密钥安全

1. **永不提交密钥到代码仓库**
2. **使用强随机密钥生成器**
3. **定期轮换 API 密钥**
4. **限制 API 密钥权限**

### CORS 安全

```bash
# ❌ 不安全：允许所有源
CORS_ALLOWED_ORIGINS=["*"]

# ✅ 安全：只允许特定域名
CORS_ALLOWED_ORIGINS=["https://yourdomain.vercel.app"]

# ✅ 多域名配置
CORS_ALLOWED_ORIGINS=["https://yourdomain.vercel.app","https://custom-domain.com"]
```

### 数据库安全

- 使用 Railway 托管的 PostgreSQL（自动加密）
- 启用 SSL 连接（默认）
- 限制数据库访问来源

## 📊 环境变量优先级

1. **Platform 环境变量**（Railway/Vercel 控制台）
2. **.env.production 文件**（如果存在）
3. **默认值**（代码中定义）

## 🔧 调试配置问题

### 验证后端配置

```bash
# 检查健康状态
curl https://your-backend.railway.app/health

# 检查环境信息（仅开发环境可用）
curl https://your-backend.railway.app/debug/config
```

### 验证前端配置

打开浏览器开发者工具控制台，输入：

```javascript
// 检查 API URL 配置
console.log('API URL:', process.env.REACT_APP_API_URL);

// 检查 WebSocket URL 配置  
console.log('WS URL:', process.env.REACT_APP_WS_URL);

// 检查 Google Client ID
console.log('Google Client ID:', process.env.REACT_APP_GOOGLE_CLIENT_ID);
```

## 🚨 常见配置错误

### 1. 数据库连接错误

```bash
# ❌ 错误格式
DATABASE_URL=postgres://user:pass@host:port/db

# ✅ 正确格式
DATABASE_URL=postgresql://user:pass@host:port/db
```

### 2. CORS 数组格式错误

```bash
# ❌ 错误：字符串格式
CORS_ALLOWED_ORIGINS=https://yourdomain.com

# ✅ 正确：JSON 数组格式
CORS_ALLOWED_ORIGINS=["https://yourdomain.com"]
```

### 3. URL 末尾斜杠问题

```bash
# ❌ 错误：有末尾斜杠
REACT_APP_API_URL=https://your-backend.railway.app/

# ✅ 正确：无末尾斜杠
REACT_APP_API_URL=https://your-backend.railway.app
```

## 📞 获取帮助

如果配置遇到问题：

1. **检查本文档的常见错误部分**
2. **使用提供的验证脚本**
3. **查看 Railway/Vercel 控制台日志**
4. **确认所有必需变量都已设置**

---

配置正确的环境变量是成功部署的关键。请仔细检查每个变量的值和格式！