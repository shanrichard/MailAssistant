/**
 * Settings Page Tests
 * 设置页面测试
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import Settings from '../Settings';
import { schedulerService } from '../../services/schedulerService';
import { showToast } from '../../utils/toast';

// Mock services
jest.mock('../../services/schedulerService');
jest.mock('../../utils/toast');

const mockSchedulerService = schedulerService as jest.Mocked<typeof schedulerService>;
const mockShowToast = showToast as jest.MockedFunction<typeof showToast>;

// Helper to render with router
const renderWithRouter = (component: React.ReactElement) => {
  return render(
    <BrowserRouter>
      {component}
    </BrowserRouter>
  );
};

describe('Settings Page', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    
    // Mock timezone
    jest.spyOn(Intl.DateTimeFormat.prototype, 'resolvedOptions').mockReturnValue({
      timeZone: 'Asia/Shanghai',
      calendar: 'gregory',
      day: 'numeric',
      locale: 'zh-CN',
      month: 'numeric',
      numberingSystem: 'latn',
      year: 'numeric'
    });
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  test('renders settings page with loading state', () => {
    mockSchedulerService.getSchedule.mockImplementation(() => 
      new Promise(() => {}) // Never resolves to keep loading
    );

    renderWithRouter(<Settings />);
    
    // Should show loading spinner
    expect(screen.getByRole('status', { hidden: true })).toBeInTheDocument();
  });

  test('loads and displays current settings', async () => {
    mockSchedulerService.getSchedule.mockResolvedValue({
      daily_report_time: '10:30',
      timezone: 'Asia/Shanghai',
      auto_sync_enabled: true
    });

    renderWithRouter(<Settings />);
    
    await waitFor(() => {
      expect(screen.getByText('设置')).toBeInTheDocument();
    });
    
    // Check if time is loaded
    const timeInput = screen.getByDisplayValue('10:30') as HTMLInputElement;
    expect(timeInput).toBeInTheDocument();
    expect(timeInput.type).toBe('time');
    
    // Check timezone display
    expect(screen.getByText('当前时区：Asia/Shanghai (本地)')).toBeInTheDocument();
  });

  test('handles save settings successfully', async () => {
    mockSchedulerService.getSchedule.mockResolvedValue({
      daily_report_time: '09:00',
      timezone: 'Asia/Shanghai',
      auto_sync_enabled: true
    });
    
    mockSchedulerService.updateSchedule.mockResolvedValue({
      daily_report_time: '14:00',
      timezone: 'Asia/Shanghai',
      auto_sync_enabled: true,
      next_run: '2025-07-19T14:00:00+08:00'
    });

    renderWithRouter(<Settings />);
    
    await waitFor(() => {
      expect(screen.getByDisplayValue('09:00')).toBeInTheDocument();
    });
    
    // Change time
    const timeInput = screen.getByDisplayValue('09:00') as HTMLInputElement;
    fireEvent.change(timeInput, { target: { value: '14:00' } });
    
    // Click save
    const saveButton = screen.getByText('保存');
    fireEvent.click(saveButton);
    
    // Check loading state
    expect(screen.getByText('保存中...')).toBeInTheDocument();
    
    await waitFor(() => {
      expect(mockSchedulerService.updateSchedule).toHaveBeenCalledWith({
        time: '14:00',
        timezone: 'Asia/Shanghai'
      });
      expect(mockShowToast).toHaveBeenCalledWith('设置保存成功', 'success');
      expect(screen.getByText('已保存')).toBeInTheDocument();
    });
    
    // Button should return to normal after 2 seconds
    await waitFor(() => {
      expect(screen.getByText('保存')).toBeInTheDocument();
    }, { timeout: 3000 });
  });

  test('handles validation error', async () => {
    mockSchedulerService.getSchedule.mockResolvedValue({
      daily_report_time: '09:00',
      timezone: 'Asia/Shanghai',
      auto_sync_enabled: true
    });
    
    mockSchedulerService.updateSchedule.mockRejectedValue({
      code: 'VALIDATION_ERROR',
      message: '时间格式必须为 HH:mm',
      details: { message: '时间格式必须为 HH:mm' },
      timestamp: new Date()
    });

    renderWithRouter(<Settings />);
    
    await waitFor(() => {
      expect(screen.getByDisplayValue('09:00')).toBeInTheDocument();
    });
    
    // Click save
    const saveButton = screen.getByText('保存');
    fireEvent.click(saveButton);
    
    await waitFor(() => {
      expect(screen.getByText('时间格式必须为 HH:mm')).toBeInTheDocument();
      expect(mockShowToast).toHaveBeenCalledWith('时间格式必须为 HH:mm', 'error');
    });
  });

  test('handles network error', async () => {
    mockSchedulerService.getSchedule.mockResolvedValue({
      daily_report_time: '09:00',
      timezone: 'Asia/Shanghai',
      auto_sync_enabled: true
    });
    
    mockSchedulerService.updateSchedule.mockRejectedValue({
      code: 'NETWORK_ERROR',
      message: '网络连接失败',
      timestamp: new Date()
    });

    renderWithRouter(<Settings />);
    
    await waitFor(() => {
      expect(screen.getByDisplayValue('09:00')).toBeInTheDocument();
    });
    
    // Click save
    const saveButton = screen.getByText('保存');
    fireEvent.click(saveButton);
    
    await waitFor(() => {
      expect(screen.getByText('网络连接失败，请检查网络')).toBeInTheDocument();
    });
  });

  test('manual trigger daily report', async () => {
    mockSchedulerService.getSchedule.mockResolvedValue({
      daily_report_time: '09:00',
      timezone: 'Asia/Shanghai',
      auto_sync_enabled: true
    });
    
    mockSchedulerService.triggerDailyReport.mockResolvedValue({
      task_id: 'task-123',
      message: 'Daily report triggered'
    });

    renderWithRouter(<Settings />);
    
    await waitFor(() => {
      expect(screen.getByText('手动生成日报')).toBeInTheDocument();
    });
    
    // Click trigger button
    const triggerButton = screen.getByText('立即生成');
    fireEvent.click(triggerButton);
    
    await waitFor(() => {
      expect(mockSchedulerService.triggerDailyReport).toHaveBeenCalled();
      expect(mockShowToast).toHaveBeenCalledWith('日报生成任务已触发', 'success');
    });
  });

  test('clears error when time is changed', async () => {
    mockSchedulerService.getSchedule.mockResolvedValue({
      daily_report_time: '09:00',
      timezone: 'Asia/Shanghai',
      auto_sync_enabled: true
    });
    
    // First save fails
    mockSchedulerService.updateSchedule.mockRejectedValueOnce({
      code: 'VALIDATION_ERROR',
      message: '时间格式错误',
      timestamp: new Date()
    });

    renderWithRouter(<Settings />);
    
    await waitFor(() => {
      expect(screen.getByDisplayValue('09:00')).toBeInTheDocument();
    });
    
    // Trigger error
    fireEvent.click(screen.getByText('保存'));
    
    await waitFor(() => {
      expect(screen.getByText('时间格式错误')).toBeInTheDocument();
    });
    
    // Change time - should clear error
    const timeInput = screen.getByDisplayValue('09:00');
    fireEvent.change(timeInput, { target: { value: '10:00' } });
    
    // Error should be cleared
    expect(screen.queryByText('时间格式错误')).not.toBeInTheDocument();
  });
});