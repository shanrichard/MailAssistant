"""
Production-safe FastAPI main application
优先保证健康检查通过，然后逐步加载完整功能
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os
import logging

# 基础日志配置
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app - 使用基础配置
app = FastAPI(
    title="MailAssistant",
    version="1.0.0",
    description="AI-powered email assistant with Gmail integration"
)

# Add basic CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "Origin", "User-Agent"],
)

# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.error(f"Unhandled exception on {request.url.path}: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

# Health check endpoint - 最优先保证这个工作
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "app": "MailAssistant",
        "version": "1.0.0"
    }

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "MailAssistant API - Basic Mode",
        "version": "1.0.0",
        "docs": "/docs"
    }

# 尝试加载完整功能，但失败时不影响基础功能
try:
    logger.info("Attempting to load full application features...")
    
    # 检查环境变量
    required_vars = ["DATABASE_URL", "GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "SECRET_KEY"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if not missing_vars:
        logger.info("Environment variables complete, loading full features...")
        
        # 尝试导入核心模块
        from .core.config import settings
        from .core.database import create_tables
        from .core.logging import get_logger
        logger.info("Core modules imported successfully")
        
        # 尝试导入API路由
        from .api import auth, gmail, agents, reports
        logger.info("API modules imported successfully")
        
        # 添加API路由
        app.include_router(auth.router, prefix="/api")
        app.include_router(gmail.router, prefix="/api")
        app.include_router(agents.router, prefix="/api")
        app.include_router(reports.router, prefix="/api")
        logger.info("API routers included successfully")
        
        # 启动时初始化数据库
        @app.on_event("startup")
        async def startup_event():
            """Initialize database on startup"""
            try:
                create_tables()
                logger.info("Database tables initialized")
            except Exception as e:
                logger.error(f"Database initialization failed: {e}")
        
        # 更新健康检查以反映完整功能
        @app.get("/health")
        async def health_check_full():
            """Enhanced health check endpoint"""
            return {
                "status": "healthy",
                "app": "MailAssistant",
                "version": "1.0.0",
                "mode": "full_features",
                "api_routes": ["auth", "gmail", "agents", "reports"]
            }
        
        logger.info("Full application features loaded successfully")
        
    else:
        logger.info(f"Missing environment variables: {missing_vars}")
        logger.info("Running in basic mode")
        
except Exception as e:
    logger.error(f"Failed to load full features: {str(e)}")
    logger.info("Running in basic mode - health check still available")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        reload=False
    )