# 使用官方的 Python 开发容器基础镜像
FROM mcr.microsoft.com/devcontainers/python:1-3.10-bullseye

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    # 构建工具
    build-essential \
    gcc \
    g++ \
    make \
    # PostgreSQL 客户端
    postgresql-client \
    # Redis 客户端
    redis-tools \
    # 其他有用的工具
    curl \
    wget \
    vim \
    htop \
    ncdu \
    tree \
    jq \
    # 清理缓存
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 安装 Node.js 18 (如果 devcontainer features 没有安装)
# RUN curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
#     && apt-get install -y nodejs

# 创建工作目录
WORKDIR /workspace

# 复制 Python 依赖文件（如果存在）
COPY backend/requirements*.txt /tmp/backend/

# 安装 Python 依赖
RUN if [ -f /tmp/backend/requirements.txt ]; then \
        pip install --upgrade pip setuptools wheel && \
        pip install -r /tmp/backend/requirements.txt; \
    fi

# 复制前端依赖文件（如果存在）
COPY frontend/package*.json /tmp/frontend/

# 预安装前端依赖（可选，加速首次启动）
# RUN if [ -f /tmp/frontend/package.json ]; then \
#         cd /tmp/frontend && npm ci --only=production; \
#     fi

# 安装开发工具
RUN pip install --upgrade \
    ipython \
    ipdb \
    black \
    flake8 \
    pylint \
    mypy \
    pytest \
    pytest-cov \
    pytest-asyncio \
    httpx

# 设置 Python 路径
ENV PYTHONPATH=/workspace/backend:$PYTHONPATH

# 创建非 root 用户（devcontainer 会自动处理）
# USER vscode

# 设置工作目录权限
# RUN chown -R vscode:vscode /workspace

# 暴露端口
EXPOSE 8000 3000 5432 6379 5050

# 设置默认 shell
SHELL ["/bin/bash", "-c"]