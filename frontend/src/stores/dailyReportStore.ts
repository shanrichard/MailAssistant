/**
 * Daily Report Store
 * 日报状态管理
 */

import { create } from 'zustand';
import { DailyReportResponse } from '../types/dailyReport';
import { 
  getDailyReport, 
  refreshDailyReport
} from '../services/dailyReportService';

interface DailyReportState {
  // 状态
  report: DailyReportResponse | null;
  isLoading: boolean;
  isRefreshing: boolean;
  error: string | null;
  
  // Actions
  fetchReport: () => Promise<void>;
  refreshReport: () => Promise<void>;
  clearError: () => void;
  reset: () => void;
}

const useDailyReportStore = create<DailyReportState>((set, get) => ({
  // 初始状态
  report: null,
  isLoading: false,
  isRefreshing: false,
  error: null,

  // 获取日报
  fetchReport: async () => {
    set({ isLoading: true, error: null });
    try {
      const report = await getDailyReport();
      set({ report, isLoading: false });
    } catch (error) {
      set({ 
        error: error instanceof Error ? error.message : '获取日报失败',
        isLoading: false 
      });
    }
  },

  // 刷新日报
  refreshReport: async () => {
    set({ isRefreshing: true, error: null });
    try {
      const report = await refreshDailyReport();
      set({ report, isRefreshing: false });
    } catch (error) {
      set({ 
        error: error instanceof Error ? error.message : '刷新日报失败',
        isRefreshing: false 
      });
    }
  },


  // 清除错误
  clearError: () => {
    set({ error: null });
  },

  // 重置store
  reset: () => {
    set({
      report: null,
      isLoading: false,
      isRefreshing: false,
      error: null
    });
  }
}));

export default useDailyReportStore;