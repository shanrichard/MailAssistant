/**
 * Daily Report Page Tests
 * 日报页面测试
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { MemoryRouter } from 'react-router-dom';
import DailyReport from '../DailyReport';
import useDailyReportStore from '../../stores/dailyReportStore';
import { DailyReport as DailyReportType } from '../../types/dailyReport';

// Mock store
jest.mock('../../stores/dailyReportStore');
const mockedUseDailyReportStore = useDailyReportStore as jest.MockedFunction<typeof useDailyReportStore>;

// Mock components
jest.mock('../../components/dailyReport/ValueStats', () => ({
  __esModule: true,
  default: ({ stats, onRefresh, isRefreshing }: any) => (
    <div data-testid="value-stats">
      <div>时间节省: {stats.timeSaved}</div>
      <button onClick={onRefresh} disabled={isRefreshing}>
        {isRefreshing ? '刷新中...' : '刷新'}
      </button>
    </div>
  )
}));

jest.mock('../../components/dailyReport/ImportantEmails', () => ({
  __esModule: true,
  default: ({ emails }: any) => (
    <div data-testid="important-emails">
      重要邮件数量: {emails.length}
    </div>
  )
}));

jest.mock('../../components/dailyReport/EmailCategory', () => ({
  __esModule: true,
  default: ({ category, onMarkAsRead, isMarking }: any) => (
    <div data-testid="email-category">
      <div>{category.categoryName}</div>
      <button onClick={() => onMarkAsRead(category.categoryName)} disabled={isMarking}>
        标记已读
      </button>
    </div>
  )
}));

describe('DailyReport Page', () => {
  const mockReport: DailyReportType = {
    stats: {
      timeSaved: 23,
      emailsFiltered: 47,
      totalEmails: 52
    },
    importantEmails: [
      {
        id: '1',
        subject: 'Important Email',
        sender: 'boss@company.com',
        receivedAt: '2025-07-16T10:00:00Z',
        isRead: false,
        importanceReason: 'From your boss'
      }
    ],
    categorizedEmails: [
      {
        categoryName: '工作通知',
        summary: '项目更新',
        emails: []
      }
    ],
    generatedAt: '2025-07-16T10:00:00Z'
  };

  const mockStoreState = {
    report: null,
    isLoading: false,
    isRefreshing: false,
    error: null,
    markingCategories: new Set(),
    fetchReport: jest.fn(),
    refreshReport: jest.fn(),
    markCategoryAsRead: jest.fn(),
    clearError: jest.fn(),
    reset: jest.fn()
  };

  beforeEach(() => {
    jest.clearAllMocks();
    mockedUseDailyReportStore.mockReturnValue(mockStoreState);
  });

  describe('Initial Load', () => {
    it('should fetch report on mount', () => {
      render(
        <MemoryRouter>
          <DailyReport />
        </MemoryRouter>
      );

      expect(mockStoreState.fetchReport).toHaveBeenCalledTimes(1);
    });

    it('should show loading state', () => {
      mockedUseDailyReportStore.mockReturnValue({
        ...mockStoreState,
        isLoading: true
      });

      render(
        <MemoryRouter>
          <DailyReport />
        </MemoryRouter>
      );

      expect(screen.getByTestId('loading-skeleton')).toBeInTheDocument();
    });

    it('should show error state', () => {
      mockedUseDailyReportStore.mockReturnValue({
        ...mockStoreState,
        error: '获取日报失败'
      });

      render(
        <MemoryRouter>
          <DailyReport />
        </MemoryRouter>
      );

      expect(screen.getByText('获取日报失败')).toBeInTheDocument();
      expect(screen.getByText('重试')).toBeInTheDocument();
    });
  });

  describe('Report Display', () => {
    it('should display report when loaded', () => {
      mockedUseDailyReportStore.mockReturnValue({
        ...mockStoreState,
        report: mockReport
      });

      render(
        <MemoryRouter>
          <DailyReport />
        </MemoryRouter>
      );

      expect(screen.getByTestId('value-stats')).toBeInTheDocument();
      expect(screen.getByTestId('important-emails')).toBeInTheDocument();
      expect(screen.getByTestId('email-category')).toBeInTheDocument();
    });

    it('should show page title and generation time', () => {
      mockedUseDailyReportStore.mockReturnValue({
        ...mockStoreState,
        report: mockReport
      });

      render(
        <MemoryRouter>
          <DailyReport />
        </MemoryRouter>
      );

      expect(screen.getByText('今日邮件日报')).toBeInTheDocument();
      expect(screen.getByText(/生成时间:/)).toBeInTheDocument();
    });
  });

  describe('Interactions', () => {
    it('should handle refresh', async () => {
      mockedUseDailyReportStore.mockReturnValue({
        ...mockStoreState,
        report: mockReport
      });

      render(
        <MemoryRouter>
          <DailyReport />
        </MemoryRouter>
      );

      const refreshButton = screen.getByText('刷新');
      fireEvent.click(refreshButton);

      expect(mockStoreState.refreshReport).toHaveBeenCalledTimes(1);
    });

    it('should handle mark category as read', () => {
      mockedUseDailyReportStore.mockReturnValue({
        ...mockStoreState,
        report: mockReport
      });

      render(
        <MemoryRouter>
          <DailyReport />
        </MemoryRouter>
      );

      const markAsReadButton = screen.getByText('标记已读');
      fireEvent.click(markAsReadButton);

      expect(mockStoreState.markCategoryAsRead).toHaveBeenCalledWith('工作通知');
    });

    it('should retry on error', () => {
      mockedUseDailyReportStore.mockReturnValue({
        ...mockStoreState,
        error: '网络错误'
      });

      render(
        <MemoryRouter>
          <DailyReport />
        </MemoryRouter>
      );

      const retryButton = screen.getByText('重试');
      fireEvent.click(retryButton);

      expect(mockStoreState.fetchReport).toHaveBeenCalled();
    });
  });

  describe('Empty State', () => {
    it('should show empty state when no report', () => {
      mockedUseDailyReportStore.mockReturnValue({
        ...mockStoreState,
        report: {
          ...mockReport,
          importantEmails: [],
          categorizedEmails: []
        }
      });

      render(
        <MemoryRouter>
          <DailyReport />
        </MemoryRouter>
      );

      expect(screen.getByText('暂无邮件数据')).toBeInTheDocument();
    });
  });
});