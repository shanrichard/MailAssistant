# MailAssistant GitHub Codespaces 配置

本目录包含了在 GitHub Codespaces 中运行 MailAssistant 项目所需的所有配置文件。

## 🚀 快速开始

### 在 GitHub Codespaces 中打开

1. 在 GitHub 仓库页面点击 **Code** 按钮
2. 选择 **Codespaces** 标签
3. 点击 **Create codespace on main**
4. 等待环境构建完成（首次约 5-10 分钟）
5. 环境准备就绪！

### 在本地 VS Code 中使用

1. 安装 [Docker Desktop](https://www.docker.com/products/docker-desktop)
2. 安装 VS Code 扩展：[Dev Containers](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers)
3. 在 VS Code 中打开项目
4. 按 `F1` 并选择 **Dev Containers: Reopen in Container**
5. 等待容器构建和启动

## 📁 文件结构

```
.devcontainer/
├── devcontainer.json      # 主配置文件
├── docker-compose.yml     # 多容器编排配置
├── Dockerfile            # 自定义开发环境镜像
├── scripts/
│   ├── init-db.sql       # 数据库初始化
│   ├── create-extensions.sql  # PostgreSQL 扩展安装
│   ├── post-create.sh    # 容器创建后脚本
│   └── post-start.sh     # 容器启动后脚本
├── .env.example          # 环境变量示例
└── README.md            # 本文件
```

## 🛠️ 包含的服务

### 主要服务

1. **应用容器** (`app`)
   - Python 3.10 + FastAPI 后端
   - Node.js 18 + React 前端
   - 所有开发工具预装

2. **PostgreSQL 数据库** (`db`)
   - PostgreSQL 16 with pgvector
   - 自动创建数据库和扩展
   - 端口：5432

3. **Redis 缓存** (`redis`)
   - Redis 7
   - 用于会话存储和缓存
   - 端口：6379

### 可选服务

4. **pgAdmin** (`pgadmin`)
   - 数据库管理界面
   - 端口：5050
   - 启用：`docker compose --profile tools up pgadmin`

## 🔧 配置说明

### 环境变量

1. 首次使用时，`.env` 文件会自动从 `.env.example` 创建
2. 更新 `.env` 中的以下关键配置：
   - Google OAuth 凭据
   - LLM API 密钥（至少配置一个）

### 端口映射

| 服务 | 端口 | 说明 |
|------|------|------|
| FastAPI | 8000 | 后端 API |
| React | 3000 | 前端应用 |
| PostgreSQL | 5432 | 数据库 |
| Redis | 6379 | 缓存 |
| pgAdmin | 5050 | 数据库管理（可选）|

### VS Code 扩展

开发环境会自动安装以下扩展：
- Python 相关：Python, Pylance, Black Formatter
- JavaScript 相关：ESLint, Prettier
- 数据库工具：SQLTools
- 其他：GitLens, Docker, Tailwind CSS

## 📝 常用命令

### 后端开发

```bash
# 启动后端服务
cd backend && python start_backend.py

# 运行测试
cd backend && pytest

# 代码格式化
cd backend && black .

# 数据库迁移
cd backend && alembic upgrade head
```

### 前端开发

```bash
# 启动前端服务
cd frontend && npm run dev

# 运行测试
cd frontend && npm test

# 构建生产版本
cd frontend && npm run build
```

### 数据库操作

```bash
# 连接到数据库
psql -h localhost -U postgres -d mailassistant

# 查看 pgvector 版本
psql -h localhost -U postgres -d mailassistant -c "SELECT version();"
```

## 🐛 故障排除

### 数据库连接失败

```bash
# 检查 PostgreSQL 状态
pg_isready -h localhost -p 5432

# 查看数据库日志
docker compose logs db
```

### 依赖安装问题

```bash
# 重新安装 Python 依赖
cd backend && pip install -r requirements.txt --force-reinstall

# 清理并重新安装前端依赖
cd frontend && rm -rf node_modules package-lock.json && npm install
```

### 容器重建

```bash
# 完全重建容器
docker compose down -v
docker compose build --no-cache
docker compose up -d
```

## 🔒 安全注意事项

1. **不要提交 `.env` 文件** - 已在 `.gitignore` 中
2. **定期更新密钥** - 特别是在生产环境
3. **使用强密码** - 数据库和服务密码应足够复杂

## 📚 更多信息

- [Dev Containers 文档](https://containers.dev/)
- [GitHub Codespaces 文档](https://docs.github.com/codespaces)
- [项目主 README](../README.md)