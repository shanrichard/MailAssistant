-- 创建必要的 PostgreSQL 扩展
-- 此脚本在 init-db.sql 之后执行

\c mailassistant;

-- 创建 UUID 扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 创建 pgvector 扩展（用于向量存储和搜索）
CREATE EXTENSION IF NOT EXISTS vector;

-- 创建 pg_trgm 扩展（用于全文搜索）
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- 创建 btree_gin 扩展（优化索引性能）
CREATE EXTENSION IF NOT EXISTS btree_gin;

-- 验证扩展安装
DO $$
DECLARE
    ext_record RECORD;
BEGIN
    RAISE NOTICE 'Installed PostgreSQL extensions:';
    FOR ext_record IN 
        SELECT extname, extversion 
        FROM pg_extension 
        WHERE extname IN ('uuid-ossp', 'vector', 'pg_trgm', 'btree_gin')
        ORDER BY extname
    LOOP
        RAISE NOTICE '  - %: %', ext_record.extname, ext_record.extversion;
    END LOOP;
END
$$;

-- 测试 pgvector 扩展
DO $$
BEGIN
    -- 创建一个临时表来测试 vector 类型
    CREATE TEMP TABLE vector_test (
        id serial PRIMARY KEY,
        embedding vector(3)
    );
    
    -- 插入测试数据
    INSERT INTO vector_test (embedding) VALUES ('[1,2,3]');
    
    -- 如果没有错误，说明 pgvector 工作正常
    RAISE NOTICE 'pgvector extension is working correctly!';
    
    -- 清理
    DROP TABLE vector_test;
EXCEPTION
    WHEN OTHERS THEN
        RAISE WARNING 'pgvector test failed: %', SQLERRM;
END
$$;