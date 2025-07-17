/**
 * OAuth重试机制
 * 处理session过期和自动恢复
 */

import { authService } from '../services/authService';

export interface OAuthRetryResult {
  success: boolean;
  token?: string;
  error?: string;
  needsNewLogin?: boolean;
}

export class OAuthRetryHandler {
  private static MAX_RETRIES = 2;
  
  /**
   * 带重试机制的OAuth登录
   */
  static async loginWithRetry(
    authorizationResponse: string, 
    sessionId: string
  ): Promise<OAuthRetryResult> {
    // Authorization code只能使用一次，不应该重试
    // 只尝试一次
    try {
      console.log(`OAuth login attempt with session: ${sessionId}`);
      console.log(`Authorization response: ${authorizationResponse.substring(0, 100)}...`);
      
      const token = await authService.googleLogin(authorizationResponse, sessionId);
      
      return {
        success: true,
        token
      };
      
    } catch (error: any) {
      const errorMsg = error.message || 'Unknown error';
      console.error('OAuth login failed:', errorMsg);
      
      // 检查是否是invalid_grant错误
      if (errorMsg.includes('invalid_grant') || 
          errorMsg.includes('Authorization code') ||
          errorMsg.includes('already been used')) {
        console.error('Authorization code has been used or expired');
        return {
          success: false,
          error: 'Authorization code has expired or been used. Please try logging in again.',
          needsNewLogin: true
        };
      }
      
      // 检查是否是session相关错误
      if (errorMsg.includes('Invalid or expired session') || 
          errorMsg.includes('session expired')) {
        console.error('OAuth session expired');
        // 清理无效的session
        localStorage.removeItem('oauth_session_id');
        return {
          success: false,
          error: 'OAuth session expired. Please try logging in again.',
          needsNewLogin: true
        };
      }
      
      // 其他错误
      return {
        success: false,
        error: errorMsg,
        needsNewLogin: false
      };
    }
  }
  
  /**
   * 检查session是否有效
   */
  static async validateSession(sessionId: string): Promise<boolean> {
    try {
      // 使用一个测试URL来验证session
      const testUrl = 'http://localhost:3000/auth/callback?test=true';
      
      await authService.googleLogin(testUrl, sessionId);
      
      // 如果到达这里，说明session有效（即使会因为其他原因失败）
      return true;
      
    } catch (error: any) {
      const errorMsg = error.message || '';
      
      // 如果是session相关错误，说明session无效
      if (errorMsg.includes('Invalid or expired session')) {
        return false;
      }
      
      // 其他错误（如insecure_transport）说明session是有效的
      return true;
    }
  }
  
  /**
   * 清理无效的session
   */
  static cleanupInvalidSession() {
    console.log('Cleaning up invalid session from localStorage');
    localStorage.removeItem('oauth_session_id');
  }
  
  /**
   * 获取或创建有效的session
   */
  static async getOrCreateValidSession(): Promise<{ sessionId: string; authUrl: string }> {
    // 清理任何无效的session
    const existingSessionId = localStorage.getItem('oauth_session_id');
    if (existingSessionId) {
      console.log('Found existing session in localStorage:', existingSessionId);
    }
    
    // 总是调用后端获取OAuth URL
    // 后端会自动处理session复用逻辑
    console.log('Getting OAuth URL from backend (may reuse existing session)');
    const { authUrl, sessionId } = await authService.getGoogleAuthUrl();
    
    // 检查是否复用了现有session
    if (existingSessionId === sessionId) {
      console.log('✅ Backend reused existing session:', sessionId);
    } else {
      console.log('✅ Backend created new session:', sessionId);
      // 更新localStorage
      localStorage.setItem('oauth_session_id', sessionId);
    }
    
    return { sessionId, authUrl };
  }
}

export default OAuthRetryHandler;