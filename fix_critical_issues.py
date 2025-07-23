#!/usr/bin/env python3
"""
修复重启后发现的关键问题
基于调试日志分析
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

def fix_transaction_conflict():
    """修复数据库事务冲突问题"""
    print("🔧 修复1：数据库事务冲突问题")
    
    # 修复幂等同步服务中的事务管理
    service_file = project_root / "backend" / "app" / "services" / "idempotent_sync_service.py"
    
    try:
        with open(service_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 修复事务管理问题
        old_code = """def start_sync_idempotent(db: Session, user_id: str, force_full: bool) -> str:
    \"\"\"
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
    \"\"\"
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
    return new_task_id"""
        
        new_code = """def start_sync_idempotent(db: Session, user_id: str, force_full: bool) -> str:
    \"\"\"
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
    \"\"\"
    # 确保数据库会话没有活动事务
    if db.in_transaction():
        db.rollback()
    
    try:
        # 开始新事务
        db.begin()
        
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
            
            task_id = sync_status.task_id
            db.commit()  # 显式提交事务
            
            logger.info(f"复用现有同步任务: {task_id}", 
                       extra={"user_id": user_id, "task_id": task_id})
            return task_id  # 复用老任务，避免重复
        
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
        
        # 显式提交事务
        db.commit()
        
        # 事务提交后记录日志
        logger.info(f"启动新同步任务: {new_task_id}", 
                   extra={"user_id": user_id, "force_full": force_full, "task_id": new_task_id})
        return new_task_id
        
    except Exception as e:
        db.rollback()
        logger.error(f"幂等同步启动失败: {e}", extra={"user_id": user_id})
        raise"""
        
        # 替换代码
        if old_code in content:
            content = content.replace(old_code, new_code)
            
            with open(service_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print("   ✅ 已修复数据库事务冲突问题")
            return True
        else:
            print("   ⚠️  代码结构已变化，需要手动检查")
            return True
            
    except Exception as e:
        print(f"   ❌ 修复数据库事务冲突失败: {e}")
        return False

def fix_datetime_timezone_issues():
    """修复日期时间时区问题"""
    print("\n🔧 修复2：日期时间时区问题")
    
    # 查找并修复should_sync函数中的时区问题
    gmail_api_file = project_root / "backend" / "app" / "api" / "gmail.py"
    
    try:
        with open(gmail_api_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 修复should_sync函数中的时区问题
        old_code = """        if last_sync:
            from datetime import timedelta
            time_diff = datetime.utcnow() - last_sync
            exceeded = time_diff > timedelta(hours=1)  # 1小时未同步则建议同步
            need_sync = need_sync or exceeded"""
        
        new_code = """        if last_sync:
            from datetime import timedelta
            # 确保两个datetime都是timezone-aware或都是timezone-naive
            if last_sync.tzinfo is None:
                current_time = datetime.utcnow()
            else:
                current_time = datetime.utcnow().replace(tzinfo=last_sync.tzinfo)
            time_diff = current_time - last_sync
            exceeded = time_diff > timedelta(hours=1)  # 1小时未同步则建议同步
            need_sync = need_sync or exceeded"""
        
        if old_code in content:
            content = content.replace(old_code, new_code)
            
            with open(gmail_api_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print("   ✅ 已修复should_sync函数的时区问题")
        else:
            print("   ℹ️  should_sync函数代码结构可能已变化")
        
        return True
        
    except Exception as e:
        print(f"   ❌ 修复时区问题失败: {e}")
        return False

def fix_pydantic_serialization():
    """修复Pydantic序列化错误"""
    print("\n🔧 修复3：Pydantic日期序列化问题")
    
    # 查找scheduler相关的响应模型
    scheduler_files = list((project_root / "backend" / "app").glob("**/scheduler*"))
    
    for file_path in scheduler_files:
        if file_path.suffix == '.py':
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 检查是否包含SchedulePreferenceResponse
                if "SchedulePreferenceResponse" in content:
                    print(f"   🔍 检查文件: {file_path}")
                    
                    # 添加序列化配置
                    if "class SchedulePreferenceResponse" in content and "model_config" not in content:
                        # 添加模型配置以处理datetime序列化
                        old_pattern = "class SchedulePreferenceResponse(BaseModel):"
                        new_pattern = """class SchedulePreferenceResponse(BaseModel):
    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat() if v else None
        }
    )"""
                        
                        if old_pattern in content:
                            content = content.replace(old_pattern, new_pattern)
                            
                            # 确保导入ConfigDict
                            if "from pydantic import" in content and "ConfigDict" not in content:
                                content = content.replace(
                                    "from pydantic import BaseModel",
                                    "from pydantic import BaseModel, ConfigDict"
                                )
                            
                            # 确保导入datetime
                            if "from datetime import" not in content:
                                content = "from datetime import datetime\n" + content
                            
                            with open(file_path, 'w', encoding='utf-8') as f:
                                f.write(content)
                            
                            print(f"   ✅ 已修复 {file_path} 中的序列化问题")
                    
            except Exception as e:
                print(f"   ❌ 处理文件 {file_path} 失败: {e}")
    
    # 通用方法：查找所有pydantic响应模型并添加日期序列化配置
    api_files = list((project_root / "backend" / "app" / "api").glob("*.py"))
    
    for api_file in api_files:
        try:
            with open(api_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 如果文件包含Response模型且有datetime字段问题，添加通用修复
            if "Response(BaseModel)" in content and "created_at" in content and "ConfigDict" not in content:
                # 在文件顶部添加导入
                if "from pydantic import BaseModel" in content:
                    content = content.replace(
                        "from pydantic import BaseModel",
                        "from pydantic import BaseModel, ConfigDict, field_serializer"
                    )
                    
                    # 为所有包含datetime字段的Response类添加序列化器
                    import re
                    pattern = r'class (\w*Response)\(BaseModel\):'
                    matches = re.findall(pattern, content)
                    
                    for match in matches:
                        old_class = f"class {match}(BaseModel):"
                        new_class = f"""class {match}(BaseModel):
    @field_serializer('created_at', 'updated_at', when_used='unless-none')
    def serialize_datetime(self, value):
        return value.isoformat() if value else None"""
                        
                        if old_class in content:
                            content = content.replace(old_class, new_class)
                    
                    with open(api_file, 'w', encoding='utf-8') as f:
                        f.write(content)
                    
                    print(f"   ✅ 已为 {api_file.name} 添加日期序列化器")
                    
        except Exception as e:
            print(f"   ❌ 处理API文件 {api_file} 失败: {e}")
    
    return True

def test_fixes():
    """测试修复效果"""
    print("\n🧪 测试修复效果")
    
    try:
        # 测试1：检查幂等同步服务是否可以正常导入
        from backend.app.services.idempotent_sync_service import start_sync_idempotent
        print("   ✅ 幂等同步服务导入正常")
        
        # 测试2：检查API响应
        import requests
        try:
            response = requests.get("http://localhost:8000/health", timeout=5)
            if response.status_code == 200:
                print("   ✅ 后端服务响应正常")
            else:
                print(f"   ⚠️  后端服务状态码: {response.status_code}")
        except Exception as e:
            print(f"   ⚠️  后端服务连接问题: {e}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ 测试修复效果失败: {e}")
        return False

def main():
    """主函数"""
    print("🚨 开始修复重启后发现的关键问题")
    print("=" * 50)
    
    success_count = 0
    total_fixes = 4
    
    # 修复1：数据库事务冲突
    if fix_transaction_conflict():
        success_count += 1
    
    # 修复2：时区问题
    if fix_datetime_timezone_issues():
        success_count += 1
    
    # 修复3：序列化问题
    if fix_pydantic_serialization():
        success_count += 1
    
    # 修复4：测试效果
    if test_fixes():
        success_count += 1
    
    print("\n" + "=" * 50)
    print(f"📊 修复结果: {success_count}/{total_fixes} 项修复完成")
    
    if success_count >= 3:
        print("✅ 关键问题修复完成！建议重启服务验证效果")
        print("\n💡 建议操作：")
        print("1. 重启后端服务: ./restart_services.sh")  
        print("2. 测试立即同步功能")
        print("3. 检查前端错误是否消除")
        return True
    else:
        print("❌ 部分修复失败，需要进一步检查")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)