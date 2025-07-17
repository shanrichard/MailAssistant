/**
 * Value Stats Component
 * 展示邮件助手为用户创造的价值
 */

import React from 'react';
import { ClockIcon, FunnelIcon, ArrowPathIcon } from '@heroicons/react/24/outline';
import { DailyReportStats } from '../../types/dailyReport';

interface ValueStatsProps {
  stats: DailyReportStats;
  onRefresh: () => void;
  isRefreshing?: boolean;
}

const ValueStats: React.FC<ValueStatsProps> = ({ 
  stats, 
  onRefresh, 
  isRefreshing = false 
}) => {
  return (
    <div className="bg-gradient-to-r from-blue-50 to-indigo-50 p-6 rounded-lg shadow-sm">
      <div className="flex items-center justify-between">
        <div className="flex-1">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* 时间节省统计 */}
            <div className="flex items-center space-x-4">
              <div className="flex-shrink-0">
                <div className="p-3 bg-blue-100 rounded-full">
                  <ClockIcon className="h-6 w-6 text-blue-600" />
                </div>
              </div>
              <div>
                <p className="text-sm text-gray-600">为您节省</p>
                <p className="text-2xl font-semibold text-gray-900">
                  <span className="text-3xl font-bold text-blue-600">
                    {stats.timeSaved}
                  </span>
                  <span className="ml-1 text-lg">分钟</span>
                </p>
              </div>
            </div>

            {/* 邮件过滤统计 */}
            <div className="flex items-center space-x-4">
              <div className="flex-shrink-0">
                <div className="p-3 bg-indigo-100 rounded-full">
                  <FunnelIcon className="h-6 w-6 text-indigo-600" />
                </div>
              </div>
              <div>
                <p className="text-sm text-gray-600">智能过滤</p>
                <p className="text-2xl font-semibold text-gray-900">
                  <span className="text-3xl font-bold text-indigo-600">
                    {stats.emailsFiltered}
                  </span>
                  <span className="text-lg text-gray-500">
                    /{stats.totalEmails}
                  </span>
                  <span className="ml-1 text-lg">封邮件</span>
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* 刷新按钮 */}
        <div className="flex-shrink-0 ml-6">
          <button
            onClick={onRefresh}
            disabled={isRefreshing}
            className={`
              inline-flex items-center px-4 py-2 border border-transparent 
              text-sm font-medium rounded-md shadow-sm text-white 
              ${isRefreshing 
                ? 'bg-gray-400 cursor-not-allowed' 
                : 'bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500'
              }
              transition-colors duration-200
            `}
          >
            {isRefreshing ? (
              <>
                <div 
                  data-testid="loading-spinner"
                  className="animate-spin h-4 w-4 mr-2 border-2 border-white border-t-transparent rounded-full"
                />
                刷新中...
              </>
            ) : (
              <>
                <ArrowPathIcon className="h-4 w-4 mr-2" />
                刷新日报
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};

export default ValueStats;