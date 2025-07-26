"""
逐步恢复FastAPI应用功能 - Step 3: 添加API路由模块导入
"""
from fastapi import FastAPI
import os
import logging

# 基础日志配置
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Step 2: 尝试导入核心配置模块
core_imports_success = False
core_import_error = None

try:
    from .core.config import settings
    from .core.logging import get_logger
    logger = get_logger(__name__)
    core_imports_success = True
    logger.info("Core config imports successful")
except Exception as e:
    core_import_error = str(e)
    logger.error(f"Core config import failed: {e}")
    # 继续使用基础logger

# Step 3: 尝试导入API路由模块
api_imports_success = False
api_import_error = None

if core_imports_success:
    try:
        from .api import auth, gmail, agents, reports
        api_imports_success = True
        logger.info("API router imports successful")
    except Exception as e:
        api_import_error = str(e)
        logger.error(f"API router import failed: {e}")
else:
    api_import_error = "Skipped due to core import failure"

# 检查环境变量
def check_required_env_vars():
    """检查必需的环境变量"""
    missing_vars = []
    required_vars = [
        "DATABASE_URL",
        "GOOGLE_CLIENT_ID", 
        "GOOGLE_CLIENT_SECRET",
        "GOOGLE_REDIRECT_URI",
        "SECRET_KEY",
        "ENCRYPTION_KEY"
    ]
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    return missing_vars

# 检查环境变量状态
missing_env_vars = check_required_env_vars()
has_complete_config = len(missing_env_vars) == 0

logger.info(f"Environment check: has_complete_config = {has_complete_config}")
if not has_complete_config:
    logger.info(f"Missing variables: {missing_env_vars}")

app = FastAPI(title="MailAssistant Step 3 - API Router Import Test")

@app.get("/")
def root():
    return {
        "message": "FastAPI with API router import test!", 
        "status": "success",
        "config_complete": has_complete_config,
        "core_imports_success": core_imports_success,
        "api_imports_success": api_imports_success
    }

@app.get("/health")
def health():
    return {
        "status": "healthy", 
        "mode": "step3_api_routers",
        "config_complete": has_complete_config,
        "missing_env_vars": missing_env_vars if not has_complete_config else None,
        "core_imports_success": core_imports_success,
        "core_import_error": core_import_error,
        "api_imports_success": api_imports_success,
        "api_import_error": api_import_error
    }

@app.get("/api/test")
def api_test():
    return {"message": "API route working!", "status": "success"}

# 配置状态端点
@app.get("/config/status")
def config_status():
    return {
        "config_complete": has_complete_config,
        "missing_env_vars": missing_env_vars,
        "env_count": len([k for k in os.environ.keys() if not k.startswith('_')]),
        "core_imports_success": core_imports_success,
        "core_import_error": core_import_error,
        "api_imports_success": api_imports_success,
        "api_import_error": api_import_error
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)