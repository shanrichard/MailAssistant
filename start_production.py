#!/usr/bin/env python3
"""
Production server startup script for MailAssistant
Only used in production environments (Railway, etc.)
"""
import os
import sys
import subprocess
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
backend_path = project_root / "backend"
sys.path.insert(0, str(backend_path))

# Load environment variables
from dotenv import load_dotenv
load_dotenv(project_root / '.env')

def check_production_environment():
    """确保在生产环境中运行"""
    environment = os.environ.get('ENVIRONMENT', 'development')
    if environment != 'production':
        print("⚠️  Warning: This script is designed for production environments")
        print(f"   Current environment: {environment}")
        print("   Use 'python start_backend.py' for development")
        return False
    return True

def run_database_migrations():
    """运行数据库迁移"""
    try:
        print("🔄 Running database migrations...")
        os.chdir(backend_path)
        
        # 检查数据库连接
        from app.core.database import engine
        with engine.connect() as conn:
            print("✅ Database connection successful")
        
        # 运行迁移
        from alembic.config import Config
        from alembic import command
        
        alembic_cfg = Config('alembic.ini')
        command.upgrade(alembic_cfg, 'head')
        print("✅ Database migration completed")
        
        os.chdir(project_root)
        return True
        
    except Exception as e:
        print(f"❌ Database migration failed: {e}")
        return False

def start_production_server():
    """启动生产服务器"""
    try:
        # 导入设置获取端口
        from app.core.config import settings
        
        print("🚀 Starting MailAssistant production server...")
        print(f"📁 Project root: {project_root}")
        print(f"🌐 Server will start on: {settings.host}:{settings.port}")
        print(f"🏥 Health check: http://{settings.host}:{settings.port}/health")
        print("")
        
        # 使用 gunicorn 启动
        cmd = [
            sys.executable, "-m", "gunicorn",
            "-c", str(project_root / "gunicorn.conf.py"),
            "app.main:app"
        ]
        
        # 切换到 backend 目录
        os.chdir(backend_path)
        
        # 启动服务器
        subprocess.run(cmd, check=True)
        
    except KeyboardInterrupt:
        print("\n🛑 Server shutdown requested")
    except Exception as e:
        print(f"❌ Failed to start production server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    print("🔧 MailAssistant Production Startup")
    print("=" * 40)
    
    # 检查生产环境
    if not check_production_environment():
        response = input("Continue anyway? (y/N): ")
        if response.lower() != 'y':
            print("Aborted.")
            sys.exit(0)
    
    # 运行数据库迁移
    if not run_database_migrations():
        print("❌ Cannot start server due to database issues")
        sys.exit(1)
    
    # 启动生产服务器
    start_production_server()