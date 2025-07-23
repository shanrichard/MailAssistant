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
import { useSyncStore } from '../stores/syncStore';
import { ArrowPathIcon, CheckCircleIcon, ExclamationCircleIcon } from '@heroicons/react/24/outline';

const Settings: React.FC = () => {
  const [reportTime, setReportTime] = useState<string>('09:00');
  const [timezone, setTimezone] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [loadingSettings, setLoadingSettings] = useState(true);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 同步相关状态
  const { triggerSync, syncStatus, syncStats, progress, isSyncing, hasError } = useSyncTrigger();
  const { lastSyncTime, errorMessage } = useSyncStore();

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
        
        // 获取用户的调度设置
        const schedule = await schedulerService.getSchedule();
        if (schedule && schedule.daily_report_time) {
          setReportTime(schedule.daily_report_time);
        }
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
      await schedulerService.updateSchedule({
        time: reportTime,
        timezone: timezone
      });
      
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

  // 手动同步邮件
  const handleManualSync = async () => {
    try {
      await triggerSync(true); // 智能同步，使用后台模式避免超时
      showToast('邮件同步已开始', 'success');
    } catch (error) {
      console.error('Manual sync failed:', error);
      showToast('同步启动失败，请重试', 'error');
    }
  };

  // 强制全量同步
  const handleFullSync = async () => {
    try {
      await triggerSync(true); // 强制全量同步
      showToast('全量同步已开始', 'success');
    } catch (error) {
      console.error('Full sync failed:', error);
      showToast('全量同步启动失败，请重试', 'error');
    }
  };

  // 同步状态组件
  const SyncStatusBadge: React.FC<{ status: string }> = ({ status }) => {
    switch (status) {
      case 'syncing':
        return (
          <div className="flex items-center space-x-1 text-blue-600">
            <ArrowPathIcon className="h-4 w-4 animate-spin" />
            <span className="text-sm">同步中 ({progress}%)</span>
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
              <SyncStatusBadge status={syncStatus} />
            </div>
            
            {/* 最后同步时间 */}
            {lastSyncTime && (
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-gray-700">最后同步</span>
                <span className="text-sm text-gray-600">
                  {format(lastSyncTime, 'yyyy年MM月dd日 HH:mm:ss', { locale: zhCN })}
                </span>
              </div>
            )}
            
            {/* 同步统计 */}
            {syncStats && (
              <div className="bg-gray-50 p-3 rounded-md">
                <div className="text-sm text-gray-600">
                  新邮件: {syncStats.new}，更新: {syncStats.updated}，错误: {syncStats.errors}
                </div>
              </div>
            )}
            
            {/* 错误信息 */}
            {hasError && errorMessage && (
              <div className="bg-red-50 border border-red-200 rounded-md p-3">
                <p className="text-sm text-red-600">{errorMessage}</p>
              </div>
            )}
            
            {/* 操作按钮 */}
            <div className="flex space-x-3">
              <button
                onClick={handleManualSync}
                disabled={isSyncing}
                className={`px-4 py-2 rounded-md text-white font-medium transition-colors ${
                  isSyncing
                    ? 'bg-gray-400 cursor-not-allowed'
                    : 'bg-blue-600 hover:bg-blue-700'
                }`}
              >
                {isSyncing ? '同步中...' : '立即同步'}
              </button>
              
              <button
                onClick={handleFullSync}
                disabled={isSyncing}
                className={`px-4 py-2 rounded-md border border-gray-300 text-gray-700 font-medium transition-colors ${
                  isSyncing
                    ? 'bg-gray-100 cursor-not-allowed'
                    : 'bg-white hover:bg-gray-50'
                }`}
              >
                完整重新同步
              </button>
            </div>
            
            {/* 说明文字 */}
            <p className="text-xs text-gray-500">
              "立即同步"会智能判断进行增量或全量同步；"完整重新同步"会重新同步最近30天的所有邮件。
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