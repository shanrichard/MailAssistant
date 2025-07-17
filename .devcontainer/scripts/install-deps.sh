#!/bin/bash

# MailAssistant 依赖安装脚本
# 在容器创建时执行，可以被 Codespaces 预构建缓存

set -e

echo "📦 Installing MailAssistant dependencies..."
echo "=========================================="

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 1. 安装 Python 依赖
echo -e "${YELLOW}Installing Python dependencies...${NC}"
cd /workspace/backend

# 升级 pip
pip install --upgrade pip setuptools wheel

# 安装依赖
if [ -f requirements.txt ]; then
    pip install -r requirements.txt
    echo -e "${GREEN}✓ Python dependencies installed${NC}"
else
    echo -e "${YELLOW}⚠ No requirements.txt found in backend directory${NC}"
fi

# 安装开发依赖
if [ -f requirements-dev.txt ]; then
    pip install -r requirements-dev.txt
    echo -e "${GREEN}✓ Python dev dependencies installed${NC}"
fi

# 2. 安装前端依赖
echo -e "${YELLOW}Installing frontend dependencies...${NC}"
cd /workspace/frontend

if [ -f package.json ]; then
    # 使用 npm ci 如果有 package-lock.json，否则使用 npm install
    if [ -f package-lock.json ]; then
        npm ci
    else
        npm install
    fi
    echo -e "${GREEN}✓ Frontend dependencies installed${NC}"
else
    echo -e "${YELLOW}⚠ No package.json found in frontend directory${NC}"
fi

# 3. 安装全局工具（可选）
echo -e "${YELLOW}Installing global tools...${NC}"

# Python 工具
pip install --upgrade ipython ipdb

# Node.js 工具（如果需要）
# npm install -g typescript ts-node

echo ""
echo -e "${GREEN}✅ All dependencies installed successfully!${NC}"
echo ""