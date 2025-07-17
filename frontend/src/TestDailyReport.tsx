/**
 * Test DailyReport Page - 临时测试版本
 * 用于测试DailyReport组件的基础结构，不需要认证
 */

import React from 'react';
import DailyReport from './pages/DailyReport';

// Mock auth store for testing
jest.mock('./stores/authStore', () => ({
  __esModule: true,
  default: () => ({
    isAuthenticated: true,
    user: { id: '1', email: 'test@example.com' },
    isLoading: false,
    checkAuth: () => {},
  }),
}));

const TestDailyReport: React.FC = () => {
  return <DailyReport />;
};

export default TestDailyReport;