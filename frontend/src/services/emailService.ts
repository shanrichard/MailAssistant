/**
 * Email Service
 * 邮件相关API服务
 */

import { EmailMessage, DailyReport, PaginatedResponse, ApiResponse } from '../types';
import { API_ENDPOINTS } from '../config';
import apiClient from './apiClient';

interface EmailListParams {
  page?: number;
  pageSize?: number;
  filter?: any;
  sort?: any;
}

class EmailService {
  /**
   * 获取邮件列表
   */
  async getEmails(params: EmailListParams = {}): Promise<PaginatedResponse<EmailMessage>> {
    const { page = 1, pageSize = 20, filter, sort } = params;
    
    const response = await apiClient.get<PaginatedResponse<EmailMessage>>(
      API_ENDPOINTS.GMAIL.EMAILS,
      {
        params: {
          page,
          page_size: pageSize,
          ...filter,
          ...sort,
        },
      }
    );
    
    return response;
  }

  /**
   * 同步邮件
   */
  async syncEmails(): Promise<void> {
    await apiClient.post(API_ENDPOINTS.GMAIL.SYNC);
  }

  /**
   * 搜索邮件
   */
  async searchEmails(query: string): Promise<PaginatedResponse<EmailMessage>> {
    const response = await apiClient.get<PaginatedResponse<EmailMessage>>(
      API_ENDPOINTS.GMAIL.SEARCH,
      {
        params: { q: query },
      }
    );
    
    return response;
  }

  /**
   * 标记邮件为已读
   */
  async markAsRead(emailIds: string[]): Promise<void> {
    await apiClient.post(API_ENDPOINTS.GMAIL.MARK_READ, {
      email_ids: emailIds,
    });
  }

  /**
   * 标记邮件为未读
   */
  async markAsUnread(emailIds: string[]): Promise<void> {
    await apiClient.post(API_ENDPOINTS.GMAIL.BULK_ACTION, {
      action: 'mark_unread',
      email_ids: emailIds,
    });
  }

  /**
   * 为邮件加星标
   */
  async starEmail(emailId: string): Promise<void> {
    await apiClient.post(API_ENDPOINTS.GMAIL.BULK_ACTION, {
      action: 'star',
      email_ids: [emailId],
    });
  }

  /**
   * 取消邮件星标
   */
  async unstarEmail(emailId: string): Promise<void> {
    await apiClient.post(API_ENDPOINTS.GMAIL.BULK_ACTION, {
      action: 'unstar',
      email_ids: [emailId],
    });
  }

  /**
   * 删除邮件
   */
  async deleteEmail(emailId: string): Promise<void> {
    await apiClient.post(API_ENDPOINTS.GMAIL.BULK_ACTION, {
      action: 'delete',
      email_ids: [emailId],
    });
  }

  /**
   * 归档邮件
   */
  async archiveEmail(emailId: string): Promise<void> {
    await apiClient.post(API_ENDPOINTS.GMAIL.BULK_ACTION, {
      action: 'archive',
      email_ids: [emailId],
    });
  }

  /**
   * 批量操作邮件
   */
  async bulkAction(action: string, emailIds: string[]): Promise<void> {
    await apiClient.post(API_ENDPOINTS.GMAIL.BULK_ACTION, {
      action,
      email_ids: emailIds,
    });
  }

  /**
   * 获取日报
   */
  async getDailyReport(date?: string): Promise<DailyReport> {
    const response = await apiClient.get<ApiResponse<DailyReport>>(
      API_ENDPOINTS.REPORTS.DAILY,
      {
        params: date ? { date } : {},
      }
    );
    
    return response.data;
  }

  /**
   * 生成日报
   */
  async generateDailyReport(date?: string): Promise<DailyReport> {
    const response = await apiClient.post<ApiResponse<DailyReport>>(
      API_ENDPOINTS.REPORTS.GENERATE,
      {
        date,
      }
    );
    
    return response.data;
  }

  /**
   * 获取邮件详情
   */
  async getEmailById(emailId: string): Promise<EmailMessage> {
    const response = await apiClient.get<ApiResponse<EmailMessage>>(
      `${API_ENDPOINTS.GMAIL.EMAILS}/${emailId}`
    );
    
    return response.data;
  }
}

export const emailService = new EmailService();
export default emailService;