-- 检查user_sync_status表的所有约束
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
    AND rel.relname = 'user_sync_status';

-- 检查索引
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
    AND t.relname = 'user_sync_status';