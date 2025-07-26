# Design: 修复 Agent 工具参数传递问题

## Requirements

修复 Agent 调用工具时参数传递错误的问题。当前问题是 Agent 把参数作为 JSON 字符串传给了第一个位置参数，而不是正确地传递命名参数。

示例错误：
- 用户："最近有什么人给我发邮件"
- Agent 传递：`{"__arg1": "{\"days_back\":3}"}`
- 期望传递：`search_email_history(days_back=3)`

## Solution

### 根本原因分析

LangChain Tool 对象需要明确的参数模式定义。当没有提供 `args_schema` 时，LLM 无法理解如何正确传递多个命名参数，导致把所有参数作为 JSON 字符串传给第一个位置参数。

### 方案选择

经过深入研究，发现之前移除 `@tool` 装饰器是因为使用 LangGraph 而非 LangChain。正确的方案是：

**使用 StructuredTool.from_function**（最终方案）
- 优点：
  - 自动从函数签名推断 args_schema
  - 不需要 @tool 装饰器
  - 与 LangGraph 完全兼容
  - 代码改动最小
- 实现方式：将 `Tool()` 替换为 `StructuredTool.from_function()`

### 实施步骤

1. 导入 `StructuredTool` 类
2. 将所有 `Tool()` 创建改为 `StructuredTool.from_function()`
3. 保持函数定义不变（不使用 @tool 装饰器）
4. 测试参数传递是否正确

### 代码示例

修改前：
```python
from langchain.tools import Tool

tools = [
    Tool(
        name="search_email_history",
        description="搜索历史邮件...",
        func=search_email_history
    ),
    # ... 其他工具
]
```

修改后：
```python
from langchain.tools import StructuredTool

tools = [
    StructuredTool.from_function(
        func=search_email_history,
        name="search_email_history",
        description="搜索历史邮件，支持多种搜索条件..."
    ),
    # ... 其他工具
]
```

函数定义保持不变：
```python
def search_email_history(
    query: Optional[str] = None,
    days_back: Optional[int] = None,
    sender: Optional[str] = None,
    importance_min: Optional[float] = None,
    category: Optional[str] = None,
    is_read: Optional[bool] = None,
    has_attachments: Optional[bool] = None,
    limit: int = 20
) -> str:
    """搜索历史邮件，支持多种搜索条件。"""
    # 函数实现保持不变
```

## Tests

1. 测试参数传递
   - "最近有什么人给我发邮件" → `days_back=3`
   - "张三最近发的邮件" → `sender="张三", days_back=3`
   - "搜索关于项目的邮件" → `query="项目"`

2. 验证工具调用日志
   - 检查参数是否正确解析
   - 确认没有 JSON 字符串作为参数

3. 向后兼容性测试
   - 确保现有功能正常工作