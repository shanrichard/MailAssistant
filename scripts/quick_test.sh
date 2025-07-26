#!/bin/bash
# MailAssistant 快速部署测试脚本

set -e

echo "🚀 MailAssistant Quick Deployment Test"
echo "======================================"

# 检查参数
if [ $# -lt 1 ]; then
    echo "Usage: ./quick_test.sh <backend_url> [frontend_url]"
    echo "Example: ./quick_test.sh https://your-app.railway.app https://your-app.vercel.app"
    exit 1
fi

BACKEND_URL=$1
FRONTEND_URL=${2:-""}

echo "Backend URL: $BACKEND_URL"
if [ -n "$FRONTEND_URL" ]; then
    echo "Frontend URL: $FRONTEND_URL"
fi

# 创建临时目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEMP_DIR=$(mktemp -d)
cd "$TEMP_DIR"

echo ""
echo "📦 Installing test dependencies..."
python3 -m pip install requests websockets --quiet

echo ""
echo "🧪 Running deployment tests..."
python3 "$SCRIPT_DIR/test_deployment.py" "$BACKEND_URL" "$FRONTEND_URL"

# 清理
cd "$SCRIPT_DIR"
rm -rf "$TEMP_DIR"

echo ""
echo "✨ Quick test completed!"