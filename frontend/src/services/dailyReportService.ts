/**
 * Daily Report Service
 * 日报相关的API服务
 */

import apiClient from './apiClient';
import { DailyReport } from '../types/dailyReport';

/**
 * 获取今日日报
 */
export const getDailyReport = async (): Promise<DailyReport> => {
  const response = await apiClient.get<DailyReport>('/api/reports/daily');
  return response.data;
};

/**
 * 刷新日报（重新生成）
 */
export const refreshDailyReport = async (): Promise<DailyReport> => {
  const response = await apiClient.post<DailyReport>('/api/agents/email-processor', {
    message: '请生成今天的邮件日报'
  });
  return response.data;
};

/**
 * 标记某个分类的所有邮件为已读
 */
export const markCategoryAsRead = async (
  categoryName: string,
  emailIds: string[]
): Promise<{ success: boolean; marked: number }> => {
  // 如果没有邮件ID，直接返回成功
  if (emailIds.length === 0) {
    return { success: true, marked: 0 };
  }

  const response = await apiClient.post<{ success: boolean; marked: number }>(
    '/api/gmail/bulk-action',
    {
      action: 'mark_read',
      emailIds: emailIds
    }
  );
  return response.data;
};