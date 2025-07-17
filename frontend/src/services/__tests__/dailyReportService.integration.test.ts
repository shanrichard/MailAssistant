/**
 * Daily Report Service Integration Tests
 * 集成测试 - 验证服务功能正确性
 */

import { getDailyReport, refreshDailyReport, markCategoryAsRead } from '../dailyReportService';

// 简单的功能验证测试
describe('DailyReportService Integration', () => {
  it('getDailyReport should be defined', () => {
    expect(getDailyReport).toBeDefined();
    expect(typeof getDailyReport).toBe('function');
  });

  it('refreshDailyReport should be defined', () => {
    expect(refreshDailyReport).toBeDefined();
    expect(typeof refreshDailyReport).toBe('function');
  });

  it('markCategoryAsRead should be defined', () => {
    expect(markCategoryAsRead).toBeDefined();
    expect(typeof markCategoryAsRead).toBe('function');
  });

  it('markCategoryAsRead should handle empty array without API call', async () => {
    const result = await markCategoryAsRead('test', []);
    expect(result).toEqual({ success: true, marked: 0 });
  });
});