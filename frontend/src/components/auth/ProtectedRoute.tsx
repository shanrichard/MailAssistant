/**
 * Protected Route Component
 * 受保护的路由组件
 */

import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import useAuthStore from '../../stores/authStore';
import { LoadingSpinner } from '../common/LoadingSpinner';
import { ROUTES } from '../../config';

interface ProtectedRouteProps {
  children: React.ReactNode;
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children }) => {
  const { isAuthenticated, isLoading, checkAuth } = useAuthStore();
  const location = useLocation();

  // Check auth status on mount
  React.useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  // Show loading while checking auth
  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <LoadingSpinner size="large" />
      </div>
    );
  }

  // Redirect to login if not authenticated
  if (!isAuthenticated) {
    return (
      <Navigate 
        to={ROUTES.LOGIN} 
        state={{ from: location }} 
        replace 
      />
    );
  }

  return <>{children}</>;
};