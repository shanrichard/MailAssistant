/**
 * Daily Report Type Tests
 * 验证类型定义的正确性
 */

import {
  DailyReport,
  DailyReportStats,
  ImportantEmail,
  EmailCategory,
  CategorizedEmail
} from '../dailyReport';

// 类型测试 - 这些代码只用于验证类型定义是否正确
describe('DailyReport Types', () => {
  it('should accept valid DailyReportStats', () => {
    const stats: DailyReportStats = {
      timeSaved: 23,
      emailsFiltered: 47,
      totalEmails: 52
    };
    expect(stats).toBeDefined();
  });

  it('should accept valid ImportantEmail', () => {
    const email: ImportantEmail = {
      id: '1',
      subject: '项目紧急变更通知',
      sender: '张经理',
      receivedAt: new Date(),
      isRead: false,
      importanceReason: '来自重要联系人，包含"紧急"关键词'
    };
    expect(email).toBeDefined();
  });

  it('should accept valid EmailCategory', () => {
    const category: EmailCategory = {
      categoryName: '工作通知',
      summary: '今日收到产品更新通知3封、会议安排5封...',
      emails: [
        {
          id: '1',
          subject: '产品发布会议安排',
          sender: '产品团队',
          receivedAt: '2025-07-16T14:15:00',
          isRead: false
        }
      ]
    };
    expect(category).toBeDefined();
  });

  it('should accept valid DailyReport', () => {
    const report: DailyReport = {
      stats: {
        timeSaved: 23,
        emailsFiltered: 47,
        totalEmails: 52
      },
      importantEmails: [
        {
          id: '1',
          subject: '项目紧急变更通知',
          sender: '张经理',
          receivedAt: new Date(),
          isRead: false,
          importanceReason: '来自重要联系人'
        }
      ],
      categorizedEmails: [
        {
          categoryName: '工作通知',
          summary: '产品更新和会议安排',
          emails: []
        }
      ],
      generatedAt: new Date()
    };
    expect(report).toBeDefined();
  });

  it('should handle date as string', () => {
    const email: CategorizedEmail = {
      id: '1',
      subject: 'Test',
      sender: 'test@example.com',
      receivedAt: '2025-07-16T10:00:00Z', // ISO string
      isRead: true
    };
    expect(email.receivedAt).toBe('2025-07-16T10:00:00Z');
  });
});