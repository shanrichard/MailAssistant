/**
 * Daily Report Page
 * 日报页面 - Markdown渲染版本
 */

import React, { useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import { format } from 'date-fns';
import { zhCN } from 'date-fns/locale';
import useDailyReportStore from '../stores/dailyReportStore';
import { ExclamationTriangleIcon, ArrowPathIcon, DocumentTextIcon } from '@heroicons/react/24/outline';
import { useSyncTrigger } from '../hooks/useSyncTrigger';

const DailyReport: React.FC = () => {
  const {
    report,
    isLoading,
    isRefreshing,
    error,
    fetchReport,
    refreshReport,
  } = useDailyReportStore();

  const { isSyncing } = useSyncTrigger();

  useEffect(() => {
    fetchReport();
  }, []);

  // 加载状态
  if (isLoading && !report) {
    return (
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="bg-white rounded-lg shadow p-8">
          <div className="animate-pulse space-y-4">
            <div className="h-8 bg-gray-200 rounded w-1/3"></div>
            <div className="h-4 bg-gray-200 rounded w-1/4"></div>
            <div className="space-y-2">
              <div className="h-4 bg-gray-200 rounded"></div>
              <div className="h-4 bg-gray-200 rounded"></div>
              <div className="h-4 bg-gray-200 rounded w-5/6"></div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // 错误状态
  if (error && !report) {
    return (
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
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

  return (
    <div className="max-w-full md:max-w-4xl mx-auto px-3 md:px-6 lg:px-8 py-4 md:py-8">
      <div className="bg-white rounded-lg shadow">
        {/* 页面标题和操作栏 */}
        <div className="border-b border-gray-200 px-4 md:px-6 py-4">
          <div className="flex items-center justify-between flex-wrap gap-2">
            <div className="flex items-center space-x-2 md:space-x-3 min-w-0 flex-1">
              <DocumentTextIcon className="h-5 w-5 md:h-6 md:w-6 text-gray-600 flex-shrink-0" />
              <h1 className="text-lg md:text-xl font-semibold text-gray-900 truncate">今日邮件日报</h1>
              {isSyncing && (
                <span className="flex items-center text-sm text-blue-600">
                  <ArrowPathIcon className="h-4 w-4 animate-spin mr-1" />
                  正在同步邮件...
                </span>
              )}
            </div>
            
            <button
              onClick={refreshReport}
              disabled={isRefreshing}
              className="flex items-center px-3 md:px-4 py-2 text-xs md:text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors min-h-[44px] md:min-h-0 flex-shrink-0"
            >
              {isRefreshing ? (
                <>
                  <ArrowPathIcon className="h-4 w-4 mr-2 animate-spin" />
                  重新生成中...
                </>
              ) : (
                <>
                  <ArrowPathIcon className="h-4 w-4 mr-2" />
                  重新生成
                </>
              )}
            </button>
          </div>
          
          {report?.generated_at && (
            <p className="text-sm text-gray-500 mt-2">
              生成时间: {format(new Date(report.generated_at), 'yyyy年MM月dd日 HH:mm', { locale: zhCN })}
            </p>
          )}
        </div>

        {/* 日报内容 */}
        <div className="px-4 md:px-6 py-4">
          {report?.status === 'processing' ? (
            <div className="text-center py-12">
              <ArrowPathIcon className="h-12 w-12 text-gray-400 animate-spin mx-auto mb-4" />
              <p className="text-gray-600">{report.message || '日报生成中，请稍后刷新页面'}</p>
            </div>
          ) : report?.status === 'failed' ? (
            <div className="bg-red-50 rounded-lg p-6">
              <div className="flex items-center">
                <ExclamationTriangleIcon className="h-6 w-6 text-red-500 mr-2" />
                <p className="text-red-800">日报生成失败，请稍后重试</p>
              </div>
            </div>
          ) : report?.content ? (
            <div className="prose prose-gray max-w-none">
              <ReactMarkdown
                components={{
                  // 自定义渲染组件
                  h1: ({ children }) => (
                    <h1 className="text-2xl font-bold text-gray-900 mb-4">{children}</h1>
                  ),
                  h2: ({ children }) => (
                    <h2 className="text-xl font-semibold text-gray-800 mt-6 mb-3">{children}</h2>
                  ),
                  h3: ({ children }) => (
                    <h3 className="text-lg font-medium text-gray-700 mt-4 mb-2">{children}</h3>
                  ),
                  p: ({ children }) => (
                    <p className="text-gray-600 mb-3 leading-relaxed">{children}</p>
                  ),
                  ul: ({ children }) => (
                    <ul className="list-disc list-inside space-y-1 mb-4">{children}</ul>
                  ),
                  ol: ({ children }) => (
                    <ol className="list-decimal list-inside space-y-1 mb-4">{children}</ol>
                  ),
                  li: ({ children }) => (
                    <li className="text-gray-600">{children}</li>
                  ),
                  strong: ({ children }) => (
                    <strong className="font-semibold text-gray-800">{children}</strong>
                  ),
                  blockquote: ({ children }) => (
                    <blockquote className="border-l-4 border-gray-300 pl-4 my-4 italic text-gray-600">
                      {children}
                    </blockquote>
                  ),
                  code: ({ children }) => (
                    <code className="bg-gray-100 px-1 py-0.5 rounded text-sm font-mono">{children}</code>
                  ),
                  pre: ({ children }) => (
                    <pre className="bg-gray-50 p-4 rounded-lg overflow-x-auto mb-4">{children}</pre>
                  ),
                }}
              >
                {report.content}
              </ReactMarkdown>
            </div>
          ) : (
            <div className="text-center py-12 text-gray-500">
              暂无日报内容
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default DailyReport;