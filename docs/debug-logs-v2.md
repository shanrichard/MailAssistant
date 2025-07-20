# 调试日志系统 v2 - 使用指南

## 改进内容

1. **统一存储** - 前后端错误都写入同一个日志文件 `backend/logs/app.log`
2. **JSON 格式** - 所有日志使用统一的 JSON 格式，便于查询和分析
3. **高级查询** - 支持按来源、级别、关键词过滤

## 使用方法

### 1. 查看所有错误（前端 + 后端）

```bash
# 前端需要先发送错误
curl -X POST http://localhost:8000/api/debug/logs/all \
  -H "Content-Type: application/json" \
  -d '{"frontend_errors": []}'
```

### 2. 高级搜索

```bash
# 只查看前端错误
curl "http://localhost:8000/api/debug/logs/search?source=frontend"

# 只查看错误级别的日志
curl "http://localhost:8000/api/debug/logs/search?level=error"

# 搜索包含特定关键词的错误
curl "http://localhost:8000/api/debug/logs/search?keyword=timeout"

# 组合查询
curl "http://localhost:8000/api/debug/logs/search?source=frontend&level=error&limit=50"
```

### 3. 前端使用

```javascript
// 查看本地错误
window.debugLogs.get()

// 发送到后端（错误会被写入日志文件）
await window.debugLogs.send()

// 清除本地错误
window.debugLogs.clear()
```

## 日志格式

```json
{
  "timestamp": "2025-07-20 12:00:00,123",
  "name": "frontend",
  "levelname": "ERROR",
  "message": "Cannot read property 'x' of undefined",
  "source": "frontend",
  "error_type": "unhandledRejection",
  "url": "http://localhost:3000/chat",
  "user_agent": "Mozilla/5.0...",
  "stack": "Error: Cannot read...",
  "frontend_timestamp": "2025-07-20T12:00:00.000Z"
}
```

## 特性

- 日志文件自动轮转（最大 10MB，保留 5 个备份）
- 仅在开发环境启用
- 前端错误自动发送（严重错误立即发送，普通错误批量发送）
- 支持关键词搜索和过滤