/**
 * Axios Type Extensions
 * 扩展Axios类型定义
 */

import 'axios';

declare module 'axios' {
  interface InternalAxiosRequestConfig {
    metadata?: {
      startTime: Date;
    };
  }
}