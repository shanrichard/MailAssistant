"""
Task scheduler management API routes
"""
from typing import List, Optional
from datetime import time, datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, ConfigDict

from ..core.database import get_db
from .auth import get_current_user
from ..models.user import User
from ..models.task_log import TaskType
from ..services.task_service import task_service

router = APIRouter(prefix="/scheduler", tags=["Task Scheduler"])

# Pydantic models
class SchedulePreferenceRequest(BaseModel):
    daily_report_time: str = Field(..., description="时间格式: HH:MM", example="09:00")
    timezone: str = Field(default="Asia/Shanghai", description="时区", example="Asia/Shanghai")
    auto_sync_enabled: bool = Field(default=True, description="是否启用自动同步")

class SchedulePreferenceResponse(BaseModel):
    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat() if v else None
        }
    )
    daily_report_time: str
    timezone: str
    auto_sync_enabled: bool
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

class TaskHistoryResponse(BaseModel):
    id: str
    task_type: str
    task_name: str
    status: str
    progress_percentage: int
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    execution_time_ms: Optional[int] = None
    error_message: Optional[str] = None
    retry_count: int
    emails_processed: int
    created_at: str

class TaskDetailsResponse(BaseModel):
    id: str
    user_id: Optional[str] = None
    task_type: str
    task_name: str
    task_description: Optional[str] = None
    status: str
    progress_percentage: int
    input_parameters: Optional[dict] = None
    output_results: Optional[dict] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    execution_time_ms: Optional[int] = None
    error_message: Optional[str] = None
    retry_count: int
    emails_processed: int
    created_at: str

class SchedulerStatusResponse(BaseModel):
    scheduler: dict
    active_jobs: List[dict]
    timestamp: str

class TriggerTaskResponse(BaseModel):
    task_id: Optional[str] = None
    message: str
    success: bool

@router.get("/health", response_model=SchedulerStatusResponse)
async def get_scheduler_status():
    """获取调度器健康状态"""
    try:
        status = task_service.get_scheduler_status()
        return SchedulerStatusResponse(**status)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get scheduler status: {str(e)}"
        )

@router.get("/schedule", response_model=Optional[SchedulePreferenceResponse])
async def get_user_schedule(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取用户的调度偏好设置"""
    schedule = task_service.get_user_schedule(db, str(current_user.id))
    
    if not schedule:
        return None
    
    return SchedulePreferenceResponse(**schedule)

@router.post("/schedule", response_model=dict)
async def update_user_schedule(
    request: SchedulePreferenceRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新用户的调度偏好设置"""
    try:
        # 解析时间
        time_parts = request.daily_report_time.split(":")
        if len(time_parts) != 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid time format. Use HH:MM"
            )
        
        daily_time = time(int(time_parts[0]), int(time_parts[1]))
        
        # 更新调度设置
        success = await task_service.update_user_schedule(
            db, 
            str(current_user.id), 
            daily_time, 
            request.timezone
        )
        
        if success:
            return {"message": "Schedule updated successfully", "success": True}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update schedule"
            )
            
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid time format: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update schedule: {str(e)}"
        )

@router.post("/schedule/disable", response_model=dict)
async def disable_user_schedule(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """禁用用户的定时任务"""
    try:
        success = await task_service.disable_user_schedule(db, str(current_user.id))
        
        if success:
            return {"message": "Schedule disabled successfully", "success": True}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to disable schedule"
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to disable schedule: {str(e)}"
        )

@router.post("/trigger/{task_type}", response_model=TriggerTaskResponse)
async def trigger_task(
    task_type: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """手动触发任务"""
    try:
        # 验证任务类型
        if task_type not in [e.value for e in TaskType]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid task type: {task_type}"
            )
        
        task_type_enum = TaskType(task_type)
        
        # 触发任务
        task_id = await task_service.trigger_user_task(db, str(current_user.id), task_type_enum)
        
        if task_id:
            return TriggerTaskResponse(
                task_id=task_id,
                message=f"Task {task_type} triggered successfully",
                success=True
            )
        else:
            return TriggerTaskResponse(
                task_id=None,
                message=f"Failed to trigger task {task_type}",
                success=False
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger task: {str(e)}"
        )

@router.get("/history", response_model=List[TaskHistoryResponse])
async def get_task_history(
    limit: int = 50,
    task_type: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取用户任务历史"""
    try:
        task_type_filter = None
        if task_type:
            if task_type not in [e.value for e in TaskType]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid task type: {task_type}"
                )
            task_type_filter = TaskType(task_type)
        
        history = task_service.get_user_task_history(
            db, 
            str(current_user.id), 
            limit, 
            task_type_filter
        )
        
        return [TaskHistoryResponse(**task) for task in history]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get task history: {str(e)}"
        )

@router.get("/task/{task_id}", response_model=TaskDetailsResponse)
async def get_task_details(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取任务详细信息"""
    try:
        task_details = task_service.get_task_details(db, task_id)
        
        if not task_details:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )
        
        # 检查任务是否属于当前用户
        if task_details.get("user_id") != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this task"
            )
        
        return TaskDetailsResponse(**task_details)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get task details: {str(e)}"
        )

@router.get("/jobs", response_model=List[dict])
async def get_active_jobs(current_user: User = Depends(get_current_user)):
    """获取活跃的调度任务"""
    try:
        status_info = task_service.get_scheduler_status()
        return status_info.get("active_jobs", [])
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get active jobs: {str(e)}"
        )


@router.get("/status", response_model=dict)
async def get_scheduler_status():
    """获取调度器状态和任务列表（包括僵死任务清理）"""
    try:
        from ..scheduler.scheduler_app import get_scheduler_status, get_active_jobs
        
        scheduler_status = get_scheduler_status()
        active_jobs = get_active_jobs()
        
        # 查找僵死任务清理job
        zombie_cleanup_job = next(
            (job for job in active_jobs if job["id"] == "zombie_task_cleanup"),
            None
        )
        
        return {
            "scheduler": scheduler_status,
            "jobs": active_jobs,
            "zombie_cleanup_job": zombie_cleanup_job,
            "jobs_summary": {
                "total": len(active_jobs),
                "has_zombie_cleanup": zombie_cleanup_job is not None
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get scheduler status: {str(e)}"
        )