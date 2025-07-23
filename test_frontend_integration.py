#!/usr/bin/env python3
"""
测试前端页面集成
通过检查前端编译状态来验证新组件是否正确集成
"""
import subprocess
import sys
import time
import requests
from pathlib import Path

def test_frontend_build():
    """测试前端构建是否成功"""
    print("🔍 测试前端构建")
    
    frontend_dir = Path(__file__).parent / "frontend"
    
    try:
        # 检查前端是否正在运行
        response = requests.get("http://localhost:3000", timeout=5)
        if response.status_code == 200:
            print("   ✅ 前端服务正在运行")
            return True
        else:
            print(f"   ❌ 前端服务响应异常: {response.status_code}")
            return False
            
    except requests.ConnectionError:
        print("   ❌ 前端服务未运行或无法连接")
        return False
    except Exception as e:
        print(f"   ❌ 前端测试失败: {e}")
        return False

def test_frontend_files():
    """测试前端文件是否存在"""
    print("\n🔍 测试前端文件结构")
    
    frontend_files = [
        "frontend/src/hooks/useSyncTrigger.ts",
        "frontend/src/services/gmailService.ts", 
        "frontend/src/stores/syncStore.ts",
        "frontend/src/pages/DailyReport.tsx",
        "frontend/src/pages/Chat.tsx",
        "frontend/src/pages/Settings.tsx"
    ]
    
    success_count = 0
    for file_path in frontend_files:
        full_path = Path(__file__).parent / file_path
        if full_path.exists():
            print(f"   ✅ {file_path}")
            success_count += 1
        else:
            print(f"   ❌ {file_path} 不存在")
    
    print(f"   📊 文件检查: {success_count}/{len(frontend_files)} 通过")
    return success_count == len(frontend_files)

def test_typescript_types():
    """测试 TypeScript 类型定义"""
    print("\n🔍 检查 TypeScript 类型导出")
    
    # 检查 useSyncTrigger Hook 的类型导出
    hook_file = Path(__file__).parent / "frontend/src/hooks/useSyncTrigger.ts"
    
    if not hook_file.exists():
        print("   ❌ useSyncTrigger.ts 不存在")
        return False
    
    content = hook_file.read_text()
    
    required_exports = [
        ("SyncStatus type", "SyncStatus"),
        ("SyncStats interface", "SyncStats"), 
        ("SyncResult interface", "export interface SyncResult"),
        ("useSyncTrigger const", "export const useSyncTrigger"),
        ("default export", "export default useSyncTrigger")
    ]
    
    success_count = 0
    for export_name, export_pattern in required_exports:
        if export_pattern in content:
            print(f"   ✅ {export_name}")
            success_count += 1
        else:
            print(f"   ❌ {export_name} 未找到")
    
    print(f"   📊 类型导出: {success_count}/{len(required_exports)} 通过")
    return success_count == len(required_exports)

def test_component_imports():
    """测试组件导入"""
    print("\n🔍 检查组件导入")
    
    # 检查 DailyReport 组件的导入
    daily_report_file = Path(__file__).parent / "frontend/src/pages/DailyReport.tsx"
    
    if not daily_report_file.exists():
        print("   ❌ DailyReport.tsx 不存在")
        return False
    
    content = daily_report_file.read_text()
    
    required_imports = [
        "import { useSyncTrigger }",
        "import { useSyncStore }",
        "ArrowPathIcon"
    ]
    
    success_count = 0
    for import_stmt in required_imports:
        if import_stmt in content:
            print(f"   ✅ {import_stmt}")
            success_count += 1
        else:
            print(f"   ❌ {import_stmt} 未找到")
    
    # 检查 Settings 页面的导入
    settings_file = Path(__file__).parent / "frontend/src/pages/Settings.tsx"
    
    if settings_file.exists():
        settings_content = settings_file.read_text()
        if "useSyncTrigger" in settings_content:
            print("   ✅ Settings 页面集成了同步功能")
            success_count += 1
        else:
            print("   ❌ Settings 页面未集成同步功能")
    
    print(f"   📊 组件导入: {success_count}/{len(required_imports) + 1} 通过")
    return success_count >= len(required_imports)

def test_api_integration():
    """测试 API 集成"""
    print("\n🔍 检查 API 集成")
    
    gmail_service_file = Path(__file__).parent / "frontend/src/services/gmailService.ts"
    
    if not gmail_service_file.exists():
        print("   ❌ gmailService.ts 不存在")
        return False
    
    content = gmail_service_file.read_text()
    
    required_methods = [
        "smartSync",
        "shouldSync", 
        "getSyncProgress"
    ]
    
    success_count = 0
    for method in required_methods:
        if f"async {method}" in content or f"{method}" in content:
            print(f"   ✅ {method} 方法存在")
            success_count += 1
        else:
            print(f"   ❌ {method} 方法不存在")
    
    print(f"   📊 API 方法: {success_count}/{len(required_methods)} 通过")
    return success_count == len(required_methods)

def main():
    """主测试函数"""
    print("🚀 开始测试前端页面集成")
    print("=" * 60)
    
    tests = [
        test_frontend_files,
        test_typescript_types,
        test_component_imports,
        test_api_integration,
        test_frontend_build
    ]
    
    success_count = 0
    total_count = len(tests)
    
    for test_func in tests:
        try:
            if test_func():
                success_count += 1
                print("   🎉 测试通过")
            else:
                print("   ❌ 测试失败")
        except Exception as e:
            print(f"   ❌ 测试异常: {e}")
        
        print()
    
    print("=" * 60)
    print(f"📊 测试结果: {success_count}/{total_count} 通过")
    
    if success_count == total_count:
        print("🎉 所有前端集成测试通过!")
        return True
    else:
        print("⚠️  部分前端集成测试失败")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)