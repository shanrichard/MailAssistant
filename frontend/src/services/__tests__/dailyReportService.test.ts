/**
 * Daily Report Service Tests
 * 日报API服务测试
 */

import { DailyReport } from '../../types/dailyReport';

// Mock整个apiClient模块
jest.mock('../apiClient');

// 在mock之后导入
import { getDailyReport, refreshDailyReport, markCategoryAsRead } from '../dailyReportService';
import apiClient from '../apiClient';

// 将apiClient转换为mock类型
const mockedApiClient = apiClient as jest.Mocked<typeof apiClient>;

describe('DailyReportService', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('getDailyReport', () => {
    it('should fetch daily report successfully', async () => {
      const mockReport: DailyReport = {
        stats: {
          timeSaved: 23,
          emailsFiltered: 47,
          totalEmails: 52
        },
        importantEmails: [
          {
            id: '1',
            subject: 'Test Email',
            sender: 'test@example.com',
            receivedAt: '2025-07-16T10:00:00Z',
            isRead: false,
            importanceReason: 'Test reason'
          }
        ],
        categorizedEmails: [],
        generatedAt: '2025-07-16T10:00:00Z'
      };

      mockedApiClient.get.mockResolvedValueOnce({ data: mockReport });

      const result = await getDailyReport();

      expect(mockedApiClient.get).toHaveBeenCalledWith('/api/reports/daily');
      expect(result).toEqual(mockReport);
    });

    it('should handle API error', async () => {
      const error = new Error('Network error');
      mockedApiClient.get.mockRejectedValueOnce(error);

      await expect(getDailyReport()).rejects.toThrow('Network error');
    });
  });

  describe('refreshDailyReport', () => {
    it('should refresh daily report successfully', async () => {
      const mockReport: DailyReport = {
        stats: {
          timeSaved: 30,
          emailsFiltered: 50,
          totalEmails: 60
        },
        importantEmails: [],
        categorizedEmails: [],
        generatedAt: '2025-07-16T11:00:00Z'
      };

      mockedApiClient.post.mockResolvedValueOnce({ data: mockReport });

      const result = await refreshDailyReport();

      expect(mockedApiClient.post).toHaveBeenCalledWith(
        '/api/agents/email-processor',
        { message: '请生成今天的邮件日报' }
      );
      expect(result).toEqual(mockReport);
    });

    it('should handle refresh error', async () => {
      const error = new Error('Generation failed');
      mockedApiClient.post.mockRejectedValueOnce(error);

      await expect(refreshDailyReport()).rejects.toThrow('Generation failed');
    });
  });

  describe('markCategoryAsRead', () => {
    it('should mark category as read successfully', async () => {
      const categoryName = '工作通知';
      const emailIds = ['1', '2', '3'];

      mockedApiClient.post.mockResolvedValueOnce({ 
        data: { success: true, marked: 3 } 
      });

      const result = await markCategoryAsRead(categoryName, emailIds);

      expect(mockedApiClient.post).toHaveBeenCalledWith(
        '/api/gmail/bulk-action',
        {
          action: 'mark_read',
          emailIds: emailIds
        }
      );
      expect(result).toEqual({ success: true, marked: 3 });
    });

    it('should handle empty email list', async () => {
      const result = await markCategoryAsRead('测试分类', []);
      
      expect(mockedApiClient.post).not.toHaveBeenCalled();
      expect(result).toEqual({ success: true, marked: 0 });
    });

    it('should handle marking error', async () => {
      const error = new Error('Marking failed');
      mockedApiClient.post.mockRejectedValueOnce(error);

      await expect(
        markCategoryAsRead('测试分类', ['1'])
      ).rejects.toThrow('Marking failed');
    });
  });
});