/**
 * Email Store
 * 邮件状态管理
 */

import { create } from 'zustand';
import { EmailStore, EmailMessage, DailyReportResponse, EmailFilterOptions, SortOptions, AppError } from '../types';
import { emailService } from '../services/emailService';
import { APP_CONSTANTS } from '../config';

interface ExtendedEmailStore extends EmailStore {
  // Additional state
  selectedEmails: string[];
  filterOptions: EmailFilterOptions;
  sortOptions: SortOptions;
  searchQuery: string;
  totalCount: number;
  currentPage: number;
  hasMore: boolean;
  
  // Additional actions
  setSelectedEmails: (emailIds: string[]) => void;
  toggleEmailSelection: (emailId: string) => void;
  clearSelection: () => void;
  setFilterOptions: (options: EmailFilterOptions) => void;
  setSortOptions: (options: SortOptions) => void;
  setSearchQuery: (query: string) => void;
  searchEmails: (query: string) => Promise<void>;
  loadMoreEmails: () => Promise<void>;
  refreshEmails: () => Promise<void>;
  // syncEmails 方法已删除，使用新的简单同步按钮
  markEmailAsRead: (emailId: string) => Promise<void>;
  markEmailAsUnread: (emailId: string) => Promise<void>;
  starEmail: (emailId: string) => Promise<void>;
  unstarEmail: (emailId: string) => Promise<void>;
  deleteEmail: (emailId: string) => Promise<void>;
  archiveEmail: (emailId: string) => Promise<void>;
  generateDailyReport: (date?: string) => Promise<void>;
  clearError: () => void;
}

const useEmailStore = create<ExtendedEmailStore>()((set, get) => ({
  // Initial state
  emails: [],
  currentEmail: null,
  dailyReport: null,
  categories: Object.values(APP_CONSTANTS.EMAIL_CATEGORIES),
  isLoading: false,
  error: null,
  selectedEmails: [],
  filterOptions: {},
  sortOptions: {
    field: 'receivedAt',
    direction: 'desc',
  },
  searchQuery: '',
  totalCount: 0,
  currentPage: 1,
  hasMore: true,

  // Basic actions
  setEmails: (emails: EmailMessage[]) => {
    set({ emails });
  },

  setCurrentEmail: (email: EmailMessage | null) => {
    set({ currentEmail: email });
  },

  setDailyReport: (report: DailyReportResponse | null) => {
    set({ dailyReport: report });
  },

  setLoading: (loading: boolean) => {
    set({ isLoading: loading });
  },

  setError: (error: string | null) => {
    set({ error });
  },

  // Selection actions
  setSelectedEmails: (emailIds: string[]) => {
    set({ selectedEmails: emailIds });
  },

  toggleEmailSelection: (emailId: string) => {
    const { selectedEmails } = get();
    const isSelected = selectedEmails.includes(emailId);
    
    if (isSelected) {
      set({ selectedEmails: selectedEmails.filter(id => id !== emailId) });
    } else {
      set({ selectedEmails: [...selectedEmails, emailId] });
    }
  },

  clearSelection: () => {
    set({ selectedEmails: [] });
  },

  // Filter and sort actions
  setFilterOptions: (options: EmailFilterOptions) => {
    set({ filterOptions: options, currentPage: 1 });
  },

  setSortOptions: (options: SortOptions) => {
    set({ sortOptions: options, currentPage: 1 });
  },

  setSearchQuery: (query: string) => {
    set({ searchQuery: query });
  },

  // Async actions
  fetchEmails: async () => {
    try {
      set({ isLoading: true, error: null });
      
      const { filterOptions, sortOptions, currentPage } = get();
      const response = await emailService.getEmails({
        page: currentPage,
        pageSize: APP_CONSTANTS.PAGINATION.DEFAULT_PAGE_SIZE,
        filter: filterOptions,
        sort: sortOptions,
      });
      
      set({
        emails: response.data,
        totalCount: response.total,
        hasMore: response.page < response.totalPages,
        isLoading: false,
      });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to fetch emails',
        isLoading: false,
      });
    }
  },

  loadMoreEmails: async () => {
    try {
      const { hasMore, isLoading, currentPage, emails, filterOptions, sortOptions } = get();
      
      if (!hasMore || isLoading) return;
      
      set({ isLoading: true });
      
      const response = await emailService.getEmails({
        page: currentPage + 1,
        pageSize: APP_CONSTANTS.PAGINATION.DEFAULT_PAGE_SIZE,
        filter: filterOptions,
        sort: sortOptions,
      });
      
      set({
        emails: [...emails, ...response.data],
        currentPage: currentPage + 1,
        hasMore: response.page < response.totalPages,
        isLoading: false,
      });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to load more emails',
        isLoading: false,
      });
    }
  },

  refreshEmails: async () => {
    set({ currentPage: 1, hasMore: true });
    await get().fetchEmails();
  },

  // syncEmails 方法已删除，使用新的简单同步按钮

  searchEmails: async (query: string) => {
    try {
      set({ isLoading: true, error: null, searchQuery: query });
      
      const response = await emailService.searchEmails(query);
      
      set({
        emails: response.data,
        totalCount: response.total,
        hasMore: false,
        currentPage: 1,
        isLoading: false,
      });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to search emails',
        isLoading: false,
      });
    }
  },

  // Single email actions
  markEmailAsRead: async (emailId: string) => {
    try {
      await emailService.markAsRead([emailId]);
      
      const { emails } = get();
      const updatedEmails = emails.map(email =>
        email.id === emailId ? { ...email, isRead: true } : email
      );
      
      set({ emails: updatedEmails });
    } catch (error) {
      set({ error: error instanceof Error ? error.message : 'Failed to mark email as read' });
    }
  },

  markEmailAsUnread: async (emailId: string) => {
    try {
      await emailService.markAsUnread([emailId]);
      
      const { emails } = get();
      const updatedEmails = emails.map(email =>
        email.id === emailId ? { ...email, isRead: false } : email
      );
      
      set({ emails: updatedEmails });
    } catch (error) {
      set({ error: error instanceof Error ? error.message : 'Failed to mark email as unread' });
    }
  },

  starEmail: async (emailId: string) => {
    try {
      await emailService.starEmail(emailId);
      
      const { emails } = get();
      const updatedEmails = emails.map(email =>
        email.id === emailId ? { ...email, isStarred: true } : email
      );
      
      set({ emails: updatedEmails });
    } catch (error) {
      set({ error: error instanceof Error ? error.message : 'Failed to star email' });
    }
  },

  unstarEmail: async (emailId: string) => {
    try {
      await emailService.unstarEmail(emailId);
      
      const { emails } = get();
      const updatedEmails = emails.map(email =>
        email.id === emailId ? { ...email, isStarred: false } : email
      );
      
      set({ emails: updatedEmails });
    } catch (error) {
      set({ error: error instanceof Error ? error.message : 'Failed to unstar email' });
    }
  },

  deleteEmail: async (emailId: string) => {
    try {
      await emailService.deleteEmail(emailId);
      
      const { emails } = get();
      const updatedEmails = emails.filter(email => email.id !== emailId);
      
      set({ emails: updatedEmails });
    } catch (error) {
      set({ error: error instanceof Error ? error.message : 'Failed to delete email' });
    }
  },

  archiveEmail: async (emailId: string) => {
    try {
      await emailService.archiveEmail(emailId);
      
      const { emails } = get();
      const updatedEmails = emails.filter(email => email.id !== emailId);
      
      set({ emails: updatedEmails });
    } catch (error) {
      set({ error: error instanceof Error ? error.message : 'Failed to archive email' });
    }
  },

  // Bulk actions
  markAsRead: async (emailIds: string[]) => {
    try {
      await emailService.markAsRead(emailIds);
      
      const { emails } = get();
      const updatedEmails = emails.map(email =>
        emailIds.includes(email.id) ? { ...email, isRead: true } : email
      );
      
      set({ emails: updatedEmails });
    } catch (error) {
      set({ error: error instanceof Error ? error.message : 'Failed to mark emails as read' });
    }
  },

  bulkAction: async (action: string, emailIds: string[]) => {
    try {
      await emailService.bulkAction(action, emailIds);
      
      // Update local state based on action
      const { emails } = get();
      let updatedEmails = emails;
      
      switch (action) {
        case APP_CONSTANTS.EMAIL_ACTIONS.MARK_READ:
          updatedEmails = emails.map(email =>
            emailIds.includes(email.id) ? { ...email, isRead: true } : email
          );
          break;
        case APP_CONSTANTS.EMAIL_ACTIONS.MARK_UNREAD:
          updatedEmails = emails.map(email =>
            emailIds.includes(email.id) ? { ...email, isRead: false } : email
          );
          break;
        case APP_CONSTANTS.EMAIL_ACTIONS.STAR:
          updatedEmails = emails.map(email =>
            emailIds.includes(email.id) ? { ...email, isStarred: true } : email
          );
          break;
        case APP_CONSTANTS.EMAIL_ACTIONS.UNSTAR:
          updatedEmails = emails.map(email =>
            emailIds.includes(email.id) ? { ...email, isStarred: false } : email
          );
          break;
        case APP_CONSTANTS.EMAIL_ACTIONS.DELETE:
        case APP_CONSTANTS.EMAIL_ACTIONS.ARCHIVE:
          updatedEmails = emails.filter(email => !emailIds.includes(email.id));
          break;
        default:
          break;
      }
      
      set({ emails: updatedEmails, selectedEmails: [] });
    } catch (error) {
      set({ error: error instanceof Error ? error.message : 'Bulk action failed' });
    }
  },

  // Daily report actions
  fetchDailyReport: async () => {
    try {
      set({ isLoading: true, error: null });
      
      const report = await emailService.getDailyReport();
      
      set({
        dailyReport: report,
        isLoading: false,
      });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to fetch daily report',
        isLoading: false,
      });
    }
  },

  generateDailyReport: async (date?: string) => {
    try {
      set({ isLoading: true, error: null });
      
      const report = await emailService.generateDailyReport(date);
      
      set({
        dailyReport: report,
        isLoading: false,
      });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to generate daily report',
        isLoading: false,
      });
    }
  },

  clearError: () => {
    set({ error: null });
  },
}));

export default useEmailStore;