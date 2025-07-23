#!/usr/bin/env python3
"""检查数据库约束"""
import sys
sys.path.append('/Users/shanjingxiang/projects/MailAssistant/backend')

from app.core.database import SessionLocal
from sqlalchemy import text

def check_constraints():
    db = SessionLocal()
    try:
        # 检查约束
        result = db.execute(text("""
            SELECT 
                con.conname AS constraint_name,
                con.contype AS constraint_type,
                pg_get_constraintdef(con.oid) AS constraint_definition
            FROM 
                pg_constraint con
                JOIN pg_class rel ON rel.oid = con.conrelid
                JOIN pg_namespace nsp ON nsp.oid = rel.relnamespace
            WHERE 
                nsp.nspname = 'public'
                AND rel.relname = 'user_sync_status'
        """))
        
        print("=== 现有约束 ===")
        for row in result:
            print(f"名称: {row.constraint_name}")
            print(f"类型: {row.constraint_type}")
            print(f"定义: {row.constraint_definition}")
            print("-" * 50)
        
        # 检查索引
        result = db.execute(text("""
            SELECT 
                i.relname AS index_name,
                idx.indisunique AS is_unique,
                pg_get_indexdef(idx.indexrelid) AS index_definition
            FROM 
                pg_index idx
                JOIN pg_class t ON t.oid = idx.indrelid
                JOIN pg_class i ON i.oid = idx.indexrelid
                JOIN pg_namespace n ON n.oid = t.relnamespace
            WHERE 
                n.nspname = 'public'
                AND t.relname = 'user_sync_status'
        """))
        
        print("\n=== 现有索引 ===")
        for row in result:
            print(f"名称: {row.index_name}")
            print(f"唯一: {row.is_unique}")
            print(f"定义: {row.index_definition}")
            print("-" * 50)
            
    except Exception as e:
        print(f"错误: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    check_constraints()