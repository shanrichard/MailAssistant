/**
 * 简化的同步Hook
 * 只提供基本的同步功能，删除所有复杂逻辑
 */
import { useState } from 'react';
import { gmailService } from '../services/gmailService';

export interface SyncStats {
  new: number;
  updated: number;
  errors: number;
  fetched?: number;
}

export interface SyncResult {
  success: boolean;
  stats: SyncStats;
  message: string;
}

export const useSyncTrigger = () => {
  const [isSyncing, setIsSyncing] = useState(false);
  const [lastSyncResult, setLastSyncResult] = useState<SyncResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const syncToday = async (): Promise<SyncResult> => {
    setIsSyncing(true);
    setError(null);
    try {
      const result = await gmailService.syncToday();
      setLastSyncResult(result);
      return result;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : '同步失败';
      setError(errorMessage);
      throw error;
    } finally {
      setIsSyncing(false);
    }
  };

  const syncWeek = async (): Promise<SyncResult> => {
    setIsSyncing(true);
    setError(null);
    try {
      const result = await gmailService.syncWeek();
      setLastSyncResult(result);
      return result;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : '同步失败';
      setError(errorMessage);
      throw error;
    } finally {
      setIsSyncing(false);
    }
  };

  const syncMonth = async (): Promise<SyncResult> => {
    setIsSyncing(true);
    setError(null);
    try {
      const result = await gmailService.syncMonth();
      setLastSyncResult(result);
      return result;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : '同步失败';
      setError(errorMessage);
      throw error;
    } finally {
      setIsSyncing(false);
    }
  };

  const clearError = () => setError(null);
  const clearResult = () => setLastSyncResult(null);

  return {
    // 状态
    isSyncing,
    lastSyncResult,
    error,
    
    // 方法
    syncToday,
    syncWeek,
    syncMonth,
    clearError,
    clearResult,
    
    // 便捷状态检查
    hasError: !!error,
    hasResult: !!lastSyncResult,
  };
};