"""
FastAPI main application
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from .core.config import settings
from .core.database import create_tables
from .core.logging import get_logger
from .api import auth, gmail, agents, reports
import socketio
from .socketio_app import socket_app, get_active_sessions_count, sio
from .utils.cleanup_tasks import cleanup_manager
from .utils.background_sync_tasks import background_sync_tasks

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
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
    
    yield
    
    # Shutdown
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


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="AI-powered email assistant with Gmail integration",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=True,
    allow_methods=settings.cors_allowed_methods,
    allow_headers=settings.cors_allowed_headers,
)


# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.error("Unhandled exception", error=str(exc), path=request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": settings.app_version
    }


# Include routers

app.include_router(auth.router, prefix="/api")
app.include_router(gmail.router, prefix="/api")
app.include_router(agents.router, prefix="/api")
app.include_router(reports.router, prefix="/api")

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

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "MailAssistant API",
        "version": settings.app_version,
        "docs": "/docs"
    }

# Socket.IO 集成 - 在最后包装整个应用
app = socketio.ASGIApp(sio, other_asgi_app=app)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
        reload=False
    )