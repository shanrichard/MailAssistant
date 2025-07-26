# Design: Settings页面日报定时刷新机制研究

## Requirements

通过对项目代码的深入分析，发现Settings页面的日报定时刷新设置机制存在以下问题：

### 当前状态分析

1. **前端设置页面状态**：
   - Settings页面(/frontend/src/pages/Settings.tsx)中确实存在日报时间设置UI
   - 但调度器相关功能已被完全注释掉（第42-46行和第65-69行）
   - 前端仍引用schedulerService，但实际功能被禁用

2. **前端服务层状态**：
   - schedulerService.ts文件完整存在，包含完整的API调用方法
   - 提供获取/更新调度设置、触发任务、查看历史等功能
   - 但由于Settings页面代码被注释，实际无法使用

3. **后端API状态**：
   - scheduler.py API路由文件完整存在
   - 提供完整的RESTful API端点：GET/POST /api/scheduler/schedule等
   - 但存在严重问题：引用已删除的scheduler模块

4. **后端核心调度机制状态**：
   - task_service.py中仍有调度相关代码，但引用已删除的scheduler模块
   - /backend/app/scheduler/目录已完全删除（根据git状态D标记确认）
   - 缺失关键文件：scheduler_app.py, jobs.py, __init__.py

5. **main.py集成状态**：
   - main.py中没有包含scheduler路由
   - 没有启动任何定时任务调度器
   - 缺少scheduler相关的生命周期管理

6. **现有定时机制状态**：
   - ✅ cleanup_tasks.py清理任务**正常工作**（每小时运行，清理过期日报、超时任务、孤立状态）
   - ❌ scheduled_cleanup.py**完全失效**，因为引用已删除的heartbeat_sync_service.py，无法导入

### 问题总结

**定时日报生成机制完全失效**，具体表现为：

1. **UI层面**：设置功能被注释，用户无法进行配置
2. **API层面**：后端API存在但会因导入错误而崩溃
3. **调度层面**：核心调度器代码被删除，无法执行定时任务
4. **集成层面**：main.py中没有启动调度器，系统启动时不会初始化定时功能
5. **数据层面**：数据库可能还有相关表结构，但缺乏对应的业务逻辑

### 影响范围

1. 用户无法设置日报生成时间
2. 系统不会自动生成日报
3. 相关API调用会导致500错误
4. 日报功能完全依赖手动触发

### 清理计划

根据用户要求彻底移除定时日报功能，需要清理的代码和文件：

#### 需要删除的文件：
1. `backend/app/services/scheduled_cleanup.py` - 失效的僵死任务清理
2. `frontend/src/services/schedulerService.ts` - 前端调度服务
3. `backend/app/api/scheduler.py` - 后端调度API
4. `frontend/src/pages/__tests__/Settings.test.tsx` - 调度相关测试

#### 需要清理的代码：
1. **Settings.tsx** - 移除日报时间设置UI和schedulerService导入
2. **task_service.py** - 移除所有scheduler相关方法和导入
3. **User模型** - 考虑是否保留daily_report_time和timezone字段（可能其他功能在用）

#### 清理后的好处：
- 移除失效的代码，减少维护负担
- 避免用户困惑（看到无效的设置选项）
- 简化代码库，专注于实际工作的功能
- 消除导入错误和潜在的运行时错误