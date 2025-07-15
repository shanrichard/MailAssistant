#!/usr/bin/env python3
"""
Development server startup script for MailAssistant
"""
import os
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Load environment variables
from dotenv import load_dotenv
load_dotenv(project_root / '.env')

if __name__ == "__main__":
    import uvicorn
    
    print("🚀 Starting MailAssistant backend server in development mode...")
    print(f"📁 Project root: {project_root}")
    print(f"🔧 Environment loaded from: {project_root / '.env'}")
    print("📖 API docs available at: http://localhost:8000/docs")
    print("🏥 Health check at: http://localhost:8000/health")
    print("")
    
    # Use string import for reload to work
    uvicorn.run(
        "backend.app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
        reload_dirs=[str(project_root / "backend")]
    )