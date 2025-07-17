/**
 * Daily Report Store
 * 日报状态管理
 */

import { create } from 'zustand';
import { DailyReport } from '../types/dailyReport';
import { 
  getDailyReport, 
  refreshDailyReport, 
  markCategoryAsRead 
} from '../services/dailyReportService';

interface DailyReportState {
  // 状态
  report: DailyReport | null;
  isLoading: boolean;
  isRefreshing: boolean;
  error: string | null;
  markingCategories: Set<string>; // 正在标记已读的分类
  
  // Actions
  fetchReport: () => Promise<void>;
  refreshReport: () => Promise<void>;
  markCategoryAsRead: (categoryName: string) => Promise<void>;
  clearError: () => void;
  reset: () => void;
}

const useDailyReportStore = create<DailyReportState>((set, get) => ({
  // 初始状态
  report: null,
  isLoading: false,
  isRefreshing: false,
  error: null,
  markingCategories: new Set(),

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

  // 标记分类为已读
  markCategoryAsRead: async (categoryName: string) => {
    const { report, markingCategories } = get();
    if (!report) return;

    // 找到该分类
    const category = report.categorizedEmails.find(
      cat => cat.categoryName === categoryName
    );
    if (!category) return;

    // 获取该分类下所有邮件的ID
    const emailIds = category.emails.map(email => email.id);
    if (emailIds.length === 0) return;

    // 添加到正在标记的集合
    const newMarkingCategories = new Set(markingCategories);
    newMarkingCategories.add(categoryName);
    set({ markingCategories: newMarkingCategories });

    try {
      await markCategoryAsRead(categoryName, emailIds);
      
      // 更新本地状态 - 将该分类下所有邮件标记为已读
      const updatedReport: DailyReport = {
        ...report,
        categorizedEmails: report.categorizedEmails.map(cat => {
          if (cat.categoryName === categoryName) {
            return {
              ...cat,
              emails: cat.emails.map(email => ({
                ...email,
                isRead: true
              }))
            };
          }
          return cat;
        })
      };
      
      // 移除正在标记的状态
      newMarkingCategories.delete(categoryName);
      set({ 
        report: updatedReport,
        markingCategories: newMarkingCategories 
      });
    } catch (error) {
      // 移除正在标记的状态
      newMarkingCategories.delete(categoryName);
      set({ 
        error: error instanceof Error ? error.message : '标记已读失败',
        markingCategories: newMarkingCategories
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
      error: null,
      markingCategories: new Set()
    });
  }
}));

export default useDailyReportStore;