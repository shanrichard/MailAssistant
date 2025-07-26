#!/usr/bin/env python3
"""
数据库迁移脚本 - 用于Railway部署
"""
import sys
import os
from alembic.config import Config
from alembic import command

def run_migrations():
    """运行数据库迁移"""
    try:
        print("=== Database Migration Start ===")
        
        # 检查数据库连接
        print("Testing database connection...")
        from app.core.database import engine
        with engine.connect() as conn:
            print("✅ Database connection successful")
        
        # 运行迁移
        print("Running Alembic migrations...")
        alembic_cfg = Config('alembic.ini')
        command.upgrade(alembic_cfg, 'head')
        print("✅ Database migration completed")
        
        print("=== Database Migration Success ===")
        
    except Exception as e:
        print(f"❌ Database setup failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    run_migrations()