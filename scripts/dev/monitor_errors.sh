#!/bin/bash
# 实时监控前端错误

echo "开始监控前端错误（每5秒刷新）..."
echo "按 Ctrl+C 退出"
echo ""

last_count=0

while true; do
    # 获取错误并计数
    errors=$(curl -s -X POST http://localhost:8000/api/debug/logs/all \
        -H "Content-Type: application/json" \
        -d '{"frontend_errors": []}' 2>/dev/null)
    
    current_count=$(echo "$errors" | jq -r '.errors | length')
    
    # 获取最新的几个错误
    latest_errors=$(echo "$errors" | jq -r '.errors[] | 
        select(.source == "frontend") | 
        "\(.timestamp) - \(.message)"' | tail -5)
    
    # 清屏并显示
    clear
    echo "=== 前端错误监控 ==="
    echo "时间: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "总错误数: $current_count"
    
    if [ "$current_count" -gt "$last_count" ]; then
        echo ""
        echo "⚠️  发现新错误！"
        new_errors=$((current_count - last_count))
        echo "新增 $new_errors 个错误"
    fi
    
    echo ""
    echo "最近的错误:"
    echo "$latest_errors"
    
    last_count=$current_count
    
    sleep 5
done