#!/usr/bin/env python3
"""
本地生产环境模拟测试脚本
在本地测试生产环境配置是否正确
"""
import os
import sys
import subprocess
import time
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "backend"))

def test_production_config():
    """测试生产环境配置"""
    print("🔧 Testing Production Configuration")
    print("=" * 40)
    
    # 设置生产环境变量
    test_env = os.environ.copy()
    test_env.update({
        'ENVIRONMENT': 'production',
        'DEBUG': 'false',
        'CORS_ALLOWED_ORIGINS': '["https://test-domain.vercel.app"]',
        'DATABASE_URL': 'postgresql://test:test@localhost:5432/test',
        'SECRET_KEY': 'test-secret-key-for-local-testing-only',
        'ENCRYPTION_KEY': 'test-encryption-key-32-bytes-long',
        'GOOGLE_CLIENT_ID': 'test-client-id.apps.googleusercontent.com',
        'GOOGLE_CLIENT_SECRET': 'test-client-secret',
        'GOOGLE_REDIRECT_URI': 'https://test-domain.vercel.app/auth/callback',
        'OPENAI_API_KEY': 'sk-test-key'
    })
    
    try:
        # 测试配置加载
        from backend.app.core.config import settings
        
        print(f"✅ Environment: {settings.environment}")
        print(f"✅ Debug mode: {settings.debug}")
        print(f"✅ CORS origins: {settings.cors_allowed_origins}")
        print(f"✅ Database URL configured: {bool(settings.database_url)}")
        print(f"✅ Secret key configured: {bool(settings.secret_key)}")
        
        # 测试数据库配置（不实际连接）
        db_config = settings.database
        print(f"✅ Database pool size: {db_config.pool_size}")
        print(f"✅ Database max overflow: {db_config.max_overflow}")
        
        # 测试LLM配置
        llm_config = settings.llm
        print(f"✅ Default LLM provider: {llm_config.default_provider}")
        print(f"✅ OpenAI key configured: {bool(llm_config.openai_api_key)}")
        
        # 测试安全配置
        security_config = settings.security
        print(f"✅ JWT algorithm: {security_config.jwt_algorithm}")
        print(f"✅ JWT expire minutes: {security_config.jwt_expire_minutes}")
        
        print("\n🎉 Production configuration test passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Configuration test failed: {str(e)}")
        return False

def test_frontend_build():
    """测试前端生产构建"""
    print("\n🏗️  Testing Frontend Production Build")
    print("=" * 40)
    
    frontend_dir = project_root / "frontend"
    
    if not (frontend_dir / "package.json").exists():
        print("❌ Frontend directory not found")
        return False
    
    try:
        # 设置前端环境变量
        env = os.environ.copy()
        env.update({
            'REACT_APP_API_URL': 'https://test-backend.railway.app',
            'REACT_APP_WS_URL': 'https://test-backend.railway.app',
            'REACT_APP_GOOGLE_CLIENT_ID': 'test-client-id.apps.googleusercontent.com',
            'REACT_APP_DEBUG': 'false'
        })
        
        print(f"📁 Frontend directory: {frontend_dir}")
        print(f"🔧 Building with production environment variables...")
        
        # 运行构建命令
        result = subprocess.run(
            ["npm", "run", "build"],
            cwd=frontend_dir,
            env=env,
            capture_output=True,
            text=True,
            timeout=120  # 2分钟超时
        )
        
        if result.returncode == 0:
            build_dir = frontend_dir / "build"
            if build_dir.exists():
                # 检查构建文件
                static_dir = build_dir / "static"
                index_file = build_dir / "index.html"
                
                print(f"✅ Build directory created: {build_dir}")
                print(f"✅ Static files directory: {static_dir.exists()}")
                print(f"✅ Index file created: {index_file.exists()}")
                
                if index_file.exists():
                    # 检查index.html是否包含环境变量
                    content = index_file.read_text()
                    if 'test-backend.railway.app' in content:
                        print("✅ Environment variables injected into build")
                    else:
                        print("⚠️  Environment variables may not be properly injected")
                
                print("\n🎉 Frontend build test passed!")
                return True
            else:
                print("❌ Build directory not created")
                return False
        else:
            print(f"❌ Build failed with exit code {result.returncode}")
            print(f"Error output: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ Build timed out after 2 minutes")
        return False
    except Exception as e:
        print(f"❌ Build test failed: {str(e)}")
        return False

def test_gunicorn_compatibility():
    """测试Gunicorn兼容性"""
    print("\n🦄 Testing Gunicorn Compatibility")
    print("=" * 40)
    
    try:
        # 检查gunicorn是否安装
        result = subprocess.run(
            [sys.executable, "-c", "import gunicorn; print(gunicorn.__version__)"],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print(f"✅ Gunicorn installed: v{result.stdout.strip()}")
        else:
            print("❌ Gunicorn not installed")
            return False
        
        # 测试配置文件语法
        gunicorn_conf = project_root / "gunicorn.conf.py"
        if gunicorn_conf.exists():
            print(f"✅ Gunicorn config file exists: {gunicorn_conf}")
            
            # 测试配置文件语法
            result = subprocess.run(
                [sys.executable, "-c", f"exec(open('{gunicorn_conf}').read())"],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                print("✅ Gunicorn config syntax valid")
            else:
                print(f"❌ Gunicorn config syntax error: {result.stderr}")
                return False
        else:
            print("❌ Gunicorn config file not found")
            return False
        
        # 测试应用导入
        backend_dir = project_root / "backend"
        result = subprocess.run(
            [sys.executable, "-c", "from app.main import app; print('App imported successfully')"],
            cwd=backend_dir,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print("✅ FastAPI app can be imported")
        else:
            print(f"❌ App import failed: {result.stderr}")
            return False
        
        print("\n🎉 Gunicorn compatibility test passed!")
        return True
        
    except Exception as e:
        print(f"❌ Gunicorn test failed: {str(e)}")
        return False

def main():
    """主函数"""
    print("🧪 MailAssistant Local Production Test")
    print("=" * 50)
    print("This script tests production configuration locally")
    print("without actually deploying to production services.")
    print("=" * 50)
    
    # 运行所有测试
    tests = [
        ("Production Config", test_production_config),
        ("Frontend Build", test_frontend_build),
        ("Gunicorn Compatibility", test_gunicorn_compatibility),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"\n💥 {test_name} test crashed: {str(e)}")
            results.append((test_name, False))
    
    # 汇总结果
    print("\n" + "=" * 50)
    print("📊 Test Summary")
    print("=" * 50)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Your configuration is ready for production deployment.")
        sys.exit(0)
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please fix the issues before deploying.")
        sys.exit(1)

if __name__ == "__main__":
    main()