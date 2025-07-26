// 前端错误收集器 - 仅用于开发环境调试
import axios from 'axios';
import { CONFIG } from '../config';

class ErrorCollector {
  private readonly STORAGE_KEY = 'mailassistant_frontend_errors';
  private readonly MAX_ERRORS = 100;
  private readonly BATCH_INTERVAL = 30000; // 30秒
  private readonly MAX_RETRY_ATTEMPTS = 3;
  private isEnabled: boolean;
  private autoSendQueue: ErrorLog[] = [];
  private sendTimer: NodeJS.Timeout | null = null;
  private retryCount: Map<string, number> = new Map();
  private isAutoSendEnabled: boolean = true; // 可通过配置控制

  constructor() {
    // 只在开发环境启用
    this.isEnabled = process.env.NODE_ENV === 'development';
    console.log('[ErrorCollector] Initializing...', {
      NODE_ENV: process.env.NODE_ENV,
      isEnabled: this.isEnabled
    });
    if (this.isEnabled) {
      this.setupErrorHandlers();
      this.startAutoSend();
      console.log('[ErrorCollector] Error handlers setup complete');
    }
  }

  private setupErrorHandlers() {
    // 拦截 console.error
    const originalError = console.error;
    console.error = (...args: any[]) => {
      this.logError({
        type: 'console.error',
        message: args.map(arg => 
          typeof arg === 'object' ? JSON.stringify(arg) : String(arg)
        ).join(' '),
        timestamp: new Date().toISOString(),
        url: window.location.href
      });
      originalError.apply(console, args);
    };

    // 捕获未处理的 Promise rejection
    window.addEventListener('unhandledrejection', (event) => {
      this.logError({
        type: 'unhandledRejection',
        message: event.reason?.message || String(event.reason),
        stack: event.reason?.stack,
        timestamp: new Date().toISOString(),
        url: window.location.href
      });
    });
  }

  private logError(error: ErrorLog) {
    if (!this.isEnabled) return;

    try {
      // 获取现有错误
      const existingErrors = this.getErrors();
      
      // 添加新错误到开头
      existingErrors.unshift(error);
      
      // 保留最近的 MAX_ERRORS 条
      const errorsToSave = existingErrors.slice(0, this.MAX_ERRORS);
      
      // 存储到 localStorage
      localStorage.setItem(this.STORAGE_KEY, JSON.stringify(errorsToSave));
      
      // 触发自动发送
      if (this.isAutoSendEnabled) {
        this.scheduleAutoSend(error);
      }
    } catch (e) {
      // localStorage 可能已满，忽略错误
    }
  }

  private getErrors(): ErrorLog[] {
    try {
      const stored = localStorage.getItem(this.STORAGE_KEY);
      return stored ? JSON.parse(stored) : [];
    } catch {
      return [];
    }
  }

  // 供测试使用的公共方法
  public clearErrors() {
    localStorage.removeItem(this.STORAGE_KEY);
  }

  public getAllErrors(): ErrorLog[] {
    return this.getErrors();
  }

  // 自动发送相关方法
  private startAutoSend() {
    // 页面卸载时发送剩余错误
    window.addEventListener('beforeunload', () => {
      if (this.autoSendQueue.length > 0) {
        this.sendBatch(this.autoSendQueue);
      }
    });
  }

  private scheduleAutoSend(error: ErrorLog) {
    if (error.type === 'unhandledRejection') {
      // 严重错误立即发送
      this.sendImmediately([error]);
    } else {
      // 普通错误加入队列
      this.autoSendQueue.push(error);
      this.scheduleBatchSend();
    }
  }

  private scheduleBatchSend() {
    // 如果已有定时器，不重复创建
    if (this.sendTimer) return;

    this.sendTimer = setTimeout(() => {
      if (this.autoSendQueue.length > 0) {
        const errors = this.deduplicateErrors(this.autoSendQueue);
        this.sendBatch(errors);
        this.autoSendQueue = [];
      }
      this.sendTimer = null;
    }, this.BATCH_INTERVAL);
  }

  private deduplicateErrors(errors: ErrorLog[]): ErrorLog[] {
    const seen = new Set<string>();
    return errors.filter(error => {
      const key = `${error.type}:${error.message}`;
      if (seen.has(key)) {
        return false;
      }
      seen.add(key);
      return true;
    });
  }

  private async sendImmediately(errors: ErrorLog[]) {
    try {
      await this.sendToBackend(errors);
      // 发送成功后从 localStorage 中移除
      this.removeErrorsFromStorage(errors);
    } catch (error) {
      // 发送失败，加入批量队列稍后重试
      this.autoSendQueue.push(...errors);
      this.scheduleBatchSend();
    }
  }

  private async sendBatch(errors: ErrorLog[]) {
    try {
      await this.sendToBackend(errors);
      // 发送成功后从 localStorage 中移除
      this.removeErrorsFromStorage(errors);
      // 清除重试计数
      errors.forEach(error => {
        const key = `${error.type}:${error.message}`;
        this.retryCount.delete(key);
      });
    } catch (error) {
      // 重试逻辑
      this.handleSendFailure(errors);
    }
  }

  private async sendToBackend(errors: ErrorLog[]) {
    const response = await axios.post(`${CONFIG.apiBaseUrl}/api/debug/logs/all`, {
      frontend_errors: errors
    }, {
      timeout: 5000 // 5秒超时
    });
    return response.data;
  }

  private removeErrorsFromStorage(sentErrors: ErrorLog[]) {
    const allErrors = this.getErrors();
    const sentTimestamps = new Set(sentErrors.map(e => e.timestamp));
    const remainingErrors = allErrors.filter(e => !sentTimestamps.has(e.timestamp));
    localStorage.setItem(this.STORAGE_KEY, JSON.stringify(remainingErrors));
  }

  private handleSendFailure(errors: ErrorLog[]) {
    errors.forEach(error => {
      const key = `${error.type}:${error.message}`;
      const retries = this.retryCount.get(key) || 0;
      
      if (retries < this.MAX_RETRY_ATTEMPTS) {
        this.retryCount.set(key, retries + 1);
        // 使用指数退避，延迟重试
        const delay = Math.pow(2, retries) * 1000; // 1s, 2s, 4s
        setTimeout(() => {
          this.autoSendQueue.push(error);
          this.scheduleBatchSend();
        }, delay);
      } else {
        // 超过最大重试次数，放弃
        console.warn('[ErrorCollector] Failed to send error after max retries:', error);
        this.retryCount.delete(key);
      }
    });
  }

  // 公共方法：手动发送所有错误
  public async sendAllErrors(): Promise<any> {
    const errors = this.getAllErrors();
    if (errors.length === 0) return null;
    
    try {
      const result = await this.sendToBackend(errors);
      // 发送成功后清空 localStorage
      this.clearErrors();
      return result;
    } catch (error) {
      console.error('[ErrorCollector] Failed to send errors manually:', error);
      throw error;
    }
  }

  // 控制自动发送的开关
  public setAutoSendEnabled(enabled: boolean) {
    this.isAutoSendEnabled = enabled;
    if (!enabled && this.sendTimer) {
      clearTimeout(this.sendTimer);
      this.sendTimer = null;
    }
  }
}

// 错误日志类型定义
interface ErrorLog {
  type: 'console.error' | 'unhandledRejection';
  message: string;
  stack?: string;
  timestamp: string;
  url: string;
}

// 导出单例
export const errorCollector = new ErrorCollector();