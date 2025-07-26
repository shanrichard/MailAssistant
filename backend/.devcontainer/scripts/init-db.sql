-- MailAssistant 数据库初始化脚本
-- 此脚本在 PostgreSQL 容器首次启动时执行

-- 创建数据库（如果不存在）
-- 注意：在 docker-entrypoint-initdb.d 中执行时，数据库已经存在
-- CREATE DATABASE IF NOT EXISTS mailassistant;

-- 连接到 mailassistant 数据库
\c mailassistant;

-- 创建应用 schema
CREATE SCHEMA IF NOT EXISTS app;

-- 设置搜索路径
SET search_path TO app, public;

-- 创建用户角色（如果需要）
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'mailassistant_app') THEN
        CREATE ROLE mailassistant_app WITH LOGIN PASSWORD 'app_password';
    END IF;
END
$$;

-- 授予权限
GRANT ALL PRIVILEGES ON DATABASE mailassistant TO mailassistant_app;
GRANT ALL PRIVILEGES ON SCHEMA app TO mailassistant_app;
GRANT ALL PRIVILEGES ON SCHEMA public TO mailassistant_app;

-- 设置默认权限
ALTER DEFAULT PRIVILEGES IN SCHEMA app GRANT ALL ON TABLES TO mailassistant_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA app GRANT ALL ON SEQUENCES TO mailassistant_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA app GRANT ALL ON FUNCTIONS TO mailassistant_app;

-- 输出初始化完成信息
DO $$
BEGIN
    RAISE NOTICE 'Database initialization completed successfully!';
    RAISE NOTICE 'Database: mailassistant';
    RAISE NOTICE 'Schema: app';
    RAISE NOTICE 'User: mailassistant_app';
END
$$;