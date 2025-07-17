/**
 * Auth Callback Page
 * OAuth认证回调页面
 */

import React from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import useAuthStore from '../stores/authStore';
import { authService } from '../services/authService';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { ROUTES } from '../config';

const AuthCallback: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { login } = useAuthStore();
  const [error, setError] = React.useState<string | null>(null);
  const [isProcessing, setIsProcessing] = React.useState(false);
  const processedRef = React.useRef(false);

  React.useEffect(() => {
    const handleAuthCallback = async () => {
      // 使用ref确保只处理一次，即使在StrictMode下
      if (processedRef.current || isProcessing) return;
      processedRef.current = true;
      
      try {
        setIsProcessing(true);
        const error = searchParams.get('error');

        if (error) {
          setError(`Authentication failed: ${error}`);
          return;
        }

        // 获取完整的authorization_response URL
        const authorizationResponse = window.location.href;
        
        // 从localStorage获取session_id
        const sessionId = localStorage.getItem('oauth_session_id');
        
        if (!sessionId) {
          setError('No OAuth session found. Please try logging in again.');
          console.log('No session ID found in localStorage');
          // 清理localStorage并重定向到登录页
          localStorage.removeItem('oauth_session_id');
          navigate(ROUTES.LOGIN, { replace: true });
          return;
        }
        
        console.log('Processing OAuth callback with session:', sessionId);
        console.log('Authorization response URL:', authorizationResponse);
        console.log('Starting token exchange at:', new Date().toISOString());

        // Exchange authorization_response for token (不再使用重试机制)
        try {
          console.log('Calling authService.googleLogin...');
          const response = await authService.googleLogin(authorizationResponse, sessionId);
          console.log('authService.googleLogin response:', response);
          
          if (response) {
            console.log('Got response, logging in with token');
            // Login with token
            await login(response);
            
            // 清理session_id
            localStorage.removeItem('oauth_session_id');
            
            console.log('Login successful, redirecting to daily report');
            // Redirect to daily report page
            navigate(ROUTES.DAILY_REPORT, { replace: true });
          } else {
            console.error('No token in response');
            setError('No authentication token received');
          }
        } catch (loginError: any) {
          console.error('OAuth login failed:', loginError);
          
          // 提供更具体的错误信息
          let errorMessage = loginError.message || 'Authentication failed';
          
          if (errorMessage.includes('Invalid or expired session')) {
            errorMessage = 'Session expired. Please try logging in again.';
          } else if (errorMessage.includes('数据格式错误')) {
            errorMessage = 'Authentication data format error. This may be due to a session mismatch.';
          } else if (errorMessage.includes('invalid_grant') || 
                    errorMessage.includes('Authorization code') ||
                    errorMessage.includes('already been used')) {
            errorMessage = 'Authorization code has expired or been used. Please try logging in again.';
          }
          
          setError(errorMessage);
          // 不再自动重定向，让用户有时间看到错误信息
        }
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'Authentication failed';
        
        // 如果是session相关错误，清理localStorage
        if (errorMessage.includes('Invalid or expired session') || errorMessage.includes('session')) {
          localStorage.removeItem('oauth_session_id');
          setError('OAuth session expired or invalid. Please try logging in again.');
          console.log('Session error detected, clearing localStorage');
        } else {
          setError(errorMessage);
        }
      } finally {
        setIsProcessing(false);
      }
    };

    handleAuthCallback();
  }, [searchParams, login, navigate]); // 移除isProcessing避免重复调用

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="max-w-md w-full space-y-8">
          <div className="text-center">
            <h2 className="text-2xl font-bold text-gray-900">Authentication Error</h2>
            <p className="mt-2 text-red-600">{error}</p>
            <button
              onClick={() => navigate(ROUTES.LOGIN)}
              className="mt-4 inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
            >
              Try Again
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="max-w-md w-full space-y-8">
        <div className="text-center">
          <LoadingSpinner size="large" />
          <h2 className="mt-4 text-xl font-semibold text-gray-900">
            Authenticating...
          </h2>
          <p className="mt-2 text-gray-600">
            Please wait while we complete your login
          </p>
        </div>
      </div>
    </div>
  );
};

export default AuthCallback;