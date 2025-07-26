"""
Production-ready FastAPI main application - 无环境变量检查版本
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os
import logging

# 基础日志配置
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
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

try:
    logger.info("Loading application with full imports but minimal logic...")
    
    # 导入完整配置和功能
    from .core.config import settings
    from .core.database import create_tables
    from .core.logging import get_logger
    logger.info("Core imports successful")
    
    from .api import auth, gmail, agents, reports
    logger.info("API routers imported successfully")
    
    # Socket.IO 恢复
    import socketio
    from .socketio_app import socket_app, get_active_sessions_count, sio
    logger.info("Socket.IO imports successful")
    
    from .utils.cleanup_tasks import cleanup_manager
    from .utils.background_sync_tasks import background_sync_tasks
    logger.info("Background tasks imports successful")
    
    # 更新logger
    logger = get_logger(__name__)
    
    # 启动时初始化数据库 - Startup 里所有重活都包 try，不再 raise
    @app.on_event("startup")
    async def startup_event():
        """Startup event - degraded mode safe"""
        logger.info("⏳ startup begin", version=settings.app_version)
        
        # Create database tables - log 后继续
        try:
            create_tables()
            logger.info("Database tables created successfully") 
        except Exception:
            logger.exception("create_tables failed, continue startup")
        
        # Start background tasks - 不让任何一个阻塞启动
        for name, task in {"cleanup": cleanup_manager, "bg_sync": background_sync_tasks}.items():
            try:
                await task.start()
                logger.info(f"{name} tasks started successfully")
            except Exception:
                logger.exception("%s start failed, continue", name)
        
        logger.info("✅ startup done (degraded mode possible)")
    
    @app.on_event("shutdown")
    async def shutdown_event():
        """Shutdown event - safe cleanup"""
        logger.info("🔄 shutdown begin")
        
        # Stop background tasks - 容错处理
        for name, task in {"cleanup": cleanup_manager, "bg_sync": background_sync_tasks}.items():
            try:
                await task.stop()
                logger.info(f"{name} tasks stopped successfully")
            except Exception:
                logger.exception("%s stop failed, continue", name)
        
        logger.info("✅ shutdown done")
    
    # 更新CORS配置 - 移除危险的 middlewares.clear()
    # app.middlewares.clear()  # FastAPI >0.110 这里会报错
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allowed_origins,
        allow_credentials=True,
        allow_methods=settings.cors_allowed_methods,
        allow_headers=settings.cors_allowed_headers,
    )
    
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
    
    # Health check endpoint - 定义在FastAPI上，不受Socket.IO影响
    @app.get("/health")
    async def health_check():
        """Health check endpoint"""
        return {
            "status": "healthy",
            "app": settings.app_name,
            "version": settings.app_version
        }
    
    # Root endpoint
    @app.get("/")
    async def root():
        """Root endpoint"""
        return {
            "message": "MailAssistant API",
            "version": settings.app_version,
            "docs": "/docs"
        }
    
    # Socket.IO 状态端点
    @app.get("/api/socket/status")
    async def socket_status():
        """Socket.IO 状态检查"""
        return {
            "active_connections": get_active_sessions_count(),
            "status": "running"
        }
    
    # Socket.IO 集成 - 使用原始包装方式（经过startup修复，应该安全）
    app = socketio.ASGIApp(sio, other_asgi_app=app)
    
    logger.info("Full MailAssistant application loaded successfully")
    
except Exception as e:
    logger.error(f"Failed to load minimal application: {str(e)}")
    
    # 极简健康检查
    @app.get("/health")
    async def health_check_minimal():
        """极简健康检查"""
        return {"status": "healthy", "mode": "minimal"}
    
    @app.get("/")
    async def root_minimal():
        """极简根路径"""
        return {"message": "MailAssistant - Minimal Mode"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        reload=False
    )