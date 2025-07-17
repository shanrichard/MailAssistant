/**
 * Value Stats Component Tests
 * 价值统计展示组件测试
 */

import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import ValueStats from '../ValueStats';
import { DailyReportStats } from '../../../types/dailyReport';

describe('ValueStats Component', () => {
  const mockStats: DailyReportStats = {
    timeSaved: 23,
    emailsFiltered: 47,
    totalEmails: 52
  };

  const mockOnRefresh = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Rendering', () => {
    it('should render all statistics correctly', () => {
      render(
        <ValueStats stats={mockStats} onRefresh={mockOnRefresh} />
      );

      // 检查时间节省显示
      expect(screen.getByText('为您节省')).toBeInTheDocument();
      expect(screen.getByText('23')).toBeInTheDocument();
      expect(screen.getByText('分钟')).toBeInTheDocument();

      // 检查邮件过滤显示
      expect(screen.getByText('智能过滤')).toBeInTheDocument();
      expect(screen.getByText('47')).toBeInTheDocument();
      expect(screen.getByText('/52')).toBeInTheDocument();
      expect(screen.getByText('封邮件')).toBeInTheDocument();
    });

    it('should render refresh button', () => {
      render(
        <ValueStats stats={mockStats} onRefresh={mockOnRefresh} />
      );

      const refreshButton = screen.getByRole('button', { name: /刷新/i });
      expect(refreshButton).toBeInTheDocument();
    });

    it('should display loading state', () => {
      render(
        <ValueStats 
          stats={mockStats} 
          onRefresh={mockOnRefresh} 
          isRefreshing={true}
        />
      );

      // 刷新按钮应该显示加载状态
      const refreshButton = screen.getByRole('button');
      expect(refreshButton).toBeDisabled();
      expect(screen.getByTestId('loading-spinner')).toBeInTheDocument();
    });
  });

  describe('Interactions', () => {
    it('should call onRefresh when refresh button is clicked', () => {
      render(
        <ValueStats stats={mockStats} onRefresh={mockOnRefresh} />
      );

      const refreshButton = screen.getByRole('button', { name: /刷新/i });
      fireEvent.click(refreshButton);

      expect(mockOnRefresh).toHaveBeenCalledTimes(1);
    });

    it('should not call onRefresh when button is disabled', () => {
      render(
        <ValueStats 
          stats={mockStats} 
          onRefresh={mockOnRefresh} 
          isRefreshing={true}
        />
      );

      const refreshButton = screen.getByRole('button');
      fireEvent.click(refreshButton);

      expect(mockOnRefresh).not.toHaveBeenCalled();
    });
  });

  describe('Edge Cases', () => {
    it('should handle zero values', () => {
      const zeroStats: DailyReportStats = {
        timeSaved: 0,
        emailsFiltered: 0,
        totalEmails: 0
      };

      render(
        <ValueStats stats={zeroStats} onRefresh={mockOnRefresh} />
      );

      // 查找所有的零值
      const zeroElements = screen.getAllByText('0');
      expect(zeroElements.length).toBeGreaterThan(0);
      
      // 检查是否有分钟和邮件文本
      expect(screen.getByText('分钟')).toBeInTheDocument();
      expect(screen.getByText('封邮件')).toBeInTheDocument();
    });

    it('should handle large numbers', () => {
      const largeStats: DailyReportStats = {
        timeSaved: 999,
        emailsFiltered: 1234,
        totalEmails: 5678
      };

      render(
        <ValueStats stats={largeStats} onRefresh={mockOnRefresh} />
      );

      expect(screen.getByText('999')).toBeInTheDocument();
      expect(screen.getByText('1234')).toBeInTheDocument();
      expect(screen.getByText('/5678')).toBeInTheDocument();
    });
  });

  describe('Styling', () => {
    it('should apply proper styling classes', () => {
      const { container } = render(
        <ValueStats stats={mockStats} onRefresh={mockOnRefresh} />
      );

      // 检查容器样式
      const valueSection = container.querySelector('.bg-gradient-to-r');
      expect(valueSection).toHaveClass('from-blue-50', 'to-indigo-50');

      // 检查数字样式
      const numbers = screen.getAllByText(/\d+/);
      numbers.forEach(num => {
        if (num.textContent === '23' || num.textContent === '47') {
          expect(num).toHaveClass('text-3xl', 'font-bold');
        }
      });
    });
  });
});