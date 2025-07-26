#!/usr/bin/env python3
"""
最简单的FastAPI应用用于测试Railway部署
"""
from fastapi import FastAPI

app = FastAPI(title="MailAssistant Test")

@app.get("/")
def root():
    return {"message": "MailAssistant Test Deploy Success!"}

@app.get("/health")
def health():
    return {"status": "healthy", "app": "MailAssistant Test"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)