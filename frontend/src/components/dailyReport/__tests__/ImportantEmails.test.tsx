/**
 * Important Emails Component Tests
 * 重要邮件展示组件测试
 */

import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import ImportantEmails from '../ImportantEmails';
import { ImportantEmail } from '../../../types/dailyReport';

describe('ImportantEmails Component', () => {
  const mockEmails: ImportantEmail[] = [
    {
      id: '1',
      subject: '项目截止日期通知',
      sender: 'pm@company.com',
      receivedAt: '2025-07-16T14:30:00Z',
      isRead: false,
      importanceReason: '包含"截止日期"关键词'
    },
    {
      id: '2',
      subject: '会议邀请：产品评审',
      sender: 'boss@company.com',
      receivedAt: '2025-07-16T10:00:00Z',
      isRead: true,
      importanceReason: '来自您的上级'
    }
  ];

  describe('Rendering', () => {
    it('should render section title', () => {
      render(<ImportantEmails emails={mockEmails} />);
      
      expect(screen.getByText('重要邮件')).toBeInTheDocument();
      expect(screen.getByText('需要您优先处理')).toBeInTheDocument();
    });

    it('should render all important emails', () => {
      render(<ImportantEmails emails={mockEmails} />);
      
      expect(screen.getByText('项目截止日期通知')).toBeInTheDocument();
      expect(screen.getByText('会议邀请：产品评审')).toBeInTheDocument();
    });

    it('should show importance reasons', () => {
      render(<ImportantEmails emails={mockEmails} />);
      
      expect(screen.getByText('包含"截止日期"关键词')).toBeInTheDocument();
      expect(screen.getByText('来自您的上级')).toBeInTheDocument();
    });

    it('should format time correctly', () => {
      render(<ImportantEmails emails={mockEmails} />);
      
      // 检查时间格式化（具体格式根据实现而定）
      // 由于时间显示在span中，我们需要查找包含时间的元素
      const timeSpans = screen.getAllByText(/\d{2}:\d{2}/);
      expect(timeSpans.length).toBeGreaterThan(0);
    });

    it('should show read/unread status', () => {
      render(<ImportantEmails emails={mockEmails} />);
      
      const emails = screen.getAllByTestId('important-email');
      // 第一封邮件未读，应该有特殊样式
      expect(emails[0]).toHaveClass('border-l-4', 'border-red-500');
      // 第二封邮件已读
      expect(emails[1]).not.toHaveClass('border-red-500');
    });

    it('should show empty state when no emails', () => {
      render(<ImportantEmails emails={[]} />);
      
      expect(screen.getByText('暂无重要邮件')).toBeInTheDocument();
    });
  });

  describe('Interactions', () => {
    it('should expand/collapse email content on click', () => {
      render(<ImportantEmails emails={mockEmails} />);
      
      const firstEmail = screen.getAllByTestId('important-email')[0];
      
      // 初始状态应该是折叠的
      expect(screen.queryByText(/更多内容/)).not.toBeInTheDocument();
      
      // 点击展开
      fireEvent.click(firstEmail);
      
      // 应该显示更多信息
      expect(screen.getByText(/发件人：pm@company.com/)).toBeInTheDocument();
    });
  });

  describe('Styling', () => {
    it('should apply warning styles for unread important emails', () => {
      render(<ImportantEmails emails={mockEmails} />);
      
      const emails = screen.getAllByTestId('important-email');
      const unreadEmail = emails[0];
      
      expect(unreadEmail).toHaveClass('bg-red-50');
    });

    it('should use star icon for importance indicator', () => {
      render(<ImportantEmails emails={mockEmails} />);
      
      const starIcons = screen.getAllByTestId('star-icon');
      expect(starIcons).toHaveLength(mockEmails.length);
    });
  });
});