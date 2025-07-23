#!/usr/bin/env python3
"""
测试智能同步功能
"""
import requests
import json
import time
import sys

# 服务配置
BASE_URL = "http://localhost:8000"
HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json"
}

def test_api_endpoint(endpoint, method="GET", data=None, auth_required=True):
    """测试 API 端点"""
    url = f"{BASE_URL}{endpoint}"
    
    try:
        if method == "GET":
            response = requests.get(url, headers=HEADERS)
        elif method == "POST":
            response = requests.post(url, headers=HEADERS, json=data)
        else:
            print(f"❌ 不支持的方法: {method}")
            return False
            
        print(f"🔍 测试 {method} {endpoint}")
        print(f"   状态码: {response.status_code}")
        
        if auth_required and response.status_code == 401:
            print(f"   ✅ 需要认证 (预期行为)")
            return True
        elif response.status_code == 422:
            print(f"   ⚠️  验证错误: {response.text}")
            return False
        elif response.status_code >= 400:
            print(f"   ❌ 错误: {response.text}")
            return False
        else:
            try:
                result = response.json()
                print(f"   ✅ 成功: {json.dumps(result, indent=2, ensure_ascii=False)}")
                return True
            except:
                print(f"   ✅ 成功 (非JSON响应)")
                return True
                
    except Exception as e:
        print(f"   ❌ 连接错误: {e}")
        return False

def main():
    """主测试函数"""
    print("🚀 开始测试智能同步 API 端点")
    print("=" * 50)
    
    # 测试端点列表
    test_cases = [
        # 新的智能同步端点
        ("/api/gmail/sync/smart", "POST", None, True),
        ("/api/gmail/sync/should-sync", "GET", None, True),
        
        # 健康检查 (不需要认证)
        ("/health", "GET", None, False),
        
        # 现有端点
        ("/api/gmail/sync", "POST", {"days": 1, "max_messages": 10}, True),
        ("/api/gmail/sync/status", "GET", None, True),
    ]
    
    success_count = 0
    total_count = len(test_cases)
    
    for endpoint, method, data, auth_required in test_cases:
        if test_api_endpoint(endpoint, method, data, auth_required):
            success_count += 1
        print()
        time.sleep(0.5)  # 避免请求过快
    
    print("=" * 50)
    print(f"📊 测试结果: {success_count}/{total_count} 通过")
    
    if success_count == total_count:
        print("🎉 所有 API 端点测试通过!")
        return True
    else:
        print("⚠️  部分端点测试失败")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)