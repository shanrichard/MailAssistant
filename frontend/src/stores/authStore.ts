/**
 * Authentication Store
 * 认证状态管理
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { AuthState, User, AppError } from '../types';
import { APP_CONSTANTS } from '../config';
import { authService } from '../services/authService';

interface AuthStore extends AuthState {
  // Actions
  login: (token: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshToken: () => Promise<void>;
  updateUser: (user: Partial<User>) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: AppError | null) => void;
  checkAuth: () => Promise<void>;
  clearError: () => void;
}

const useAuthStore = create<AuthStore>()(
  persist(
    (set, get) => ({
      // Initial state
      user: null,
      isAuthenticated: false,
      token: null,
      isLoading: false,
      error: null,

      // Actions
      login: async (token: string) => {
        try {
          set({ isLoading: true, error: null });
          
          // 保存token
          set({ token });
          
          // 获取用户信息
          const user = await authService.getCurrentUser();
          
          set({
            user,
            isAuthenticated: true,
            isLoading: false,
            error: null,
          });
        } catch (error) {
          const appError: AppError = {
            code: 'AUTH_LOGIN_FAILED',
            message: error instanceof Error ? error.message : 'Login failed',
            timestamp: new Date(),
          };
          
          set({
            user: null,
            isAuthenticated: false,
            token: null,
            isLoading: false,
            error: appError,
          });
          
          throw error;
        }
      },

      logout: async () => {
        try {
          set({ isLoading: true });
          
          const { token } = get();
          if (token) {
            await authService.logout();
          }
          
          set({
            user: null,
            isAuthenticated: false,
            token: null,
            isLoading: false,
            error: null,
          });
        } catch (error) {
          // 即使登出失败，也清除本地状态
          set({
            user: null,
            isAuthenticated: false,
            token: null,
            isLoading: false,
            error: null,
          });
        }
      },

      refreshToken: async () => {
        try {
          const { token } = get();
          if (!token) {
            throw new Error('No token available');
          }
          
          const newToken = await authService.refreshToken();
          set({ token: newToken });
        } catch (error) {
          // Token刷新失败，清除认证状态
          set({
            user: null,
            isAuthenticated: false,
            token: null,
            error: {
              code: 'TOKEN_REFRESH_FAILED',
              message: 'Token refresh failed',
              timestamp: new Date(),
            },
          });
          throw error;
        }
      },

      updateUser: (userUpdate: Partial<User>) => {
        const { user } = get();
        if (user) {
          set({ user: { ...user, ...userUpdate } });
        }
      },

      setLoading: (loading: boolean) => {
        set({ isLoading: loading });
      },

      setError: (error: AppError | null) => {
        set({ error });
      },

      checkAuth: async () => {
        try {
          const { token } = get();
          if (!token) {
            return;
          }
          
          // 检查token是否过期
          if (authService.isTokenExpired(token)) {
            await get().refreshToken();
            return;
          }
          
          // 验证token有效性
          const user = await authService.getCurrentUser();
          set({
            user,
            isAuthenticated: true,
            error: null,
          });
        } catch (error) {
          // 认证检查失败，清除状态
          set({
            user: null,
            isAuthenticated: false,
            token: null,
            error: {
              code: 'AUTH_CHECK_FAILED',
              message: 'Authentication check failed',
              timestamp: new Date(),
            },
          });
        }
      },

      clearError: () => {
        set({ error: null });
      },
    }),
    {
      name: APP_CONSTANTS.STORAGE_KEYS.AUTH_TOKEN,
      partialize: (state) => ({
        token: state.token,
        user: state.user,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);

export default useAuthStore;