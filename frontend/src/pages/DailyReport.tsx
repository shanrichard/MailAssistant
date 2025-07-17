/**
 * Daily Report Page
 * 日报页面 - 整合所有组件
 */

import React, { useEffect } from 'react';
import { format } from 'date-fns';
import { zhCN } from 'date-fns/locale';
import useDailyReportStore from '../stores/dailyReportStore';
import ValueStats from '../components/dailyReport/ValueStats';
import ImportantEmails from '../components/dailyReport/ImportantEmails';
import EmailCategory from '../components/dailyReport/EmailCategory';
import { ExclamationTriangleIcon } from '@heroicons/react/24/outline';

const DailyReport: React.FC = () => {
  const {
    report,
    isLoading,
    isRefreshing,
    error,
    markingCategories,
    fetchReport,
    refreshReport,
    markCategoryAsRead,
  } = useDailyReportStore();

  useEffect(() => {
    fetchReport();
  }, [fetchReport]);

  // 加载状态
  if (isLoading && !report) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div data-testid="loading-skeleton" className="space-y-4">
          <div className="bg-gray-200 animate-pulse h-32 rounded-lg"></div>
          <div className="bg-gray-200 animate-pulse h-64 rounded-lg"></div>
          <div className="bg-gray-200 animate-pulse h-48 rounded-lg"></div>
        </div>
      </div>
    );
  }

  // 错误状态
  if (error && !report) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="bg-red-50 border border-red-200 rounded-lg p-6">
          <div className="flex items-center">
            <ExclamationTriangleIcon className="h-8 w-8 text-red-500 mr-3" />
            <div>
              <h3 className="text-lg font-medium text-red-800">
                获取日报失败
              </h3>
              <p className="mt-1 text-sm text-red-700">{error}</p>
              <button
                onClick={() => fetchReport()}
                className="mt-3 bg-red-100 text-red-700 px-4 py-2 rounded hover:bg-red-200 transition-colors"
              >
                重试
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // 空状态
  if (report && report.categorizedEmails.length === 0 && report.importantEmails.length === 0) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="bg-gray-50 rounded-lg p-12 text-center">
          <h2 className="text-xl font-medium text-gray-900 mb-2">
            暂无邮件数据
          </h2>
          <p className="text-gray-600">
            今天还没有收到任何邮件，请稍后再来查看
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="space-y-6">
        {/* 页面标题 */}
        <div>
          <h1 className="text-2xl font-bold text-gray-900">今日邮件日报</h1>
          {report && (
            <p className="text-sm text-gray-500 mt-1">
              生成时间: {format(new Date(report.generatedAt), 'yyyy年MM月dd日 HH:mm', { locale: zhCN })}
            </p>
          )}
        </div>

        {/* 价值统计 */}
        {report && (
          <ValueStats
            stats={report.stats}
            onRefresh={refreshReport}
            isRefreshing={isRefreshing}
          />
        )}

        {/* 重要邮件 */}
        {report && report.importantEmails.length > 0 && (
          <ImportantEmails emails={report.importantEmails} />
        )}

        {/* 分类邮件 */}
        {report && report.categorizedEmails.length > 0 && (
          <div className="space-y-4">
            <h2 className="text-lg font-semibold text-gray-900">所有邮件</h2>
            {report.categorizedEmails.map((category) => (
              <EmailCategory
                key={category.categoryName}
                category={category}
                onMarkAsRead={markCategoryAsRead}
                isMarking={markingCategories.has(category.categoryName)}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default DailyReport;