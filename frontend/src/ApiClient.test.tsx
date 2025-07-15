/**
 * API客户端测试
 * 步骤5：验证前端能正常调用后端API
 */

import { render, screen, waitFor } from '@testing-library/react';
import { appConfig, API_ENDPOINTS } from './config';

// Mock axios
jest.mock('axios', () => ({
  create: jest.fn(() => ({
    interceptors: {
      request: { use: jest.fn() },
      response: { use: jest.fn() }
    },
    get: jest.fn(),
    post: jest.fn(),
    put: jest.fn(),
    patch: jest.fn(),
    delete: jest.fn()
  }))
}));

// Import services after mocking axios
import { apiClient } from './services/apiClient';
import { authService } from './services/authService';
import { emailService } from './services/emailService';

describe('步骤5: API客户端测试', () => {
  beforeEach(() => {
    // 清除所有mock
    jest.clearAllMocks();
  });

  describe('API客户端基础功能', () => {
    test('应该正确配置API base URL', () => {
      expect(appConfig.apiBaseUrl).toBe('http://localhost:8000');
    });

    test('应该正确配置请求超时', () => {
      expect(appConfig.requestTimeout).toBe(10000);
    });

    test('应该能够获取API客户端实例', () => {
      const client = apiClient;
      expect(client).toBeDefined();
      expect(typeof client.get).toBe('function');
      expect(typeof client.post).toBe('function');
      expect(typeof client.put).toBe('function');
      expect(typeof client.delete).toBe('function');
    });

    test('应该能够获取原始axios实例', () => {
      const rawClient = apiClient.getRawClient();
      expect(rawClient).toBeDefined();
    });
  });

  describe('认证服务API调用', () => {
    test('应该能够调用Google登录API', async () => {
      const mockResponse = {
        data: {
          token: 'mock-jwt-token'
        }
      };
      
      apiClient.post = jest.fn().mockResolvedValue(mockResponse);
      
      const token = await authService.googleLogin('mock-auth-code');
      
      expect(apiClient.post).toHaveBeenCalledWith(
        API_ENDPOINTS.AUTH.GOOGLE,
        { code: 'mock-auth-code' }
      );
      expect(token).toBe('mock-jwt-token');
    });

    test('应该能够调用获取当前用户API', async () => {
      const mockUser = {
        id: '123',
        email: 'test@example.com',
        name: 'Test User',
        createdAt: new Date(),
        updatedAt: new Date()
      };
      
      const mockResponse = {
        data: mockUser
      };
      
      apiClient.get = jest.fn().mockResolvedValue(mockResponse);
      
      const user = await authService.getCurrentUser();
      
      expect(apiClient.get).toHaveBeenCalledWith(API_ENDPOINTS.AUTH.ME);
      expect(user).toEqual(mockUser);
    });

    test('应该能够调用刷新令牌API', async () => {
      const mockResponse = {
        data: {
          token: 'new-jwt-token'
        }
      };
      
      apiClient.post = jest.fn().mockResolvedValue(mockResponse);
      
      const token = await authService.refreshToken();
      
      expect(apiClient.post).toHaveBeenCalledWith(API_ENDPOINTS.AUTH.REFRESH);
      expect(token).toBe('new-jwt-token');
    });

    test('应该能够调用登出API', async () => {
      apiClient.delete = jest.fn().mockResolvedValue(undefined);
      
      await authService.logout();
      
      expect(apiClient.delete).toHaveBeenCalledWith(API_ENDPOINTS.AUTH.LOGOUT);
    });
  });

  describe('邮件服务API调用', () => {
    test('应该能够调用获取邮件列表API', async () => {
      const mockEmails = {
        data: [
          {
            id: '1',
            subject: 'Test Email',
            sender: 'sender@example.com',
            content: 'Test content',
            timestamp: new Date(),
            isRead: false
          }
        ],
        pagination: {
          page: 1,
          pageSize: 20,
          total: 1,
          totalPages: 1
        }
      };
      
      apiClient.get = jest.fn().mockResolvedValue(mockEmails);
      
      const result = await emailService.getEmails({ page: 1, pageSize: 20 });
      
      expect(apiClient.get).toHaveBeenCalledWith(
        API_ENDPOINTS.GMAIL.EMAILS,
        {
          params: {
            page: 1,
            page_size: 20
          }
        }
      );
      expect(result).toEqual(mockEmails);
    });

    test('应该能够调用同步邮件API', async () => {
      apiClient.post = jest.fn().mockResolvedValue(undefined);
      
      await emailService.syncEmails();
      
      expect(apiClient.post).toHaveBeenCalledWith(API_ENDPOINTS.GMAIL.SYNC);
    });

    test('应该能够调用搜索邮件API', async () => {
      const mockSearchResult = {
        data: [],
        pagination: {
          page: 1,
          pageSize: 20,
          total: 0,
          totalPages: 0
        }
      };
      
      apiClient.get = jest.fn().mockResolvedValue(mockSearchResult);
      
      const result = await emailService.searchEmails('test query');
      
      expect(apiClient.get).toHaveBeenCalledWith(
        API_ENDPOINTS.GMAIL.SEARCH,
        {
          params: { q: 'test query' }
        }
      );
      expect(result).toEqual(mockSearchResult);
    });

    test('应该能够调用标记为已读API', async () => {
      apiClient.post = jest.fn().mockResolvedValue(undefined);
      
      await emailService.markAsRead(['1', '2', '3']);
      
      expect(apiClient.post).toHaveBeenCalledWith(
        API_ENDPOINTS.GMAIL.MARK_READ,
        {
          email_ids: ['1', '2', '3']
        }
      );
    });

    test('应该能够调用批量操作API', async () => {
      apiClient.post = jest.fn().mockResolvedValue(undefined);
      
      await emailService.bulkAction('archive', ['1', '2']);
      
      expect(apiClient.post).toHaveBeenCalledWith(
        API_ENDPOINTS.GMAIL.BULK_ACTION,
        {
          action: 'archive',
          email_ids: ['1', '2']
        }
      );
    });

    test('应该能够调用获取日报API', async () => {
      const mockDailyReport = {
        data: {
          id: '1',
          date: '2025-07-15',
          totalEmails: 50,
          importantEmails: 5,
          categories: {},
          summary: 'Daily summary',
          createdAt: new Date()
        }
      };
      
      apiClient.get = jest.fn().mockResolvedValue(mockDailyReport);
      
      const result = await emailService.getDailyReport('2025-07-15');
      
      expect(apiClient.get).toHaveBeenCalledWith(
        API_ENDPOINTS.REPORTS.DAILY,
        {
          params: { date: '2025-07-15' }
        }
      );
      expect(result).toEqual(mockDailyReport.data);
    });

    test('应该能够调用生成日报API', async () => {
      const mockDailyReport = {
        data: {
          id: '1',
          date: '2025-07-15',
          totalEmails: 50,
          importantEmails: 5,
          categories: {},
          summary: 'Daily summary',
          createdAt: new Date()
        }
      };
      
      apiClient.post = jest.fn().mockResolvedValue(mockDailyReport);
      
      const result = await emailService.generateDailyReport('2025-07-15');
      
      expect(apiClient.post).toHaveBeenCalledWith(
        API_ENDPOINTS.REPORTS.GENERATE,
        {
          date: '2025-07-15'
        }
      );
      expect(result).toEqual(mockDailyReport.data);
    });
  });

  describe('错误处理', () => {
    test('应该能够处理网络错误', async () => {
      const networkError = new Error('Network Error');
      networkError.request = {};
      
      apiClient.get = jest.fn().mockRejectedValue(networkError);
      
      await expect(authService.getCurrentUser()).rejects.toThrow();
    });

    test('应该能够处理401未授权错误', async () => {
      const authError = new Error('Unauthorized');
      authError.response = {
        status: 401,
        data: { message: 'Token expired' }
      };
      
      apiClient.get = jest.fn().mockRejectedValue(authError);
      
      await expect(authService.getCurrentUser()).rejects.toThrow();
    });

    test('应该能够处理500服务器错误', async () => {
      const serverError = new Error('Server Error');
      serverError.response = {
        status: 500,
        data: { message: 'Internal server error' }
      };
      
      apiClient.get = jest.fn().mockRejectedValue(serverError);
      
      await expect(authService.getCurrentUser()).rejects.toThrow();
    });
  });

  describe('令牌管理', () => {
    test('应该能够检测令牌过期', () => {
      // 创建一个过期的JWT令牌
      const expiredToken = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyLCJleHAiOjE1MTYyMzkwMjJ9.invalid';
      
      const isExpired = authService.isTokenExpired(expiredToken);
      expect(isExpired).toBe(true);
    });

    test('应该能够解析JWT令牌', () => {
      // 创建一个有效的JWT令牌
      const validToken = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c';
      
      const payload = authService.parseToken(validToken);
      expect(payload).toEqual({
        sub: '1234567890',
        name: 'John Doe',
        iat: 1516239022
      });
    });

    test('应该能够生成Google OAuth URL', () => {
      // 设置环境变量
      process.env.REACT_APP_GOOGLE_CLIENT_ID = 'test-client-id';
      
      const url = authService.getGoogleAuthUrl();
      
      expect(url).toContain('accounts.google.com/o/oauth2/v2/auth');
      expect(url).toContain('client_id=test-client-id');
      expect(url).toContain('response_type=code');
      expect(url).toContain('scope=');
    });
  });

  describe('API端点配置', () => {
    test('应该包含所有必需的认证端点', () => {
      expect(API_ENDPOINTS.AUTH.GOOGLE).toBe('/auth/google');
      expect(API_ENDPOINTS.AUTH.REFRESH).toBe('/auth/refresh');
      expect(API_ENDPOINTS.AUTH.LOGOUT).toBe('/auth/logout');
      expect(API_ENDPOINTS.AUTH.ME).toBe('/auth/me');
    });

    test('应该包含所有必需的Gmail端点', () => {
      expect(API_ENDPOINTS.GMAIL.EMAILS).toBe('/gmail/emails');
      expect(API_ENDPOINTS.GMAIL.SYNC).toBe('/gmail/sync');
      expect(API_ENDPOINTS.GMAIL.SEARCH).toBe('/gmail/search');
      expect(API_ENDPOINTS.GMAIL.MARK_READ).toBe('/gmail/mark-read');
      expect(API_ENDPOINTS.GMAIL.BULK_ACTION).toBe('/gmail/bulk-action');
    });

    test('应该包含所有必需的报告端点', () => {
      expect(API_ENDPOINTS.REPORTS.DAILY).toBe('/reports/daily');
      expect(API_ENDPOINTS.REPORTS.GENERATE).toBe('/reports/generate');
      expect(API_ENDPOINTS.REPORTS.HISTORY).toBe('/reports/history');
    });

    test('应该包含所有必需的Agent端点', () => {
      expect(API_ENDPOINTS.AGENTS.EMAIL_PROCESSOR).toBe('/agents/email-processor');
      expect(API_ENDPOINTS.AGENTS.CONVERSATION).toBe('/agents/conversation');
      expect(API_ENDPOINTS.AGENTS.SESSION).toBe('/agents/session');
    });

    test('应该包含所有必需的任务端点', () => {
      expect(API_ENDPOINTS.TASKS.LOGS).toBe('/tasks/logs');
      expect(API_ENDPOINTS.TASKS.SCHEDULE).toBe('/tasks/schedule');
      expect(API_ENDPOINTS.TASKS.STATUS).toBe('/tasks/status');
    });
  });

  describe('配置验证', () => {
    test('应该正确配置默认设置', () => {
      expect(appConfig.apiBaseUrl).toBe('http://localhost:8000');
      expect(appConfig.wsUrl).toBe('ws://localhost:8000');
      expect(appConfig.requestTimeout).toBe(10000);
      expect(appConfig.defaultPageSize).toBe(20);
      expect(appConfig.maxRetries).toBe(3);
    });

    test('应该能够处理环境变量', () => {
      // 测试默认值
      const originalEnv = process.env;
      process.env = {};
      
      const getEnvVar = (name: string, defaultValue?: string): string => {
        const value = process.env[name];
        if (!value && !defaultValue) {
          throw new Error(`Environment variable ${name} is required`);
        }
        return value || defaultValue!;
      };
      
      expect(getEnvVar('TEST_VAR', 'default')).toBe('default');
      
      process.env = originalEnv;
    });
  });
});