"""
最简单的FastAPI应用，仅用于测试部署
"""
from fastapi import FastAPI

app = FastAPI(title="MailAssistant Minimal Test")

@app.get("/")
def root():
    return {"message": "Minimal FastAPI working!", "status": "success"}

@app.get("/health")
def health():
    return {"status": "healthy", "mode": "minimal"}

@app.get("/api/test")
def api_test():
    return {"message": "API route working!", "status": "success"}

if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)