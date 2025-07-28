"""
ConversationHandler Agent - 基于LangGraph的对话处理代理
"""
from typing import List, Dict, Any, Optional, Annotated, TypedDict, Sequence
from datetime import datetime, timezone
import uuid
import json
from threading import Lock
import asyncio

from langchain.tools import Tool, StructuredTool
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph.message import add_messages

from .base_agent import StatefulAgent
from .conversation_tools import create_conversation_tools
from ..core.config import settings
from ..core.logging import get_logger
from ..core.cache import CheckpointerCache
from ..core.errors import AppError, ErrorCategory, translate_error
from ..core.retry import with_retry, CONVERSATION_RETRY_POLICY
from ..models.conversation import ConversationMessage
from ..utils.chunk_accumulator import ChunkAccumulator

logger = get_logger(__name__)

class AgentState(TypedDict):
    """Agent状态定义"""
    messages: Annotated[Sequence[BaseMessage], add_messages]
    user_id: str
    session_id: str

class ConversationHandler(StatefulAgent):
    """对话处理Agent - 基于LangGraph，支持流式响应和工具调用可视化"""
    
    # 类级别缓存LLM实例，避免重复初始化
    # 使用 (provider, model, temperature) 作为缓存键
    _llm_cache = {}
    _cache_lock = Lock()  # 线程安全的缓存访问锁
    
    # 使用TTL缓存替代弱引用字典，解决竞态条件问题
    _checkpointer_cache = CheckpointerCache(max_size=1000, ttl_hours=24)
    
    def __init__(self, user_id: str, db_session, user=None):
        """初始化ConversationHandler"""
        super().__init__(user_id, db_session, user)
        
        # 创建LangGraph agent，使用更精确的缓存键
        cache_key = (
            settings.llm.default_provider,
            self._get_default_model(),
            self._get_temperature()
        )
        
        # 线程安全的缓存访问
        with self._cache_lock:
            if cache_key not in self._llm_cache:
                self._llm_cache[cache_key] = self.llm
            
        # 获取 checkpointer
        self.checkpointer = self._get_checkpointer()
        
        # 创建 agent，使用 prompt 参数（LangGraph 0.5.3 推荐）
        self.graph_agent = create_react_agent(
            model=self._llm_cache[cache_key],
            tools=self.tools,
            prompt=self._build_prompt,
            checkpointer=self.checkpointer
        )
    
    def _wrap_tool_with_error_handling(self, tool: Tool) -> Tool:
        """包装工具，添加统一的错误处理"""
        original_func = tool.func
        original_afunc = getattr(tool, 'afunc', None)
        
        def sync_wrapper(*args, **kwargs):
            try:
                return original_func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Tool {tool.name} failed", 
                           tool_name=tool.name,
                           error=str(e),
                           user_id=self.user_id)
                return {
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "tool": tool.name,
                    "success": False,
                    "message": self._get_user_friendly_error_message(e)
                }
        
        async def async_wrapper(*args, **kwargs):
            try:
                if original_afunc:
                    return await original_afunc(*args, **kwargs)
                else:
                    # 在异步上下文中运行同步函数
                    loop = asyncio.get_event_loop()
                    return await loop.run_in_executor(None, original_func, *args, **kwargs)
            except Exception as e:
                logger.error(f"Tool {tool.name} failed (async)", 
                           tool_name=tool.name,
                           error=str(e),
                           user_id=self.user_id)
                return {
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "tool": tool.name,
                    "success": False,
                    "message": self._get_user_friendly_error_message(e)
                }
        
        # 创建新的工具实例，保留原有属性
        # 使用 StructuredTool 以正确处理多参数函数
        return StructuredTool(
            name=tool.name,
            description=tool.description,
            func=sync_wrapper,
            afunc=async_wrapper,
            return_direct=tool.return_direct,
            args_schema=tool.args_schema
        )
    
    def _get_user_friendly_error_message(self, error: Exception) -> str:
        """将技术错误转换为用户友好的消息"""
        error_messages = {
            "ConnectionError": "连接服务失败，请稍后重试",
            "TimeoutError": "操作超时，请稍后重试",
            "ValueError": "输入参数有误，请检查后重试",
            "PermissionError": "权限不足，无法执行此操作"
        }
        
        error_type = type(error).__name__
        return error_messages.get(error_type, f"操作失败: {str(error)}")
    
    def _create_tools(self) -> List[Tool]:
        """创建对话处理工具集，应用统一的错误处理"""
        user_context = {
            "user_id": self.user_id,
            "db_session": self.db,
            "user": self.user
        }
        
        # 获取原始工具列表
        raw_tools = create_conversation_tools(self.user_id, self.db, user_context)
        
        # 为每个工具应用错误处理包装
        wrapped_tools = []
        for tool in raw_tools:
            wrapped_tool = self._wrap_tool_with_error_handling(tool)
            wrapped_tools.append(wrapped_tool)
            logger.debug(f"Wrapped tool: {tool.name}", user_id=self.user_id)
        
        return wrapped_tools
    
    def _get_default_model(self) -> str:
        """获取默认模型"""
        return settings.agents.conversation_handler_default_model
    
    def _get_temperature(self) -> float:
        """获取温度参数"""
        return settings.agents.conversation_handler_temperature
    
    @with_retry(CONVERSATION_RETRY_POLICY)
    def _get_checkpointer(self):
        """根据策略获取 checkpointer - 默认使用 per_user 策略，带重试机制"""
        # 默认使用 per_user 策略，每个用户共享一个 checkpointer
        checkpointer_key = f"user_{self.user_id}"
        
        # 使用新的TTL缓存，自动处理线程安全和过期清理
        return self._checkpointer_cache.get_or_create(
            checkpointer_key,
            lambda: InMemorySaver()
        )
    
    def _build_prompt(self, state: Dict, config: Dict) -> List[BaseMessage]:
        """构建包含系统提示的消息列表"""
        system_prompt = self._build_system_prompt_for_graph()
        messages = state.get("messages", [])
        
        # 应用消息裁剪（如果启用）
        if settings.agents.message_pruning_enabled:
            messages = self._prune_messages(messages)
        
        return [SystemMessage(content=system_prompt)] + messages
    
    def _prune_messages(self, messages: List[BaseMessage]) -> List[BaseMessage]:
        """裁剪消息以防止超过限制"""
        if settings.agents.pruning_strategy == "count":
            return self._prune_by_count(messages)
        elif settings.agents.pruning_strategy == "tokens":
            return self._prune_by_tokens(messages)
        else:
            return messages
    
    def _prune_by_count(self, messages: List[BaseMessage]) -> List[BaseMessage]:
        """基于消息数量的裁剪"""
        max_count = settings.agents.max_messages_count
        
        if len(messages) <= max_count:
            return messages
        
        # 保留最近的 N 条消息
        return messages[-max_count:]
    
    def _prune_by_tokens(self, messages: List[BaseMessage]) -> List[BaseMessage]:
        """基于 token 数量的智能裁剪"""
        max_tokens = settings.agents.max_tokens_count
        
        # 简化版实现：基于字符数估算 (约4个字符 = 1个token)
        # 生产环境建议使用 tiktoken 进行精确计算
        total_chars = 0
        result = []
        
        # 从后往前遍历，保留最新的消息
        for msg in reversed(messages):
            msg_chars = len(msg.content)
            estimated_tokens = msg_chars // 4
            
            if total_chars + msg_chars > max_tokens * 4:
                break
            
            result.insert(0, msg)
            total_chars += msg_chars
        
        return result
    
    def _build_system_prompt_for_graph(self) -> str:
        """构建LangGraph使用的系统prompt"""
        return """你是用户的贴心邮件管家。在回应用户之前，你必须先深入思考和理解用户的真实需求。

## 🧠 核心思维模式

### 第一步：深入理解用户需求
当用户提出请求时，你必须：
1. **暂停并思考** - 不要急于调用工具，先理解用户真正想要什么
2. **分析本质需求** - 用户说的话背后，他们真正的目的是什么？
   - 例如："最近的邮件" → 用户可能想了解错过了什么重要信息
   - 例如："Google的邮件" → 用户可能在找某个特定的验证码或通知
3. **识别隐含意图** - 用户没说出来但可能需要的是什么？
4. **评估模糊性** - 如果请求不清晰，列出可能的理解并询问澄清

### 💡 用户意图的核心判断原则

用户的表达往往是模糊和不规范的，不要试图匹配具体的词汇或句式，而应该基于以下原则进行语义理解：

**核心判断原则：**
1. **意图本质判断**：用户是想"告诉你自己的情况"还是"获取信息"？
2. **动作类型分析**：是"配置类动作"还是"查询类动作"？
3. **语义上下文理解**：从整句话的语义结构判断真实意图
4. **避免表面匹配**：不要被词汇表面相似性误导

当用户的表达涉及邮件和公司名称时，重点理解：
- 用户是在"表达偏好/设置想法"（→ 偏好管理）
- 还是在"寻求已有信息"（→ 邮件搜索）

相信你的语义理解能力，从用户话语的整体意图出发做判断。

### 第二步：工具使用策略分析
在理解需求后，认真分析如何使用工具：
1. **工具能力映射** - 我有哪些工具可以帮助实现用户的目标？
2. **组合策略** - 是否需要多个工具配合？执行顺序如何？
3. **参数优化** - 如何设置参数才能最好地满足用户需求？
4. **自动处理复杂性** - 特别是搜索邮件时，如果结果超过单页限制（50封），必须自动通过分页获取所有相关数据，而不是让用户处理分页细节

### 第三步：邮件搜索的智慧使用
邮件搜索是最复杂的工具，使用时必须：
1. **理解筛选器的局限性** - 数据库只能做硬匹配，所以：
   - 时间筛选：将"最近"、"这几天"等模糊表述转换为具体的 days_back
   - 发件人筛选：理解用户可能用简称，但数据库存储的是完整格式
   - 状态筛选：理解"重要邮件"需要先搜索再根据内容判断
   
2. **搜索策略选择**：
   - 宽松搜索：当用户需求模糊时，使用较宽的条件，获取更多结果后再分析
   - 精确搜索：当用户需求明确时，使用精确条件快速定位
   - 迭代搜索：第一次搜索无结果时，放宽条件重试

3. **结果分析与处理**：
   - 不只是展示邮件列表，要分析邮件内容的重要性
   - 识别邮件类型（通知、验证码、工作邮件、广告等）
   - 提供处理建议（需要回复、仅供参考、可以忽略等）

## 📋 你的专业能力

1. **深度理解与分析** - 不满足于表面理解，深挖用户真实需求
2. **智能工具编排** - 根据需求选择最优的工具组合方案
3. **用户偏好管理** - 记住这是为生成日报准备的，不是Gmail标签
4. **邮件内容解读** - 分析邮件重要性和处理优先级
5. **主动追问澄清** - 当信息不足时，主动询问获取更多上下文
6. **个性化建议** - 基于用户历史偏好提供定制化建议

## 🔧 邮件搜索工具

你有两个邮件搜索工具：

### 1. search_gmail_online - 直连 Gmail 搜索
- 能搜索 Gmail 中的所有邮件，包括所有分类
- 搜索范围最全面，包括推广、社交、动态、论坛等所有分类的邮件
- 使用 Gmail 搜索语法：`search_gmail_online(query="from:google.com newer_than:7d")`
- 最多返回40封邮件，但覆盖范围最广

### 2. search_email_history - 本地数据库搜索
- 速度快，支持分页，可获取更多邮件
- 仅搜索已同步到本地的邮件（可能不完整）
- 使用参数化调用：`search_email_history(query="关键词", days_back=7, sender="发件人", is_read=False)`

### 🎯 必须执行的搜索策略：

**重要原则：每次搜索都必须同时使用两个搜索工具，互相补充！**

1. **标准搜索流程**：
   - 第一步：同时调用 `search_gmail_online` 和 `search_email_history`
   - 第二步：合并两个搜索结果，去除重复邮件
   - 第三步：基于合并后的完整结果进行分析

2. **为什么要同时使用两个工具**：
   - Gmail在线搜索：确保不漏掉任何分类的邮件
   - 本地数据库搜索：可以获取更多历史邮件和支持分页
   - 两者互补：一个搜不到的邮件可能在另一个中存在

3. **智能搜索转换**：
   - 将用户的搜索需求转换成两种不同的查询格式
   - Gmail查询：使用 Gmail 语法如 "from:apple.com newer_than:7d"
   - 本地查询：使用参数如 sender="apple", days_back=7

### 搜索语法差异

本地搜索使用参数：
- query, days_back, sender, is_read, has_attachments, limit, offset

Gmail 搜索使用查询字符串（注意时间语法）：
- from:, to:, subject:, is:, has:, label:
- **时间搜索可以使用以下操作符：**
  - newer_than: 或 newer: 或 after: （都是相同效果）
  - older_than: 或 older: 或 before: （都是相同效果）
  - 相对时间：7d (天), 2m (月), 1y (年)
  - 具体日期：YYYY/MM/DD 或 YYYY-MM-DD 格式
- 支持 AND/OR 组合

### 时间搜索示例
- 搜索5月份的邮件：`after:2025/5/1 before:2025/6/1` 或 `newer_than:2025/5/1 older_than:2025/6/1`
- 搜索最近30天：`newer_than:30d` 或 `newer:30d`
- 搜索2-3个月前的邮件：`older_than:2m newer_than:3m`
- 搜索特定日期后：`after:2025/1/15`

### 返回的邮件字段说明：
- `subject`: 完整的邮件主题
- `sender`: 发件人信息
- `recipients`: 收件人列表（JSON格式）
- `cc_recipients`: 抄送人列表（JSON格式）
- `body`: 邮件正文内容（固定返回前1000字符，足够分析）
- `body_truncated`: 布尔值，表示正文是否被截断
- `received_at`: 接收时间
- `is_read`/`is_important`/`has_attachments`: 状态标记

注意：现在返回的是 `body` 而不是 `snippet`，包含更多内容供分析。

### 搜索结果分页机制（重要）：
**默认限制**：每次搜索最多返回50封邮件（之前是20封）

**你必须自动处理分页**：当搜索结果超过50封时，你需要：

1. **自动获取所有数据**：
   - 第一次搜索获取前50封和`total_count`
   - 如果`has_more`为true，自动使用`offset`参数继续获取后续页面
   - 重复直到获取所有相关邮件（但要注意合理限制）
   
2. **智能处理策略**：
   - **50-150封**：自动分页获取所有数据，然后统一分析总结
   - **150-300封**：获取前150封最新的，同时提醒用户可能有更早的邮件未展示
   - **300封以上**：只获取前100封（2页），明确告诉用户需要缩小搜索范围才能有效分析
   
3. **分页获取示例**：
   ```python
   # 初次搜索
   result1 = search_email_history(days_back=30)  # 获取前50封
   # 如果 has_more=true 且 total_count 在合理范围内
   result2 = search_email_history(days_back=30, offset=50)  # 获取51-100封
   result3 = search_email_history(days_back=30, offset=100)  # 获取101-150封
   # 合并所有结果后统一分析
   ```

4. **给用户的反馈**：
   - 不要向用户展示分页细节
   - 直接告诉用户找到的邮件总数
   - 根据所有获取到的邮件进行综合分析
   - 如果邮件太多无法全部获取，明确说明只分析了最新的N封

5. **错误处理**：
   - 如果搜索出错，检查错误信息并给出合理建议
   - 不要让用户手动处理分页

### ⚡ 搜索失败时的智能处理策略：

当搜索没有找到结果时，**必须主动进行智能重试**：

1. **智能字段切换策略**：
   - 发件人搜不到 → 尝试在关键词中搜索
   - 关键词搜不到 → 尝试在发件人中搜索
   - 严格匹配失败 → 使用模糊匹配
   
   例如：
   - sender="apple" 无结果 → 尝试 query="apple"
   - query="验证码" 无结果 → 尝试 query="verification" 或 "code"
   - sender="Google" 无结果 → 尝试 sender="google.com" 或 query="google"

2. **智能关键词变换**：
   - 中英文互换："微软" ↔ "Microsoft"
   - 简称全称转换："MS" ↔ "Microsoft"
   - 同义词替换："账单" → "invoice", "bill", "payment"
   - 拼写纠正："appel" → "apple"

3. **扩展搜索范围**：
   - 时间范围：7天无结果 → 扩展到30天
   - 搜索精度：精确匹配 → 模糊匹配
   - 搜索字段：单字段 → 多字段组合

### 🔄 搜索无结果的处理流程

当邮件搜索返回空结果时的标准处理流程：

**第一步：自动尝试Gmail在线搜索**
如果你刚才使用的是本地数据库搜索，立即自动尝试Gmail在线搜索：

```
"本地搜索没有找到结果，让我直接从Gmail服务器搜索..."
使用 search_gmail_online(query="用户的搜索条件")
```

**第二步：分析和反馈**
- 如果Gmail在线搜索找到了结果：说明是本地同步不完整
- 如果都没找到：分析搜索词并提供建议

2. **其他可能性**：
   - 邮件发件人的显示名称与您搜索的不完全匹配
   - 邮件可能在较早或较晚的时间范围内
   - 搜索的公司名称可能需要调整"

**智能建议策略**
基于sender_summary中的实际数据，给出具体的替代搜索建议，而不是空洞的"请重试"。

### 🔄 失败后的智能重试策略：

**重要：当两个搜索工具都没有找到结果时，你必须立即启动智能重试机制！**

#### 第一轮重试 - 字段切换：
如果 sender="apple" 无结果：
- 立即尝试 query="apple"（可能邮件内容中包含）
- 同时尝试 sender="apple.com"（域名形式）
- 再试 query="Apple Inc"（公司全称）

#### 第二轮重试 - 智能变体：
1. **拼写纠错**：
   - "appel" → "apple"
   - "mircosoft" → "microsoft" 
   - "gmial" → "gmail"

2. **语言转换**：
   - "微软" → "Microsoft"
   - "谷歌" → "Google"
   - "苹果" → "Apple"

3. **同义词替换**：
   - "账单" → "invoice", "bill", "payment", "费用"
   - "验证码" → "verification", "code", "OTP", "verify"
   - "会议" → "meeting", "calendar", "会议邀请"

#### 第三轮重试 - 扩大范围：
1. **时间范围扩展**：
   - 7天无结果 → 扩展到30天
   - 30天无结果 → 扩展到90天

2. **模糊搜索**：
   - 从精确的发件人搜索改为关键词搜索
   - 使用部分匹配而非完全匹配

#### 实际操作示例：
用户："帮我找苹果公司的邮件"
- 第1次：sender="苹果" （两个工具同时搜索）
- 第2次：sender="apple", query="苹果"（智能切换）
- 第3次：sender="apple.com", query="Apple"（域名+英文）
- 第4次：query="Apple Inc" OR "苹果公司"（扩大范围）

**每次重试都要告诉用户你在做什么，保持透明！**

## 📊 输出格式要求

**始终使用 Markdown 格式**，但要根据内容调整结构：

### 邮件搜索结果展示：
```markdown
## 🔍 搜索与分析

**理解您的需求**：[说明你理解的用户真实意图]

**搜索情况**：共找到 [total_count] 封相关邮件[如果超过获取数量，说明只分析了最新的N封]

## 📊 综合分析结果

### 📌 关键发现
[基于所有获取到的邮件，总结最重要的发现和模式]

### 🔴 需要立即关注的邮件
[只列出真正重要的3-5封邮件，包含关键信息和建议行动]

### 📈 邮件概况
- 主要发件人分布：[基于统计的洞察]
- 时间分布特征：[什么时段邮件最多]
- 内容类型分析：[邮件主要涉及哪些主题]

### 💡 行动建议
[基于整体分析给出的建议，而不是逐封邮件建议]

---
## 💭 深度洞察

[基于所有邮件的整体趋势、模式识别、潜在问题等深入分析]
```

## 🎯 用户偏好管理原则

**重要提醒**：用户偏好是为了生成个性化的邮件日报，不是为了给Gmail打标签！

记录偏好时关注：
1. **重要性判断** - 用户认为什么类型的邮件重要/不重要
2. **分类偏好** - 用户希望邮件如何分组（工作/个人/财务等）
3. **关注重点** - 用户特别关心哪些发件人或主题
4. **处理习惯** - 用户通常如何处理不同类型的邮件
5. **时间偏好** - 用户查看邮件的时间习惯

这些信息将用于：
- 生成符合用户阅读习惯的日报
- 突出用户关心的重要邮件
- 按用户喜欢的方式组织邮件

## 🛠️ 可用工具说明

- **search_email_history**: 搜索本地数据库邮件
  - 必须使用关键字参数
  - 支持多条件组合搜索
  - 返回结果包含 sender_summary 统计

- **search_gmail_online**: 直连 Gmail 搜索邮件
  - 使用 Gmail 搜索语法
  - 最多返回 40 封邮件
  - 可搜索所有 Gmail 邮件

- **read_daily_report**: 读取已生成的邮件日报

- **bulk_mark_read**: 批量标记邮件已读
  - 需要先搜索确认要标记的邮件

- **update_user_preferences**: 更新用户偏好
  - 记录用户对邮件重要性的判断
  - 用于优化日报生成

- **trigger_email_processor**: 触发邮件处理任务
  - 可以生成日报或执行其他批处理

- **get_task_status**: 查询任务状态

## 💡 核心工作原则

1. **先思考，后行动** - 深入理解需求再调用工具
2. **主动不盲动** - 预测用户需求但要确认理解正确
3. **详细不冗长** - 提供深度分析但保持清晰简洁
4. **智能不自作聪明** - 不确定时询问，不要猜测
5. **个性化服务** - 基于用户历史偏好定制回应
6. **永不放弃搜索** - 搜索失败时必须智能重试，尝试多种策略
7. **双管齐下** - 每次搜索都同时使用本地和在线两个工具

记住：
- 你的价值不在于快速调用工具，而在于深入理解用户需求并提供最合适的解决方案
- 搜索邮件时，必须同时使用两个搜索工具，确保不遗漏任何邮件
- 当搜索无结果时，立即启动智能重试机制，通过字段切换、关键词变换等策略找到邮件
- 每次回应都应该体现出你的思考深度和专业性"""
    
    async def stream_response(self, message: str, session_id: str):
        """流式传输响应，包含工具调用信息"""
        try:
            # 构建输入状态（无需手动加载历史，checkpointer会自动管理）
            input_state = {
                "messages": [HumanMessage(content=message)],
                "user_id": self.user_id,
                "session_id": session_id
            }
            
            # 保存用户消息到数据库（用于前端展示）
            user_msg = ConversationMessage(
                user_id=self.user_id,
                session_id=session_id,
                role="user",
                content=message,
                message_type="user_message"
            )
            self.db.add(user_msg)
            self.db.commit()
            
            # 使用新的 astream API（切换到messages模式以获取tool_call_chunks）
            response_id = str(uuid.uuid4())
            config = {"configurable": {"thread_id": f"{self.user_id}_{session_id}"}}
            
            # 初始化工具调用状态跟踪
            if not hasattr(self, '_active_tool_calls'):
                self._active_tool_calls = {}
            
            # 初始化 chunk 累积器
            accumulator = ChunkAccumulator(
                min_chunk_size=settings.chunk_min_size,
                max_wait_time=settings.chunk_max_wait,
                delimiter_pattern=settings.chunk_delimiter_pattern
            )
            accumulated_content = ""  # 用于数据库写入
            
            async for chunk, metadata in self.graph_agent.astream(
                input_state,
                config=config,
                stream_mode="messages"  # 切换到messages模式以获取tool_call_chunks
            ):
                # 🎯 处理tool_call_chunks（LangGraph工具调用流）
                if hasattr(chunk, 'tool_call_chunks') and chunk.tool_call_chunks:
                    for tool_chunk in chunk.tool_call_chunks:
                        async for event in self._handle_tool_call_chunk(tool_chunk):
                            yield event
                
                # 处理AI响应内容
                if hasattr(chunk, 'content') and chunk.content:
                    # 🔍 检查是否是工具执行结果
                    tool_result_event = self._extract_tool_result_from_content(chunk.content)
                    if tool_result_event:
                        # 这是工具执行结果，发送工具结果事件而不是普通响应
                        yield tool_result_event
                    else:
                        # 使用累积器处理普通AI响应内容
                        emit_content = accumulator.add(chunk.content)
                        accumulated_content += chunk.content
                        
                        if emit_content:
                            yield {
                                "type": "agent_response_chunk",
                                "content": emit_content,
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                                "id": response_id
                            }
                
                # 🗑️ 移除所有基于错误假设的工具调用处理代码
                # 现在使用正确的tool_call_chunks处理机制
            
            # 发送剩余内容
            final_content = accumulator.flush()
            if final_content:
                yield {
                    "type": "agent_response_chunk",
                    "content": final_content,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "id": response_id
                }
            
            # 一次性写入完整消息到数据库
            if accumulated_content:
                ai_msg = ConversationMessage(
                    user_id=self.user_id,
                    session_id=session_id,
                    role="assistant",
                    content=accumulated_content,
                    message_type="ai_response"
                )
                self.db.add(ai_msg)
                self.db.commit()
            
            # 发送完成信号
            yield {
                "type": "conversation_complete",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
                
        except Exception as e:
            # 转换为用户友好的错误
            if isinstance(e, AppError):
                app_error = e
            else:
                app_error = translate_error(e)
            
            logger.error("Stream response failed", 
                        user_id=self.user_id,
                        session_id=session_id,
                        error=str(e),
                        error_category=app_error.category.value)
            
            # 返回用户友好的错误信息
            error_response = app_error.to_dict()
            error_response['timestamp'] = datetime.now(timezone.utc).isoformat()
            yield error_response
    
    async def _handle_tool_call_chunk(self, tool_chunk):
        """处理单个工具调用chunk - 基于真实的LangGraph结构"""
        
        # 🎯 第一个chunk：包含完整工具信息 (name, id, type)
        if tool_chunk.get('name') and tool_chunk.get('id'):
            tool_id = tool_chunk['id']
            tool_name = tool_chunk['name']
            
            # 初始化工具调用状态
            self._active_tool_calls[tool_id] = {
                'name': tool_name,
                'args_fragments': [tool_chunk.get('args', '')],  # 开始收集参数片段
                'status': 'building_args',
                'start_time': datetime.now(timezone.utc)
            }
            
            logger.debug(f"Tool call started: {tool_name} (ID: {tool_id})", 
                        user_id=self.user_id, tool_name=tool_name, tool_id=tool_id)
            
            # 🚀 发送工具调用开始事件
            yield {
                "type": "tool_call_start",
                "tool_name": tool_name,
                "tool_args": None,  # 参数还在构建中
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "id": tool_id
            }
        
        # 🎯 后续chunks：累积参数片段 (只有args字段，name和id为None)
        elif tool_chunk.get('args') is not None:
            # 找到对应的活跃工具调用（最近的正在构建参数的调用）
            active_call = None
            for call_id, call_data in self._active_tool_calls.items():
                if call_data['status'] == 'building_args':
                    active_call = (call_id, call_data)
                    break
            
            if active_call:
                call_id, call_data = active_call
                call_data['args_fragments'].append(tool_chunk['args'])
                
                # 🔧 尝试解析完整参数
                full_args_str = ''.join(call_data['args_fragments'])
                try:
                    args_dict = json.loads(full_args_str)
                    # 参数构建完成
                    call_data['status'] = 'args_complete'
                    call_data['args'] = args_dict
                    
                    logger.debug(f"Tool call args complete: {call_data['name']}", 
                                user_id=self.user_id, tool_args=args_dict, tool_id=call_id)
                    
                    # 🎯 发送参数完整事件
                    yield {
                        "type": "tool_call_args_complete",
                        "tool_name": call_data['name'],
                        "tool_args": args_dict,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "id": call_id
                    }
                except json.JSONDecodeError:
                    # 参数还在构建中，继续等待
                    logger.debug(f"Tool call args building: {len(full_args_str)} chars", 
                                user_id=self.user_id, args_preview=full_args_str[:100])
                    pass
            else:
                # 没有找到对应的活跃工具调用，记录警告
                logger.warning("Received tool args chunk but no active tool call found", 
                              user_id=self.user_id, chunk_args=tool_chunk.get('args', '')[:50])

    def _extract_tool_result_from_content(self, content):
        """从AI响应内容中提取工具执行结果"""
        try:
            # 🔍 检查是否是JSON格式的工具结果
            if content.strip().startswith('{"status"'):
                # 尝试解析工具结果JSON
                tool_result = json.loads(content.strip())
                
                # 找到对应的活跃工具调用
                for call_id, call_data in list(self._active_tool_calls.items()):
                    if call_data['status'] in ['building_args', 'args_complete']:
                        # 找到匹配的工具调用，生成结果事件
                        call_data['status'] = 'completed'
                        call_data['result'] = tool_result
                        
                        # 🎯 发送工具执行结果事件
                        result_event = {
                            "type": "tool_call_result",
                            "tool_name": call_data['name'],
                            "tool_result": tool_result,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "id": call_id
                        }
                        
                        # 清理已完成的工具调用
                        del self._active_tool_calls[call_id]
                        
                        logger.debug(f"Tool call completed: {call_data['name']}", 
                                    user_id=self.user_id, tool_id=call_id, 
                                    result_size=len(str(tool_result)))
                        
                        return result_event
                        
        except (json.JSONDecodeError, KeyError, AttributeError) as e:
            # 不是工具结果，返回None继续作为普通内容处理
            logger.debug(f"Content is not tool result: {str(e)}", 
                        user_id=self.user_id, content_preview=content[:50])
            pass
        
        return None
    
    
    @classmethod
    def clear_llm_cache(cls):
        """清理 LLM 缓存（用于测试或内存管理）"""
        with cls._cache_lock:
            cls._llm_cache.clear()
            logger.info("LLM cache cleared")
    
    @classmethod
    def clear_checkpointer_cache(cls):
        """清理 checkpointer 缓存"""
        cls._checkpointer_cache.clear()
        logger.info("Checkpointer cache cleared")
    
    @classmethod
    def get_cache_stats(cls) -> Dict[str, Any]:
        """获取缓存统计信息"""
        with cls._cache_lock:
            llm_stats = {
                "size": len(cls._llm_cache),
                "keys": list(cls._llm_cache.keys()),
                "memory_usage_estimate": f"{len(cls._llm_cache) * 100}MB"  # 粗略估计
            }
        
        # 获取 checkpointer 缓存统计（TTL缓存自带统计方法）
        checkpointer_stats = cls._checkpointer_cache.get_stats()
        
        return {
            "llm_cache": llm_stats,
            "checkpointer_cache": checkpointer_stats
        }
    
    def process(self, message: str) -> str:
        """同步处理消息（保持向后兼容）"""
        try:
            import asyncio
            # 正确调用基类的异步方法
            return asyncio.run(super().process(message))
        except Exception as e:
            logger.error("Process message failed", 
                        user_id=self.user_id,
                        error=str(e))
            return f"处理失败：{str(e)}"
    
    def get_capabilities(self) -> List[str]:
        """获取Agent能力列表"""
        return [
            "natural_language_understanding",  # 自然语言理解
            "task_orchestration",             # 任务编排
            "preference_management",          # 偏好管理
            "email_search",                   # 邮件搜索
            "bulk_operations",                # 批量操作
            "status_tracking",                # 状态跟踪
            "conversation_management",        # 对话管理
            "intelligent_suggestions",       # 智能建议
            "workflow_automation",            # 工作流自动化
            "context_awareness",              # 上下文感知
            "streaming_response",             # 流式响应
            "tool_visualization"              # 工具可视化
        ]