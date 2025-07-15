#!/usr/bin/env python3
"""
Server startup script for MailAssistant backend
"""
import os
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables
from dotenv import load_dotenv
load_dotenv(project_root / '.env')

# Import and run the app
if __name__ == "__main__":
    import uvicorn
    from backend.app.main import app
    
    print("🚀 Starting MailAssistant backend server...")
    print(f"📁 Project root: {project_root}")
    print(f"🔧 Environment loaded from: {project_root / '.env'}")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )