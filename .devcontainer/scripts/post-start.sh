#!/bin/bash

# MailAssistant 开发环境启动脚本
# 每次容器启动时执行

set -e

echo "🔄 Starting MailAssistant development services..."

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# 1. 检查数据库连接
echo -e "${YELLOW}Checking database connection...${NC}"
if pg_isready -h localhost -p 5432 -U postgres > /dev/null 2>&1; then
    echo -e "${GREEN}✓ PostgreSQL is running${NC}"
else
    echo -e "${RED}✗ PostgreSQL is not running${NC}"
    echo "Please check your database container"
fi

# 2. 检查 Redis 连接
echo -e "${YELLOW}Checking Redis connection...${NC}"
if redis-cli -h localhost ping > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Redis is running${NC}"
else
    echo -e "${RED}✗ Redis is not running${NC}"
    echo "Please check your Redis container"
fi

# 3. 激活 Python 环境变量
export PYTHONPATH=/workspace/backend:$PYTHONPATH

# 4. 显示当前分支和状态
echo -e "${YELLOW}Git status:${NC}"
cd /workspace
if [ -d .git ]; then
    BRANCH=$(git branch --show-current 2>/dev/null || echo "unknown")
    echo -e "Current branch: ${GREEN}$BRANCH${NC}"
    
    # 显示未提交的更改数量
    CHANGES=$(git status --porcelain 2>/dev/null | wc -l)
    if [ $CHANGES -gt 0 ]; then
        echo -e "${YELLOW}You have $CHANGES uncommitted changes${NC}"
    fi
fi

# 5. 检查环境变量
echo -e "${YELLOW}Checking environment configuration...${NC}"
if [ -f /workspace/.env ]; then
    # 检查关键环境变量
    if grep -q "your-.*-key" /workspace/.env; then
        echo -e "${YELLOW}⚠ Some environment variables are not configured${NC}"
        echo "Please update your .env file with actual values"
    else
        echo -e "${GREEN}✓ Environment variables configured${NC}"
    fi
else
    echo -e "${RED}✗ No .env file found${NC}"
    echo "Run: cp .env.example .env"
fi

# 6. 启动后台服务（可选）
# 如果需要自动启动某些服务，可以在这里添加
# 例如：启动后台任务调度器
# cd /workspace/backend && python -m app.scheduler &

# 7. 显示快速启动命令
echo ""
echo -e "${GREEN}Ready to develop!${NC}"
echo ""
echo "Quick commands:"
echo "  Start backend:  cd backend && python start_backend.py"
echo "  Start frontend: cd frontend && npm run dev"
echo "  Run tests:      cd backend && pytest"
echo "  Format code:    cd backend && black ."
echo ""

# 8. 检查是否有待运行的迁移
cd /workspace/backend
if [ -f alembic.ini ]; then
    PENDING=$(alembic history 2>/dev/null | grep -c "(head)" || echo "0")
    if [ "$PENDING" != "0" ]; then
        echo -e "${YELLOW}⚠ You have pending database migrations${NC}"
        echo "Run: cd backend && alembic upgrade head"
    fi
fi