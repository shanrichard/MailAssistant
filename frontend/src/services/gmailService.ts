/**
 * Gmail Service
 * Gmail相关API服务，包括智能同步功能
 */

import apiClient from './apiClient';

export interface SyncStats {
  fetched: number;
  new: number;
  updated: number;
  errors: number;
}

export interface SyncResult {
  success: boolean;
  stats: SyncStats;
  message: string;
  in_progress?: boolean;
  progress_percentage?: number;
  task_id?: string;
}

// 简化的接口定义，删除复杂的同步选项

class GmailService {
  private baseUrl = '/api/gmail';

  /**
   * 同步今天的邮件
   */
  async syncToday(): Promise<SyncResult> {
    const response = await apiClient.post<SyncResult>(
      `${this.baseUrl}/sync/today`
    );
    
    return response;
  }

  /**
   * 同步本周的邮件
   */
  async syncWeek(): Promise<SyncResult> {
    const response = await apiClient.post<SyncResult>(
      `${this.baseUrl}/sync/week`
    );
    
    return response;
  }

  /**
   * 同步本月的邮件
   */
  async syncMonth(): Promise<SyncResult> {
    const response = await apiClient.post<SyncResult>(
      `${this.baseUrl}/sync/month`
    );
    
    return response;
  }

  /**
   * 传统同步邮件（兼容性）
   */
  async syncEmails(days: number = 1, maxMessages: number = 100): Promise<SyncResult> {
    const response = await apiClient.post<SyncResult>(
      `${this.baseUrl}/sync`,
      {
        days,
        max_messages: maxMessages
      }
    );
    
    return response;
  }

  /**
   * 同步未读邮件
   */
  async syncUnreadEmails(): Promise<SyncResult> {
    const response = await apiClient.post<SyncResult>(
      `${this.baseUrl}/sync/unread`
    );
    
    return response;
  }

  /**
   * 获取同步状态
   */
  async getSyncStatus(): Promise<any> {
    const response = await apiClient.get(
      `${this.baseUrl}/sync/status`
    );
    
    return response;
  }

  /**
   * 搜索邮件
   */
  async searchEmails(query: string, maxResults: number = 50): Promise<any[]> {
    const response = await apiClient.post<any[]>(
      `${this.baseUrl}/search`,
      {
        query,
        max_results: maxResults
      }
    );
    
    return response;
  }

  /**
   * 获取最近邮件
   */
  async getRecentEmails(days: number = 1, maxResults: number = 20): Promise<any[]> {
    const response = await apiClient.get<any[]>(
      `${this.baseUrl}/recent`,
      {
        params: {
          days,
          max_results: maxResults
        }
      }
    );
    
    return response;
  }

  /**
   * 获取未读邮件
   */
  async getUnreadEmails(maxResults: number = 50): Promise<any[]> {
    const response = await apiClient.get<any[]>(
      `${this.baseUrl}/unread`,
      {
        params: {
          max_results: maxResults
        }
      }
    );
    
    return response;
  }

  /**
   * 标记邮件为已读
   */
  async markAsRead(emailIds: string[]): Promise<any> {
    const response = await apiClient.post(
      `${this.baseUrl}/mark-read`,
      {
        email_ids: emailIds
      }
    );
    
    return response;
  }

  /**
   * 按类别标记为已读
   */
  async markCategoryAsRead(category: string): Promise<any> {
    const response = await apiClient.post(
      `${this.baseUrl}/mark-read/category/${category}`
    );
    
    return response;
  }

  /**
   * 获取Gmail用户资料
   */
  async getProfile(): Promise<any> {
    const response = await apiClient.get(
      `${this.baseUrl}/profile`
    );
    
    return response;
  }

  /**
   * 获取邮件详情
   */
  async getMessageDetails(messageId: string): Promise<any> {
    const response = await apiClient.get(
      `${this.baseUrl}/message/${messageId}`
    );
    
    return response;
  }

  /**
   * 根据发件人获取邮件
   */
  async getMessagesBySender(senderEmail: string, maxResults: number = 20): Promise<any[]> {
    const response = await apiClient.get<any[]>(
      `${this.baseUrl}/sender/${senderEmail}`,
      {
        params: {
          max_results: maxResults
        }
      }
    );
    
    return response;
  }

  /**
   * 添加标签到邮件
   */
  async addLabels(messageIds: string[], labelIds: string[]): Promise<any> {
    const response = await apiClient.post(
      `${this.baseUrl}/labels/add`,
      {
        message_ids: messageIds,
        label_ids: labelIds
      }
    );
    
    return response;
  }

  /**
   * 从邮件移除标签
   */
  async removeLabels(messageIds: string[], labelIds: string[]): Promise<any> {
    const response = await apiClient.post(
      `${this.baseUrl}/labels/remove`,
      {
        message_ids: messageIds,
        label_ids: labelIds
      }
    );
    
    return response;
  }
}

export const gmailService = new GmailService();
export default gmailService;