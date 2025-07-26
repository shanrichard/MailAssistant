# Design: 改进邮件搜索工具和Agent提示词

## Requirements

1. 改进 `search_email_history` 工具，支持更智能的搜索参数
   - 支持时间范围搜索（days_back参数）
   - 支持发件人筛选
   - 支持重要性筛选
   - 支持分类筛选
   - 支持已读/未读状态筛选

2. 改进 ConversationHandler 的系统提示词
   - 添加详细的搜索指导
   - 提供常见查询模式的示例
   - 定义"最近"的默认值为3天

## Solution

### 1. 改进 search_email_history 工具

修改函数签名，支持多个可选参数：
```python
def search_email_history(
    query: Optional[str] = None,          # 关键词搜索
    days_back: Optional[int] = None,      # 最近N天
    sender: Optional[str] = None,         # 发件人筛选
    importance_min: Optional[float] = None, # 最低重要性分数
    category: Optional[str] = None,       # 分类筛选
    is_read: Optional[bool] = None,       # 已读/未读筛选
    has_attachments: Optional[bool] = None, # 是否有附件
    limit: int = 20                       # 结果数量限制
) -> str:
```

### 2. 改进搜索逻辑

- 使用 SQLAlchemy 的链式查询构建动态条件
- 支持多条件组合搜索
- 按 received_at 降序排序（最新的在前）

### 3. 改进 Agent 系统提示词

添加详细的搜索指导，包括：
- 常见查询意图的识别和参数映射
- "最近"等模糊时间表达的处理规则
- 各种查询示例

## Detailed Implementation Plan

### 1. 修改 conversation_tools.py 中的 search_email_history 函数

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
    """搜索历史邮件，支持多种搜索条件。
    
    Args:
        query: 搜索关键词，在主题、发件人或内容中搜索
        days_back: 搜索最近多少天的邮件
        sender: 发件人邮箱或名称筛选
        importance_min: 最低重要性分数（0-1）
        category: 邮件分类（important/spam/promotional/social等）
        is_read: 是否已读（True=已读，False=未读，None=全部）
        has_attachments: 是否有附件
        limit: 返回结果数量限制，默认20
        
    Returns:
        搜索结果的JSON字符串
    """
```

### 2. 修改 ConversationHandler 的系统提示词

在 `_build_system_prompt_for_graph` 方法中添加搜索指导：

```
邮件搜索指导原则：

1. 时间相关查询：
   - "最近"、"这几天" → 使用 days_back=3
   - "今天" → 使用 days_back=1
   - "本周"、"这周" → 使用 days_back=7
   - "上周" → 使用 days_back= 14
   - "本月"、"这个月" → 使用 days_back=30

2. 发件人相关查询：
   - "张三发的邮件" → 使用 sender="张三"
   - "谁给我发邮件" → 不设置query，使用days_back获取邮件
   - "某公司的邮件" → 使用 sender包含公司名称

3. 重要性相关查询：
   - "重要邮件" → 使用 importance_min=0.7
   - "不重要的邮件" → 使用 importance_min=0, category="promotional"或"spam"

4. 状态相关查询：
   - "未读邮件" → 使用 is_read=False
   - "已读邮件" → 使用 is_read=True
   - "有附件的邮件" → 使用 has_attachments=True

5. 组合查询示例：
   - "张三最近发的重要邮件" → sender="张三", days_back=3, importance_min=0.7
   - "本周的未读邮件" → days_back=7, is_read=False
   - "最近有什么人给我发邮件" → days_back=3, 不设置其他参数，获取所有发件人
```

### 3. 搜索结果的返回格式优化

返回结果中包含：
- 总数统计
- 按发件人分组的统计（用于"谁给我发邮件"这类查询）
- 邮件列表，包含完整信息

## Tests

1. 测试各种参数组合：
   - 只有关键词搜索
   - 只有时间范围搜索
   - 发件人 + 时间范围
   - 重要性筛选
   - 多条件组合

2. 测试 Agent 对自然语言查询的理解：
   - "最近有什么人给我发邮件" → days_back=3
   - "张三最近发了什么" → sender="张三", days_back=3
   - "最近的重要邮件" → days_back=3, importance_min=0.7
   - "上周的未读邮件" → days_back=7, is_read=False
   - "今天收到的邮件" → days_back=1
   - "有附件的重要邮件" → has_attachments=True, importance_min=0.7