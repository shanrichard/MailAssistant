/**
 * Email Category Component Tests
 * 邮件分类组件测试
 */

import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import EmailCategory from '../EmailCategory';
import { EmailCategory as EmailCategoryType } from '../../../types/dailyReport';

describe('EmailCategory Component', () => {
  const mockCategory: EmailCategoryType = {
    categoryName: '工作通知',
    summary: '包含3个项目更新和2个会议邀请',
    emails: [
      {
        id: '1',
        subject: '项目A进度更新',
        sender: 'projecta@company.com',
        receivedAt: '2025-07-16T14:00:00Z',
        isRead: false
      },
      {
        id: '2',
        subject: '会议邀请：产品评审',
        sender: 'meeting@company.com',
        receivedAt: '2025-07-16T13:00:00Z',
        isRead: true
      },
      {
        id: '3',
        subject: '项目B里程碑完成',
        sender: 'projectb@company.com',
        receivedAt: '2025-07-16T12:00:00Z',
        isRead: false
      }
    ]
  };

  const mockOnMarkAsRead = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Rendering', () => {
    it('should render category name', () => {
      render(
        <EmailCategory 
          category={mockCategory} 
          onMarkAsRead={mockOnMarkAsRead} 
        />
      );
      
      expect(screen.getByText('工作通知')).toBeInTheDocument();
    });

    it('should render email count', () => {
      render(
        <EmailCategory 
          category={mockCategory} 
          onMarkAsRead={mockOnMarkAsRead} 
        />
      );
      
      expect(screen.getByText('3 封邮件')).toBeInTheDocument();
    });

    it('should render category summary', () => {
      render(
        <EmailCategory 
          category={mockCategory} 
          onMarkAsRead={mockOnMarkAsRead} 
        />
      );
      
      expect(screen.getByText('包含3个项目更新和2个会议邀请')).toBeInTheDocument();
    });

    it('should render all emails in the category', () => {
      render(
        <EmailCategory 
          category={mockCategory} 
          onMarkAsRead={mockOnMarkAsRead} 
        />
      );
      
      expect(screen.getByText('项目A进度更新')).toBeInTheDocument();
      expect(screen.getByText('会议邀请：产品评审')).toBeInTheDocument();
      expect(screen.getByText('项目B里程碑完成')).toBeInTheDocument();
    });

    it('should show mark as read button when there are unread emails', () => {
      render(
        <EmailCategory 
          category={mockCategory} 
          onMarkAsRead={mockOnMarkAsRead} 
        />
      );
      
      expect(screen.getByText('标记已读')).toBeInTheDocument();
    });

    it('should not show mark as read button when all emails are read', () => {
      const allReadCategory = {
        ...mockCategory,
        emails: mockCategory.emails.map(email => ({ ...email, isRead: true }))
      };
      
      render(
        <EmailCategory 
          category={allReadCategory} 
          onMarkAsRead={mockOnMarkAsRead} 
        />
      );
      
      expect(screen.queryByText('标记已读')).not.toBeInTheDocument();
    });
  });

  describe('Expand/Collapse', () => {
    it('should be expanded by default', () => {
      render(
        <EmailCategory 
          category={mockCategory} 
          onMarkAsRead={mockOnMarkAsRead} 
          defaultExpanded={true}
        />
      );
      
      // 邮件列表应该可见
      expect(screen.getByText('项目A进度更新')).toBeVisible();
    });

    it('should toggle expand state on header click', () => {
      render(
        <EmailCategory 
          category={mockCategory} 
          onMarkAsRead={mockOnMarkAsRead} 
        />
      );
      
      const header = screen.getByTestId('category-header');
      
      // 点击收起
      fireEvent.click(header);
      expect(screen.queryByText('项目A进度更新')).not.toBeInTheDocument();
      
      // 再次点击展开
      fireEvent.click(header);
      expect(screen.getByText('项目A进度更新')).toBeInTheDocument();
    });
  });

  describe('Mark as Read', () => {
    it('should call onMarkAsRead when button is clicked', () => {
      render(
        <EmailCategory 
          category={mockCategory} 
          onMarkAsRead={mockOnMarkAsRead} 
        />
      );
      
      const markAsReadButton = screen.getByText('标记已读');
      fireEvent.click(markAsReadButton);
      
      expect(mockOnMarkAsRead).toHaveBeenCalledWith('工作通知');
    });

    it('should show loading state when marking', () => {
      render(
        <EmailCategory 
          category={mockCategory} 
          onMarkAsRead={mockOnMarkAsRead} 
          isMarking={true}
        />
      );
      
      expect(screen.getByText('标记中...')).toBeInTheDocument();
      const button = screen.getByRole('button', { name: /标记中/ });
      expect(button).toBeDisabled();
    });
  });

  describe('Styling', () => {
    it('should show unread count', () => {
      render(
        <EmailCategory 
          category={mockCategory} 
          onMarkAsRead={mockOnMarkAsRead} 
        />
      );
      
      // 2封未读邮件
      const unreadBadge = screen.getByTestId('unread-count');
      expect(unreadBadge).toHaveTextContent('2');
      expect(unreadBadge).toHaveClass('bg-blue-500');
    });
  });
});