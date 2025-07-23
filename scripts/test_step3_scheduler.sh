#!/bin/bash
# Test Step 3: 验证调度器集成

echo "=== Step 3 测试：验证僵死任务清理集成到主调度器 ==="

TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI2MGYyY2NiZC1kNzU0LTRmYTAtYWE0ZC0zNWE3ZDY1NTFkMzgiLCJlbWFpbCI6ImphbWVzLnNoYW5Ac2lnbmFscGx1cy5jb20iLCJ0eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzUzMjUyNzIwLCJpYXQiOjE3NTMxNjYzMjB9.H6CjDP5L3wwwO1lrdJyEwX8id7TxU_9J7BQ52v4IMUM"

# 1. 检查调度器状态
echo "1. 检查调度器状态..."
SCHEDULER_STATUS=$(curl -s http://localhost:8000/api/scheduler/status)

if [ -z "$SCHEDULER_STATUS" ]; then
  echo "❌ 无法获取调度器状态"
  exit 1
fi

# 检查调度器是否运行
IS_RUNNING=$(echo "$SCHEDULER_STATUS" | jq -r '.scheduler.running')
if [ "$IS_RUNNING" != "true" ]; then
  echo "❌ 调度器未运行"
  exit 1
fi

echo "✓ 调度器正在运行"

# 2. 检查僵死任务清理job
echo -e "\n2. 检查僵死任务清理job..."
HAS_ZOMBIE_CLEANUP=$(echo "$SCHEDULER_STATUS" | jq -r '.jobs_summary.has_zombie_cleanup')
if [ "$HAS_ZOMBIE_CLEANUP" != "true" ]; then
  echo "❌ 未找到僵死任务清理job"
  exit 1
fi

ZOMBIE_JOB=$(echo "$SCHEDULER_STATUS" | jq -r '.zombie_cleanup_job')
echo "✓ 找到僵死任务清理job"
echo "   ID: $(echo "$ZOMBIE_JOB" | jq -r '.id')"
echo "   名称: $(echo "$ZOMBIE_JOB" | jq -r '.name')"
echo "   触发器: $(echo "$ZOMBIE_JOB" | jq -r '.trigger')"
echo "   下次运行: $(echo "$ZOMBIE_JOB" | jq -r '.next_run_time')"

# 3. 创建一个僵死任务进行测试
echo -e "\n3. 创建测试用的僵死任务..."
# 这里需要创建一个会变成僵死的任务
# 为了测试，我们可以创建一个任务但不让它更新心跳

# 4. 等待清理周期（最多等待2.5分钟）
echo -e "\n4. 等待清理周期（最多2.5分钟）..."
echo "监控清理日志..."

# 获取当前时间
START_TIME=$(date +%s)
CLEANUP_DETECTED=false

# 循环检查日志，最多等待150秒（2.5分钟）
while [ $(($(date +%s) - START_TIME)) -lt 150 ]; do
  # 检查最近的日志
  LOGS=$(curl -s http://localhost:8000/api/debug/logs/backend | jq -r '.errors[-50:][].message' 2>/dev/null | grep -E "Starting zombie task cleanup|Zombie task cleanup completed")
  
  if [ ! -z "$LOGS" ]; then
    echo "检测到清理活动："
    echo "$LOGS" | tail -5
    CLEANUP_DETECTED=true
    break
  fi
  
  sleep 10
done

# 5. 验证结果
echo -e "\n5. 测试结果："
if [ "$CLEANUP_DETECTED" = true ]; then
  echo "✅ Step 3 测试通过！"
  echo "   - 调度器正常运行"
  echo "   - 僵死任务清理job已集成"
  echo "   - 清理任务按计划执行"
else
  echo "❌ 测试失败：未检测到清理活动"
  echo "   可能原因："
  echo "   - 清理周期还未到达"
  echo "   - 调度器未正确启动清理任务"
  exit 1
fi

# 6. 显示所有调度任务
echo -e "\n6. 当前所有调度任务："
echo "$SCHEDULER_STATUS" | jq '.jobs[] | {id: .id, name: .name, next_run: .next_run_time}'