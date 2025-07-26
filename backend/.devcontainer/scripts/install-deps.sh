#!/bin/bash

# MailAssistant 依赖安装脚本
# 在容器创建后执行，以正确的用户身份运行

set -e

echo "📦 Installing MailAssistant dependencies..."
echo "=========================================="

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 确保 npm 缓存目录权限正确（如果以 root 运行）
if [ "$EUID" -eq 0 ]; then
    echo -e "${YELLOW}Running as root, fixing npm cache permissions...${NC}"
    mkdir -p /home/vscode/.npm
    chown -R vscode:vscode /home/vscode/.npm || true
    chown -R vscode:vscode /home/vscode/.cache || true
fi

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
    # 确保以正确的用户身份运行 npm
    if [ "$EUID" -eq 0 ]; then
        # 如果是 root，使用 sudo 切换到 vscode 用户
        if [ -f package-lock.json ]; then
            sudo -u vscode -E npm ci
        else
            sudo -u vscode -E npm install
        fi
    else
        # 否则直接运行
        if [ -f package-lock.json ]; then
            npm ci
        else
            npm install
        fi
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
# if [ "$EUID" -eq 0 ]; then
#     sudo -u vscode -E npm install -g typescript ts-node
# else
#     npm install -g typescript ts-node
# fi

echo ""
echo -e "${GREEN}✅ All dependencies installed successfully!${NC}"
echo ""