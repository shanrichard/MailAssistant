/**
 * Application Routes
 * 应用路由配置
 */

import React, { Suspense } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ROUTES } from '../config';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { ProtectedRoute } from '../components/auth/ProtectedRoute';
import useAuthStore from '../stores/authStore';

// Lazy load components for better performance
const Dashboard = React.lazy(() => import('../pages/Dashboard'));
const EmailList = React.lazy(() => import('../pages/EmailList'));
const EmailDetail = React.lazy(() => import('../pages/EmailDetail'));
const DailyReport = React.lazy(() => import('../pages/DailyReport'));
const Chat = React.lazy(() => import('../pages/Chat'));
const Settings = React.lazy(() => import('../pages/Settings'));
const Preferences = React.lazy(() => import('../pages/Preferences'));
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
            {/* Dashboard - Home page */}
            <Route index element={<Dashboard />} />
            <Route path={ROUTES.DASHBOARD} element={<Dashboard />} />
            
            {/* Email management */}
            <Route path={ROUTES.EMAILS} element={<EmailList />} />
            <Route path={ROUTES.EMAIL_DETAIL} element={<EmailDetail />} />
            
            {/* Daily report */}
            <Route path={ROUTES.DAILY_REPORT} element={<DailyReport />} />
            
            {/* Chat interface */}
            <Route path={ROUTES.CHAT} element={<Chat />} />
            
            {/* Settings and preferences */}
            <Route path={ROUTES.SETTINGS} element={<Settings />} />
            <Route path={ROUTES.PREFERENCES} element={<Preferences />} />
          </Route>

          {/* Redirect root to daily report if authenticated */}
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