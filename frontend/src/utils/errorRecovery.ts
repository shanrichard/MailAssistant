/**
 * 错误恢复管理器
 * 提供智能重试和错误恢复功能
 */

export interface RetryConfig {
  maxAttempts: number;
  baseDelay: number;
  maxDelay: number;
  exponentialBase?: number;
}

export interface RetryTask {
  id: string;
  operation: () => Promise<any>;
  attempt: number;
  lastError?: any;
  createdAt: Date;
}

export interface ErrorEvent {
  type: 'error' | 'agent_error';
  error: string;
  error_code?: string;
  retryable?: boolean;
  timestamp: string;
  details?: Record<string, any>;
}

export class ErrorRecoveryManager {
  private retryQueue: Map<string, RetryTask> = new Map();
  private defaultConfig: RetryConfig = {
    maxAttempts: 3,
    baseDelay: 1000,
    maxDelay: 5000,
    exponentialBase: 2
  };
  
  /**
   * 执行操作，带自动重试
   */
  async executeWithRetry<T>(
    taskId: string,
    operation: () => Promise<T>,
    config?: Partial<RetryConfig>,
    callbacks?: {
      onRetry?: (attempt: number, delay: number) => void;
      onError?: (error: any) => void;
      onSuccess?: (result: T) => void;
    }
  ): Promise<T> {
    const retryConfig = { ...this.defaultConfig, ...config };
    let lastError: any = null;
    
    // 创建重试任务
    const task: RetryTask = {
      id: taskId,
      operation,
      attempt: 0,
      createdAt: new Date()
    };
    
    this.retryQueue.set(taskId, task);
    
    try {
      for (let attempt = 0; attempt < retryConfig.maxAttempts; attempt++) {
        task.attempt = attempt + 1;
        
        try {
          const result = await operation();
          
          // 成功，清理任务
          this.retryQueue.delete(taskId);
          callbacks?.onSuccess?.(result);
          
          // 如果是重试成功，记录日志
          if (attempt > 0) {
            console.log(`Retry succeeded for task ${taskId} on attempt ${attempt + 1}`);
          }
          
          return result;
        } catch (error) {
          lastError = error;
          task.lastError = error;
          
          // 检查是否可重试
          if (!this.isRetryable(error) || attempt >= retryConfig.maxAttempts - 1) {
            break;
          }
          
          // 计算延迟时间（指数退避）
          const delay = this.calculateDelay(attempt, retryConfig);
          
          // 通知重试回调
          callbacks?.onRetry?.(attempt + 1, delay);
          
          console.warn(
            `Retrying task ${taskId}, attempt ${attempt + 1}/${retryConfig.maxAttempts} after ${delay}ms`,
            error
          );
          
          // 等待延迟
          await this.delay(delay);
        }
      }
      
      // 所有重试都失败
      this.retryQueue.delete(taskId);
      callbacks?.onError?.(lastError);
      
      throw lastError;
    } catch (error) {
      // 确保任务被清理
      this.retryQueue.delete(taskId);
      throw error;
    }
  }
  
  /**
   * 检查错误是否可重试
   */
  private isRetryable(error: any): boolean {
    // 检查错误对象的 retryable 标志
    if (error?.retryable === true) return true;
    
    // 检查错误代码
    if (error?.error_code) {
      const retryableCodes = ['temporary', 'network', 'database'];
      return retryableCodes.includes(error.error_code);
    }
    
    // 检查网络错误
    if (error?.code === 'ECONNABORTED' || error?.code === 'ECONNRESET') {
      return true;
    }
    
    // 检查 HTTP 状态码
    if (error?.response?.status) {
      const status = error.response.status;
      // 5xx 错误和某些 4xx 错误可重试
      return status >= 500 || status === 429 || status === 408;
    }
    
    return false;
  }
  
  /**
   * 计算重试延迟时间（指数退避）
   */
  private calculateDelay(attempt: number, config: RetryConfig): number {
    const base = config.exponentialBase || 2;
    const delay = Math.min(
      config.baseDelay * Math.pow(base, attempt),
      config.maxDelay
    );
    
    // 添加随机抖动（±10%），避免同时重试
    const jitter = delay * 0.1 * (2 * Math.random() - 1);
    return Math.max(0, Math.floor(delay + jitter));
  }
  
  /**
   * 延迟函数
   */
  private delay(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
  
  /**
   * 获取当前重试队列状态
   */
  getRetryQueueStatus(): {
    size: number;
    tasks: Array<{
      id: string;
      attempt: number;
      createdAt: Date;
      lastError?: any;
    }>;
  } {
    const tasks = Array.from(this.retryQueue.values()).map(task => ({
      id: task.id,
      attempt: task.attempt,
      createdAt: task.createdAt,
      lastError: task.lastError
    }));
    
    return {
      size: this.retryQueue.size,
      tasks
    };
  }
  
  /**
   * 取消特定任务的重试
   */
  cancelRetry(taskId: string): boolean {
    return this.retryQueue.delete(taskId);
  }
  
  /**
   * 清空所有重试任务
   */
  clearRetryQueue(): void {
    this.retryQueue.clear();
  }
}

// 创建全局实例
export const errorRecoveryManager = new ErrorRecoveryManager();

// 导出便捷函数
export async function withRetry<T>(
  operation: () => Promise<T>,
  options?: {
    taskId?: string;
    config?: Partial<RetryConfig>;
    onRetry?: (attempt: number, delay: number) => void;
    onError?: (error: any) => void;
  }
): Promise<T> {
  const taskId = options?.taskId || `task_${Date.now()}`;
  
  return errorRecoveryManager.executeWithRetry(
    taskId,
    operation,
    options?.config,
    {
      onRetry: options?.onRetry,
      onError: options?.onError
    }
  );
}