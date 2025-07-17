/**
 * Daily Report Store Tests
 * 日报状态管理测试
 */

import useDailyReportStore from '../dailyReportStore';
import { DailyReport } from '../../types/dailyReport';

// Mock services
jest.mock('../../services/dailyReportService', () => ({
  getDailyReport: jest.fn(),
  refreshDailyReport: jest.fn(),
  markCategoryAsRead: jest.fn()
}));

import { 
  getDailyReport, 
  refreshDailyReport, 
  markCategoryAsRead 
} from '../../services/dailyReportService';

const mockedGetDailyReport = getDailyReport as jest.MockedFunction<typeof getDailyReport>;
const mockedRefreshDailyReport = refreshDailyReport as jest.MockedFunction<typeof refreshDailyReport>;
const mockedMarkCategoryAsRead = markCategoryAsRead as jest.MockedFunction<typeof markCategoryAsRead>;

describe('DailyReportStore', () => {
  // Mock data
  const mockReport: DailyReport = {
    stats: {
      timeSaved: 23,
      emailsFiltered: 47,
      totalEmails: 52
    },
    importantEmails: [],
    categorizedEmails: [
      {
        categoryName: '工作通知',
        summary: '测试摘要',
        emails: [
          {
            id: '1',
            subject: '测试邮件',
            sender: 'test@example.com',
            receivedAt: '2025-07-16T10:00:00Z',
            isRead: false
          }
        ]
      }
    ],
    generatedAt: '2025-07-16T10:00:00Z'
  };

  beforeEach(() => {
    // Reset store
    useDailyReportStore.getState().reset();
    // Clear mocks
    jest.clearAllMocks();
  });

  describe('Initial State', () => {
    it('should have correct initial state', () => {
      const state = useDailyReportStore.getState();
      expect(state.report).toBeNull();
      expect(state.isLoading).toBeFalsy();
      expect(state.isRefreshing).toBeFalsy();
      expect(state.error).toBeNull();
      expect(state.markingCategories.size).toBe(0);
    });
  });

  describe('fetchReport', () => {
    it('should fetch report successfully', async () => {
      mockedGetDailyReport.mockResolvedValueOnce(mockReport);

      const { fetchReport } = useDailyReportStore.getState();
      await fetchReport();

      const state = useDailyReportStore.getState();
      expect(state.report).toEqual(mockReport);
      expect(state.isLoading).toBeFalsy();
      expect(state.error).toBeNull();
    });

    it('should handle fetch error', async () => {
      const error = new Error('Network error');
      mockedGetDailyReport.mockRejectedValueOnce(error);

      const { fetchReport } = useDailyReportStore.getState();
      await fetchReport();

      const state = useDailyReportStore.getState();
      expect(state.report).toBeNull();
      expect(state.isLoading).toBeFalsy();
      expect(state.error).toBe('Network error');
    });
  });

  describe('refreshReport', () => {
    it('should refresh report successfully', async () => {
      mockedRefreshDailyReport.mockResolvedValueOnce(mockReport);

      const { refreshReport } = useDailyReportStore.getState();
      await refreshReport();

      const state = useDailyReportStore.getState();
      expect(state.report).toEqual(mockReport);
      expect(state.isRefreshing).toBeFalsy();
      expect(state.error).toBeNull();
    });
  });

  describe('markCategoryAsRead', () => {
    it('should mark category as read successfully', async () => {
      // Set initial report
      useDailyReportStore.setState({ report: mockReport });
      mockedMarkCategoryAsRead.mockResolvedValueOnce({ success: true, marked: 1 });

      const { markCategoryAsRead } = useDailyReportStore.getState();
      await markCategoryAsRead('工作通知');

      const state = useDailyReportStore.getState();
      const category = state.report?.categorizedEmails[0];
      expect(category?.emails[0].isRead).toBe(true);
      expect(state.markingCategories.has('工作通知')).toBe(false);
    });

    it('should handle empty report', async () => {
      const { markCategoryAsRead } = useDailyReportStore.getState();
      await markCategoryAsRead('工作通知');

      expect(mockedMarkCategoryAsRead).not.toHaveBeenCalled();
    });
  });

  describe('clearError', () => {
    it('should clear error', () => {
      useDailyReportStore.setState({ error: 'Test error' });
      
      const { clearError } = useDailyReportStore.getState();
      clearError();

      const state = useDailyReportStore.getState();
      expect(state.error).toBeNull();
    });
  });

  describe('reset', () => {
    it('should reset store to initial state', () => {
      useDailyReportStore.setState({
        report: mockReport,
        isLoading: true,
        error: 'Test error'
      });

      const { reset } = useDailyReportStore.getState();
      reset();

      const state = useDailyReportStore.getState();
      expect(state.report).toBeNull();
      expect(state.isLoading).toBeFalsy();
      expect(state.error).toBeNull();
    });
  });
});