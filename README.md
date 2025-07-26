# MailAssistant - AI智能邮件助手

> 让AI帮你处理邮件过载，专注真正重要的事情

MailAssistant是一个基于LangGraph的Gmail智能助手，通过AI自动分析、分类邮件并生成每日摘要，帮你从邮件海洋中解脱出来。

## ✨ 核心功能

- **🤖 智能对话助手** - 用自然语言管理邮件："帮我找昨天王总发的工作邮件"
- **📊 自动邮件分析** - AI评估邮件重要性，自动分类工作、个人、广告邮件
- **📝 每日智能摘要** - 生成个性化邮件日报，突出重要信息和待办事项
- **🔍 智能搜索** - 告别复杂搜索语法，直接说"找本周的项目相关邮件"
- **⚡ 实时同步** - 基于Gmail History API的增量同步，及时获取最新邮件
- **🛠️ 批量操作** - 一句话完成邮件标记、归档、回复等批量操作

## 🚀 快速体验

### 环境要求
- Python 3.11+
- Node.js 18+
- PostgreSQL 15+
- Google账号（用于Gmail OAuth）

### 一键启动

1. **克隆项目**
   ```bash
   git clone https://github.com/yourusername/MailAssistant.git
   cd MailAssistant
   ```

2. **配置环境**
   ```bash
   cp .env.example .env
   # 编辑 .env 文件，填写必要配置：
   # - DATABASE_URL: PostgreSQL连接
   # - GOOGLE_CLIENT_ID/SECRET: Google OAuth配置
   # - 至少一个LLM API密钥 (OpenAI/Anthropic/Google)
   ```

3. **启动后端**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   cd backend && pip install -r requirements.txt
   alembic upgrade head
   cd .. && python3 start_backend.py
   ```

4. **启动前端**
   ```bash
   cd frontend
   npm install && npm start
   ```

5. **开始使用**
   
   打开 http://localhost:3000，用Google账号登录即可开始体验AI邮件助手！

## 💡 使用场景

### 智能对话管理
```
你: "帮我找本周收到的重要工作邮件"
AI: 找到了12封重要工作邮件，包括项目进度更新、会议邀请...

你: "把昨天未读的广告邮件都标记为已读"
AI: 已为您标记了8封广告邮件为已读状态
```

### 每日邮件摘要
- 自动生成当日重要邮件概览
- 识别需要回复的邮件和截止日期
- 按优先级排序待处理事项

### 智能邮件分类
- 工作邮件：项目更新、会议邀请、客户沟通
- 个人邮件：朋友消息、家庭事务、兴趣爱好
- 系统邮件：通知、账单、订阅内容

## 🛠️ 技术特色

- **🧠 LangGraph对话引擎** - 支持复杂工具调用和多轮对话
- **🔗 多LLM支持** - OpenAI GPT-4、Anthropic Claude、Google Gemini
- **⚡ 实时通信** - WebSocket支持流式响应和实时推送
- **🔐 安全可靠** - OAuth2认证，数据加密存储，权限最小化
- **📱 响应式UI** - React + Tailwind，支持移动端访问

## 📁 项目结构

```
MailAssistant/
├── backend/          # FastAPI后端服务
│   ├── app/agents/   # LangGraph AI Agents
│   ├── app/api/      # REST API接口
│   └── app/services/ # 业务服务层
├── frontend/         # React前端应用
│   ├── src/pages/    # 页面组件
│   └── src/stores/   # 状态管理
└── tasks/           # 开发任务文档
```

## 🔒 隐私与安全

- ✅ 使用Google官方OAuth2，不存储用户密码
- ✅ 所有敏感数据加密存储
- ✅ 支持本地部署，数据不离开你的服务器
- ✅ 已通过安全审计，修复潜在风险
- ✅ 最小权限原则，仅请求必要的Gmail权限

## 📊 开发状态

当前版本：**v1.0.0** (生产就绪)

**✅ 已完成功能**
- 完整的Gmail集成和邮件同步
- AI对话引擎和工具调用系统
- 智能邮件分析和日报生成
- React前端界面和WebSocket通信
- 用户认证和权限管理
- 安全审计和漏洞修复


## 🤝 贡献指南

欢迎提交Issue和Pull Request！项目遵循[RPE人机协作协议](CLAUDE.md)进行开发。

开发环境：
- 使用项目根目录的 `.venv` 虚拟环境
- 环境变量配置在根目录 `.env` 文件
- 遵循Python PEP8和TypeScript规范

## 📜 开源协议

本项目基于 MIT 协议开源 - 查看 [LICENSE](LICENSE) 了解详情

---

<div align="center">
  <p><strong>告别邮件过载，拥抱AI助手 🚀</strong></p>
  <p>如果这个项目对你有帮助，请给个 ⭐️ 支持一下！</p>
</div>