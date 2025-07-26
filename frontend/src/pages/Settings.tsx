/**
 * Settings Page
 * 设置页面 - 日报时间设置
 */

import React, { useState, useEffect } from 'react';
import { showToast } from '../utils/toast';
import { useSyncTrigger } from '../hooks/useSyncTrigger';
import { useDecoupledSync } from '../hooks/useDecoupledSync';

const Settings: React.FC = () => {
  const [loadingSettings, setLoadingSettings] = useState(true);
  const [useDecoupledMode, setUseDecoupledMode] = useState(true); // 控制使用新架构还是旧架构

  // 旧的同步状态（保持兼容性）
  const { isSyncing, lastSyncResult, error: syncError, syncToday, syncWeek, syncMonth, clearError, clearResult } = useSyncTrigger();
  
  // 新的解耦同步状态
  const { 
    latestEmailInfo, 
    loading: emailTimeLoading, 
    requesting, 
    error: decoupledError,
    requestSync,
    refreshLatestEmailTime,
    clearError: clearDecoupledError,
    formatLatestEmailTime,
    hasEmailData
  } = useDecoupledSync();

  // 加载当前设置
  useEffect(() => {
    const loadSettings = async () => {
      try {
        setLoadingSettings(true);
        // 暂时没有需要加载的设置
      } catch (err) {
        console.error('Failed to load settings:', err);
      } finally {
        setLoadingSettings(false);
      }
    };

    loadSettings();
  }, []);

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

  // 解耦架构的同步处理函数
  const handleDecoupledSync = async (syncType: 'today' | 'week' | 'month') => {
    try {
      const message = await requestSync(syncType);
      showToast(message, 'success');
    } catch (error) {
      console.error(`Decoupled ${syncType} sync failed:`, error);
      showToast(`请求${syncType === 'today' ? '今天' : syncType === 'week' ? '本周' : '本月'}同步失败，请重试`, 'error');
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
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-900">邮件同步</h2>
            <div className="flex items-center space-x-2">
              <span className="text-sm text-gray-600">架构模式:</span>
              <button
                onClick={() => setUseDecoupledMode(!useDecoupledMode)}
                className={`px-3 py-1 text-xs rounded-full transition-colors ${
                  useDecoupledMode 
                    ? 'bg-green-100 text-green-800' 
                    : 'bg-blue-100 text-blue-800'
                }`}
              >
                {useDecoupledMode ? '解耦模式' : '传统模式'}
              </button>
            </div>
          </div>
          <p className="text-gray-600 mb-4">
            {useDecoupledMode 
              ? '解耦架构：查看最新邮件时间，非阻塞同步请求' 
              : '传统架构：等待同步完成，可能会超时'
            }
          </p>
          
          <div className="space-y-4">
            {useDecoupledMode ? (
              // 解耦架构UI
              <>
                {/* 最新邮件时间显示 */}
                <div className="bg-blue-50 border border-blue-200 rounded-md p-4">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-blue-900">最后同步邮件时间</span>
                    <button
                      onClick={refreshLatestEmailTime}
                      disabled={emailTimeLoading}
                      className="text-blue-600 hover:text-blue-800 text-sm underline"
                    >
                      {emailTimeLoading ? '刷新中...' : '刷新'}
                    </button>
                  </div>
                  {emailTimeLoading ? (
                    <div className="text-sm text-blue-600 mt-2">加载中...</div>
                  ) : hasEmailData ? (
                    <div className="mt-2">
                      <div className="text-lg font-semibold text-blue-900">
                        {formatLatestEmailTime(latestEmailInfo)}
                      </div>
                      {latestEmailInfo?.latest_email_subject && (
                        <div className="text-sm text-blue-700 mt-1">
                          最新邮件: {latestEmailInfo.latest_email_subject}
                        </div>
                      )}
                      {latestEmailInfo?.latest_email_sender && (
                        <div className="text-xs text-blue-600 mt-1">
                          发件人: {latestEmailInfo.latest_email_sender}
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="text-sm text-blue-600 mt-2">
                      {latestEmailInfo?.message || '暂无邮件数据'}
                    </div>
                  )}
                </div>

                {/* 解耦模式同步按钮 */}
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  <button
                    onClick={() => handleDecoupledSync('today')}
                    disabled={requesting}
                    className={`px-4 py-3 rounded-md text-white font-medium transition-colors ${
                      requesting
                        ? 'bg-gray-400 cursor-not-allowed'
                        : 'bg-blue-600 hover:bg-blue-700'
                    }`}
                  >
                    {requesting ? '请求中...' : '请求同步今天'}
                  </button>
                  
                  <button
                    onClick={() => handleDecoupledSync('week')}
                    disabled={requesting}
                    className={`px-4 py-3 rounded-md font-medium transition-colors ${
                      requesting
                        ? 'bg-gray-400 text-white cursor-not-allowed'
                        : 'bg-green-600 text-white hover:bg-green-700'
                    }`}
                  >
                    {requesting ? '请求中...' : '请求同步本周'}
                  </button>
                  
                  <button
                    onClick={() => handleDecoupledSync('month')}
                    disabled={requesting}
                    className={`px-4 py-3 rounded-md font-medium transition-colors ${
                      requesting
                        ? 'bg-gray-400 text-white cursor-not-allowed'
                        : 'bg-orange-600 text-white hover:bg-orange-700'
                    }`}
                  >
                    {requesting ? '请求中...' : '请求同步本月'}
                  </button>
                </div>

                {/* 解耦模式说明 */}
                <div className="bg-yellow-50 border border-yellow-200 rounded-md p-3">
                  <p className="text-xs text-yellow-800">
                    💡 <strong>解耦模式说明：</strong>
                    点击按钮后会立即收到确认，同步在后台进行。请稍等1-2分钟后点击"刷新"按钮查看最新邮件时间的更新。
                  </p>
                </div>

                {/* 解耦模式错误显示 */}
                {decoupledError && (
                  <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-md">
                    <p className="text-sm text-red-700">{decoupledError}</p>
                    <button
                      onClick={clearDecoupledError}
                      className="text-xs text-red-600 hover:text-red-800 mt-1 underline"
                    >
                      清除
                    </button>
                  </div>
                )}
              </>
            ) : (
              // 传统架构UI（原有的）
              <>
                {/* 同步状态显示 */}
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-gray-700">同步状态</span>
                  <span className="text-sm text-gray-600">传统同步模式</span>
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
            
                {/* 传统模式说明文字 */}
                <p className="text-xs text-gray-500">
                  点击按钮同步相应时间范围的邮件。同步可能需要10-30秒时间，请耐心等待。
                </p>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Settings;