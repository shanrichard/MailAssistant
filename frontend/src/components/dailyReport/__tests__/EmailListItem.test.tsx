/**
 * Email List Item Component Tests
 * 邮件列表项组件测试
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import EmailListItem from '../EmailListItem';
import { Email } from '../../../types/dailyReport';

describe('EmailListItem Component', () => {
  const mockEmail: Email = {
    id: '1',
    subject: '产品会议记录',
    sender: 'product@company.com',
    receivedAt: '2025-07-16T15:30:00Z',
    isRead: false
  };

  const mockReadEmail: Email = {
    ...mockEmail,
    id: '2',
    isRead: true
  };

  describe('Rendering', () => {
    it('should render email subject', () => {
      render(<EmailListItem email={mockEmail} />);
      
      expect(screen.getByText('产品会议记录')).toBeInTheDocument();
    });

    it('should render sender', () => {
      render(<EmailListItem email={mockEmail} />);
      
      expect(screen.getByText('product@company.com')).toBeInTheDocument();
    });

    it('should render time', () => {
      render(<EmailListItem email={mockEmail} />);
      
      // 检查时间显示 - 时间可能是不同格式（如 7/16 或 15:30）
      const timeElement = screen.getByText((content, element) => {
        return element?.className === 'text-xs text-gray-500 flex-shrink-0' && content.length > 0;
      });
      expect(timeElement).toBeInTheDocument();
    });

    it('should show unread indicator for unread emails', () => {
      render(<EmailListItem email={mockEmail} />);
      
      const unreadIndicator = screen.getByTestId('unread-indicator');
      expect(unreadIndicator).toBeInTheDocument();
      expect(unreadIndicator).toHaveClass('bg-blue-500');
    });

    it('should not show unread indicator for read emails', () => {
      render(<EmailListItem email={mockReadEmail} />);
      
      expect(screen.queryByTestId('unread-indicator')).not.toBeInTheDocument();
    });
  });

  describe('Styling', () => {
    it('should apply bold font for unread emails', () => {
      render(<EmailListItem email={mockEmail} />);
      
      const subject = screen.getByText('产品会议记录');
      expect(subject).toHaveClass('font-semibold');
    });

    it('should apply normal font for read emails', () => {
      render(<EmailListItem email={mockReadEmail} />);
      
      const subject = screen.getByText('产品会议记录');
      expect(subject).toHaveClass('font-normal');
    });

    it('should have hover effect', () => {
      const { container } = render(<EmailListItem email={mockEmail} />);
      
      const item = container.firstChild;
      expect(item).toHaveClass('hover:bg-gray-50');
    });
  });

  describe('Long content', () => {
    it('should truncate long subject', () => {
      const longSubjectEmail: Email = {
        ...mockEmail,
        subject: '这是一个非常非常长的邮件主题，需要被截断以保持界面的美观和一致性'
      };
      
      render(<EmailListItem email={longSubjectEmail} />);
      
      const subject = screen.getByText(/这是一个非常非常长的邮件主题/);
      expect(subject).toHaveClass('truncate');
    });

    it('should truncate long sender', () => {
      const longSenderEmail: Email = {
        ...mockEmail,
        sender: 'very.long.email.address@very.long.company.domain.com'
      };
      
      render(<EmailListItem email={longSenderEmail} />);
      
      const sender = screen.getByText(/very.long.email.address/);
      expect(sender).toHaveClass('truncate');
    });
  });
});