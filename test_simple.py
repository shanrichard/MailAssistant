#!/usr/bin/env python3
"""
简单的FastAPI测试应用
"""
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"status": "ok", "message": "Simple FastAPI test"}

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "test"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8002)