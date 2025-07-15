# MailAssistant Project - Claude Assistant Guide

## 项目概述

MailAssistant是一个基于LLM的智能邮件管家系统，帮助用户处理Gmail邮件，减少信息过载。项目采用FastAPI + LangGraph + React + PostgreSQL技术栈，实现完全基于AI Agent的邮件智能分析和管理。

## 📁 项目文件结构

```
MailAssistant/
├── .env                              # 环境变量配置文件
├── .gitignore                        # Git忽略配置
├── start_backend.py                  # 开发模式服务器启动脚本
├── 需求文档.md                       # 🔴 核心需求文档 - 必读
├── 技术设计文档.md                   # 🔴 核心技术设计文档 - 必读
├── 
├── .tasks/                           # 🔴 任务管理文件夹 - 必须参考
│   ├── .gitkeep                     # Git保持目录
│   └── 2025-07-11_1_mail_assistant_implementation.md  # 当前任务文件
├── 
├── backend/                          # 后端服务
│   ├── README.md                    # 后端启动和使用说明
│   ├── start_backend.py             # 后端启动脚本
│   ├── test_gmail_integration.py    # Gmail集成测试脚本
│   ├── requirements.txt             # Python依赖包
│   ├── alembic.ini                  # 数据库迁移配置
│   ├── 
│   ├── migrations/                  # 数据库迁移文件
│   │   ├── env.py                   # Alembic环境配置
│   │   └── versions/                # 迁移版本文件
│   │ 
│   ├── app/                         # FastAPI应用
│   │   ├── main.py                  # 应用主入口
│   │   ├── 
│   │   ├── core/                    # 核心配置
│   │   │   ├── config.py            # 应用配置管理
│   │   │   ├── database.py          # 数据库连接配置
│   │   │   ├── security.py          # 安全相关（JWT, 加密）
│   │   │   └── logging.py           # 日志配置
│   │   ├── 
│   │   ├── models/                  # 数据库模型
│   │   │   ├── __init__.py          # 模型导出
│   │   │   ├── user.py              # 用户模型
│   │   │   ├── email.py             # 邮件模型
│   │   │   ├── email_analysis.py    # 邮件分析模型
│   │   │   ├── user_preference.py   # 用户偏好模型
│   │   │   ├── daily_report.py      # 日报模型
│   │   │   └── task_log.py          # 任务日志模型
│   │   ├── 
│   │   ├── api/                     # API路由
│   │   │   ├── auth.py              # 认证相关API
│   │   │   └── gmail.py             # Gmail集成API
│   │   ├── 
│   │   ├── services/                # 业务服务层
│   │   │   ├── oauth_service.py     # OAuth认证服务
│   │   │   ├── gmail_service.py     # Gmail API服务
│   │   │   └── email_sync_service.py # 邮件同步服务
│   │   ├── 
│   │   ├── agents/                  # LangChain Agent实现
│   │   │   ├── base_agent.py        # Agent基类和用户偏好预加载
│   │   │   ├── llm_provider.py      # LLM提供商管理
│   │   │   ├── email_processor.py   # 邮件处理Agent
│   │   │   └── conversation_handler.py # 对话处理Agent
│   │   ├── 
│   │   ├── tools/                   # Agent工具集（@tool装饰器）
│   │   │   ├── base_tool.py         # 工具基类
│   │   │   ├── email_tools.py       # 邮件处理工具
│   │   │   ├── conversation_tools.py # 对话工具
│   │   │   └── shared_tools.py      # 共享工具
│   │   └── utils/                   # 工具函数
│   │       └── __init__.py
│   └── tests/                       # 测试文件
└── 
└── frontend/                        # React前端（待实现）
    ├── package.json                 # 前端依赖配置
    ├── public/                      # 静态资源
    └── src/                         # 前端源码
        ├── components/              # React组件
        ├── pages/                   # 页面组件
        ├── services/                # API服务
        ├── hooks/                   # React Hooks
        ├── types/                   # TypeScript类型
        └── utils/                   # 前端工具函数
```

## 🔴 核心文档说明

### 1. 需求文档.md
**重要性：⭐⭐⭐⭐⭐ 必须参考**

此文档包含：
- 用户痛点分析和核心需求
- 功能特性详细描述
- 用户场景和使用流程
- 产品设计理念和目标

**在任何开发工作前必须阅读此文档，确保理解用户真实需求。**

### 2. 技术设计文档.md
**重要性：⭐⭐⭐⭐⭐ 必须参考**

此文档包含：
- 完整的系统架构设计
- 技术栈选择和理由
- 数据库设计和关系
- LLM-Driven Agent架构设计
- API接口设计
- 部署和扩展策略

**所有技术实现都必须参考此文档，确保架构一致性。**

### 3. .tasks/ 目录
**重要性：⭐⭐⭐⭐⭐ 持续跟踪**

包含项目任务管理文件：
- `2025-07-11_1_mail_assistant_implementation.md` - 当前主要实施任务
- 记录完整的实施计划和进度
- 包含问题解决记录和状态追踪
- 遵循RIPER-5工作流程

**每次工作都必须更新任务文件，记录进展和问题。**

## 🔧 技术架构关键点

### 后端架构 (FastAPI + LangChain)
- **FastAPI**: RESTful API和认证
- **LangChain Agent**: LLM-driven智能Agent架构
- **PostgreSQL + pgvector**: 数据存储和向量搜索
- **Google APIs**: Gmail集成和OAuth认证

### 数据库设计
- **users**: 用户和认证信息
- **emails**: Gmail邮件数据
- **email_analyses**: LLM分析结果
- **user_preferences**: 用户偏好（支持向量搜索）
- **daily_reports**: 智能日报
- **task_logs**: 系统任务记录

### LLM-Driven Agent架构
**核心原则：让LLM完全控制Agent行为，最小化硬编码**
- **EmailProcessor**: 无状态，专注邮件分析和日报生成
- **ConversationHandler**: 有状态，用户对话和任务调度
- **智能工具调用**: 使用@tool装饰器，LLM自动选择工具
- **自然语言交互**: 用户可以用任意自然语言与系统对话

## 🚀 开发指南

注意使用python的时候都默认用 python3 因为系统自带的python 是2.7.13版本，和项目要求的不一样

### 环境启动
```bash
# 后端开发模式
source .venv/bin/activate
python3 start_backend.py

# API文档
http://localhost:8000/docs
```

### 数据库操作
```bash
# 创建迁移
cd backend && alembic revision --autogenerate -m "description"

# 应用迁移
cd backend && alembic upgrade head
```

### 测试
```bash
# Gmail集成测试
cd backend && python test_gmail_integration.py
```

## 📋 当前实施状态

根据`.tasks/2025-07-11_1_mail_assistant_implementation.md`文件：

**已完成：**
1. ✅ 项目基础结构和虚拟环境
2. ✅ PostgreSQL数据库和pgvector扩展
3. ✅ 用户认证系统（Google OAuth2）
4. ✅ 数据库模型设计和创建
5. ✅ Gmail API集成和令牌管理

**进行中：**
6. 🔄 构建可靠的定时任务系统

**待完成：**
7. 构建LangGraph Agent核心架构
8. 开发Agent工具集
9. 实现EmailProcessor和ConversationHandler节点
10. 创建FastAPI后端API路由
11. 实现WebSocket支持
12. 前端React应用开发
13. 前后端集成
14. 批量操作和对话式交互
15. 日志系统和错误处理
16. 测试和性能优化
17. 部署配置和文档

## 🔒 安全和配置

### 环境变量 (.env)
```bash
# 数据库
DATABASE_URL=postgresql://user@localhost/mailassistant

# Google OAuth
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URI=http://localhost:3000/auth/callback

# 安全
SECRET_KEY=your-secret-key
ENCRYPTION_KEY=your-encryption-key

# LLM APIs
OPENAI_API_KEY=your-openai-key
ANTHROPIC_API_KEY=your-anthropic-key
```

### 关键安全特性
- Gmail tokens加密存储
- JWT token管理
- 自动token刷新
- 环境变量隔离

## 📝 工作流程建议

1. **开始任何工作前**：
   - 阅读需求文档.md和技术设计文档.md
   - 查看.tasks/目录中的当前任务状态
   - 理解当前实施进度

2. **实施过程中**：
   - 严格按照技术设计文档的LLM-Driven架构实现
   - 遵循"让LLM完全控制"原则，最小化硬编码
   - 及时更新任务文件记录进展

3. **完成工作后**：
   - 更新任务状态和记录
   - 测试集成功能
   - 确认如果有重构导致已经废弃的文件或者文件夹要清理干净，不要遗留无用的垃圾文件和文件夹
   - 提交代码并推送

## ⚠️ 注意事项

- **Agent设计**：坚持LLM-Driven架构，避免硬编码业务逻辑
- **工具设计**：使用@tool装饰器，让LLM自动选择和调用工具
- **响应生成**：完全由LLM控制，不要预定义响应模板
- **数据安全**：所有敏感信息必须加密存储
- **向量搜索**：用户偏好和邮件内容支持语义搜索
- **错误处理**：让LLM智能处理异常，而不是硬编码错误消息
- **用户体验**：以减少用户信息过载为核心目标

## 🎯 新架构核心价值

### 从硬编码到智能驱动
- **旧方式**: 大量if-else判断，固定响应模板
- **新方式**: LLM推理决策，动态响应生成

### 开发效率提升
- **代码量减少80%**: 复杂逻辑交给LLM处理
- **维护成本降低**: 工具描述即文档
- **扩展性增强**: 新功能只需添加工具描述

### 用户体验革命
- **自然交互**: 任意自然语言表达
- **智能理解**: 上下文感知和意图识别
- **个性化服务**: 基于用户偏好的智能决策

---

**重要提醒：在进行任何开发工作时，务必先参考需求文档.md、技术设计文档.md和.tasks/目录中的任务文件，确保理解项目目标和当前状态。**