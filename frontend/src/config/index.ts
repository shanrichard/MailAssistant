/**
 * MailAssistant Frontend Configuration
 * 应用配置管理
 */

import { AppConfig } from '../types';

// 环境变量配置
const getEnvVar = (name: string, defaultValue?: string): string => {
  const value = process.env[name];
  if (!value && !defaultValue) {
    throw new Error(`Environment variable ${name} is required`);
  }
  return value || defaultValue!;
};

// 应用配置
export const appConfig: AppConfig = {
  apiBaseUrl: getEnvVar('REACT_APP_API_URL', 'http://localhost:8000'),
  wsUrl: getEnvVar('REACT_APP_WS_URL', 'ws://localhost:8000'),
  googleClientId: getEnvVar('REACT_APP_GOOGLE_CLIENT_ID', ''),
  enableDebug: getEnvVar('REACT_APP_DEBUG', 'false') === 'true',
  defaultPageSize: parseInt(getEnvVar('REACT_APP_DEFAULT_PAGE_SIZE', '20')),
  maxRetries: parseInt(getEnvVar('REACT_APP_MAX_RETRIES', '3')),
  requestTimeout: parseInt(getEnvVar('REACT_APP_REQUEST_TIMEOUT', '10000')),
};

// API端点常量
export const API_ENDPOINTS = {
  // 认证相关
  AUTH: {
    GOOGLE: '/api/auth/google',
    GOOGLE_AUTH_URL: '/api/auth/google-auth-url',
    REFRESH: '/api/auth/refresh',
    LOGOUT: '/api/auth/logout',
    ME: '/api/auth/me',
  },
  
  // Gmail集成
  GMAIL: {
    EMAILS: '/api/gmail/emails',
    SYNC: '/api/gmail/sync',
    SEARCH: '/api/gmail/search',
    MARK_READ: '/api/gmail/mark-read',
    BULK_ACTION: '/api/gmail/bulk-action',
  },
  
  // Agent交互
  AGENTS: {
    EMAIL_PROCESSOR: '/api/agents/email-processor',
    CONVERSATION: '/api/agents/conversation',
    SESSION: '/api/agents/session',
  },
  
  // 任务和调度
  TASKS: {
    LOGS: '/api/tasks/logs',
    SCHEDULE: '/api/tasks/schedule',
    STATUS: '/api/tasks/status',
  },
  
  // 报告
  REPORTS: {
    DAILY: '/api/reports/daily',
    GENERATE: '/api/reports/generate',
    HISTORY: '/api/reports/history',
  },
  
  // 用户偏好
  PREFERENCES: {
    LIST: '/api/preferences',
    UPDATE: '/api/preferences/update',
    DELETE: '/api/preferences/delete',
  },
  
  // 健康检查
  HEALTH: '/health',
} as const;

// WebSocket事件常量
export const WS_EVENTS = {
  // 连接事件
  CONNECT: 'connect',
  DISCONNECT: 'disconnect',
  ERROR: 'error',
  
  // Agent事件
  AGENT_MESSAGE: 'agent_message',
  AGENT_RESPONSE: 'agent_response',
  AGENT_RESPONSE_CHUNK: 'agent_response_chunk',
  
  // 任务事件
  TASK_PROGRESS: 'task_progress',
  TASK_COMPLETED: 'task_completed',
  TASK_FAILED: 'task_failed',
  
  // 邮件事件
  EMAIL_SYNC_PROGRESS: 'email_sync_progress',
  DAILY_REPORT_READY: 'daily_report_ready',
  
  // 系统事件
  SYSTEM_STATUS: 'system_status',
  HEARTBEAT: 'heartbeat',
} as const;

// 应用常量
export const APP_CONSTANTS = {
  // 本地存储键
  STORAGE_KEYS: {
    AUTH_TOKEN: 'mailassistant_auth_token',
    USER_PREFERENCES: 'mailassistant_user_preferences',
    THEME: 'mailassistant_theme',
    SETTINGS: 'mailassistant_settings',
  },
  
  // 邮件分类
  EMAIL_CATEGORIES: {
    IMPORTANT: 'important',
    BUSINESS: 'business',
    PERSONAL: 'personal',
    NEWSLETTER: 'newsletter',
    PROMOTION: 'promotion',
    SPAM: 'spam',
    OTHER: 'other',
  },
  
  // 任务状态
  TASK_STATUS: {
    PENDING: 'pending',
    RUNNING: 'running',
    COMPLETED: 'completed',
    FAILED: 'failed',
  },
  
  // Agent类型
  AGENT_TYPES: {
    EMAIL_PROCESSOR: 'email_processor',
    CONVERSATION_HANDLER: 'conversation_handler',
  },
  
  // 分页配置
  PAGINATION: {
    DEFAULT_PAGE_SIZE: 20,
    MAX_PAGE_SIZE: 100,
    INFINITE_SCROLL_THRESHOLD: 5,
  },
  
  // 时间格式
  DATE_FORMATS: {
    SHORT: 'MM/dd/yyyy',
    MEDIUM: 'MMM dd, yyyy',
    LONG: 'MMMM dd, yyyy',
    WITH_TIME: 'MMM dd, yyyy HH:mm',
  },
  
  // 邮件操作
  EMAIL_ACTIONS: {
    MARK_READ: 'mark_read',
    MARK_UNREAD: 'mark_unread',
    STAR: 'star',
    UNSTAR: 'unstar',
    DELETE: 'delete',
    ARCHIVE: 'archive',
  },
  
  // 通知类型
  NOTIFICATION_TYPES: {
    SUCCESS: 'success',
    ERROR: 'error',
    WARNING: 'warning',
    INFO: 'info',
  },
  
  // 主题
  THEMES: {
    LIGHT: 'light',
    DARK: 'dark',
    SYSTEM: 'system',
  },
} as const;

// 默认设置
export const DEFAULT_SETTINGS = {
  dailyReportTime: '08:00',
  enableNotifications: true,
  emailSyncInterval: 300000, // 5分钟
  theme: APP_CONSTANTS.THEMES.SYSTEM,
  pageSize: APP_CONSTANTS.PAGINATION.DEFAULT_PAGE_SIZE,
  autoMarkRead: false,
  enableSounds: true,
  compactView: false,
} as const;

// 错误消息
export const ERROR_MESSAGES = {
  NETWORK_ERROR: '网络连接错误，请检查您的网络连接',
  AUTH_FAILED: '认证失败，请重新登录',
  TOKEN_EXPIRED: '登录已过期，请重新登录',
  PERMISSION_DENIED: '权限不足，无法执行此操作',
  SERVER_ERROR: '服务器内部错误，请稍后重试',
  INVALID_DATA: '数据格式错误，请检查输入',
  OPERATION_FAILED: '操作失败，请重试',
  WEBSOCKET_ERROR: '实时连接错误，正在重新连接...',
} as const;

// 成功消息
export const SUCCESS_MESSAGES = {
  EMAIL_MARKED_READ: '邮件已标记为已读',
  EMAIL_STARRED: '邮件已加星标',
  PREFERENCES_UPDATED: '偏好设置已更新',
  REPORT_GENERATED: '报告生成成功',
  SYNC_COMPLETED: '邮件同步完成',
  OPERATION_SUCCESS: '操作成功完成',
} as const;

// 验证规则
export const VALIDATION_RULES = {
  EMAIL: {
    REQUIRED: '邮箱地址是必填项',
    INVALID: '请输入有效的邮箱地址',
  },
  PASSWORD: {
    REQUIRED: '密码是必填项',
    MIN_LENGTH: '密码长度至少为8位',
    WEAK: '密码强度较弱，请使用字母、数字和特殊字符的组合',
  },
  PREFERENCE: {
    REQUIRED: '偏好描述是必填项',
    MIN_LENGTH: '偏好描述至少需要10个字符',
    MAX_LENGTH: '偏好描述不能超过500个字符',
  },
} as const;

// 路由路径
export const ROUTES = {
  HOME: '/',
  DASHBOARD: '/',
  DAILY_REPORT: '/report',
  CHAT: '/chat',
  SETTINGS: '/settings',
  PREFERENCES: '/preferences',
  LOGIN: '/login',
  CALLBACK: '/auth/callback',
  NOT_FOUND: '/404',
} as const;

// 导出类型安全的配置
export type ApiEndpoints = typeof API_ENDPOINTS;
export type WsEvents = typeof WS_EVENTS;
export type AppConstants = typeof APP_CONSTANTS;
export type Routes = typeof ROUTES;