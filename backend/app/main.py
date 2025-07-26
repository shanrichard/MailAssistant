"""
Production-ready FastAPI main application
能够在缺少某些环境变量的情况下优雅启动，仅提供基本的健康检查
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os
import logging

# 基础日志配置
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 检查必需的环境变量
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

# Create FastAPI app
app = FastAPI(
    title="MailAssistant",
    version="1.0.0",
    description="AI-powered email assistant with Gmail integration"
)

# Add basic CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 临时允许所有来源
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

# Health check endpoint - always available
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "app": "MailAssistant",
        "version": "1.0.0",
        "config_complete": has_complete_config,
        "missing_env_vars": missing_env_vars if not has_complete_config else None
    }

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    if has_complete_config:
        return {
            "message": "MailAssistant API - Fully Configured",
            "version": "1.0.0",
            "docs": "/docs"
        }
    else:
        return {
            "message": "MailAssistant API - Configuration Incomplete",
            "version": "1.0.0",
            "status": "missing_environment_variables",
            "missing_vars": missing_env_vars,
            "docs": "/docs"
        }

# Configuration status endpoint
@app.get("/config/status")
async def config_status():
    """Configuration status endpoint"""
    return {
        "config_complete": has_complete_config,
        "missing_env_vars": missing_env_vars,
        "available_endpoints": ["/", "/health", "/config/status"]
    }

# 只有在配置完整的情况下才加载完整的应用功能
if has_complete_config:
    try:
        logger.info("Complete configuration found, loading full application...")
        
        # 导入完整配置和功能
        from .core.config import settings
        from .core.database import create_tables
        from .core.logging import get_logger
        logger.info("Core imports successful")
        
        from .api import auth, gmail, agents, reports
        logger.info("API routers imported successfully")
        
        import socketio
        from .socketio_app import socket_app, get_active_sessions_count, sio
        logger.info("Socket.IO imports successful")
        
        from .utils.cleanup_tasks import cleanup_manager
        from .utils.background_sync_tasks import background_sync_tasks
        logger.info("Background tasks imports successful")
        
        # 更新logger
        logger = get_logger(__name__)
        
        # 启动时初始化数据库
        @app.on_event("startup")
        async def startup_event():
            """Startup event"""
            logger.info("Starting MailAssistant application", version=settings.app_version)
            
            # Create database tables
            try:
                create_tables()
                logger.info("Database tables created successfully")
            except Exception as e:
                logger.error("Failed to create database tables", error=str(e))
                raise
            
            # Start cleanup tasks
            try:
                await cleanup_manager.start()
                logger.info("Cleanup tasks started successfully")
            except Exception as e:
                logger.error("Failed to start cleanup tasks", error=str(e))
            
            # Start background sync tasks
            try:
                await background_sync_tasks.start()
                logger.info("Background sync tasks started successfully")
            except Exception as e:
                logger.error("Failed to start background sync tasks", error=str(e))
        
        @app.on_event("shutdown")
        async def shutdown_event():
            """Shutdown event"""
            logger.info("Shutting down MailAssistant application")
            
            # Stop cleanup tasks
            try:
                await cleanup_manager.stop()
                logger.info("Cleanup tasks stopped successfully")
            except Exception as e:
                logger.error("Failed to stop cleanup tasks", error=str(e))
            
            # Stop background sync tasks
            try:
                await background_sync_tasks.stop()
                logger.info("Background sync tasks stopped successfully")
            except Exception as e:
                logger.error("Failed to stop background sync tasks", error=str(e))
        
        # 更新CORS配置
        app.middlewares.clear()  # 清除之前的中间件
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_allowed_origins,
            allow_credentials=True,
            allow_methods=settings.cors_allowed_methods,
            allow_headers=settings.cors_allowed_headers,
        )
        
        # 先添加一个简单的测试路由
        @app.get("/api/test")
        async def test_endpoint():
            """简单测试端点"""
            return {"message": "API routes working!", "status": "success"}
        
        # Include routers
        logger.info("Including API routers...")
        app.include_router(auth.router, prefix="/api")
        logger.info("Auth router included")
        app.include_router(gmail.router, prefix="/api")
        logger.info("Gmail router included")
        app.include_router(agents.router, prefix="/api")
        logger.info("Agents router included")
        app.include_router(reports.router, prefix="/api")
        logger.info("Reports router included")
        
        # Debug endpoints (only in development)
        if settings.environment == "development":
            from .api import debug_logs
            app.include_router(debug_logs.router)
        
        # Socket.IO 状态端点
        @app.get("/api/socket/status")
        async def socket_status():
            """Socket.IO 状态检查"""
            return {
                "active_connections": get_active_sessions_count(),
                "status": "running"
            }
        
        # Socket.IO 集成 - 在最后包装整个应用
        app = socketio.ASGIApp(sio, other_asgi_app=app)
        logger.info("Socket.IO integration completed")
        
        logger.info("Full MailAssistant application loaded successfully")
        
    except Exception as e:
        logger.error(f"Failed to load full application: {str(e)}")
        logger.info("Running in minimal mode with health check only")
else:
    logger.info("Running in minimal mode - missing required environment variables")
    logger.info(f"Missing variables: {missing_env_vars}")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        reload=False
    )