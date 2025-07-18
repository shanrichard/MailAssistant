/**
 * Toast Notification Utility
 * 简单的提示信息工具
 */

export type ToastType = 'success' | 'error' | 'info' | 'warning';

interface ToastOptions {
  duration?: number;
  position?: 'top' | 'bottom';
}

class ToastManager {
  private container: HTMLDivElement | null = null;

  private getContainer(): HTMLDivElement {
    if (!this.container) {
      this.container = document.createElement('div');
      this.container.id = 'toast-container';
      this.container.className = 'fixed top-4 right-4 z-50 space-y-2';
      document.body.appendChild(this.container);
    }
    return this.container;
  }

  show(message: string, type: ToastType = 'info', options?: ToastOptions) {
    const container = this.getContainer();
    const toast = document.createElement('div');
    
    // 设置样式
    const baseClasses = 'px-4 py-3 rounded-lg shadow-lg transform transition-all duration-300 max-w-sm';
    const typeClasses = {
      success: 'bg-green-500 text-white',
      error: 'bg-red-500 text-white',
      warning: 'bg-yellow-500 text-white',
      info: 'bg-blue-500 text-white'
    };
    
    toast.className = `${baseClasses} ${typeClasses[type]} translate-x-full`;
    toast.textContent = message;
    
    container.appendChild(toast);
    
    // 动画进入
    setTimeout(() => {
      toast.classList.remove('translate-x-full');
      toast.classList.add('translate-x-0');
    }, 10);
    
    // 自动移除
    const duration = options?.duration || 3000;
    setTimeout(() => {
      toast.classList.add('translate-x-full');
      setTimeout(() => {
        container.removeChild(toast);
        // 如果没有更多toast，移除容器
        if (container.children.length === 0 && this.container) {
          document.body.removeChild(this.container);
          this.container = null;
        }
      }, 300);
    }, duration);
  }
}

// 创建单例
const toastManager = new ToastManager();

// 导出便捷方法
export const showToast = (message: string, type: ToastType = 'info', options?: ToastOptions) => {
  toastManager.show(message, type, options);
};

export const showSuccess = (message: string, options?: ToastOptions) => {
  toastManager.show(message, 'success', options);
};

export const showError = (message: string, options?: ToastOptions) => {
  toastManager.show(message, 'error', options);
};

export const showWarning = (message: string, options?: ToastOptions) => {
  toastManager.show(message, 'warning', options);
};

export const showInfo = (message: string, options?: ToastOptions) => {
  toastManager.show(message, 'info', options);
};