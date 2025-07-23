/**
 * 同步状态管理Store
 * 用于全局管理邮件同步状态
 */

import { create } from 'zustand';
import { devtools } from 'zustand/middleware';

export type SyncStatus = 'idle' | 'syncing' | 'completed' | 'error';

export interface SyncStats {
  fetched: number;
  new: number;
  updated: number;
  errors: number;
}

interface SyncStore {
  // 状态
  globalSyncStatus: SyncStatus;
  lastSyncTime: Date | null;
  syncStats: SyncStats | null;
  currentTaskId: string | null;
  progress: number;
  errorMessage: string | null;
  
  // Actions
  updateSyncStatus: (status: SyncStatus) => void;
  updateSyncStats: (stats: SyncStats) => void;
  setLastSyncTime: (time: Date) => void;
  setCurrentTaskId: (taskId: string | null) => void;
  setProgress: (progress: number) => void;
  setErrorMessage: (message: string | null) => void;
  resetSyncState: () => void;
  
  // 便捷状态检查
  isIdle: () => boolean;
  isSyncing: () => boolean;
  isCompleted: () => boolean;
  hasError: () => boolean;
}

export const useSyncStore = create<SyncStore>()(
  devtools(
    (set, get) => ({
      // 初始状态
      globalSyncStatus: 'idle',
      lastSyncTime: null,
      syncStats: null,
      currentTaskId: null,
      progress: 0,
      errorMessage: null,
      
      // Actions
      updateSyncStatus: (status: SyncStatus) => {
        set({ globalSyncStatus: status }, false, 'updateSyncStatus');
        
        // 状态变更时的副作用
        if (status === 'completed') {
          set({ lastSyncTime: new Date(), progress: 100 }, false, 'syncCompleted');
        } else if (status === 'idle') {
          set({ progress: 0, errorMessage: null }, false, 'syncReset');
        } else if (status === 'syncing') {
          set({ errorMessage: null }, false, 'syncStarted');
        }
      },
      
      updateSyncStats: (stats: SyncStats) => {
        set({ syncStats: stats }, false, 'updateSyncStats');
      },
      
      setLastSyncTime: (time: Date) => {
        set({ lastSyncTime: time }, false, 'setLastSyncTime');
      },
      
      setCurrentTaskId: (taskId: string | null) => {
        set({ currentTaskId: taskId }, false, 'setCurrentTaskId');
      },
      
      setProgress: (progress: number) => {
        set({ progress: Math.max(0, Math.min(100, progress)) }, false, 'setProgress');
      },
      
      setErrorMessage: (message: string | null) => {
        set({ errorMessage: message }, false, 'setErrorMessage');
        if (message) {
          set({ globalSyncStatus: 'error' }, false, 'errorOccurred');
        }
      },
      
      resetSyncState: () => {
        set({
          globalSyncStatus: 'idle',
          syncStats: null,
          currentTaskId: null,
          progress: 0,
          errorMessage: null
        }, false, 'resetSyncState');
      },
      
      // 便捷状态检查
      isIdle: () => get().globalSyncStatus === 'idle',
      isSyncing: () => get().globalSyncStatus === 'syncing',
      isCompleted: () => get().globalSyncStatus === 'completed',
      hasError: () => get().globalSyncStatus === 'error'
    }),
    {
      name: 'sync-store',
      // 只在开发环境启用devtools
      enabled: process.env.NODE_ENV === 'development'
    }
  )
);

// 导出便捷的选择器
export const selectSyncStatus = (state: any) => state.globalSyncStatus;
export const selectSyncStats = (state: any) => state.syncStats;
export const selectSyncProgress = (state: any) => state.progress;
export const selectLastSyncTime = (state: any) => state.lastSyncTime;
export const selectCurrentTaskId = (state: any) => state.currentTaskId;
export const selectErrorMessage = (state: any) => state.errorMessage;

export default useSyncStore;