/**
 * Daily Report Structure Test
 * 步骤6：DailyReport页面基础结构测试
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

// Mock the email service
jest.mock('./services/emailService', () => ({
  getDailyReport: jest.fn().mockResolvedValue({
    id: '1',
    userId: 'user1',
    reportDate: new Date('2025-07-15'),
    totalEmails: 50,
    importantEmails: 5,
    categorySummary: [
      {
        category: 'Newsletters',
        count: 20,
        description: 'Various newsletter subscriptions',
        priority: 'low',
      },
      {
        category: 'Promotions',
        count: 15,
        description: 'Marketing emails and promotions',
        priority: 'low',
      },
    ],
    importantEmailsList: [
      {
        id: '1',
        gmailId: 'gmail1',
        subject: 'Important Business Meeting',
        sender: 'boss@company.com',
        bodyText: 'Meeting content',
        isImportant: true,
        importanceReason: 'Contains urgent meeting request',
        category: 'work',
        receivedAt: new Date('2025-07-15T09:00:00Z'),
        isRead: false,
        isStarred: false,
      },
    ],
    summary: 'Daily email summary',
    generatedAt: new Date('2025-07-15T08:00:00Z'),
  }),
}));

describe('DailyReport Page Structure', () => {
  const renderDailyReport = () => {
    return render(
      <BrowserRouter>
        <DailyReport />
      </BrowserRouter>
    );
  };

  test('renders daily report page with correct title', async () => {
    renderDailyReport();
    
    // Wait for the data to load
    await waitFor(() => {
      expect(screen.getByText('Daily Report')).toBeInTheDocument();
    });
    
    expect(screen.getByText('Daily Report')).toHaveClass('text-2xl', 'font-bold');
  });

  test('renders report header section', async () => {
    renderDailyReport();
    
    // Should have a header section with date or refresh functionality
    await waitFor(() => {
      const headerSection = screen.getByTestId('report-header');
      expect(headerSection).toBeInTheDocument();
    });
  });

  test('renders stats cards section', async () => {
    renderDailyReport();
    
    // Should have a stats section
    await waitFor(() => {
      const statsSection = screen.getByTestId('stats-section');
      expect(statsSection).toBeInTheDocument();
    });
  });

  test('renders important emails section', async () => {
    renderDailyReport();
    
    // Should have an important emails section
    await waitFor(() => {
      const importantSection = screen.getByTestId('important-emails-section');
      expect(importantSection).toBeInTheDocument();
      
      // Should have a section title
      expect(screen.getByText('重要邮件')).toBeInTheDocument();
    });
  });

  test('renders category emails section', async () => {
    renderDailyReport();
    
    // Should have a category emails section
    await waitFor(() => {
      const categorySection = screen.getByTestId('category-emails-section');
      expect(categorySection).toBeInTheDocument();
      
      // Should have a section title
      expect(screen.getByText('分类邮件')).toBeInTheDocument();
    });
  });

  test('renders loading state initially', () => {
    renderDailyReport();
    
    // Should show loading spinner initially
    expect(screen.getByTestId('loading-spinner')).toBeInTheDocument();
  });

  test('renders empty state when no data', async () => {
    // Mock empty data
    const mockEmailService = require('./services/emailService');
    mockEmailService.getDailyReport.mockResolvedValueOnce(null);
    
    renderDailyReport();
    
    await waitFor(() => {
      expect(screen.getByTestId('empty-state')).toBeInTheDocument();
    });
  });

  test('has proper responsive layout classes', async () => {
    renderDailyReport();
    
    await waitFor(() => {
      const mainContainer = screen.getByTestId('daily-report-container');
      expect(mainContainer).toHaveClass('container', 'mx-auto', 'px-4');
    });
  });

  test('renders refresh button', async () => {
    renderDailyReport();
    
    await waitFor(() => {
      const refreshButton = screen.getByTestId('refresh-button');
      expect(refreshButton).toBeInTheDocument();
      expect(refreshButton).toHaveAttribute('type', 'button');
    });
  });

  test('renders proper section spacing', async () => {
    renderDailyReport();
    
    // Check that sections have proper spacing
    await waitFor(() => {
      const sections = screen.getAllByTestId(/section$/);
      sections.forEach(section => {
        expect(section).toHaveClass('mb-6');
      });
    });
  });

  test('renders with proper semantic HTML structure', async () => {
    renderDailyReport();
    
    // Should use semantic HTML elements
    await waitFor(() => {
      expect(screen.getByRole('main')).toBeInTheDocument();
      expect(screen.getByRole('heading', { level: 1 })).toBeInTheDocument();
    });
  });
});