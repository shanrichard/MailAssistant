/**
 * Scheduler Service
 * 定时任务调度服务
 */

import apiClient from './apiClient';

// 类型定义
export interface ScheduleSettings {
  daily_report_time: string;  // HH:mm 格式
  timezone: string;           // IANA 时区名
  auto_sync_enabled: boolean;
  next_run?: string;          // ISO 8601 格式的下次运行时间
}

export interface ScheduleUpdate {
  time: string;      // HH:mm 格式
  timezone: string;  // IANA 时区名
}

export interface TaskHistory {
  id: string;
  task_type: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  started_at: string;
  completed_at?: string;
  error_message?: string;
}

class SchedulerService {
  /**
   * 获取用户的调度设置
   */
  async getSchedule(): Promise<ScheduleSettings> {
    return apiClient.get<ScheduleSettings>('/scheduler/schedule');
  }

  /**
   * 更新用户的调度设置
   */
  async updateSchedule(update: ScheduleUpdate): Promise<ScheduleSettings> {
    // 转换为后端期望的格式
    const data = {
      daily_report_time: update.time,
      timezone: update.timezone,
      auto_sync_enabled: true  // 默认启用自动同步
    };
    
    // 使用 PUT 进行幂等更新
    return apiClient.put<ScheduleSettings>('/scheduler/schedule', data);
  }

  /**
   * 禁用定时任务
   */
  async disableSchedule(): Promise<{ message: string }> {
    return apiClient.post<{ message: string }>('/scheduler/schedule/disable');
  }

  /**
   * 手动触发日报生成
   */
  async triggerDailyReport(): Promise<{ task_id: string; message: string }> {
    return apiClient.post<{ task_id: string; message: string }>(
      '/scheduler/trigger/daily_report'
    );
  }

  /**
   * 手动触发邮件同步
   */
  async triggerEmailSync(): Promise<{ task_id: string; message: string }> {
    return apiClient.post<{ task_id: string; message: string }>(
      '/scheduler/trigger/sync_emails'
    );
  }

  /**
   * 获取任务历史记录
   */
  async getTaskHistory(
    taskType?: string,
    limit: number = 20
  ): Promise<TaskHistory[]> {
    const params = new URLSearchParams();
    if (taskType) params.append('task_type', taskType);
    params.append('limit', limit.toString());
    
    return apiClient.get<TaskHistory[]>(`/scheduler/history?${params.toString()}`);
  }

  /**
   * 获取调度器健康状态
   */
  async getSchedulerHealth(): Promise<{
    status: string;
    jobs_count: number;
    next_jobs: Array<{
      job_id: string;
      next_run_time: string;
      task_type: string;
    }>;
  }> {
    return apiClient.get('/scheduler/health');
  }

  /**
   * 格式化时间为本地时间字符串
   */
  formatLocalTime(isoTime: string): string {
    const date = new Date(isoTime);
    return date.toLocaleTimeString('zh-CN', {
      hour: '2-digit',
      minute: '2-digit',
      hour12: false
    });
  }

  /**
   * 格式化日期时间
   */
  formatDateTime(isoTime: string): string {
    const date = new Date(isoTime);
    return date.toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      hour12: false
    });
  }
}

// 导出单例实例
export const schedulerService = new SchedulerService();
export default schedulerService;