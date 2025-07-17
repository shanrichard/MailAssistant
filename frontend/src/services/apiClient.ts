/**
 * API Client
 * 统一的API请求客户端
 */

import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios';
import { AppError } from '../types';
import { appConfig, ERROR_MESSAGES } from '../config';

class ApiClient {
  private client: AxiosInstance;
  private static instance: ApiClient;

  private constructor() {
    this.client = axios.create({
      baseURL: appConfig.apiBaseUrl,
      timeout: appConfig.requestTimeout,
      headers: {
        'Content-Type': 'application/json',
      },
      withCredentials: true,  // 确保跨域请求携带cookies
    });

    this.setupInterceptors();
  }

  static getInstance(): ApiClient {
    if (!ApiClient.instance) {
      ApiClient.instance = new ApiClient();
    }
    return ApiClient.instance;
  }

  private setupInterceptors(): void {
    // Request interceptor
    this.client.interceptors.request.use(
      (config) => {
        // Add auth token if available
        const token = this.getAuthToken();
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        
        // Add request timestamp
        config.metadata = { startTime: new Date() };
        
        return config;
      },
      (error) => {
        return Promise.reject(this.handleError(error));
      }
    );

    // Response interceptor
    this.client.interceptors.response.use(
      (response: AxiosResponse) => {
        // Log response time in development
        if (appConfig.enableDebug) {
          const startTime = response.config.metadata?.startTime;
          if (startTime) {
            const duration = new Date().getTime() - startTime.getTime();
            console.log(`API ${response.config.method?.toUpperCase()} ${response.config.url}: ${duration}ms`);
          }
        }
        
        return response;
      },
      async (error) => {
        const originalRequest = error.config;

        // Handle 401 errors (token expired)
        if (error.response?.status === 401 && !originalRequest._retry) {
          originalRequest._retry = true;
          
          try {
            await this.refreshToken();
            const token = this.getAuthToken();
            if (token) {
              originalRequest.headers.Authorization = `Bearer ${token}`;
              return this.client(originalRequest);
            }
          } catch (refreshError) {
            // Refresh failed, redirect to login
            this.handleAuthFailure();
            return Promise.reject(this.handleError(refreshError));
          }
        }

        return Promise.reject(this.handleError(error));
      }
    );
  }

  private getAuthToken(): string | null {
    try {
      const authData = localStorage.getItem('mailassistant_auth_token');
      if (authData) {
        const parsed = JSON.parse(authData);
        return parsed.state?.token || null;
      }
      return null;
    } catch {
      return null;
    }
  }

  private async refreshToken(): Promise<string> {
    try {
      const response = await this.client.post('/auth/refresh');
      const { token } = response.data;
      
      // Update stored token
      const authData = localStorage.getItem('mailassistant_auth_token');
      if (authData) {
        const parsed = JSON.parse(authData);
        parsed.state.token = token;
        localStorage.setItem('mailassistant_auth_token', JSON.stringify(parsed));
      }
      
      return token;
    } catch (error) {
      throw new Error('Token refresh failed');
    }
  }

  private handleAuthFailure(): void {
    // Clear auth data
    localStorage.removeItem('mailassistant_auth_token');
    
    // Redirect to login
    window.location.href = '/login';
  }

  private handleError(error: any): AppError {
    if (error.response) {
      // Server responded with error status
      const { status, data } = error.response;
      
      switch (status) {
        case 400:
          // 处理新的详细错误格式
          if (data.detail && typeof data.detail === 'object') {
            return {
              code: 'BAD_REQUEST',
              message: data.detail.message || data.detail.error || ERROR_MESSAGES.INVALID_DATA,
              details: data.detail,
              timestamp: new Date(),
            };
          }
          return {
            code: 'BAD_REQUEST',
            message: data.message || data.detail || ERROR_MESSAGES.INVALID_DATA,
            details: data.details,
            timestamp: new Date(),
          };
        case 401:
          return {
            code: 'UNAUTHORIZED',
            message: data.message || ERROR_MESSAGES.AUTH_FAILED,
            timestamp: new Date(),
          };
        case 403:
          return {
            code: 'FORBIDDEN',
            message: data.message || ERROR_MESSAGES.PERMISSION_DENIED,
            timestamp: new Date(),
          };
        case 404:
          return {
            code: 'NOT_FOUND',
            message: data.message || 'Resource not found',
            timestamp: new Date(),
          };
        case 422:
          return {
            code: 'VALIDATION_ERROR',
            message: data.message || ERROR_MESSAGES.INVALID_DATA,
            details: data.details,
            timestamp: new Date(),
          };
        case 500:
          return {
            code: 'SERVER_ERROR',
            message: data.message || ERROR_MESSAGES.SERVER_ERROR,
            timestamp: new Date(),
          };
        default:
          return {
            code: 'HTTP_ERROR',
            message: data.message || `HTTP ${status} error`,
            timestamp: new Date(),
          };
      }
    } else if (error.request) {
      // Network error
      return {
        code: 'NETWORK_ERROR',
        message: ERROR_MESSAGES.NETWORK_ERROR,
        timestamp: new Date(),
      };
    } else {
      // Request setup error
      return {
        code: 'REQUEST_ERROR',
        message: error.message || 'Request failed',
        timestamp: new Date(),
      };
    }
  }

  // HTTP methods
  async get<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.get(url, config);
    return response.data;
  }

  async post<T>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.post(url, data, config);
    return response.data;
  }

  async put<T>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.put(url, data, config);
    return response.data;
  }

  async patch<T>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.patch(url, data, config);
    return response.data;
  }

  async delete<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.delete(url, config);
    return response.data;
  }

  // Upload files
  async upload<T>(url: string, formData: FormData, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.post(url, formData, {
      ...config,
      headers: {
        ...config?.headers,
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  }

  // Download files
  async download(url: string, config?: AxiosRequestConfig): Promise<Blob> {
    const response = await this.client.get(url, {
      ...config,
      responseType: 'blob',
    });
    return response.data;
  }

  // Get raw axios instance for special use cases
  getRawClient(): AxiosInstance {
    return this.client;
  }
}

// Export singleton instance
export const apiClient = ApiClient.getInstance();
export default apiClient;