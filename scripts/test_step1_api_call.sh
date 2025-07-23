#!/bin/bash
# Test Step 1: 验证API函数调用修复

echo "=== Step 1 测试：验证API函数调用 ==="

# 设置token（需要替换为实际token）
TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI2MGYyY2NiZC1kNzU0LTRmYTAtYWE0ZC0zNWE3ZDY1NTFkMzgiLCJlbWFpbCI6ImphbWVzLnNoYW5Ac2lnbmFscGx1cy5jb20iLCJ0eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzUzMjUyNzIwLCJpYXQiOjE3NTMxNjYzMjB9.H6CjDP5L3wwwO1lrdJyEwX8id7TxU_9J7BQ52v4IMUM"

# 1. 调用智能同步API
echo "1. 调用智能同步API..."
RESPONSE=$(curl -s -X POST http://localhost:8000/api/gmail/sync/smart \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json")

echo "响应: $RESPONSE"

# 2. 检查是否有错误
if echo "$RESPONSE" | grep -q "execute_background_sync_v2"; then
  echo "❌ 测试失败：函数名错误仍然存在"
  exit 1
fi

if echo "$RESPONSE" | grep -q "NameError"; then
  echo "❌ 测试失败：NameError异常"
  exit 1
fi

# 3. 验证返回了task_id
TASK_ID=$(echo "$RESPONSE" | jq -r '.task_id' 2>/dev/null)
if [ -z "$TASK_ID" ] || [ "$TASK_ID" == "null" ]; then
  echo "❌ 测试失败：没有返回task_id"
  exit 1
fi

echo "✅ Step 1 测试通过！"
echo "任务ID: $TASK_ID"
echo "消息: $(echo "$RESPONSE" | jq -r '.message')"