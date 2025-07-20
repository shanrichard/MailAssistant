# 调试日志系统使用指南

## 功能说明

本系统用于开发环境下收集和查看前后端错误日志，方便调试问题。支持自动发送功能，让 Claude 能够实时获取错误信息。

## 前端错误收集

系统会自动捕获以下类型的错误：
- console.error 调用
- 未处理的 Promise rejection
- React 组件错误（通过 ErrorBoundary）

错误存储在浏览器的 localStorage 中：
- Key: `mailassistant_frontend_errors`
- 最多保存最近 100 条错误
- 包含时间戳、错误类型、消息、堆栈信息、URL

## 自动发送功能（新增）

系统现在支持错误自动发送：
- **严重错误立即发送**：未处理的 Promise rejection 会立即发送到后端
- **普通错误批量发送**：console.error 每 30 秒批量发送一次
- **去重机制**：相同的错误只发送一次
- **失败重试**：网络失败时自动重试（最多 3 次）
- **页面卸载时发送**：关闭页面时会尝试发送剩余错误

## 查看日志的方法

### 方法一：浏览器控制台（快速查看）

打开浏览器开发者工具，在控制台中输入：

```javascript
// 查看所有前端错误
window.debugLogs.get()

// 清除所有错误记录
window.debugLogs.clear()

// 发送日志到后端（用于 API 查看）
await window.debugLogs.send()

// 控制自动发送功能
window.debugLogs.setAutoSend(false)  // 关闭自动发送
window.debugLogs.setAutoSend(true)   // 开启自动发送（默认开启）
```

### 方法二：通过 API（推荐 Claude 使用）

1. **仅查看后端错误日志**
   ```bash
   curl http://localhost:8000/api/debug/logs/backend
   ```

2. **查看前后端所有错误日志**
   
   首先在浏览器控制台执行：
   ```javascript
   await window.debugLogs.send()
   ```
   
   这会返回所有日志数据。或者直接调用 API：
   ```bash
   curl -X POST http://localhost:8000/api/debug/logs/all \
     -H "Content-Type: application/json" \
     -d '{"frontend_errors": []}'
   ```

## 测试错误收集

在浏览器控制台中制造一些测试错误：

```javascript
// 测试 console.error
console.error('This is a test error')

// 测试 Promise rejection
Promise.reject(new Error('Test promise rejection'))

// 测试错误对象
console.error(new Error('Test error with stack'))
```

然后查看错误是否被正确收集：
```javascript
window.debugLogs.get()
```

## 注意事项

1. **仅在开发环境可用** - 生产环境不会启用错误收集和调试 API
2. **localStorage 容量限制** - 超过 100 条错误会自动删除最旧的
3. **隐私保护** - 注意错误信息可能包含敏感数据，仅用于开发调试
4. **性能影响** - 错误收集对性能影响极小，但仍建议仅在开发环境使用

## 常见问题

### Q: 为什么看不到 `window.debugLogs`？
A: 确保你在开发环境（`NODE_ENV=development`），并且已经刷新页面。

### Q: API 返回 403 错误？
A: 调试 API 仅在开发环境可用，检查后端的 `ENVIRONMENT` 设置。

### Q: 前端错误没有被捕获？
A: 某些类型的错误（如语法错误）可能无法被捕获。检查浏览器原生控制台。