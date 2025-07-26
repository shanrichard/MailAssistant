/**
 * Daily Report Service
 * 日报相关的API服务
 */

import apiClient from './apiClient';
import { DailyReportResponse } from '../types/dailyReport';

/**
 * 获取今日日报
 */
export const getDailyReport = async (): Promise<DailyReportResponse> => {
  const response = await apiClient.get<DailyReportResponse>('/api/reports/daily');
  return response;
};

/**
 * 刷新日报（重新生成）
 */
export const refreshDailyReport = async (): Promise<DailyReportResponse> => {
  const response = await apiClient.post<DailyReportResponse>('/api/reports/daily/refresh');
  return response;
};

