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

  React.useEffect(() => {
    const handleAuthCallback = async () => {
      try {
        const code = searchParams.get('code');
        const error = searchParams.get('error');

        if (error) {
          setError(`Authentication failed: ${error}`);
          return;
        }

        if (!code) {
          setError('No authorization code received');
          return;
        }

        // Exchange code for token
        const token = await authService.googleLogin(code);
        
        // Login with token
        await login(token);
        
        // Redirect to dashboard
        navigate(ROUTES.DASHBOARD, { replace: true });
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'Authentication failed';
        setError(errorMessage);
      }
    };

    handleAuthCallback();
  }, [searchParams, login, navigate]);

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