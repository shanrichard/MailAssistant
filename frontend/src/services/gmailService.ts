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

export interface ShouldSyncResult {
  needsSync: boolean;
  reason: 'firstSync' | 'thresholdExceeded' | 'scheduled';
  lastSyncTime: string | null;
  emailCount: number;
  isFirstSync: boolean;
}

export interface SyncProgress {
  success: boolean;
  isRunning: boolean;
  progress: number;
  stats: SyncStats;
  error: string | null;
  syncType: string;
  startedAt: string | null;
  updatedAt: string | null;
}

export interface SmartSyncOptions {
  force_full?: boolean;
  background?: boolean;
}

class GmailService {
  private baseUrl = '/api/gmail';

  /**
   * 智能同步邮件
   */
  async smartSync(options: SmartSyncOptions = {}): Promise<SyncResult> {
    const { force_full = false, background = false } = options;
    
    const response = await apiClient.post<SyncResult>(
      `${this.baseUrl}/sync/smart`,
      {},
      {
        params: {
          force_full,
          background
        }
      }
    );
    
    return response;
  }

  /**
   * 检查是否需要同步
   */
  async shouldSync(): Promise<ShouldSyncResult> {
    const response = await apiClient.get<ShouldSyncResult>(
      `${this.baseUrl}/sync/should-sync`
    );
    
    return response;
  }

  /**
   * 获取同步进度
   */
  async getSyncProgress(taskId: string): Promise<SyncProgress> {
    const response = await apiClient.get<SyncProgress>(
      `${this.baseUrl}/sync/progress/${taskId}`
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
  async markAsRead(emailIds: string[]): Promise<{ success: boolean; stats: any; message: string }> {
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
  async markCategoryAsRead(category: string): Promise<{ success: boolean; stats: any; message: string }> {
    const response = await apiClient.post(
      `${this.baseUrl}/mark-read/category/${category}`
    );
    
    return response;
  }

  /**
   * 获取Gmail用户资料
   */
  async getProfile(): Promise<{ success: boolean; profile: any }> {
    const response = await apiClient.get(
      `${this.baseUrl}/profile`
    );
    
    return response;
  }

  /**
   * 获取邮件详情
   */
  async getMessageDetails(messageId: string): Promise<{ success: boolean; message: any }> {
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
  async addLabels(messageIds: string[], labelIds: string[]): Promise<{ success: boolean; message: string }> {
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
  async removeLabels(messageIds: string[], labelIds: string[]): Promise<{ success: boolean; message: string }> {
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