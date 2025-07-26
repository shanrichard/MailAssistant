"""
逐步恢复FastAPI应用功能 - Step 1: 添加配置加载
"""
from fastapi import FastAPI
import os
import logging

# 基础日志配置
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

app = FastAPI(title="MailAssistant Step 1 - Config Test")

@app.get("/")
def root():
    return {
        "message": "FastAPI with config check working!", 
        "status": "success",
        "config_complete": has_complete_config
    }

@app.get("/health")
def health():
    return {
        "status": "healthy", 
        "mode": "step1_config",
        "config_complete": has_complete_config,
        "missing_env_vars": missing_env_vars if not has_complete_config else None
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
        "env_count": len([k for k in os.environ.keys() if not k.startswith('_')])
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)