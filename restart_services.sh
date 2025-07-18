#!/bin/bash

# MailAssistant 服务重启脚本
# 用于杀死现有进程并重新启动前后端服务

echo "🛑 正在停止现有服务..."

# 杀死后端进程
echo "  - 停止后端服务..."
pkill -f "python3.*start_backend" 2>/dev/null || true
pkill -f "uvicorn" 2>/dev/null || true
pkill -f "python3.*main:app" 2>/dev/null || true

# 杀死前端进程
echo "  - 停止前端服务..."
pkill -f "npm start" 2>/dev/null || true
pkill -f "react-scripts start" 2>/dev/null || true
pkill -f "node.*react-scripts" 2>/dev/null || true

# 杀死占用端口的进程
echo "  - 清理端口占用..."
lsof -ti:8000 | xargs kill -9 2>/dev/null || true
lsof -ti:3000 | xargs kill -9 2>/dev/null || true

echo "  - 等待进程完全停止..."
sleep 3

echo "✅ 所有服务已停止"
echo ""

# 启动后端
echo "🚀 启动后端服务..."
cd /workspace
python3 start_backend.py &
BACKEND_PID=$!

echo "  - 后端启动中... (PID: $BACKEND_PID)"
echo "  - 等待后端启动完成..."
sleep 8

# 检查后端是否启动成功
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "  ✅ 后端启动成功: http://localhost:8000"
else
    echo "  ❌ 后端启动失败，请检查日志"
fi

echo ""

# 启动前端
echo "🚀 启动前端服务..."
cd /workspace/frontend
npm start &
FRONTEND_PID=$!

echo "  - 前端启动中... (PID: $FRONTEND_PID)"
echo "  - 等待前端启动完成..."
sleep 15

# 检查前端是否启动成功
if curl -s http://localhost:3000 > /dev/null 2>&1; then
    echo "  ✅ 前端启动成功: http://localhost:3000"
else
    echo "  ❌ 前端启动失败，请检查日志"
fi

echo ""
echo "🎉 服务重启完成！"
echo ""
echo "📋 服务状态："
echo "  - 后端: http://localhost:8000 (PID: $BACKEND_PID)"
echo "  - 前端: http://localhost:3000 (PID: $FRONTEND_PID)"
echo "  - API文档: http://localhost:8000/docs"
echo "  - 健康检查: http://localhost:8000/health"
echo ""
echo "💡 提示："
echo "  - 使用 'ps aux | grep -E \"python3|npm\"' 查看进程状态"
echo "  - 使用 'kill -9 <PID>' 手动停止进程"
echo "  - 日志可以在终端中查看"