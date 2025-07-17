"""
FastAPI main application
"""
from fastapi import FastAPI, Request, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

from .core.config import settings
from .core.database import create_tables
from .core.logging import get_logger
from .api import auth, gmail, scheduler, agents
from .websockets.agent_ws import websocket_handler

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
    
    # Start task scheduler
    # TODO: Fix scheduler startup issue
    # try:
    #     from .scheduler import start_scheduler
    #     await start_scheduler()
    #     logger.info("Task scheduler started successfully")
    # except Exception as e:
    #     logger.error("Failed to start task scheduler", error=str(e))
    #     raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down MailAssistant application")
    
    # Stop task scheduler
    # TODO: Fix scheduler shutdown issue
    # try:
    #     from .scheduler import stop_scheduler
    #     await stop_scheduler()
    #     logger.info("Task scheduler stopped successfully")
    # except Exception as e:
    #     logger.error("Failed to stop task scheduler", error=str(e))


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
    allow_origins=["http://localhost:3000"],  # React app origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
app.include_router(scheduler.router, prefix="/api")
app.include_router(agents.router, prefix="/api")

# WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = None):
    """WebSocket endpoint for real-time communication"""
    await websocket_handler(websocket, token)


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "MailAssistant API",
        "version": settings.app_version,
        "docs": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    # When running directly, use the app object
    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
        reload=False  # Disable reload when running directly
    )