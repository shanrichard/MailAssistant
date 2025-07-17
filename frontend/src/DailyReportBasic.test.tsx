/**
 * Daily Report Basic Structure Test
 * 步骤6：DailyReport页面基础结构测试 - 简化版
 */

import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { BrowserRouter } from 'react-router-dom';
import DailyReport from './pages/DailyReport';

// Mock the auth store
jest.mock('./stores/authStore', () => ({
  __esModule: true,
  default: () => ({
    isAuthenticated: true,
    user: { id: '1', email: 'test@example.com' },
  }),
}));

// Mock the email service with null response (empty state)
jest.mock('./services/emailService', () => ({
  getDailyReport: jest.fn().mockResolvedValue(null),
}));

describe('DailyReport Page Basic Structure', () => {
  const renderDailyReport = () => {
    return render(
      <BrowserRouter>
        <DailyReport />
      </BrowserRouter>
    );
  };

  test('renders with proper semantic HTML structure', () => {
    renderDailyReport();
    
    // Should use semantic HTML elements
    expect(screen.getByRole('main')).toBeInTheDocument();
    expect(screen.getByRole('main')).toHaveClass('container', 'mx-auto', 'px-4', 'py-8');
  });

  test('renders empty state when no data', async () => {
    renderDailyReport();
    
    // Should show empty state after loading
    await waitFor(() => {
      expect(screen.getByTestId('empty-state')).toBeInTheDocument();
    });
    
    expect(screen.getByText('暂无日报数据')).toBeInTheDocument();
    expect(screen.getByText('尚未生成今日邮件日报')).toBeInTheDocument();
  });

  test('renders loading state initially', () => {
    renderDailyReport();
    
    // Should show loading spinner initially
    expect(screen.getByTestId('loading-spinner')).toBeInTheDocument();
  });

  test('has proper responsive layout', () => {
    renderDailyReport();
    
    const mainContainer = screen.getByRole('main');
    expect(mainContainer).toHaveClass('container', 'mx-auto', 'px-4', 'py-8');
  });

  test('renders generate report button in empty state', async () => {
    renderDailyReport();
    
    // Should have generate report button after loading
    await waitFor(() => {
      expect(screen.getByText('生成日报')).toBeInTheDocument();
    });
  });
});