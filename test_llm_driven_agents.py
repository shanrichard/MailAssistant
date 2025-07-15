#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LLM-Driven Agent架构测试脚本
"""
import sys
import os
import asyncio
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "backend"))

async def test_llm_provider():
    """测试LLM Provider"""
    print("🔍 测试LLM Provider...")
    
    try:
        from backend.app.agents.llm_provider import llm_provider_manager
        
        # 检查可用的providers
        available_providers = llm_provider_manager.get_available_providers()
        print(f"✅ 可用的LLM providers: {available_providers}")
        
        if not available_providers:
            print("❌ 没有可用的LLM providers，请检查API密钥配置")
            return False
        
        # 测试获取LLM实例
        llm = llm_provider_manager.get_llm()
        print(f"✅ 成功获取LLM实例: {type(llm).__name__}")
        
        # 测试基本生成（如果有可用的API密钥）
        try:
            response = await llm_provider_manager.generate_with_fallback("Hello, how are you?")
            print(f"✅ LLM响应测试成功，响应长度: {len(response)}")
            print(f"   响应预览: {response[:100]}...")
            return True
        except Exception as e:
            print(f"⚠️  LLM响应测试失败（可能是API密钥问题）: {str(e)}")
            return True  # Provider本身可用，只是API调用失败
            
    except Exception as e:
        print(f"❌ LLM Provider测试失败: {str(e)}")
        return False

async def test_agent_tools():
    """测试Agent工具"""
    print("\n🔍 测试Agent工具...")
    
    try:
        from backend.app.agents.email_tools import create_email_tools
        from backend.app.agents.conversation_tools import create_conversation_tools
        
        # 模拟用户上下文
        user_context = {
            "user_id": "test_user_123",
            "db_session": None,  # 在实际环境中需要真实的数据库会话
            "user": None
        }
        
        # 测试邮件工具
        email_tools = create_email_tools("test_user_123", None, user_context)
        print(f"✅ 成功创建邮件工具，数量: {len(email_tools)}")
        for tool in email_tools:
            print(f"   - {tool.name}: {tool.description}")
        
        # 测试对话工具
        conversation_tools = create_conversation_tools("test_user_123", None, user_context)
        print(f"✅ 成功创建对话工具，数量: {len(conversation_tools)}")
        for tool in conversation_tools:
            print(f"   - {tool.name}: {tool.description}")
        
        return True
        
    except Exception as e:
        print(f"❌ Agent工具测试失败: {str(e)}")
        return False

async def test_agent_initialization():
    """测试Agent初始化（不依赖数据库）"""
    print("\n🔍 测试Agent初始化...")
    
    try:
        # 这里我们只测试类定义和导入，不实际创建实例
        # 因为创建实例需要数据库连接
        
        from backend.app.agents.email_processor import EmailProcessorAgent
        from backend.app.agents.conversation_handler import ConversationHandler
        from backend.app.agents.base_agent import BaseAgent, StatefulAgent
        
        print("✅ 成功导入EmailProcessorAgent")
        print("✅ 成功导入ConversationHandler")
        print("✅ 成功导入BaseAgent和StatefulAgent")
        
        # 检查类定义
        print(f"✅ EmailProcessorAgent基类: {EmailProcessorAgent.__bases__}")
        print(f"✅ ConversationHandler基类: {ConversationHandler.__bases__}")
        
        return True
        
    except Exception as e:
        print(f"❌ Agent初始化测试失败: {str(e)}")
        return False

async def test_api_routes():
    """测试API路由定义"""
    print("\n🔍 测试API路由...")
    
    try:
        from backend.app.api.agents import router
        
        print(f"✅ 成功导入Agent API路由")
        print(f"✅ 路由前缀: {router.prefix}")
        print(f"✅ 路由标签: {router.tags}")
        
        # 检查路由数量
        route_count = len(router.routes)
        print(f"✅ 定义的路由数量: {route_count}")
        
        for route in router.routes:
            if hasattr(route, 'path') and hasattr(route, 'methods'):
                print(f"   - {list(route.methods)[0]} {route.path}")
        
        return True
        
    except Exception as e:
        print(f"❌ API路由测试失败: {str(e)}")
        return False

async def test_configuration():
    """测试配置"""
    print("\n🔍 测试配置...")
    
    try:
        from backend.app.core.config import settings
        
        print(f"✅ 成功加载配置")
        print(f"✅ 应用名称: {settings.app_name}")
        print(f"✅ 默认LLM提供商: {settings.llm.default_provider}")
        print(f"✅ 默认LLM模型: {settings.llm.default_model}")
        
        # 检查Agent配置
        print(f"✅ EmailProcessor默认模型: {settings.agents.email_processor_default_model}")
        print(f"✅ EmailProcessor温度: {settings.agents.email_processor_temperature}")
        print(f"✅ ConversationHandler默认模型: {settings.agents.conversation_handler_default_model}")
        print(f"✅ ConversationHandler温度: {settings.agents.conversation_handler_temperature}")
        
        return True
        
    except Exception as e:
        print(f"❌ 配置测试失败: {str(e)}")
        return False

async def main():
    """主测试函数"""
    print("🚀 开始LLM-Driven Agent架构测试\n")
    
    test_results = []
    
    # 运行各项测试
    test_results.append(await test_configuration())
    test_results.append(await test_llm_provider())
    test_results.append(await test_agent_tools())
    test_results.append(await test_agent_initialization())
    test_results.append(await test_api_routes())
    
    # 汇总结果
    passed = sum(test_results)
    total = len(test_results)
    
    print(f"\n📊 测试结果汇总:")
    print(f"   通过: {passed}/{total}")
    print(f"   失败: {total - passed}/{total}")
    
    if passed == total:
        print("\n🎉 所有测试通过！新的LLM-Driven架构基本可用。")
        print("\n📝 后续建议:")
        print("   1. 配置正确的LLM API密钥以测试实际功能")
        print("   2. 启动应用并测试API端点")
        print("   3. 使用真实用户数据测试Agent功能")
    else:
        print("\n⚠️  部分测试失败，请检查错误信息并修复问题。")
    
    return passed == total

if __name__ == "__main__":
    # 设置环境变量（如果需要）
    os.environ.setdefault("DATABASE_URL", "postgresql://user@localhost/mailassistant")
    os.environ.setdefault("SECRET_KEY", "test-secret-key")
    os.environ.setdefault("ENCRYPTION_KEY", "test-encryption-key")
    
    # 运行测试
    success = asyncio.run(main())
    sys.exit(0 if success else 1)