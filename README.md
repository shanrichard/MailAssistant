# MailAssistant - AI驱动的智能邮件管家

<div align="center">
  <h3>让AI帮你处理邮件，专注于真正重要的事</h3>
  <p>基于LangGraph的Gmail智能助手，自动分析、分类和生成邮件日报</p>
</div>

## 🎯 项目愿景

MailAssistant致力于解决现代人的邮件过载问题。通过AI技术自动处理繁琐的邮件管理工作，让用户能够专注于真正重要的邮件和工作。

## ✨ 核心特性

### 智能邮件处理
- 🤖 **AI自动分析**：使用多种LLM（OpenAI/Anthropic/Google）分析邮件重要性和紧急程度
- 📊 **智能分类**：自动将邮件分类为工作、个人、广告等类别
- 📝 **每日摘要**：生成个性化的邮件日报，突出重要信息
- 🎯 **个性化学习**：根据用户反馈不断优化分析准确度
- 🔄 **智能同步**：基于Gmail History API的增量同步机制

### 对话式交互
- 💬 **LangGraph对话引擎**：基于LangGraph的多轮对话Agent
- 🔍 **智能搜索**：用自然语言搜索历史邮件
- ⚡ **批量操作**：一句话完成批量标记、归档等操作
- 📱 **实时通信**：WebSocket实时推送和交互
- 🛠️ **丰富工具集**：邮件搜索、标记、归档等多种工具

### 安全可靠
- 🔐 **OAuth2认证**：使用Google官方认证，不存储密码
- 🔒 **数据加密**：所有敏感数据加密存储
- 🛡️ **隐私保护**：本地部署选项，数据不离开您的服务器
- ✅ **权限最小化**：仅请求必要的Gmail权限

## 🛠️ 技术架构

```
┌─────────────────────────────────────┐
│     React Frontend (TypeScript)    │
│   Pages: Chat|DailyReport|Settings │
│   State: Zustand + React Query     │
└──────────────┬──────────────────────┘
               │ REST API + WebSocket
┌──────────────┴──────────────────────┐
│         FastAPI Backend             │
│   LangGraph Agents + LangChain     │
│   ConversationHandler + EmailTools │
└──────────────┬──────────────────────┘
               │
┌──────────────┴──────────────────────┐
│   PostgreSQL + SQLAlchemy ORM      │
│   Alembic Migrations + Models      │
└─────────────────────────────────────┘
```

### 技术栈详情

**前端框架**
- React 18 + TypeScript
- Tailwind CSS + HeadlessUI
- Zustand状态管理 + React Query
- React Router + Socket.IO Client

**后端框架**
- FastAPI + Uvicorn
- LangGraph 0.5.3 (最新)
- LangChain + 多LLM提供商支持
- SQLAlchemy 2.0 + Alembic
- WebSocket实时通信

**AI集成**
- OpenAI GPT-4o
- Anthropic Claude
- Google Gemini
- 智能工具调用和流式响应

**数据库**
- PostgreSQL 数据库
- Alembic数据库迁移
- 完整的数据模型：User、Email、Conversation、DailyReport等

## 🚀 快速开始

### 环境要求
- Python 3.11+ (推荐3.11.x)
- Node.js 18+
- PostgreSQL 15+
- Google Cloud Console账号（用于OAuth配置）

### 1. 克隆项目
```bash
git clone https://github.com/yourusername/MailAssistant.git
cd MailAssistant
```

### 2. 配置环境变量
复制环境变量模板并填写配置：
```bash
cp .env.example .env
```

关键环境变量配置：
```bash
# 数据库
DATABASE_URL=postgresql://user:password@localhost:5432/mailassistant

# Google OAuth
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URI=http://localhost:3000/auth/callback

# 安全密钥
SECRET_KEY=your-secret-key
ENCRYPTION_KEY=your-32-byte-encryption-key

# LLM API（至少配置一个）
OPENAI_API_KEY=your-openai-key
ANTHROPIC_API_KEY=your-anthropic-key
GEMINI_API_KEY=your-gemini-key
DEFAULT_LLM_PROVIDER=openai
DEFAULT_LLM_MODEL=gpt-4o

# 应用配置
DEBUG=true
ENVIRONMENT=development
```

### 3. 启动后端
```bash
# 创建虚拟环境（在项目根目录）
python3 -m venv .venv
source .venv/bin/activate  # Linux/Mac
# 或 .venv\Scripts\activate  # Windows

# 安装依赖
cd backend
pip install -r requirements.txt

# 运行数据库迁移
alembic upgrade head

# 启动开发服务器（回到根目录）
cd ..
python3 start_backend.py
```

后端将在 http://localhost:8000 启动

### 4. 启动前端
```bash
# 新开终端
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm start
```

前端将在 http://localhost:3000 启动

### 5. 访问应用
打开浏览器访问 http://localhost:3000，使用Google账号登录即可开始使用。

## 📖 使用指南

### 主要功能页面

1. **登录页面** - Google OAuth2认证
2. **DailyReport页面** - 查看每日邮件摘要和分析
3. **Chat页面** - 与AI助手对话，管理邮件
4. **Settings页面** - 用户偏好设置和同步管理

### 核心功能

**智能对话**
- 自然语言描述需求："帮我找昨天的工作邮件"
- AI自动调用相应工具完成操作
- 流式响应，实时显示处理过程

**邮件同步**
- 自动增量同步Gmail邮件
- 智能去重和状态管理
- 支持手动触发同步

**日报生成**
- 定时分析新邮件
- 生成个性化日报
- 支持历史日报查看

## 🔧 开发指南

### 项目结构
```
MailAssistant/
├── backend/              # FastAPI后端
│   ├── app/
│   │   ├── agents/       # LangGraph Agents
│   │   ├── api/          # API路由
│   │   ├── core/         # 核心配置
│   │   ├── models/       # 数据模型
│   │   ├── services/     # 业务服务
│   │   └── utils/        # 工具函数
│   ├── migrations/       # Alembic迁移
│   └── tests/           # 后端测试
├── frontend/            # React前端
│   ├── src/
│   │   ├── components/  # 通用组件
│   │   ├── pages/       # 页面组件
│   │   ├── services/    # API服务
│   │   ├── stores/      # 状态管理
│   │   └── utils/       # 工具函数
│   └── public/         # 静态资源
├── tasks/              # 任务文档系统
├── docs/               # 项目文档
├── scripts/            # 脚本工具
├── .env.example        # 环境变量示例
└── start_backend.py    # 后端启动脚本
```

### 开发特性

**调试日志系统**
- 前端错误自动收集
- 后端API日志查看
- 开发环境自动启用

**API监控**
```bash
# 查看后端错误日志
curl http://localhost:8000/api/debug/logs/backend

# 查看所有错误日志
curl -X POST http://localhost:8000/api/debug/logs/all \
  -H "Content-Type: application/json" \
  -d '{"frontend_errors": []}'
```

**任务文档系统**
- 基于RPE人机协作协议
- 完整的任务追踪体系
- 设计文档和实现分离

### 核心Agent架构

**ConversationHandler**
- 基于LangGraph的对话引擎
- 支持工具调用和流式响应
- 多轮对话状态管理

**EmailProcessor**
- 邮件内容分析和分类
- 重要性评估算法
- 个性化学习机制

## 🧪 测试

```bash
# 后端测试
cd backend
python -m pytest tests/

# 前端测试
cd frontend
npm test
```

## 🚢 部署

### Docker部署（推荐）
```bash
# 构建和启动
docker-compose up -d

# 查看日志
docker-compose logs -f
```

### 手动部署
1. 配置生产环境变量
2. 构建前端：`npm run build`
3. 启动后端：`gunicorn -c gunicorn.conf.py`
4. 配置反向代理（Nginx）

## 🤝 贡献指南

### 开发规范
- 遵循RPE人机协作协议
- 使用项目根目录的`.venv`虚拟环境
- 环境变量配置在根目录`.env`
- 遵循Python PEP8和TypeScript规范

### 贡献流程
1. Fork项目
2. 创建特性分支
3. 编写测试用例
4. 提交Pull Request

## 📊 项目状态

当前版本：v1.0.0

**已完成功能**
- ✅ 完整的用户认证系统
- ✅ Gmail API集成和邮件同步
- ✅ LangGraph对话引擎
- ✅ 邮件分析和日报生成
- ✅ WebSocket实时通信
- ✅ React前端界面

**正在开发**
- 🔄 性能优化和监控
- 🔄 移动端适配

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

## 🙏 致谢

- Google Gmail API
- OpenAI、Anthropic、Google的LLM支持
- LangChain和LangGraph社区
- 所有贡献者的努力

---

<div align="center">
  <p>如果这个项目对您有帮助，请给一个⭐️！</p>
  <p>Made with ❤️ by MailAssistant Team</p>
</div>