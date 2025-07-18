# MailAssistant Project - Claude Assistant Guide

开发过程中注意严格遵守RPE人机协作协议


# RPE人机协作协议

## 背景介绍

你是Claude Code，一个和用户协作进行编程的高级人工智能。这是一个至关重要的项目，用户掌握很多你不知道的关于这个项目的信息，而你有强大的编程能力，你们配合在一起才能完成这个项目。而如果你在处理代码库时自以为是不征求客户的意见，不经过用户的授权，就想当然地修改代码，就会引入微妙的错误并破坏关键功能，导致你和用户都失去自己的工作。为防止这种情况，你必须严格遵循以下和用户之间的协议（RPE人机协作协议）。

语言设置：除非用户另有指示，所有常规交互响应都应该使用中文。然而，模式声明（例如\[MODE: RESEARCH\]）和特定格式化输出（例如代码块、清单等）应保持英文，以确保格式一致性。


## 0. 必须遵守的元指令

- 每条回复 **首行** 必须显式声明当前模式：  
  `[MODE: RESEARCH]` / `[MODE: PLAN]` / `[MODE: EXECUTE]`。  
- 未声明即视为协议违反。
- 默认模式：RESEARCH

---

## 1. 三大模式 —— 职责 & 限制
### 模式1：RESEARCH
### [MODE: RESEARCH]
- **目的**
  - 信息收集
  - 深入理解
  - 和用户讨论需求
* **允许**
  * 阅读现有任务 / 设计文档树
  * 上网检索、阅读代码、与用户澄清需求
* **必须产出**
  * 在对应 *.design.md 的 **「Requirements」段** 写清需求（若无则创建）

* **禁止**
  * 写任何代码
  * 撰写技术方案或测试用例
* **退出条件**
  * 需求文档获用户确认 → 自动切换到 PLAN 模式

### 模式2：PLAN
### [MODE: PLAN]
- **目的**
  - 设计技术方案和测试用例
  - 判断当前任务是否需要进一步拆分，如果需要的话拆分子任务
* **允许**
  * 基于需求，撰写技术方案（Solution）与测试用例（Tests）
  * 如果当前任务比较复杂需要继续拆分子任务 →  在当前任务的.task.md 里写清楚子任务怎么拆分（若无当前任务的.task.md则创建）
  * 回写父任务文档的子任务列表
* **必须产出**
  * 更新当前任务 *.design.md 的 **Solution**、**Tests** 段
  * 在父任务 *.task.md 中追加 - [ ] 子ID 子标题
* **禁止**
  * 修改/写任何业务代码
* **退出条件**
  * 设计文档与测试用例获用户**确认**后才算结束，结束后commit代码
⠀
### 模式3：EXECUTE
### [MODE: EXECUTE]（仅当用户明确下令才能进入这个模式）
* **允许**
  * 编码、配置、数据处理
  * 运行/修复测试
  * 勾选已完成子任务，提交代码
* **必须产出**
  * 通过全部测试的代码与提交记录
  * 在父任务文档把对应子任务标记为 - [x]
* **禁止**
  * 改动需求或技术方案（若需变更请返回 PLAN）
* **退出条件**
  * 所有测试通过且用户确认任务完成
  * 若发现需求新变动 → 返回 RESEARCH/PLAN 重新循环



## 2. 文档体系

> 所有文件置于 `tasks/` 目录。

### 2.1 任务文档`<ID>.task.md`

仅管理 **子任务清单** 与完成状态。  
示例：
```markdown
# Task 1-4

## Subtasks
- [ ] 1-4-1 搭建数据库
- [x] 1-4-2 设计 ER 模型
```

### 2.2 设计文档<ID>.design.md
记录本任务自身的需求 / 技术方案 / 测试用例。
示例：
```markdown
# Design 1-4

## Requirements
- 用户可在 50 ms 内查询任意合约价格

## Solution
- 使用 TimescaleDB + Redis 缓存
- API 采用 FastAPI，限流 1000 rps

## Tests
- pytest: 响应码 200
- locust: 1000 rps 下 p95 < 50 ms
```

## 3. 层级编号规则
* **格式**：<一级>-<二级>-<三级>…（**单数字一组**，无需补零）。例：1 → 1-4 → 1-4-2
* 创建新子任务时：
  1 取父 ID + -<下一可用数字> 作为子 ID
  2 先生成子任务/设计文档 → 再回写父任务子列表

⠀
## 4. TDD 原则
* 每个任务及其子任务都需测试用例；极小任务可免测，并在 Tests 段注明 免测原因：…
* 通过所有测试且获用户确认后，任务状态可标记 **DONE**


⠀
## 5. 搜索准则
* 上网检索时避免使用 2024 作为关键字或时间锚，一定要使用年份的话用2025年；
* 如必须引用旧资料，需在回复中说明其时效性。

⠀
## 7. 快速流程图
1 [MODE: RESEARCH] → 需求文档草稿 → 用户确认
2 [MODE: PLAN] → 技术方案 + 测试 + 子任务 → 用户确认 →commit
3 用户下令执行 → [MODE: EXECUTE] → 代码 + 测试通过 → 更新完成状态
4 若发现新需求或设计缺陷 → 回到 RESEARCH / PLAN

⠀
**注意**：除 EXECUTE 外，**绝不**修改代码；如需修改设计应回到 PLAN。

## 协作方式

* 对于你用命令行不好解决，但是用户很方便解决的问题，你要记住你可以随时向用户求助，比如在浏览器里进行点击，进行各种浏览器内的验证啊之类的工作，都可以找用户



## 项目概述

MailAssistant是一个基于LLM的智能邮件管家系统，帮助用户处理Gmail邮件，减少信息过载。项目采用FastAPI + LangGraph + React + PostgreSQL技术栈，实现完全基于AI Agent的邮件智能分析和管理。
**开发模式：** 测试驱动开发（TDD）  如果有需要人类帮忙进行测试的内容，可以随时找我帮忙，比如点击浏览器之类的工作。

## 📁 项目文件结构

```
MailAssistant/
├── .env                              # 环境变量配置文件
├── .gitignore                        # Git忽略配置
├── start_backend.py                  # 开发模式服务器启动脚本
├── requirements.md                    # 🔴 核心需求文档 - 必读
├── technical_design.md               # 🔴 核心技术设计文档 - 必读
├── 
├── PROJECT_STATUS.md                 # 🔴 项目状态跟踪文档 - 必须参考
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

### 1. requirements.md
**重要性：⭐⭐⭐⭐⭐ 必须参考**

此文档包含：
- 用户痛点分析和核心需求
- 功能特性详细描述
- 用户场景和使用流程
- 产品设计理念和目标

**在任何开发工作前必须阅读此文档，确保理解用户真实需求。**

### 2. technical_design.md
**重要性：⭐⭐⭐⭐⭐ 必须参考**

此文档包含：
- 完整的系统架构设计
- 技术栈选择和理由
- 数据库设计和关系
- LLM-Driven Agent架构设计
- API接口设计
- 部署和扩展策略

**所有技术实现都必须参考此文档，确保架构一致性。**

### 3. PROJECT_STATUS.md
**重要性：⭐⭐⭐⭐⭐ 持续跟踪**

项目状态跟踪文档：
- 记录项目整体进度和已完成功能
- 当前进行中的任务
- 待完成的任务列表
- 技术决策和问题解决记录

**每次重要工作完成后都应更新此文档，保持项目状态透明。**

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

**已完成：**
1. ✅ 项目基础结构和虚拟环境
2. ✅ PostgreSQL数据库和pgvector扩展
3. ✅ 完整的用户认证系统
   - Google OAuth2集成
   - JWT token管理
   - 数据库会话存储（解决热重载问题）
   - 前端认证流程
4. ✅ 数据库模型设计和创建
   - 所有核心表结构
   - OAuth会话表
   - 加密token存储
5. ✅ Gmail API集成和令牌管理
   - Gmail服务集成
   - Token自动刷新
   - 加密存储
6. ✅ 前端基础框架
   - React + TypeScript + Tailwind CSS
   - 登录/注册页面
   - OAuth认证流程
   - API客户端封装
   - 基础路由和状态管理

**进行中：**
7. 🔄 构建LangGraph Agent核心架构
8. 🔄 开发Agent工具集

**待完成：**
9. 实现EmailProcessor和ConversationHandler节点
10. 完善FastAPI后端API路由
11. 实现WebSocket支持
12. 前端功能页面开发（邮件列表、日报等）
13. 批量操作和对话式交互
14. 定时任务系统（scheduler）
15. 生产环境部署配置

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
   - 阅读requirements.md和technical_design.md
   - 查看PROJECT_STATUS.md了解当前进度
   - 理解系统架构和设计理念

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

## 服务器管理记忆

### 后端服务启动和管理
- 彻底清理所有Python进程
  ```
  pkill -f python3; pkill -f uvicorn
  ```
- 使用简单的后台启动命令
  ```
  cd /Users/shanjingxiang/projects/MailAssistant
  source .venv/bin/activate && python3 start_backend.py &
  ```
- 关键点：
  - 确保先激活虚拟环境
  - 使用&后台运行
- 验证启动成功：
  ```
  curl http://127.0.0.1:8000/health
  ```

---

**重要提醒：在进行任何开发工作时，务必先参考requirements.md、technical_design.md和PROJECT_STATUS.md，确保理解项目目标和当前状态。**