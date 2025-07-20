// 调试辅助函数 - 用于发送日志到后端
import { errorCollector } from './errorCollector';
import axios from 'axios';

export const sendLogsToBackend = async () => {
  // 只在开发环境执行
  if (process.env.NODE_ENV !== 'development') {
    return;
  }

  try {
    // 使用 errorCollector 的新方法
    return await errorCollector.sendAllErrors();
  } catch (error) {
    console.error('Failed to send logs to backend:', error);
    return null;
  }
};

// 可以在控制台手动调用的全局函数
if (process.env.NODE_ENV === 'development') {
  (window as any).debugLogs = {
    send: sendLogsToBackend,
    clear: () => errorCollector.clearErrors(),
    get: () => errorCollector.getAllErrors(),
    setAutoSend: (enabled: boolean) => errorCollector.setAutoSendEnabled(enabled)
  };
  
  // 在控制台输出使用提示
  console.log('%c[Debug Tools Ready]', 'color: #4CAF50; font-weight: bold');
  console.log('Available commands:');
  console.log('- window.debugLogs.get()           // View frontend errors');
  console.log('- window.debugLogs.send()          // Send logs to backend manually');
  console.log('- window.debugLogs.clear()         // Clear error logs');
  console.log('- window.debugLogs.setAutoSend()   // Enable/disable auto-send');
  console.log('');
  console.log('%c[Auto-send is ON]', 'color: #2196F3');
  console.log('- Severe errors are sent immediately');
  console.log('- Normal errors are sent every 30 seconds');
}