/**
 * Authentication Service
 * 认证相关API服务
 */

import { User, ApiResponse } from '../types';
import { API_ENDPOINTS } from '../config';
import apiClient from './apiClient';

class AuthService {
  /**
   * Google OAuth登录
   */
  async googleLogin(authorizationResponse: string, sessionId: string): Promise<string> {
    try {
      const response = await apiClient.post<{ access_token: string; token_type: string; user: User }>(
        API_ENDPOINTS.AUTH.GOOGLE,
        { authorization_response: authorizationResponse, session_id: sessionId }
      );
      
      return response.access_token;
    } catch (error: any) {
      console.error('Google login failed:', error);
      
      // 从axios错误中提取信息
      let errorMessage = 'Authentication failed';
      
      if (error?.response?.data) {
        const responseData = error.response.data;
        
        // 处理FastAPI的HTTPException格式
        if (responseData.detail) {
          if (typeof responseData.detail === 'object') {
            // 处理我们自定义的详细错误格式
            errorMessage = responseData.detail.message || responseData.detail.error || 'Authentication failed';
            console.error('Detailed error info:', responseData.detail);
          } else if (typeof responseData.detail === 'string') {
            // 处理简单字符串错误
            errorMessage = responseData.detail;
          }
        } else if (responseData.message) {
          // 处理其他可能的错误格式
          errorMessage = responseData.message;
        }
      } else if (error.message) {
        // 处理非HTTP错误
        errorMessage = error.message;
      }
      
      // 检查是否是session相关错误
      if (errorMessage.includes('Invalid or expired session')) {
        console.log('Session expired, attempting auto-recovery...');
        localStorage.removeItem('oauth_session_id');
        throw new Error('OAuth session expired. Please try logging in again.');
      }
      
      // 检查是否是invalid_grant错误
      if (errorMessage.includes('invalid_grant')) {
        console.log('Authorization code invalid or expired');
        localStorage.removeItem('oauth_session_id');
        throw new Error('Authorization code has expired or been used. Please try logging in again.');
      }
      
      // 抛出包含详细信息的错误
      throw new Error(errorMessage);
    }
  }

  /**
   * 获取当前用户信息
   */
  async getCurrentUser(): Promise<User> {
    const response = await apiClient.get<ApiResponse<User>>(
      API_ENDPOINTS.AUTH.ME
    );
    
    return response.data ? response.data : response as unknown as User;
  }

  /**
   * 刷新访问令牌
   */
  async refreshToken(): Promise<string> {
    const response = await apiClient.post<ApiResponse<{ token: string }>>(
      API_ENDPOINTS.AUTH.REFRESH
    );
    
    return response.data ? response.data.token : (response as any).token;
  }

  /**
   * 登出
   */
  async logout(): Promise<void> {
    await apiClient.delete(API_ENDPOINTS.AUTH.LOGOUT);
  }

  /**
   * 检查token是否过期
   */
  isTokenExpired(token: string): boolean {
    try {
      const payload = JSON.parse(atob(token.split('.')[1]));
      const currentTime = Date.now() / 1000;
      return payload.exp < currentTime;
    } catch (error) {
      return true;
    }
  }

  /**
   * 解析JWT token获取用户信息
   */
  parseToken(token: string): any {
    try {
      return JSON.parse(atob(token.split('.')[1]));
    } catch (error) {
      return null;
    }
  }

  /**
   * 获取Google OAuth URL和session ID
   */
  async getGoogleAuthUrl(): Promise<{ authUrl: string; sessionId: string }> {
    const response = await apiClient.get<{ authorization_url: string; session_id: string }>(
      API_ENDPOINTS.AUTH.GOOGLE_AUTH_URL
    );
    
    return {
      authUrl: response.authorization_url,
      sessionId: response.session_id
    };
  }

  /**
   * 验证认证状态
   */
  async validateAuth(): Promise<boolean> {
    try {
      await this.getCurrentUser();
      return true;
    } catch (error) {
      return false;
    }
  }
}

export const authService = new AuthService();
export default authService;