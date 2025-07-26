/**
 * 解耦同步Hook
 * 支持新的解耦架构 - 显示最新邮件时间，非阻塞同步请求
 */
import { useState, useEffect } from 'react';
import { gmailService } from '../services/gmailService';

export interface LatestEmailInfo {
  latest_email_time: string | null;
  latest_email_subject?: string;
  latest_email_sender?: string;
  message?: string;
}

export const useDecoupledSync = () => {
  const [latestEmailInfo, setLatestEmailInfo] = useState<LatestEmailInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [requesting, setRequesting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 获取最新邮件时间
  const fetchLatestEmailTime = async () => {
    try {
      setLoading(true);
      const response = await gmailService.getLatestEmailTime();
      setLatestEmailInfo(response);
      setError(null);
    } catch (error) {
      console.error('获取最新邮件时间失败:', error);
      setError(error instanceof Error ? error.message : '获取最新邮件时间失败');
    } finally {
      setLoading(false);
    }
  };

  // 组件挂载时加载数据
  useEffect(() => {
    fetchLatestEmailTime();
  }, []);

  // 请求同步（非阻塞）
  const requestSync = async (syncType: 'today' | 'week' | 'month'): Promise<string> => {
    setRequesting(true);
    setError(null);
    try {
      const response = await gmailService.requestSync(syncType);
      return response.message || '同步请求已发送';
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : '同步请求失败';
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setRequesting(false);
    }
  };

  // 刷新最新邮件时间
  const refreshLatestEmailTime = () => {
    fetchLatestEmailTime();
  };

  // 清除错误
  const clearError = () => setError(null);

  // 格式化最新邮件时间显示
  const formatLatestEmailTime = (emailInfo: LatestEmailInfo | null): string => {
    if (!emailInfo?.latest_email_time) {
      return '暂无邮件数据';
    }
    
    try {
      const date = new Date(emailInfo.latest_email_time);
      return date.toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch {
      return '时间格式错误';
    }
  };

  return {
    // 状态
    latestEmailInfo,
    loading,
    requesting,
    error,
    
    // 方法
    requestSync,
    refreshLatestEmailTime,
    clearError,
    formatLatestEmailTime,
    
    // 便捷状态检查
    hasEmailData: !!latestEmailInfo?.latest_email_time,
    hasError: !!error,
  };
};