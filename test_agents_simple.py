#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化的Agent架构测试脚本
"""
import sys
import os
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "backend"))

def test_imports():
    """测试基本导入"""
    print("Testing basic imports...")
    
    try:
        # 测试配置导入
        from backend.app.core.config import settings
        print("✓ Config imported successfully")
        print(f"  App name: {settings.app_name}")
        
        # 测试LLM Provider导入
        from backend.app.agents.llm_provider import llm_provider_manager
        print("✓ LLM Provider imported successfully")
        
        # 测试工具导入
        from backend.app.agents.email_tools import create_email_tools
        from backend.app.agents.conversation_tools import create_conversation_tools
        print("✓ Agent tools imported successfully")
        
        # 测试Agent导入
        from backend.app.agents.email_processor import EmailProcessorAgent
        from backend.app.agents.conversation_handler import ConversationHandler
        print("✓ Agents imported successfully")
        
        # 测试API路由导入
        from backend.app.api.agents import router
        print("✓ API routes imported successfully")
        print(f"  Routes count: {len(router.routes)}")
        
        return True
        
    except Exception as e:
        print(f"✗ Import test failed: {str(e)}")
        return False

def test_tools_creation():
    """测试工具创建"""
    print("\nTesting tools creation...")
    
    try:
        from backend.app.agents.email_tools import create_email_tools
        from backend.app.agents.conversation_tools import create_conversation_tools
        
        # 模拟用户上下文
        user_context = {
            "user_id": "test_user_123",
            "db_session": None,
            "user": None
        }
        
        # 测试邮件工具创建
        email_tools = create_email_tools("test_user_123", None, user_context)
        print(f"✓ Email tools created: {len(email_tools)} tools")
        for tool in email_tools:
            print(f"  - {tool.name}")
        
        # 测试对话工具创建
        conversation_tools = create_conversation_tools("test_user_123", None, user_context)
        print(f"✓ Conversation tools created: {len(conversation_tools)} tools")
        for tool in conversation_tools:
            print(f"  - {tool.name}")
        
        return True
        
    except Exception as e:
        print(f"✗ Tools creation test failed: {str(e)}")
        return False

def test_llm_provider():
    """测试LLM Provider"""
    print("\nTesting LLM Provider...")
    
    try:
        from backend.app.agents.llm_provider import llm_provider_manager
        
        # 检查可用providers
        available_providers = llm_provider_manager.get_available_providers()
        print(f"✓ Available providers: {available_providers}")
        
        if available_providers:
            # 尝试获取LLM实例
            llm = llm_provider_manager.get_llm()
            print(f"✓ LLM instance created: {type(llm).__name__}")
        else:
            print("! No LLM providers available (check API keys)")
        
        return True
        
    except Exception as e:
        print(f"✗ LLM Provider test failed: {str(e)}")
        return False

def test_agent_config():
    """测试Agent配置"""
    print("\nTesting Agent configuration...")
    
    try:
        from backend.app.core.config import settings
        
        print(f"✓ Email processor model: {settings.agents.email_processor_default_model}")
        print(f"✓ Email processor temperature: {settings.agents.email_processor_temperature}")
        print(f"✓ Conversation handler model: {settings.agents.conversation_handler_default_model}")
        print(f"✓ Conversation handler temperature: {settings.agents.conversation_handler_temperature}")
        
        return True
        
    except Exception as e:
        print(f"✗ Agent config test failed: {str(e)}")
        return False

def main():
    """主测试函数"""
    print("Starting LLM-Driven Agent architecture tests\n")
    
    # 设置基本环境变量
    os.environ.setdefault("DATABASE_URL", "postgresql://user@localhost/mailassistant")
    os.environ.setdefault("SECRET_KEY", "test-secret-key")
    os.environ.setdefault("ENCRYPTION_KEY", "test-encryption-key")
    
    tests = [
        test_imports,
        test_agent_config,
        test_llm_provider,
        test_tools_creation,
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"✗ Test {test.__name__} crashed: {str(e)}")
            results.append(False)
    
    # 汇总结果
    passed = sum(results)
    total = len(results)
    
    print(f"\n--- Test Results ---")
    print(f"Passed: {passed}/{total}")
    print(f"Failed: {total - passed}/{total}")
    
    if passed == total:
        print("\n✓ All tests passed! LLM-Driven architecture is ready.")
        print("\nNext steps:")
        print("1. Configure LLM API keys")
        print("2. Start the application and test API endpoints")
        print("3. Test with real user data")
    else:
        print("\n✗ Some tests failed. Please check the errors above.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)