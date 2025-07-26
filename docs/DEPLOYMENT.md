# MailAssistant 生产环境部署指南

本指南将帮助您将 MailAssistant 部署到生产环境：后端部署到 Railway，前端部署到 Vercel。

## 🚀 快速部署概览

1. **Railway 后端部署** - 一键部署 FastAPI 后端服务
2. **Vercel 前端部署** - 一键部署 React 前端应用
3. **环境变量配置** - 配置生产环境变量
4. **DNS 和域名设置** - 配置自定义域名（可选）

## 📋 部署前准备

### 必需账号
- [Railway](https://railway.app) 账号
- [Vercel](https://vercel.com) 账号  
- [Google Cloud Console](https://console.cloud.google.com) 项目（用于 OAuth）
- 至少一个 LLM API 密钥（OpenAI/Anthropic/Google）

### 必需信息收集
- PostgreSQL 数据库连接信息
- Google OAuth 客户端 ID 和密钥
- LLM API 密钥
- 生产环境域名信息

## 🛤️ Railway 后端部署

### 步骤 1：创建 Railway 项目

1. 登录 [Railway](https://railway.app)
2. 点击 "New Project" → "Deploy from GitHub repo"
3. 选择您的 MailAssistant 仓库
4. Railway 会自动检测到 `railway.json` 配置文件

### 步骤 2：添加 PostgreSQL 数据库

1. 在 Railway 项目中点击 "New Service"
2. 选择 "PostgreSQL"
3. 等待数据库创建完成
4. 复制数据库连接 URL（格式：`postgresql://user:password@host:port/dbname`）

### 步骤 3：配置环境变量

在 Railway 项目的 "Variables" 标签页中添加以下环境变量：

```bash
# 必需变量
DATABASE_URL=postgresql://user:password@host:port/dbname  # 从第2步获取
GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=https://your-frontend-domain.vercel.app/auth/callback
SECRET_KEY=your-super-strong-secret-key-at-least-32-characters-long
ENCRYPTION_KEY=your-32-byte-base64-encoded-encryption-key
OPENAI_API_KEY=sk-your-openai-api-key

# 自动设置的变量
ENVIRONMENT=production
DEBUG=false
HOST=0.0.0.0
PORT=$PORT

# CORS 配置（重要：替换为您的 Vercel 域名）
CORS_ALLOWED_ORIGINS=["https://your-frontend-domain.vercel.app"]
```

### 步骤 4：获取后端 URL

部署成功后，Railway 会提供一个 URL，格式类似：
`https://your-project-name.railway.app`

保存此 URL，前端部署时需要用到。

## 🌐 Vercel 前端部署

### 步骤 1：创建 Vercel 项目

1. 登录 [Vercel](https://vercel.com)
2. 点击 "New Project" → "Import Git Repository"
3. 选择您的 MailAssistant 仓库
4. Vercel 会自动检测到 `vercel.json` 配置文件

### 步骤 2：配置环境变量

在 Vercel 项目的 "Settings" → "Environment Variables" 中添加：

```bash
REACT_APP_API_URL=https://your-backend.railway.app  # 从 Railway 获取
REACT_APP_WS_URL=https://your-backend.railway.app   # 同上
REACT_APP_GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com  # 同后端
REACT_APP_DEBUG=false
```

### 步骤 3：获取前端 URL

部署成功后，Vercel 会提供一个 URL，格式类似：
`https://your-project-name.vercel.app`

## 🔐 Google OAuth 配置

### 更新 OAuth 回调 URL

1. 打开 [Google Cloud Console](https://console.cloud.google.com)
2. 选择您的项目 → "APIs & Services" → "Credentials"
3. 点击您的 OAuth 2.0 客户端 ID
4. 在 "Authorized redirect URIs" 中添加：
   ```
   https://your-frontend-domain.vercel.app/auth/callback
   ```
5. 保存更改

## 🔧 生产环境配置优化

### 密钥生成

使用以下命令生成安全密钥：

```bash
# SECRET_KEY 生成
python -c "import secrets; print(secrets.token_urlsafe(32))"

# ENCRYPTION_KEY 生成
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 环境变量安全检查清单

- [ ] `DATABASE_URL` 包含正确的 PostgreSQL 连接信息
- [ ] `SECRET_KEY` 至少 32 个字符的强密钥
- [ ] `ENCRYPTION_KEY` 32 字节的 base64 编码密钥
- [ ] `GOOGLE_CLIENT_ID` 和 `GOOGLE_CLIENT_SECRET` 匹配
- [ ] `GOOGLE_REDIRECT_URI` 指向正确的前端域名
- [ ] `CORS_ALLOWED_ORIGINS` 只包含信任的域名
- [ ] 所有 LLM API 密钥有效且有足够配额

## 🧪 部署验证

### 自动健康检查

Railway 会自动使用 `/health` 端点进行健康检查。您也可以手动验证：

```bash
# 检查后端健康状态
curl https://your-backend.railway.app/health

# 预期响应：
{
  "status": "healthy",
  "app": "MailAssistant", 
  "version": "1.0.0"
}
```

### 功能测试清单

- [ ] 前端应用加载正常
- [ ] Google OAuth 登录流程工作
- [ ] 用户认证状态保持
- [ ] Gmail 同步功能正常
- [ ] Agent 对话功能正常
- [ ] WebSocket 连接稳定
- [ ] 日报生成功能正常

## 🚨 故障排除

### 常见问题

**1. 数据库连接失败**
- 检查 `DATABASE_URL` 格式是否正确
- 确认 PostgreSQL 服务正在运行
- 验证网络连接和防火墙设置

**2. OAuth 认证失败**
- 确认 `GOOGLE_REDIRECT_URI` 与前端域名匹配
- 检查 Google Cloud Console 中的回调 URL 配置
- 验证客户端 ID 和密钥是否正确

**3. CORS 错误**
- 确认 `CORS_ALLOWED_ORIGINS` 包含前端域名
- 检查域名格式（包含 https://）
- 验证前后端 URL 配置一致

**4. Socket.IO 连接失败**
- 检查 WebSocket 支持是否启用
- 确认 CORS 配置包含 WebSocket 源
- 验证防火墙不阻止 WebSocket 连接

### 查看日志

**Railway 日志：**
```bash
# 通过 Railway CLI
railway logs

# 或在 Railway 控制台查看
```

**Vercel 日志：**
- 在 Vercel 控制台的 "Functions" → "View Function Logs"

### 性能监控

**推荐监控指标：**
- API 响应时间
- 数据库连接池状态
- WebSocket 连接数量
- 内存和 CPU 使用率
- 错误率和异常日志

## 🔄 更新和维护

### 自动部署

推送到 main 分支会自动触发部署：

```bash
git push origin main
```

### 手动重部署

**Railway:**
- 在控制台点击 "Redeploy"

**Vercel:**
- 在控制台点击 "Redeploy"

### 数据库迁移

新的数据库迁移会在部署时自动运行（通过 `Procfile` 中的 `release` 命令）。

## 📞 支持

如果遇到部署问题：

1. 检查本指南的故障排除部分
2. 查看项目 Issues 页面
3. 运行提供的测试脚本进行诊断

---

## 🎉 部署成功！

恭喜！您的 MailAssistant 现在已经在生产环境中运行。访问您的前端 URL 开始使用这个 AI 驱动的邮件助手吧！

记住定期：
- 备份数据库
- 更新依赖包
- 监控性能指标
- 检查安全更新