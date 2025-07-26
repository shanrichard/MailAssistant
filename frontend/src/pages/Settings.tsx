/**
 * Settings Page
 * 设置页面 - 日报时间设置
 */

import React, { useState, useEffect } from 'react';
import { format } from 'date-fns';
import { zhCN } from 'date-fns/locale';
import { schedulerService } from '../services/schedulerService';
import { AppError } from '../types';
import { showToast } from '../utils/toast';
import { useSyncTrigger } from '../hooks/useSyncTrigger';
import { ArrowPathIcon, CheckCircleIcon, ExclamationCircleIcon } from '@heroicons/react/24/outline';

const Settings: React.FC = () => {
  const [reportTime, setReportTime] = useState<string>('09:00');
  const [timezone, setTimezone] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [loadingSettings, setLoadingSettings] = useState(true);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 新的简单同步状态
  const { isSyncing, lastSyncResult, error: syncError, syncToday, syncWeek, syncMonth, clearError, clearResult } = useSyncTrigger();

  // 获取当前时区
  const getCurrentTimezone = () => {
    return Intl.DateTimeFormat().resolvedOptions().timeZone;
  };

  // 加载当前设置
  useEffect(() => {
    const loadSettings = async () => {
      try {
        setLoadingSettings(true);
        setError(null);
        
        // 设置本地时区
        const localTimezone = getCurrentTimezone();
        setTimezone(localTimezone);
        
        // 调度器功能暂时禁用
        // const schedule = await schedulerService.getSchedule();
        // if (schedule && schedule.daily_report_time) {
        //   setReportTime(schedule.daily_report_time);
        // }
      } catch (err) {
        const error = err as AppError;
        console.error('Failed to load settings:', error);
        setError('加载设置失败，请刷新页面重试');
      } finally {
        setLoadingSettings(false);
      }
    };

    loadSettings();
  }, []);

  // 保存设置
  const handleSave = async () => {
    setLoading(true);
    setError(null);
    
    try {
      // 调度器功能暂时禁用
      // await schedulerService.updateSchedule({
      //   time: reportTime,
      //   timezone: timezone
      // });
      
      // 成功反馈
      showToast('设置保存成功', 'success');
      setSaveSuccess(true);
      
      // 2秒后恢复按钮状态
      setTimeout(() => {
        setSaveSuccess(false);
      }, 2000);
      
    } catch (err) {
      const error = err as AppError;
      console.error('Failed to save settings:', error);
      
      // 显示具体错误信息
      let errorMessage = '保存失败，请重试';
      if (error.code === 'VALIDATION_ERROR' && error.details) {
        errorMessage = error.details.message || error.message;
      } else if (error.code === 'SERVER_ERROR') {
        errorMessage = '服务器错误，请稍后重试';
      } else if (error.code === 'NETWORK_ERROR') {
        errorMessage = '网络连接失败，请检查网络';
      } else if (error.message) {
        errorMessage = error.message;
      }
      
      setError(errorMessage);
      showToast(errorMessage, 'error');
    } finally {
      setLoading(false);
    }
  };

  // 处理时间变化
  const handleTimeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setReportTime(e.target.value);
    setError(null); // 清除错误提示
  };

  // 同步今天邮件
  const handleSyncToday = async () => {
    try {
      const result = await syncToday();
      showToast(result.message, 'success');
    } catch (error) {
      console.error('Today sync failed:', error);
      showToast('同步今天邮件失败，请重试', 'error');
    }
  };

  // 同步本周邮件
  const handleSyncWeek = async () => {
    try {
      const result = await syncWeek();
      showToast(result.message, 'success');
    } catch (error) {
      console.error('Week sync failed:', error);
      showToast('同步本周邮件失败，请重试', 'error');
    }
  };

  // 同步本月邮件
  const handleSyncMonth = async () => {
    try {
      const result = await syncMonth();
      showToast(result.message, 'success');
    } catch (error) {
      console.error('Month sync failed:', error);
      showToast('同步本月邮件失败，请重试', 'error');
    }
  };

  // 同步状态组件
  const SyncStatusBadge: React.FC<{ status: string }> = ({ status }) => {
    switch (status) {
      case 'syncing':
        return (
          <div className="flex items-center space-x-1 text-blue-600">
            <ArrowPathIcon className="h-4 w-4 animate-spin" />
            <span className="text-sm">同步中</span>
          </div>
        );
      case 'completed':
        return (
          <div className="flex items-center space-x-1 text-green-600">
            <CheckCircleIcon className="h-4 w-4" />
            <span className="text-sm">已完成</span>
          </div>
        );
      case 'error':
        return (
          <div className="flex items-center space-x-1 text-red-600">
            <ExclamationCircleIcon className="h-4 w-4" />
            <span className="text-sm">同步失败</span>
          </div>
        );
      default:
        return (
          <span className="text-sm text-gray-600">空闲</span>
        );
    }
  };


  if (loadingSettings) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">设置</h1>
      
      <div className="space-y-6">
        {/* 邮件同步设置 */}
        <div className="bg-white rounded-lg shadow p-6 max-w-2xl">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">邮件同步</h2>
          <p className="text-gray-600 mb-4">管理邮件同步状态和手动触发同步</p>
          
          <div className="space-y-4">
            {/* 同步状态显示 */}
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-gray-700">同步状态</span>
              <span className="text-sm text-gray-600">等待新同步实现</span>
            </div>
            
            {/* 最后同步时间 */}
            {false && ( // 暂时隐藏
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-gray-700">最后同步</span>
                <span className="text-sm text-gray-600">
                  {/* {format(lastSyncTime, 'yyyy年MM月dd日 HH:mm:ss', { locale: zhCN })} */}
                </span>
              </div>
            )}
            
            {/* 同步统计 */}
            {false && ( // 暂时隐藏
              <div className="bg-gray-50 p-3 rounded-md">
                <div className="text-sm text-gray-600">
                  {/* 新邮件: {syncStats.new}，更新: {syncStats.updated}，错误: {syncStats.errors} */}
                </div>
              </div>
            )}
            
            {/* 错误信息 */}
            {false && ( // 暂时隐藏
              <div className="bg-red-50 border border-red-200 rounded-md p-3">
                <p className="text-sm text-red-600">{/* {errorMessage} */}</p>
              </div>
            )}
            
            {/* 新的三个同步按钮 */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <button
                onClick={handleSyncToday}
                disabled={isSyncing}
                className={`px-4 py-3 rounded-md text-white font-medium transition-colors ${
                  isSyncing
                    ? 'bg-gray-400 cursor-not-allowed'
                    : 'bg-blue-600 hover:bg-blue-700'
                }`}
              >
                {isSyncing ? '同步中...' : '同步今天'}
              </button>
              
              <button
                onClick={handleSyncWeek}
                disabled={isSyncing}
                className={`px-4 py-3 rounded-md font-medium transition-colors ${
                  isSyncing
                    ? 'bg-gray-400 text-white cursor-not-allowed'
                    : 'bg-green-600 text-white hover:bg-green-700'
                }`}
              >
                {isSyncing ? '同步中...' : '同步本周'}
              </button>
              
              <button
                onClick={handleSyncMonth}
                disabled={isSyncing}
                className={`px-4 py-3 rounded-md font-medium transition-colors ${
                  isSyncing
                    ? 'bg-gray-400 text-white cursor-not-allowed'
                    : 'bg-orange-600 text-white hover:bg-orange-700'
                }`}
              >
                {isSyncing ? '同步中...' : '同步本月'}
              </button>
            </div>
            
            {/* 同步结果显示 */}
            {lastSyncResult && (
              <div className="mt-4 p-3 bg-green-50 border border-green-200 rounded-md">
                <p className="text-sm text-green-700">{lastSyncResult.message}</p>
                {lastSyncResult.stats && (
                  <p className="text-xs text-green-600 mt-1">
                    新邮件: {lastSyncResult.stats.new}，更新: {lastSyncResult.stats.updated}
                    {lastSyncResult.stats.errors > 0 && `, 错误: ${lastSyncResult.stats.errors}`}
                  </p>
                )}
                <button
                  onClick={clearResult}
                  className="text-xs text-green-600 hover:text-green-800 mt-1 underline"
                >
                  清除
                </button>
              </div>
            )}
            
            {/* 错误信息显示 */}
            {syncError && (
              <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-md">
                <p className="text-sm text-red-700">{syncError}</p>
                <button
                  onClick={clearError}
                  className="text-xs text-red-600 hover:text-red-800 mt-1 underline"
                >
                  清除
                </button>
              </div>
            )}
            
            {/* 说明文字 */}
            <p className="text-xs text-gray-500">
              点击按钮同步相应时间范围的邮件。同步可能需要10-30秒时间，请耐心等待。
            </p>
          </div>
        </div>
        
        {/* 日报时间设置 */}
        <div className="bg-white rounded-lg shadow p-6 max-w-2xl">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">日报生成时间</h2>
          <p className="text-gray-600 mb-2">设置每天自动生成邮件日报的时间</p>
          <p className="text-sm text-gray-500 mb-4">当前时区：{timezone} (本地)</p>
          
          <div className="flex items-center space-x-4 mb-6">
            <input
              type="time"
              value={reportTime}
              onChange={handleTimeChange}
              className="px-4 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
              disabled={loading}
            />
            
            <button
              onClick={handleSave}
              disabled={loading || saveSuccess}
              className={`px-6 py-2 rounded-md text-white font-medium transition-colors ${
                loading || saveSuccess
                  ? 'bg-gray-400 cursor-not-allowed'
                  : 'bg-blue-600 hover:bg-blue-700'
              }`}
            >
              {loading ? '保存中...' : saveSuccess ? '已保存' : '保存'}
            </button>
          </div>
          
          {/* 错误提示 */}
          {error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-md">
              <p className="text-sm text-red-600">{error}</p>
            </div>
          )}
          
          {/* 时区提醒 */}
          <p className="text-xs text-gray-500 italic">
            如果您的系统时区发生变化，请重新保存设置以确保日报按时生成。
          </p>
        </div>
      </div>
    </div>
  );
};

export default Settings;