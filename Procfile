web: python -m gunicorn -c gunicorn.conf.py app.main:app
release: cd backend && python -c "
import sys
import os
sys.path.insert(0, '.')
from alembic.config import Config
from alembic import command

# 检查数据库是否可连接
try:
    from app.core.database import engine
    with engine.connect() as conn:
        print('Database connection successful')
    
    # 运行数据库迁移
    alembic_cfg = Config('alembic.ini')
    command.upgrade(alembic_cfg, 'head')
    print('Database migration completed')
except Exception as e:
    print(f'Database setup failed: {e}')
    sys.exit(1)
"