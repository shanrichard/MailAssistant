/**
 * 邮件同步触发Hook
 * 用于智能触发邮件同步和管理同步状态
 */
import { useCallback } from 'react';
import { gmailService } from '../services/gmailService';
import { useSyncStore, SyncStats, SyncStatus } from '../stores/syncStore';

// 重新导出类型以便其他组件使用
export type { SyncStatus, SyncStats } from '../stores/syncStore';

export interface SyncResult {
  success: boolean;
  stats: SyncStats;
  message: string;
  in_progress?: boolean;
  progress_percentage?: number;
  task_id?: string;
}

export interface ShouldSyncResult {
  needsSync: boolean;
  reason: 'firstSync' | 'thresholdExceeded' | 'scheduled';
  lastSyncTime: string | null;
  emailCount: number;
  isFirstSync: boolean;
}

export interface SyncProgress {
  isRunning: boolean;
  progress: number;
  stats: SyncStats;
  error: string | null;
  syncType: string;
  startedAt: string | null;
  updatedAt: string | null;
}

export const useSyncTrigger = () => {
  const {
    globalSyncStatus,
    syncStats,
    currentTaskId,
    progress,
    updateSyncStatus,
    updateSyncStats,
    setCurrentTaskId,
    setProgress,
    setErrorMessage,
    resetSyncState,
    isIdle,
    isSyncing,
    isCompleted,
    hasError
  } = useSyncStore();

  const checkAndSync = useCallback(async (triggerType: 'page-visit' | 'manual' | 'auto'): Promise<SyncResult | null> => {
    try {
      // 1. 检查是否需要同步
      const shouldSyncResult = await gmailService.shouldSync();
      
      // 2. 根据策略决定是否同步
      if (shouldSyncResult.needsSync || triggerType === 'manual') {
        return await triggerSync(shouldSyncResult.isFirstSync);
      }
      
      return null;
    } catch (error) {
      console.error('检查同步状态失败:', error);
      setErrorMessage(error instanceof Error ? error.message : '检查同步状态失败');
      throw error;
    }
  }, [setErrorMessage]);

  const triggerSync = useCallback(async (forceFullSync = false): Promise<SyncResult> => {
    updateSyncStatus('syncing');
    setProgress(0);
    
    try {
      const result = await gmailService.smartSync({
        force_full: forceFullSync,
        background: forceFullSync // 全量同步时使用后台模式
      });
      
      updateSyncStats(result.stats);
      
      if (result.in_progress && result.task_id) {
        // 后台任务模式，开始轮询进度
        setCurrentTaskId(result.task_id);
        await pollSyncProgress(result.task_id);
      } else {
        // 直接同步完成
        setProgress(100);
        updateSyncStatus('completed');
      }
      
      return result;
    } catch (error) {
      console.error('同步失败:', error);
      setErrorMessage(error instanceof Error ? error.message : '同步失败');
      throw error;
    }
  }, [updateSyncStatus, setProgress, updateSyncStats, setCurrentTaskId, setErrorMessage]);

  const pollSyncProgress = useCallback(async (taskId: string) => {
    const maxAttempts = 180; // 最多轮询3分钟
    let attempts = 0;
    
    const poll = async () => {
      try {
        const progressResult = await gmailService.getSyncProgress(taskId);
        
        setProgress(progressResult.progress);
        if (progressResult.stats) {
          updateSyncStats(progressResult.stats);
        }
        
        if (!progressResult.isRunning) {
          // 同步完成
          setProgress(100);
          updateSyncStatus(progressResult.error ? 'error' : 'completed');
          setCurrentTaskId(null);
          
          if (progressResult.error) {
            setErrorMessage(progressResult.error);
          }
          return;
        }
        
        attempts++;
        if (attempts < maxAttempts) {
          // 继续轮询
          setTimeout(poll, 1000); // 每秒轮询一次
        } else {
          // 超时
          setErrorMessage('同步超时');
          setCurrentTaskId(null);
        }
      } catch (error) {
        console.error('获取同步进度失败:', error);
        setErrorMessage(error instanceof Error ? error.message : '获取同步进度失败');
        setCurrentTaskId(null);
      }
    };
    
    // 开始轮询
    setTimeout(poll, 1000);
  }, [setProgress, updateSyncStats, updateSyncStatus, setCurrentTaskId, setErrorMessage]);

  const cancelSync = useCallback(async () => {
    // TODO: 实现取消同步功能
    resetSyncState();
  }, [resetSyncState]);

  return {
    // 状态
    syncStatus: globalSyncStatus,
    syncStats,
    currentTaskId,
    progress,
    
    // 方法
    checkAndSync,
    triggerSync,
    cancelSync,
    resetSyncState,
    
    // 便捷状态检查
    isIdle: isIdle(),
    isSyncing: isSyncing(),
    isCompleted: isCompleted(),
    hasError: hasError()
  };
};

export default useSyncTrigger;