# MailAssistant - AI驱动的智能邮件管家

<div align="center">
  <h3>让AI帮你处理邮件，专注于真正重要的事</h3>
  <p>基于LLM的Gmail智能助手，自动分析、分类和生成邮件日报</p>
</div>

## 🎯 项目愿景

MailAssistant致力于解决现代人的邮件过载问题。通过AI技术自动处理繁琐的邮件管理工作，让用户能够专注于真正重要的邮件和工作。

## ✨ 核心特性

### 智能邮件处理
- 🤖 **AI自动分析**：使用LLM分析邮件重要性和紧急程度
- 📊 **智能分类**：自动将邮件分类为工作、个人、广告等类别
- 📝 **每日摘要**：生成个性化的邮件日报，突出重要信息
- 🎯 **个性化学习**：根据用户反馈不断优化分析准确度

### 对话式交互
- 💬 **自然语言对话**：用自然语言与AI助手交流
- 🔍 **智能搜索**：用自然语言搜索历史邮件
- ⚡ **批量操作**：一句话完成批量标记、归档等操作
- 📱 **实时通知**：重要邮件实时推送提醒

### 安全可靠
- 🔐 **OAuth2认证**：使用Google官方认证，不存储密码
- 🔒 **数据加密**：所有敏感数据加密存储
- 🛡️ **隐私保护**：本地部署选项，数据不离开您的服务器
- ✅ **权限最小化**：仅请求必要的Gmail权限

## 🛠️ 技术架构

```
┌─────────────────────────────────────┐
│          React Frontend             │
│    (TypeScript + Tailwind CSS)      │
└──────────────┬──────────────────────┘
               │ REST API + WebSocket
┌──────────────┴──────────────────────┐
│         FastAPI Backend             │
│    (LangGraph Agent + LangChain)    │
└──────────────┬──────────────────────┘
               │
┌──────────────┴──────────────────────┐
│   PostgreSQL + pgvector Database    │
└─────────────────────────────────────┘
```

### 技术栈
- **前端**：React 18 + TypeScript + Tailwind CSS
- **后端**：FastAPI + LangGraph + SQLAlchemy
- **AI**：LangChain + OpenAI/Anthropic/Google
- **数据库**：PostgreSQL + pgvector（向量搜索）
- **认证**：Google OAuth2 + JWT
- **实时通信**：WebSocket

## 🚀 快速开始

### 环境要求
- Python 3.11+
- Node.js 18+
- PostgreSQL 15+（含pgvector扩展）
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

必需的环境变量：
```bash
# 数据库
DATABASE_URL=postgresql://user:password@localhost/mailassistant

# Google OAuth
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret

# 安全密钥
SECRET_KEY=your-secret-key
ENCRYPTION_KEY=your-encryption-key

# LLM API（至少配置一个）
OPENAI_API_KEY=your-openai-key
ANTHROPIC_API_KEY=your-anthropic-key
```

### 3. 启动后端
```bash
# 创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate

# 安装依赖
cd backend
pip install -r requirements.txt

# 运行数据库迁移
alembic upgrade head

# 启动开发服务器
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
npm run dev
```

前端将在 http://localhost:3000 启动

### 5. 访问应用
打开浏览器访问 http://localhost:3000，使用Google账号登录即可开始使用。

## 📖 使用指南

### 首次使用
1. 点击"Sign in with Google"使用Google账号登录
2. 授权MailAssistant访问您的Gmail
3. 等待系统同步和分析您的邮件
4. 查看自动生成的邮件日报

### 日常使用
- **查看日报**：每天定时生成，包含重要邮件摘要
- **对话交互**：点击聊天图标，用自然语言管理邮件
- **批量操作**：告诉AI"把所有广告邮件标记已读"
- **搜索邮件**：用自然语言搜索，如"上周的会议邮件"

### 个性化设置
- 设置日报生成时间
- 调整重要性判断标准
- 自定义邮件分类规则

## 🔧 开发指南

### 项目结构
```
MailAssistant/
├── backend/          # FastAPI后端
├── frontend/         # React前端
├── docs/            # 文档
├── scripts/         # 部署脚本
├── tests/           # 测试用例
├── .env.example     # 环境变量示例
├── docker-compose.yml # Docker配置
├── 需求文档.md      # 产品需求文档
├── 技术设计文档.md   # 技术架构文档
├── PROJECT_STATUS.md # 项目进度跟踪
└── CLAUDE.md        # AI助手使用指南
```

### 核心文档
- [需求文档](./需求文档.md) - 了解产品需求和用户场景
- [技术设计文档](./技术设计文档.md) - 深入理解系统架构
- [项目状态](./PROJECT_STATUS.md) - 查看开发进度
- [后端文档](./backend/README.md) - 后端开发指南
- [前端文档](./frontend/README.md) - 前端开发指南

### 开发模式
本项目采用AI驱动的开发模式：
- **LLM-Driven架构**：核心业务逻辑由AI处理
- **测试驱动开发**：TDD确保代码质量
- **持续集成**：自动化测试和部署

## 🤝 贡献指南

欢迎贡献代码、报告问题或提出建议！

### 贡献流程
1. Fork项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启Pull Request

### 开发规范
- 遵循Python PEP8和TypeScript规范
- 编写单元测试
- 更新相关文档
- 提交信息清晰明确

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

## 🙏 致谢

- 感谢Google提供Gmail API
- 感谢OpenAI/Anthropic提供LLM支持
- 感谢所有贡献者的努力

## 📞 联系方式

- 项目主页：[GitHub](https://github.com/yourusername/MailAssistant)
- 问题反馈：[Issues](https://github.com/yourusername/MailAssistant/issues)
- 邮件联系：your-email@example.com

---

<div align="center">
  <p>如果这个项目对您有帮助，请给一个⭐️！</p>
  <p>Made with ❤️ by MailAssistant Team</p>
</div>