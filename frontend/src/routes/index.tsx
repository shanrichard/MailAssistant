/**
 * Application Routes
 * 应用路由配置 - 简化版
 */

import React, { Suspense } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ROUTES } from '../config';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { ProtectedRoute } from '../components/auth/ProtectedRoute';
import useAuthStore from '../stores/authStore';

// Lazy load components for better performance
const DailyReport = React.lazy(() => import('../pages/DailyReport'));
const Chat = React.lazy(() => import('../pages/Chat'));
const Settings = React.lazy(() => import('../pages/Settings'));
const Login = React.lazy(() => import('../pages/Login'));
const AuthCallback = React.lazy(() => import('../pages/AuthCallback'));
const NotFound = React.lazy(() => import('../pages/NotFound'));

// Layout components
const MainLayout = React.lazy(() => import('../components/layout/MainLayout'));
const AuthLayout = React.lazy(() => import('../components/layout/AuthLayout'));

const AppRoutes: React.FC = () => {
  const { isAuthenticated } = useAuthStore();

  return (
    <BrowserRouter>
      <Suspense fallback={<LoadingSpinner />}>
        <Routes>
          {/* Public routes */}
          <Route 
            path={ROUTES.LOGIN} 
            element={
              <AuthLayout>
                <Login />
              </AuthLayout>
            } 
          />
          
          <Route 
            path={ROUTES.CALLBACK} 
            element={
              <AuthLayout>
                <AuthCallback />
              </AuthLayout>
            } 
          />

          {/* Protected routes */}
          <Route 
            path="/" 
            element={
              <ProtectedRoute>
                <MainLayout />
              </ProtectedRoute>
            }
          >
            {/* Daily report - Default page after login */}
            <Route index element={<Navigate to={ROUTES.DAILY_REPORT} replace />} />
            <Route path={ROUTES.DAILY_REPORT} element={<DailyReport />} />
            
            {/* Chat interface */}
            <Route path={ROUTES.CHAT} element={<Chat />} />
            
            {/* Settings */}
            <Route path={ROUTES.SETTINGS} element={<Settings />} />
          </Route>

          {/* Redirect root based on auth status */}
          <Route 
            path={ROUTES.HOME} 
            element={
              isAuthenticated ? (
                <Navigate to={ROUTES.DAILY_REPORT} replace />
              ) : (
                <Navigate to={ROUTES.LOGIN} replace />
              )
            } 
          />

          {/* 404 - Not found */}
          <Route path={ROUTES.NOT_FOUND} element={<NotFound />} />
          <Route path="*" element={<Navigate to={ROUTES.NOT_FOUND} replace />} />
        </Routes>
      </Suspense>
    </BrowserRouter>
  );
};

export default AppRoutes;