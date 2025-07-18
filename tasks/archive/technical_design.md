# 邮件管家 - 技术设计文档

## 技术架构概览

### 总体架构
**方案：单体应用 + Agent架构**

- **后端**：FastAPI + LangGraph + SQLAlchemy
- **前端**：React + TypeScript
- **数据库**：PostgreSQL + pgvector扩展
- **认证**：Google OAuth2
- **LLM**：支持OpenAI/Anthropic/Gemini多Provider

### 核心设计原则
1. **Agent优先**：能用AI的地方都用AI，避免硬编码
2. **简洁架构**：最少的节点数量，最大的可靠性
3. **个性化**：基于用户偏好的智能分析
4. **可扩展**：支持多种LLM Provider

## LLM-Driven Agent架构

### 核心设计理念

**完全依赖LLM推理的Agent架构**

- **最小化硬编码**：让LLM自己决定何时、如何使用工具
- **自然交互**：LLM完全控制对话流程和响应格式
- **智能工具选择**：基于用户请求和上下文自动选择工具组合
- **动态响应**：LLM根据执行结果动态调整回复内容

### 分层架构设计

```
┌─────────────────┐
│   API Layer    │ ← FastAPI routes
├─────────────────┤
│  Agents Layer  │ ← LangChain Agent框架
├─────────────────┤
│  Tools Layer   │ ← @tool装饰器，LLM自动调用
├─────────────────┤
│ Services Layer │ ← 现有的gmail_service, task_service等
├─────────────────┤
│ Database Layer │ ← SQLAlchemy models
└─────────────────┘
```

### 独立的2Agent设计

**1. EmailProcessor Agent（无状态）**
```python
from langchain.agents import create_openai_tools_agent
from langchain.tools import tool

class EmailProcessorAgent:
    def __init__(self, user_id: str):
        self.user_preferences = self._load_preferences(user_id)
        self.agent = create_openai_tools_agent(
            llm=self.llm,
            tools=self.email_tools,
            prompt=self._build_system_prompt()
        )
    
    async def process(self, request: str) -> str:
        # LLM完全控制处理流程
        return await self.agent.ainvoke({"input": request})
```

**2. ConversationHandler Agent（有状态）**
```python
from langchain.agents import AgentExecutor
from langchain.memory import ConversationBufferMemory

class ConversationHandler:
    def __init__(self, user_id: str):
        self.memory = ConversationBufferMemory(return_messages=True)
        self.agent = create_openai_tools_agent(
            llm=self.llm,
            tools=self.conversation_tools,
            prompt=self._build_system_prompt()
        )
        self.executor = AgentExecutor(
            agent=self.agent,
            tools=self.conversation_tools,
            memory=self.memory,
            verbose=True
        )
    
    async def chat(self, message: str) -> str:
        # LLM控制对话，自动记忆上下文
        return await self.executor.ainvoke({"input": message})
```

### 核心设计原则

1. **LLM完全控制**：Agent行为完全由LLM推理决定
2. **自然工具调用**：使用LangChain的function calling机制
3. **动态响应生成**：LLM根据工具执行结果自由生成回复
4. **最小化业务逻辑**：复杂逻辑交给LLM处理
5. **偏好自然融合**：用户偏好自然地融入系统prompt

### LLM-Driven工具设计

**使用LangChain @tool装饰器**：
```python
from langchain.tools import tool

@tool
def analyze_email(email_content: str, sender: str) -> str:
    """分析邮件内容并判断重要性。
    
    Args:
        email_content: 邮件正文内容
        sender: 发件人邮箱
        
    Returns:
        包含重要性分析结果的JSON字符串
    """
    # 调用service层执行实际分析
    return email_service.analyze_email(email_content, sender)

@tool
def generate_daily_report(date: str = None) -> str:
    """生成指定日期的邮件日报。
    
    Args:
        date: 日期（YYYY-MM-DD格式），不指定则生成今日报告
        
    Returns:
        包含日报内容的JSON字符串
    """
    return report_service.generate_daily_report(date)

@tool
def search_email_history(query: str, limit: int = 10) -> str:
    """搜索历史邮件。
    
    Args:
        query: 搜索关键词
        limit: 返回结果数量限制
        
    Returns:
        匹配的邮件列表JSON字符串
    """
    return email_service.search_emails(query, limit)
```

**系统Prompt设计**：
```python
def build_system_prompt(self, user_preferences: dict) -> str:
    return f"""
你是用户的智能邮件助手。你可以：

1. 分析邮件内容和重要性
2. 生成每日邮件报告
3. 搜索历史邮件
4. 批量操作邮件（标记已读等）
5. 学习和更新用户偏好

用户偏好：
{self._format_preferences(user_preferences)}

请以自然、友好的方式与用户交流。根据用户请求智能选择和使用工具。
你的回复应该简洁明了，必要时询问澄清信息。
"""
```

## 数据库设计

### 混合存储方案
- **PostgreSQL**：用户信息、邮件元数据、分类结果
- **pgvector扩展**：用户偏好向量存储和相似性匹配

### 核心表结构

**用户表 (users)**
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    google_id VARCHAR(255) UNIQUE NOT NULL,
    encrypted_gmail_tokens TEXT,
    preferences_text TEXT,
    daily_report_time TIME DEFAULT '08:00:00',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

**邮件表 (emails)**
```sql
CREATE TABLE emails (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    gmail_id VARCHAR(255) NOT NULL,
    subject TEXT,
    sender VARCHAR(255),
    body_text TEXT,
    is_important BOOLEAN DEFAULT FALSE,
    importance_reason TEXT,
    category VARCHAR(100),
    received_at TIMESTAMP WITH TIME ZONE,
    processed_at TIMESTAMP WITH TIME ZONE,
    UNIQUE(user_id, gmail_id)
);
```

**Agent会话表 (agent_sessions)**
```sql
CREATE TABLE agent_sessions (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    agent_type VARCHAR(50), -- 'email_processor' or 'conversation_handler'
    session_data JSON,
    status VARCHAR(20),
    created_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE
);
```

**工具执行日志表 (tool_executions)**
```sql
CREATE TABLE tool_executions (
    id UUID PRIMARY KEY,
    session_id UUID REFERENCES agent_sessions(id),
    tool_name VARCHAR(100),
    input_data JSON,
    output_data JSON,
    execution_time_ms INTEGER,
    status VARCHAR(20),
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE
);
```

## API设计

### 简化的RESTful API接口

**认证相关**
- `POST /auth/google` - Google OAuth登录
- `POST /auth/refresh` - 刷新令牌
- `DELETE /auth/logout` - 登出

**Agent交互**
- `POST /agents/email-processor` - 直接与EmailProcessor对话
- `POST /agents/conversation` - 与ConversationHandler对话
- `GET /agents/session/{session_id}` - 获取对话会话状态
- `DELETE /agents/session/{session_id}` - 结束对话会话

**请求格式**：
```json
{
  "message": "帮我生成今天的邮件日报",
  "session_id": "optional-session-id"
}
```

**响应格式**：
```json
{
  "response": "我已经为您生成了今天的邮件日报...",
  "session_id": "session-123",
  "tool_calls": [
    {
      "tool": "generate_daily_report",
      "result": {...}
    }
  ]
}
```

### WebSocket接口
- `/ws?token=jwt_token` - 实时Agent响应和进度推送

**WebSocket消息格式**：
```json
{
  "type": "agent_response",
  "agent": "conversation_handler",
  "message": "正在分析您的邮件...",
  "progress": 0.5,
  "tool_calls": [...]
}
```

## 关键技术实现

### 1. LLM-Driven Agent核心实现
```python
from langchain.agents import create_openai_tools_agent, AgentExecutor
from langchain.memory import ConversationBufferMemory
from langchain.tools import tool

class BaseAgent:
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.user_preferences = self._load_user_preferences()
        self.llm = self._create_llm()
        self.tools = self._create_tools()
        self.agent = self._create_agent()
    
    def _create_agent(self):
        prompt = self._build_system_prompt()
        return create_openai_tools_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=prompt
        )
    
    def _build_system_prompt(self) -> str:
        # 将用户偏好自然融入系统prompt
        return f"""
        你是用户的智能邮件助手。
        
        用户偏好：
        {self._format_preferences()}
        
        请根据用户请求智能使用工具，以自然方式回复。
        """
```

### 2. 智能工具自动调用
```python
@tool
def analyze_email(email_content: str, sender: str) -> str:
    """分析邮件内容并判断重要性。LLM会根据用户偏好自动调用此工具。"""
    # 调用现有service层
    result = email_service.analyze_with_preferences(
        email_content, sender, user_preferences
    )
    return json.dumps(result)

@tool  
def generate_daily_report(date: str = None) -> str:
    """生成每日邮件报告。LLM会根据用户请求智能调用。"""
    result = report_service.generate_report(date)
    return json.dumps(result)

@tool
def bulk_mark_read(criteria: str) -> str:
    """批量标记邮件为已读。LLM会解析用户的自然语言criteria。"""
    result = email_service.bulk_mark_read(criteria)
    return json.dumps(result)
```

### 3. 对话记忆和会话管理
```python
class ConversationHandler(BaseAgent):
    def __init__(self, user_id: str):
        super().__init__(user_id)
        self.memory = ConversationBufferMemory(
            return_messages=True,
            memory_key="chat_history"
        )
        self.executor = AgentExecutor(
            agent=self.agent,
            tools=self.tools,
            memory=self.memory,
            verbose=True,
            handle_parsing_errors=True
        )
    
    async def chat(self, message: str) -> str:
        """LLM完全控制对话，自动记忆上下文"""
        response = await self.executor.ainvoke({"input": message})
        return response["output"]
```

### 4. 自动化任务调度
```python
class TaskScheduler:
    async def schedule_daily_report(self, user_id: str):
        # 创建EmailProcessor实例
        processor = EmailProcessorAgent(user_id)
        
        # 直接用自然语言请求
        request = "请生成今天的邮件日报，包含重要邮件分析和摘要"
        
        # LLM自动选择工具并执行
        result = await processor.process(request)
        
        # 通过WebSocket推送结果
        await websocket_manager.send_to_user(user_id, {
            "type": "daily_report",
            "content": result
        })
```

### 5. 实时WebSocket通信
```python
class WebSocketManager:
    async def handle_agent_message(self, websocket, message):
        # 直接转发给ConversationHandler
        handler = ConversationHandler(user_id)
        
        # 流式响应支持
        async for chunk in handler.chat_stream(message):
            await websocket.send_json({
                "type": "agent_response_chunk",
                "content": chunk
            })
```

## 数据流设计

### LLM-Driven邮件处理流程
1. **定时任务触发** → EmailProcessor Agent创建
2. **自然语言请求** → "请生成今天的邮件日报"
3. **LLM智能规划** → 自动选择工具序列：
   - 调用sync_emails工具获取最新邮件
   - 调用analyze_email工具分析重要性
   - 调用generate_daily_report工具生成报告
4. **偏好自动应用** → 用户偏好已预加载到Agent prompt
5. **结果自然生成** → LLM生成人性化的日报内容
6. **实时推送** → WebSocket发送给用户

### 用户对话交互流程
1. **用户自然语言** → "帮我把所有广告邮件标记为已读"
2. **ConversationHandler接收** → 带有对话记忆的Agent
3. **LLM智能推理** → 理解意图并规划执行：
   - 识别"广告邮件"的标准
   - 选择bulk_mark_read工具
   - 确定执行参数
4. **工具自动调用** → LLM调用相应工具
5. **动态响应生成** → 根据执行结果生成自然回复
6. **上下文记忆** → 保存对话历史，支持连续交互

### 偏好学习流程
1. **用户反馈** → "这类邮件对我很重要"
2. **LLM理解** → 提取偏好特征
3. **工具调用** → update_user_preferences
4. **自动应用** → 后续分析自动考虑新偏好

## OAuth认证实现细节

### OAuth Flow Manager架构

**设计原则：**
- 支持热重载的会话持久化
- 防止会话重放攻击
- 优雅的错误处理

**数据库会话存储：**
```python
class OAuthFlowManagerDB:
    def create_oauth_flow(self) -> Tuple[str, str]:
        """创建OAuth流程，存储到数据库"""
        flow = self._create_flow()
        session_id = self._generate_session_id()
        
        # 存储到oauth_sessions表
        oauth_session = OAuthSession(
            session_id=session_id,
            status=SessionStatus.PENDING,
            flow_data=pickle.dumps(flow),
            authorization_url=auth_url,
            state=flow.state,
            expires_at=datetime.utcnow() + timedelta(minutes=30)
        )
        db.add(oauth_session)
        db.commit()
        
        return session_id, authorization_url
```

**会话状态管理：**
- PENDING: 初始状态，等待用户授权
- CONSUMED: 已使用，防止重复使用
- EXPIRED: 已过期，自动清理

### 前端OAuth集成

**认证流程：**
1. 用户点击"Sign in with Google"
2. 后端创建OAuth会话，返回session_id
3. 前端保存session_id并跳转到Google
4. Google回调到前端AuthCallback页面
5. 前端使用session_id完成认证

**防止重复处理：**
```typescript
// 使用useRef防止React StrictMode双重执行
const processedRef = React.useRef(false);

React.useEffect(() => {
  if (processedRef.current || isProcessing) return;
  processedRef.current = true;
  
  // 处理OAuth回调
  handleOAuthCallback();
}, []);
```

**错误处理优化：**
- 移除自动重试机制
- 清晰展示错误信息
- 提供手动重试选项

### JWT Token管理

**Token存储策略：**
- HttpOnly Cookie存储（防XSS）
- SameSite=Lax（CSRF防护）
- Secure标记（生产环境）

**Token刷新机制：**
```python
@router.post("/refresh")
async def refresh_token(
    refresh_token: str = Cookie(None)
) -> TokenResponse:
    """自动刷新Access Token"""
    payload = jwt.decode(refresh_token, SECRET_KEY)
    user = get_user(payload["sub"])
    
    new_access_token = create_access_token(user)
    return TokenResponse(
        access_token=new_access_token,
        token_type="bearer"
    )
```

## 安全设计

### 数据保护
- Gmail令牌AES加密存储
- 用户数据严格隔离
- API访问控制和限流
- 敏感信息不记录日志

### 权限管理
- JWT认证（Access + Refresh Token）
- 用户授权验证（每个API端点）
- 操作权限检查（基于用户角色）
- OAuth会话防重放

## 性能优化

### 数据库优化
- 索引优化
- 连接池管理
- 查询优化

### LLM调用优化
- 批量处理
- 结果缓存
- 多Provider支持

### 前端优化
- 懒加载
- 状态管理
- 缓存策略

## 前端用户界面设计

### 简化的3页面架构

基于深入的用户需求分析，前端采用极简的3页面架构，专注于"减少信息过载"的核心目标：

**页面结构：**
1. **Login页面** - Google OAuth认证
2. **DailyReport页面** - 主页面，展示完整日报内容
3. **Chat页面** - 对话式交互
4. **Settings页面** - 极简设置（日报时间）

### 创新用户体验功能

**1. 重要性色彩语言系统**
- 紧急邮件：红色边框 + 脉动动画 + ⚡图标
- 商业机会：金色边框 + 💼图标  
- 个人重要：蓝色边框 + ❤️图标
- 工作重要：绿色边框 + 📄图标

**2. 手势批量操作**
- 双击分类标题：批量标记该类邮件已读
- 左滑邮件：标记已读
- 右滑邮件：加星标
- 长按邮件：显示快速操作菜单

**3. AI情感理解显示**
- 🚨 发件人似乎很着急
- 😊 这是一封友好的邮件
- 📋 这是一封正式的商务邮件
- ❓ 发件人可能需要帮助
- 🙏 这是一封感谢邮件

**4. 减负心理暗示**
- 顶部统计卡片：`今日为您节省了23分钟`
- 过滤统计：`已智能过滤47封不重要邮件`
- 完成庆祝：`🎉 今日邮件清零！干得漂亮！`

**5. 邮件情绪地图**
- ☀️ 积极邮件（好消息、表扬）
- ⛅ 中性邮件（信息性内容）
- 🌧️ 消极邮件（问题、需处理）
- ⛈️ 紧急邮件（紧急、愤怒）
- ❄️ 冷淡邮件（正式、拒绝）

### 技术实现架构

**前端技术栈：**
- React 18 + TypeScript
- Zustand状态管理
- React Router v6
- Tailwind CSS + 自定义设计系统
- react-use-gesture手势库
- WebSocket实时通信

**组件架构：**
```
/pages/
├── Login/                    # 认证页面
├── DailyReport/             # 主页面
│   ├── ReportHeader/        # 日报头部
│   ├── StatsCard/           # 统计卡片
│   ├── ImportantEmails/     # 重要邮件列表
│   ├── CategoryEmails/      # 分类邮件列表
│   └── BatchOperations/     # 批量操作
├── Chat/                    # 对话界面
│   ├── MessageList/         # 消息列表
│   ├── InputBox/            # 输入框
│   └── QuickActions/        # 快速操作
└── Settings/                # 设置页面
```

**状态管理设计：**
```typescript
interface AppState {
  auth: {
    user: User | null;
    token: string | null;
    isAuthenticated: boolean;
  };
  dailyReport: {
    data: DailyReportData | null;
    loading: boolean;
    lastUpdated: Date | null;
  };
  chat: {
    messages: ChatMessage[];
    isTyping: boolean;
    sessionId: string | null;
  };
  settings: {
    dailyReportTime: string;
  };
}
```

**API集成：**
- 认证服务：Google OAuth2 + JWT
- 邮件服务：日报获取、批量操作
- 对话服务：WebSocket实时通信
- 设置服务：时间配置管理

### 响应式设计

**断点策略：**
- Mobile: < 768px
- Tablet: 768px - 1024px
- Desktop: > 1024px

**移动端优化：**
- 底部Tab导航
- 手势操作增强
- 卡片式布局
- 渐进式信息披露

### 前端实现更新

**实际组件结构：**
```
/pages/
├── Login/                    # 完整实现
│   ├── GoogleButton         # OAuth触发组件
│   └── ErrorDisplay         # 错误展示
├── AuthCallback/            # 完整实现
│   ├── ProcessingState      # 处理中状态
│   ├── ErrorState          # 错误状态
│   └── SuccessRedirect     # 成功跳转
├── DailyReport/            # 基础实现
│   ├── StatsCards          # 统计卡片组
│   ├── ImportantEmails     # 重要邮件列表
│   └── CategorizedEmails   # 分类邮件
└── Chat/                    # 待实现
```

**API客户端封装：**
```typescript
class ApiClient {
  constructor() {
    this.client = axios.create({
      baseURL: config.apiBaseUrl,
      withCredentials: true,  // 关键：携带Cookie
    });
    
    // 自动注入认证头
    this.client.interceptors.request.use(
      async (config) => {
        const token = await authService.getAccessToken();
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      }
    );
  }
}
```

**状态管理实现：**
- 使用React Context（认证状态）
- 本地状态管理（页面状态）
- 计划引入Zustand（复杂状态）

### 性能优化

**加载优化：**
- 代码分割和懒加载
- 组件级缓存
- 虚拟滚动（大量邮件）
- 图片优化

**交互优化：**
- 页面加载时间 < 2秒
- 交互响应时间 < 200ms
- 流畅的动画效果
- 离线缓存支持

## AI编程测试驱动开发（TDD）方法

### 核心原则

**红-绿-重构循环：**
1. **红**：先编写测试，测试必须失败
2. **绿**：编写最小代码使测试通过
3. **重构**：改进代码质量，保持测试通过

**小步快跑：**
- 每个功能都分解为独立的小步骤
- 每个步骤都有明确的测试验证
- 每完成一步立即验证，不积累问题

**AI-人工协作：**
- AI负责编写测试、实现功能、运行验证
- 人工负责提供反馈、调整方向、验收结果
- 每完成一个步骤，AI报告结果，人工确认后继续

### 测试策略

**单元测试：**
- 每个组件都有对应的测试用例
- 测试组件渲染、用户交互、状态变化
- 使用Jest + React Testing Library

**集成测试：**
- 测试组件间的交互
- 测试API调用和数据流
- 测试状态管理和路由

**端到端测试：**
- 测试完整的用户流程
- 模拟真实用户操作
- 验证整个应用的工作流程

### 质量保证

**自动化验证：**
- TypeScript类型检查
- ESLint代码规范检查
- 测试覆盖率检查
- 自动化测试运行

**持续集成：**
- 每个步骤完成后运行所有测试
- 确保新功能不破坏现有功能
- 及时发现和解决问题

## LLM-Driven架构优势

### 1. 开发效率提升
- **代码量减少80%**：从硬编码模板到LLM自然生成
- **逻辑简化**：复杂的条件判断交给LLM处理
- **维护性增强**：工具描述即文档，易于理解和扩展

### 2. 用户体验优化
- **自然交互**：用户可以用任意自然语言与系统对话
- **智能理解**：LLM能理解上下文和隐含意图
- **动态响应**：根据执行结果灵活调整回复内容
- **学习能力**：通过对话不断优化理解用户偏好

### 3. 系统可靠性
- **错误处理**：LLM能够优雅处理异常情况
- **容错性**：工具调用失败时LLM能自动重试或寻找替代方案
- **扩展性**：新增工具只需要添加@tool装饰器

### 4. 技术优势
- **标准化**：使用LangChain标准框架
- **可观测性**：Agent执行过程完全可追踪
- **多模态支持**：未来可轻松扩展到图像、语音等
- **模型无关**：可随时切换不同的LLM提供商

### 5. 与传统架构对比

| 特性 | 传统硬编码 | LLM-Driven |
|------|------------|------------|
| 代码复杂度 | 高，大量条件判断 | 低，工具描述+LLM推理 |
| 响应格式 | 固定模板 | 动态生成，自然流畅 |
| 用户交互 | 预定义命令 | 自然语言，任意表达 |
| 功能扩展 | 需要修改大量代码 | 只需添加工具描述 |
| 错误处理 | 硬编码错误消息 | LLM智能处理和解释 |
| 学习能力 | 无 | 通过对话持续优化 |

这个新架构代表了从传统的规则驱动系统向智能驱动系统的根本转变，是真正的AI-native设计。

## 项目实施状态

### 已完成模块（截至2025-07-16）

1. **基础架构** ✅
   - 项目结构和环境配置
   - 数据库设计和迁移
   - 基础API框架

2. **认证系统** ✅
   - Google OAuth2完整流程
   - JWT Token管理
   - 数据库会话存储
   - 前端认证集成

3. **Gmail集成** ✅
   - Gmail API服务
   - Token加密存储
   - 自动刷新机制

4. **前端基础** ✅
   - React项目框架
   - 登录和认证流程
   - API客户端封装
   - 基础页面组件

### 进行中模块

1. **LangGraph Agent系统** 🔄
   - Agent基础架构设计完成
   - 工具集开发中
   - EmailProcessor待实现
   - ConversationHandler待实现

2. **定时任务系统** 🔄
   - 基础框架已集成
   - 与热重载冲突待解决

### 待开发模块

1. **核心业务功能** ⏳
   - 邮件自动分析
   - 日报生成逻辑
   - 批量操作功能

2. **前端功能页面** ⏳
   - 邮件列表页面
   - Chat对话页面
   - 设置页面

3. **高级功能** ⏳
   - WebSocket实时通信
   - 向量搜索集成
   - 多语言支持

### 技术债务

1. **需要解决的问题：**
   - Scheduler与uvicorn reload冲突
   - 前端错误边界未实现
   - WebSocket连接管理

2. **需要优化的部分：**
   - 数据库查询性能
   - 前端bundle大小
   - API响应缓存

### 下一步计划

1. **短期目标（1-2周）：**
   - 完成EmailProcessor Agent
   - 实现基础邮件分析功能
   - 开发邮件列表页面

2. **中期目标（3-4周）：**
   - 完成ConversationHandler
   - 实现Chat对话界面
   - 集成WebSocket通信

3. **长期目标（2个月）：**
   - 完善所有功能
   - 性能优化
   - 部署到生产环境