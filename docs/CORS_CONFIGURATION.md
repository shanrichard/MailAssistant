# CORS 配置指南

## 概述

本文档说明如何正确配置 MailAssistant 的 CORS（跨源资源共享）设置，确保应用安全性。

## 配置方法

### 1. 开发环境

在开发环境的 `.env` 文件中添加：

```env
# CORS配置（开发环境）
CORS_ALLOWED_ORIGINS=["http://localhost:3000", "http://127.0.0.1:3000"]
```

### 2. 生产环境

在生产环境的 `.env` 文件中，必须指定具体的前端域名：

```env
# CORS配置（生产环境）
CORS_ALLOWED_ORIGINS=["https://your-app.com", "https://www.your-app.com"]
```

### 3. 多域名支持

如果需要支持多个前端域名，可以添加多个源：

```env
CORS_ALLOWED_ORIGINS=["https://app.example.com", "https://admin.example.com", "https://beta.example.com"]
```

## 安全注意事项

### ❌ 不要这样做

```env
# 危险：允许所有源
CORS_ALLOWED_ORIGINS=["*"]
```

这会允许任何网站向你的API发送请求，可能导致：
- CSRF（跨站请求伪造）攻击
- 数据泄露
- API滥用

### ✅ 应该这样做

1. **明确指定允许的源**
   - 只添加你控制的前端域名
   - 使用完整的URL，包括协议（http/https）

2. **区分环境**
   - 开发环境：可以包含 localhost
   - 生产环境：只包含实际的域名

3. **定期审查**
   - 定期检查允许的源列表
   - 移除不再使用的域名

## 测试CORS配置

使用提供的测试脚本验证配置：

```bash
python test_cors.py
```

## 故障排除

### 问题：前端请求被阻止

1. 检查浏览器控制台的CORS错误信息
2. 确认前端域名是否在允许列表中
3. 检查是否包含了正确的协议（http/https）

### 问题：预检请求失败

确保配置包含了必要的请求方法和头：
- Methods: GET, POST, PUT, DELETE, OPTIONS
- Headers: Authorization, Content-Type

## 配置示例

### Vercel部署

```env
CORS_ALLOWED_ORIGINS=["https://mail-assistant.vercel.app"]
```

### 自定义域名

```env
CORS_ALLOWED_ORIGINS=["https://mail.mycompany.com"]
```

### 开发+预览环境

```env
CORS_ALLOWED_ORIGINS=["http://localhost:3000", "https://preview.myapp.com"]
```