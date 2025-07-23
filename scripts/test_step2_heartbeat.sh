#!/bin/bash
# Test Step 2: 验证心跳机制修复

echo "=== Step 2 测试：验证心跳更新 ==="

TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI2MGYyY2NiZC1kNzU0LTRmYTAtYWE0ZC0zNWE3ZDY1NTFkMzgiLCJlbWFpbCI6ImphbWVzLnNoYW5Ac2lnbmFscGx1cy5jb20iLCJ0eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzUzMjUyNzIwLCJpYXQiOjE3NTMxNjYzMjB9.H6CjDP5L3wwwO1lrdJyEwX8id7TxU_9J7BQ52v4IMUM"

# 1. 创建新的同步任务
echo "1. 创建同步任务..."
RESPONSE=$(curl -s -X POST http://localhost:8000/api/gmail/sync/smart \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json")

TASK_ID=$(echo "$RESPONSE" | jq -r '.task_id')
if [ -z "$TASK_ID" ] || [ "$TASK_ID" == "null" ]; then
  echo "❌ 无法创建任务"
  exit 1
fi

echo "任务ID: $TASK_ID"

# 2. 监控心跳更新（30秒，应该看到至少2次更新）
echo -e "\n2. 监控心跳更新（30秒）..."
echo "时间戳记录："

LAST_UPDATE=""
UPDATE_COUNT=0

for i in {1..6}; do
  sleep 5
  
  PROGRESS=$(curl -s http://localhost:8000/api/gmail/sync/progress/$TASK_ID \
    -H "Authorization: Bearer $TOKEN")
  
  CURRENT_UPDATE=$(echo "$PROGRESS" | jq -r '.updatedAt')
  IS_RUNNING=$(echo "$PROGRESS" | jq -r '.isRunning')
  PROGRESS_PCT=$(echo "$PROGRESS" | jq -r '.progress')
  
  echo "[$i] 更新时间: $CURRENT_UPDATE, 进度: $PROGRESS_PCT%, 运行中: $IS_RUNNING"
  
  # 检查时间戳是否更新
  if [ "$LAST_UPDATE" != "$CURRENT_UPDATE" ] && [ ! -z "$LAST_UPDATE" ]; then
    UPDATE_COUNT=$((UPDATE_COUNT + 1))
    echo "    ✓ 检测到心跳更新！"
  fi
  
  LAST_UPDATE="$CURRENT_UPDATE"
  
  # 如果任务已完成，退出
  if [ "$IS_RUNNING" == "false" ]; then
    echo "任务已完成"
    break
  fi
done

# 3. 验证结果
echo -e "\n3. 测试结果："
if [ $UPDATE_COUNT -ge 1 ]; then
  echo "✅ Step 2 测试通过！检测到 $UPDATE_COUNT 次心跳更新"
else
  echo "❌ 测试失败：没有检测到心跳更新"
  echo "可能原因：异步函数仍在使用同步阻塞调用"
  exit 1
fi