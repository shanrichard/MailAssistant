"""调试日志 API - 仅在开发环境可用"""
from fastapi import APIRouter, Query, Request, HTTPException
from typing import Optional, List, Dict
from datetime import datetime
import json
import os
from pathlib import Path

from app.core.config import settings
from app.core.logging import log_frontend_error

router = APIRouter(prefix="/api/debug/logs", tags=["debug"])


def check_dev_environment():
    """检查是否为开发环境"""
    if settings.environment != "development":
        raise HTTPException(
            status_code=403, 
            detail="This endpoint is only available in development environment"
        )


@router.post("/all")
async def get_all_logs(request: Request):
    """
    获取前后端所有错误日志
    前端需要在请求体中传入 localStorage 的错误数据
    """
    check_dev_environment()
    
    # 获取前端传来的错误
    body = await request.json()
    frontend_errors = body.get("frontend_errors", [])
    
    # 将前端错误写入日志文件
    user_agent = request.headers.get("User-Agent")
    for error in frontend_errors:
        log_frontend_error(error, user_agent)
    
    # 获取所有错误（包括刚写入的）
    all_errors = await get_all_errors_from_log_file(limit=200)
    
    # 分别统计前后端错误数量
    frontend_count = sum(1 for e in all_errors if e.get("source") == "frontend")
    backend_count = sum(1 for e in all_errors if e.get("source") == "backend")
    
    return {
        "errors": all_errors,
        "frontend_count": frontend_count,
        "backend_count": backend_count,
        "total_count": len(all_errors)
    }


@router.get("/backend")
async def get_backend_logs(
    limit: int = Query(100, le=500),
    level: Optional[str] = Query(None, description="error/warning/info")
):
    """仅获取后端日志"""
    check_dev_environment()
    
    errors = await get_backend_errors(limit=limit, level=level)
    return {
        "errors": errors,
        "count": len(errors)
    }


@router.get("/search")
async def search_logs(
    source: Optional[str] = Query(None, description="frontend|backend - 错误来源"),
    level: Optional[str] = Query(None, description="error|warning|info - 日志级别"),
    keyword: Optional[str] = Query(None, description="搜索关键词"),
    limit: int = Query(100, le=1000, description="返回条数限制"),
):
    """高级日志搜索功能"""
    check_dev_environment()
    
    errors = await get_all_errors_from_log_file(
        limit=limit,
        source=source,
        level=level,
        keyword=keyword
    )
    
    return {
        "errors": errors,
        "count": len(errors),
        "query": {
            "source": source,
            "level": level,
            "keyword": keyword,
            "limit": limit
        }
    }


async def get_all_errors_from_log_file(
    limit: int = 200,
    source: Optional[str] = None,
    level: Optional[str] = None,
    keyword: Optional[str] = None
) -> List[Dict]:
    """从日志文件读取所有错误（包括前端和后端）"""
    errors = []
    
    # 日志文件路径
    log_file_path = "logs/app.log"
    
    if not os.path.exists(log_file_path):
        # 如果找不到日志文件，返回一个提示
        return [{
            "source": "backend",
            "timestamp": datetime.now().isoformat(),
            "type": "info",
            "message": "No log file found. Starting fresh logs.",
            "level": "info"
        }]
    
    try:
        with open(log_file_path, 'r', encoding='utf-8') as f:
            # 读取文件的最后部分（避免读取整个大文件）
            f.seek(0, 2)  # 移到文件末尾
            file_size = f.tell()
            
            # 读取最后 500KB 的内容
            read_size = min(file_size, 500 * 1024)
            f.seek(max(0, file_size - read_size))
            content = f.read()
            lines = content.splitlines()
            
        # 从后往前处理日志行
        for line in reversed(lines):
            if not line.strip():
                continue
                
            try:
                # 尝试解析为 JSON 格式的日志
                log_entry = json.loads(line)
                
                # 过滤来源
                entry_source = log_entry.get("source", "backend")
                if source and entry_source != source:
                    continue
                
                # 过滤级别
                log_level = log_entry.get("levelname", "").lower()
                if level and log_level != level.lower():
                    continue
                
                # 关键词搜索
                if keyword and keyword.lower() not in str(log_entry).lower():
                    continue
                
                # 构造统一的错误格式
                error_item = {
                    "source": entry_source,
                    "timestamp": log_entry.get("timestamp"),
                    "type": log_entry.get("error_type", "backend_log"),
                    "message": log_entry.get("message"),
                    "level": log_level,
                    "stack": log_entry.get("stack"),
                    "url": log_entry.get("url"),
                    "user_agent": log_entry.get("user_agent"),
                    "name": log_entry.get("name")
                }
                
                # 移除 None 值
                error_item = {k: v for k, v in error_item.items() if v is not None}
                
                errors.append(error_item)
                
                if len(errors) >= limit:
                    break
                    
            except json.JSONDecodeError:
                # 忽略非 JSON 格式的日志行
                continue
                
    except Exception as e:
        return [{
            "source": "backend",
            "timestamp": datetime.now().isoformat(),
            "type": "error",
            "message": f"Failed to read log file: {str(e)}",
            "level": "error"
        }]
    
    return errors[:limit]


async def get_backend_errors(limit: int = 100, level: Optional[str] = None) -> List[Dict]:
    """从日志文件读取后端错误（保留用于向后兼容）"""
    return await get_all_errors_from_log_file(
        limit=limit,
        source="backend",
        level=level
    )