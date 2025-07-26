#!/usr/bin/env python3
"""
Development server startup script for MailAssistant
"""
import os
import sys
import subprocess
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
backend_path = project_root / "backend"
sys.path.insert(0, str(backend_path))

# Load environment variables
from dotenv import load_dotenv
load_dotenv(project_root / '.env')


if __name__ == "__main__":
    import uvicorn
    
    # Import settings to get host/port from config
    from app.core.config import settings
    
    print("🚀 Starting MailAssistant backend server in development mode...")
    print(f"📁 Project root: {project_root}")
    print(f"🔧 Environment loaded from: {project_root / '.env'}")
    print(f"📖 API docs available at: http://{settings.host}:{settings.port}/docs")
    print(f"🏥 Health check at: http://{settings.host}:{settings.port}/health")
    print("")
    
    # Use string import for reload to work
    # 直接使用 app（Socket.IO 已移除）
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
        log_level="info",
        reload_dirs=[str(backend_path)]
    )