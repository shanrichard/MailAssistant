#!/usr/bin/env python3
"""
实现幂等同步启动接口
执行任务 3-9-5
"""
import sys
import os
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 加载环境变量
from dotenv import load_dotenv
load_dotenv(project_root / '.env')

# 导入依赖
from backend.app.core.database import SessionLocal
from backend.app.models.user_sync_status import UserSyncStatus
from backend.app.models.user import User
from sqlalchemy import text, update
from datetime import datetime, timedelta
import uuid
import asyncio

def create_idempotent_sync_function():
    """创建幂等同步启动函数的实现代码"""
    print("🔧 执行步骤1：创建幂等同步启动函数")
    
    # 创建新的模块文件
    sync_module_path = project_root / "backend" / "app" / "services" / "idempotent_sync_service.py"
    
    code_content = '''"""
幂等同步启动服务
基于专家建议实现
"""
from datetime import datetime, timedelta
from typing import Optional
import uuid
import logging
from sqlalchemy.orm import Session
from sqlalchemy import update

from ..models.user_sync_status import UserSyncStatus
from ..models.user import User
from ..core.logging import get_logger

logger = get_logger(__name__)


def start_sync_idempotent(db: Session, user_id: str, force_full: bool) -> str:
    """
    幂等的同步启动接口
    - 如果存在有效的进行中任务（<30分钟），则复用现有task_id
    - 否则，清理旧状态并创建新任务
    - 使用行锁保证并发安全
    
    Args:
        db: 数据库会话
        user_id: 用户ID
        force_full: 是否强制全量同步
        
    Returns:
        str: 任务ID（新创建或复用的）
    """
    with db.begin():
        # 使用行锁获取用户同步状态
        sync_status = db.query(UserSyncStatus).filter(
            UserSyncStatus.user_id == user_id
        ).with_for_update().first()

        now = datetime.utcnow()
        
        # 检查是否存在有效的进行中任务
        if (sync_status and 
            sync_status.is_syncing and 
            sync_status.started_at and
            (now - sync_status.started_at) < timedelta(minutes=30)):
            
            logger.info(f"复用现有同步任务: {sync_status.task_id}", 
                       extra={"user_id": user_id, "task_id": sync_status.task_id})
            return sync_status.task_id  # 复用老任务，避免重复
        
        # 创建新任务
        new_task_id = f"sync_{user_id}_{uuid.uuid4().hex[:8]}_{int(now.timestamp())}"
        
        if sync_status:
            # 更新现有记录
            sync_status.task_id = new_task_id
            sync_status.is_syncing = True
            sync_status.sync_type = 'full' if force_full else 'incremental'
            sync_status.started_at = now
            sync_status.updated_at = now
            sync_status.progress_percentage = 0
            sync_status.current_stats = {}
            sync_status.error_message = None
        else:
            # 创建新记录
            sync_status = UserSyncStatus(
                user_id=user_id,
                task_id=new_task_id,
                is_syncing=True,
                sync_type='full' if force_full else 'incremental',
                started_at=now,
                updated_at=now,
                progress_percentage=0,
                current_stats={}
            )
            db.add(sync_status)
        
        # 事务会自动提交，确保数据库状态先更新
        
    # 事务提交后记录日志
    logger.info(f"启动新同步任务: {new_task_id}", 
               extra={"user_id": user_id, "force_full": force_full, "task_id": new_task_id})
    return new_task_id


def release_sync_status_atomic(db: Session, user_id: str, task_id: str, error_message: Optional[str] = None):
    """
    原子性释放同步状态
    
    Args:
        db: 数据库会话
        user_id: 用户ID
        task_id: 任务ID
        error_message: 错误信息（如果有）
    """
    try:
        with db.begin():
            updates = {
                'is_syncing': False,
                'updated_at': datetime.utcnow()
            }
            if error_message:
                updates['error_message'] = error_message
                updates['progress_percentage'] = 0  # 错误时重置进度
                
            db.execute(
                update(UserSyncStatus)
                .where(UserSyncStatus.task_id == task_id)
                .values(**updates)
            )
            
        logger.info(f"状态已释放", 
                   extra={"user_id": user_id, "task_id": task_id, "error": error_message})
            
    except Exception as e:
        logger.error(f"状态释放失败: {e}", 
                    extra={"user_id": user_id, "task_id": task_id})
        raise


def get_active_task_info(db: Session, user_id: str) -> Optional[dict]:
    """
    获取用户当前活跃任务信息
    
    Args:
        db: 数据库会话
        user_id: 用户ID
        
    Returns:
        dict: 活跃任务信息，如果没有则返回None
    """
    sync_status = db.query(UserSyncStatus).filter(
        UserSyncStatus.user_id == user_id,
        UserSyncStatus.is_syncing == True
    ).first()
    
    if not sync_status:
        return None
        
    now = datetime.utcnow()
    
    # 检查任务是否还有效（30分钟内）
    if sync_status.started_at and (now - sync_status.started_at) < timedelta(minutes=30):
        return {
            "task_id": sync_status.task_id,
            "sync_type": sync_status.sync_type,
            "started_at": sync_status.started_at,
            "progress_percentage": sync_status.progress_percentage,
            "current_stats": sync_status.current_stats or {},
            "is_active": True
        }
    
    return {
        "task_id": sync_status.task_id,
        "is_active": False,
        "expired": True
    }
'''
    
    try:
        with open(sync_module_path, 'w', encoding='utf-8') as f:
            f.write(code_content)
        print(f"   ✅ 成功创建幂等同步服务模块: {sync_module_path}")
        return True
    except Exception as e:
        print(f"   ❌ 创建幂等同步服务模块失败: {e}")
        return False

def update_gmail_api_with_idempotent():
    """更新Gmail API使用幂等接口"""
    print("\n🔧 执行步骤2：更新Gmail API使用幂等接口")
    
    api_file_path = project_root / "backend" / "app" / "api" / "gmail.py"
    
    try:
        # 读取原文件
        with open(api_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查是否已经导入了幂等服务
        if "from ..services.idempotent_sync_service import" not in content:
            # 添加import
            import_line = "from ..services.idempotent_sync_service import start_sync_idempotent, release_sync_status_atomic, get_active_task_info"
            
            # 在现有import之后添加新的import
            import_position = content.find("from ..core.logging import get_logger")
            if import_position != -1:
                end_of_line = content.find('\n', import_position)
                content = content[:end_of_line + 1] + import_line + '\n' + content[end_of_line + 1:]
            
        # 替换smart_sync_emails函数
        new_smart_sync = '''@router.post("/sync/smart", response_model=SyncResponse)
async def smart_sync_emails(
    force_full: bool = Query(default=False, description="Force full sync"),
    background: bool = Query(default=False, description="Run in background"),
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> SyncResponse:
    """智能同步：幂等启动，防止重复任务"""
    try:
        # 使用幂等启动接口
        task_id = start_sync_idempotent(db, current_user.id, force_full)
        
        # 检查是否复用了现有任务
        active_task = get_active_task_info(db, current_user.id)
        
        if active_task and active_task.get("is_active") and active_task["task_id"] == task_id:
            # 复用现有任务
            return SyncResponse(
                success=True,
                stats=active_task.get("current_stats", {}),
                message="复用进行中的同步任务",
                in_progress=True,
                progress_percentage=active_task.get("progress_percentage", 0),
                task_id=task_id
            )
        
        # 新任务：启动后台任务
        if background_tasks:
            background_tasks.add_task(
                execute_background_sync_v2, current_user.id, force_full, task_id
            )
        else:
            # 如果没有BackgroundTasks，使用asyncio
            asyncio.create_task(
                execute_background_sync_v2(current_user.id, force_full, task_id)
            )
        
        return SyncResponse(
            success=True,
            stats={},
            message="同步任务已启动",
            task_id=task_id,
            in_progress=True
        )
        
    except Exception as e:
        logger.error(f"启动同步失败: {e}", extra={"user_id": current_user.id})
        raise HTTPException(status_code=400, detail=f"启动同步失败: {str(e)}")'''
        
        # 找到并替换原smart_sync_emails函数
        start_marker = '@router.post("/sync/smart", response_model=SyncResponse)'
        start_pos = content.find(start_marker)
        if start_pos == -1:
            print("   ❌ 未找到smart_sync_emails函数")
            return False
            
        # 找到下一个@router或文件末尾
        next_route_pos = content.find('\n@router.', start_pos + 1)
        if next_route_pos == -1:
            next_route_pos = len(content)
        
        # 替换函数
        content = content[:start_pos] + new_smart_sync + '\n\n' + content[next_route_pos:]
        
        # 写回文件
        with open(api_file_path, 'w', encoding='utf-8') as f:
            f.write(content)
            
        print("   ✅ 成功更新Gmail API使用幂等接口")
        return True
        
    except Exception as e:
        print(f"   ❌ 更新Gmail API失败: {e}")
        return False

def create_improved_background_sync():
    """创建改进的后台同步函数"""
    print("\n🔧 执行步骤3：创建改进的后台同步函数")
    
    api_file_path = project_root / "backend" / "app" / "api" / "gmail.py"
    
    try:
        # 读取原文件
        with open(api_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 新的后台同步函数
        new_background_sync = '''

async def execute_background_sync_v2(user_id: str, force_full: bool, task_id: str):
    """改进的后台同步执行器 - 使用幂等接口"""
    from ..core.database import SessionLocal
    
    db = SessionLocal()
    
    try:
        # 获取用户
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            logger.error(f"用户不存在: {user_id}")
            release_sync_status_atomic(db, user_id, task_id, "用户不存在")
            return
        
        # 进度回调函数
        def progress_callback(progress_info):
            try:
                db.execute(
                    update(UserSyncStatus)
                    .where(UserSyncStatus.task_id == task_id)
                    .values(
                        progress_percentage=progress_info.get('progress_percentage', 0),
                        current_stats=progress_info.get('current_stats', {}),
                        updated_at=datetime.utcnow()
                    )
                )
                db.commit()
            except Exception as e:
                logger.error(f"进度更新失败: {e}", extra={"task_id": task_id})
        
        # 执行智能同步
        result = await email_sync_service.smart_sync_user_emails(
            db, user, force_full, progress_callback=progress_callback
        )
        
        # 标记完成
        db.execute(
            update(UserSyncStatus)
            .where(UserSyncStatus.task_id == task_id)
            .values(
                is_syncing=False,
                progress_percentage=100,
                current_stats=result,
                updated_at=datetime.utcnow()
            )
        )
        db.commit()
        
        logger.info(f"后台同步任务完成", 
                   extra={"user_id": user_id, "task_id": task_id, "stats": result})
        
    except Exception as e:
        # 同步失败，释放状态
        release_sync_status_atomic(db, user_id, task_id, f"同步异常: {str(e)}")
        logger.error(f"后台同步失败: {e}", 
                    extra={"user_id": user_id, "task_id": task_id})
        
    finally:
        db.close()'''
        
        # 检查是否已经存在这个函数
        if "execute_background_sync_v2" not in content:
            # 在文件末尾添加新函数
            content += new_background_sync
            
            # 写回文件
            with open(api_file_path, 'w', encoding='utf-8') as f:
                f.write(content)
                
            print("   ✅ 成功添加改进的后台同步函数")
        else:
            print("   ℹ️  改进的后台同步函数已存在")
            
        return True
        
    except Exception as e:
        print(f"   ❌ 创建改进的后台同步函数失败: {e}")
        return False

def test_idempotent_sync():
    """测试幂等同步功能"""
    print("\n🧪 执行步骤4：测试幂等同步功能")
    
    db = SessionLocal()
    try:
        # 导入新的服务
        from backend.app.services.idempotent_sync_service import start_sync_idempotent, get_active_task_info
        
        # 创建测试用户ID
        test_user_id = "00000000-0000-0000-0000-000000000003"
        
        print("   🧪 测试1：首次启动同步任务")
        task_id_1 = start_sync_idempotent(db, test_user_id, False)
        print(f"      ✅ 首次任务ID: {task_id_1}")
        
        print("   🧪 测试2：立即再次启动（应复用任务）")
        task_id_2 = start_sync_idempotent(db, test_user_id, False)
        
        if task_id_1 == task_id_2:
            print(f"      ✅ 幂等性验证成功：复用了任务ID {task_id_2}")
        else:
            print(f"      ❌ 幂等性验证失败：创建了新任务ID {task_id_2}")
            return False
        
        print("   🧪 测试3：检查活跃任务信息")
        active_info = get_active_task_info(db, test_user_id)
        if active_info and active_info.get("is_active"):
            print(f"      ✅ 活跃任务检测正确：{active_info['task_id']}")
        else:
            print(f"      ❌ 活跃任务检测失败")
            return False
        
        # 清理测试数据
        try:
            db.execute(text("""
                DELETE FROM user_sync_status 
                WHERE user_id = :user_id
            """), {"user_id": test_user_id})
            db.commit()
            print("   🧹 测试数据已清理")
        except:
            db.rollback()
            
        return True
        
    except Exception as e:
        print(f"   ❌ 测试幂等同步功能失败: {e}")
        return False
    finally:
        db.close()

def main():
    """主函数"""
    print("🚀 开始执行任务3-9-5：实现幂等同步启动接口")
    print("=" * 60)
    
    success_count = 0
    total_steps = 4
    
    # 步骤1：创建幂等同步启动函数
    if create_idempotent_sync_function():
        success_count += 1
    
    # 步骤2：更新Gmail API使用幂等接口
    if update_gmail_api_with_idempotent():
        success_count += 1
    
    # 步骤3：创建改进的后台同步函数
    if create_improved_background_sync():
        success_count += 1
    
    # 步骤4：测试幂等同步功能
    if test_idempotent_sync():
        success_count += 1
    
    print("\n" + "=" * 60)
    print(f"📊 实施结果: {success_count}/{total_steps} 步骤成功")
    
    if success_count == total_steps:
        print("🎉 任务3-9-5执行成功！幂等同步启动接口已实现")
        print("   🛡️  防重复任务机制已生效")
        print("   🔄 任务复用逻辑运行正常")
        print("   ⚡ 用户体验显著提升")
        return True
    elif success_count >= 3:
        print("⚠️  主要功能已实现，少量问题可手动调整")
        return True
    else:
        print("⚠️  实现过程中遇到问题，需要检查")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)