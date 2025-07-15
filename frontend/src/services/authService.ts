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
  async googleLogin(authCode: string): Promise<string> {
    const response = await apiClient.post<ApiResponse<{ token: string }>>(
      API_ENDPOINTS.AUTH.GOOGLE,
      { code: authCode }
    );
    
    return response.data.token;
  }

  /**
   * 获取当前用户信息
   */
  async getCurrentUser(): Promise<User> {
    const response = await apiClient.get<ApiResponse<User>>(
      API_ENDPOINTS.AUTH.ME
    );
    
    return response.data;
  }

  /**
   * 刷新访问令牌
   */
  async refreshToken(): Promise<string> {
    const response = await apiClient.post<ApiResponse<{ token: string }>>(
      API_ENDPOINTS.AUTH.REFRESH
    );
    
    return response.data.token;
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
   * 生成Google OAuth URL
   */
  getGoogleAuthUrl(): string {
    const baseUrl = 'https://accounts.google.com/o/oauth2/v2/auth';
    const params = new URLSearchParams({
      client_id: process.env.REACT_APP_GOOGLE_CLIENT_ID || '',
      redirect_uri: `${window.location.origin}/auth/callback`,
      response_type: 'code',
      scope: [
        'openid',
        'email',
        'profile',
        'https://www.googleapis.com/auth/gmail.modify',
        'https://www.googleapis.com/auth/gmail.readonly',
      ].join(' '),
      access_type: 'offline',
      prompt: 'consent',
    });

    return `${baseUrl}?${params.toString()}`;
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